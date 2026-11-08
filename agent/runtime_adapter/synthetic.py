"""Synthetic external boundaries for the Runtime MVP worker.

The real ``run_grc_analysis_endpoint`` runs unchanged. Only its external seams are
replaced for one attempt: the module-level RSS service's ``fetch_feed`` and
``enrich_articles`` and the ``GRCModelService`` class, the same seams the existing
workflow tests patch. Every invocation is recorded durably before it does any
work, so at-least-once execution is observable. While installed, real HTTP clients
in the service modules refuse construction.

The model boundary has three behaviours:

- ``plan``: return an analysis and a report plan that the real
  ``parse_report_plan``/``render_report_plan`` accept (model-mode report);
- ``unavailable``: construct the real ``GRCModelService``, which raises its own
  ``ValueError`` without an OpenRouter key (the real fallback path);
- ``plan`` with a routing alias as ``resolved_model``, which the real workflow
  converts into a fallback report.

Fixtures are synthetic JSON documents on RFC 2606 reserved hosts; their bytes are
part of the frozen submission identity.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
import threading
from typing import Any, Callable, Iterator

import httpx

from runtime_adapter import contract

FIXTURE_SCHEMA = "grcinsight.synthetic-fixture.v1"
MAX_FIXTURE_BYTES = 64 * 1024
MAX_FIXTURE_ENTRIES = 30
MAX_DELAY_SECONDS = 120
MODEL_MODES = ("plan", "unavailable")
SYNTHETIC_FEED_ERROR = "synthetic feed boundary unavailable"
GUARDED_MODULES = (
    "services.rss_service",
    "services.openrouter_client",
    "services.regulatory_sources",
    "services.relevance_decisions",
)

# Module attributes are process-global; one attempt installs boundaries at a time.
_INSTALL_LOCK = threading.Lock()


class FixtureError(ValueError):
    """The synthetic fixture is missing, changed, oversized or not synthetic."""


class EgressRefused(RuntimeError):
    """A real network client was constructed inside the synthetic boundary."""


def fixture_path(fixture_dir: str | Path, fixture_id: str) -> Path:
    if not contract.FIXTURE_ID.fullmatch(fixture_id or ""):
        raise FixtureError("fixture id is malformed")
    return Path(fixture_dir) / f"{fixture_id}.json"


def fixture_sha256(fixture_dir: str | Path, fixture_id: str) -> str:
    return contract.sha256_hex(_read_bounded(fixture_path(fixture_dir, fixture_id)))


def _read_bounded(path: Path) -> bytes:
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_FIXTURE_BYTES + 1)
    except OSError as error:
        raise FixtureError("fixture is unreadable") from error
    if len(data) > MAX_FIXTURE_BYTES:
        raise FixtureError("fixture exceeds the size bound")
    return data


def _synthetic_url(value: Any, field: str) -> str:
    if not isinstance(value, str) or not contract.reserved_synthetic_host(value):
        raise FixtureError(f"{field} must use a reserved synthetic host")
    return value


def _bounded_int(value: Any, field: str, maximum: int) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise FixtureError(f"{field} must be an integer from 0 to {maximum}")
    return value


def load_fixture(fixture_dir: str | Path, fixture_id: str, expected_sha256: str) -> dict[str, Any]:
    data = _read_bounded(fixture_path(fixture_dir, fixture_id))
    if contract.sha256_hex(data) != expected_sha256:
        raise FixtureError("fixture does not match its frozen digest")
    try:
        fixture = json.loads(data)
    except ValueError as error:
        raise FixtureError("fixture is not JSON") from error
    if not isinstance(fixture, dict) or fixture.get("schema") != FIXTURE_SCHEMA:
        raise FixtureError("fixture schema is not supported")
    feed = fixture.get("feed")
    if not isinstance(feed, dict) or not isinstance(feed.get("entries"), list):
        raise FixtureError("fixture feed is malformed")
    _synthetic_url(feed.get("link"), "feed.link")
    if len(feed["entries"]) > MAX_FIXTURE_ENTRIES:
        raise FixtureError("fixture has too many entries")
    for entry in feed["entries"]:
        if not isinstance(entry, dict):
            raise FixtureError("fixture entry is malformed")
        if entry.get("link"):
            _synthetic_url(entry["link"], "entry.link")
    behaviour = fixture.get("feed_behaviour", {})
    if not isinstance(behaviour, dict):
        raise FixtureError("feed_behaviour is malformed")
    _bounded_int(
        behaviour.get("transient_failures", 0), "transient_failures", contract.MAX_ATTEMPTS_LIMIT
    )
    if not isinstance(behaviour.get("permanent_failure", False), bool):
        raise FixtureError("permanent_failure must be a boolean")
    model = fixture.get("model")
    if not isinstance(model, dict) or model.get("mode") not in MODEL_MODES:
        raise FixtureError("model mode is not a synthetic behaviour")
    _bounded_int(model.get("delay_seconds", 0), "model.delay_seconds", MAX_DELAY_SECONDS)
    if model["mode"] == "plan":
        if not isinstance(model.get("plan"), dict):
            raise FixtureError("plan mode requires a plan object")
        if not isinstance(model.get("resolved_model"), str):
            raise FixtureError("plan mode requires a resolved model identity")
    return fixture


class _RefusingHttpx:
    """Stands in for ``httpx`` inside service modules while boundaries are installed."""

    def __getattr__(self, name: str) -> Any:
        return getattr(httpx, name)

    @staticmethod
    def AsyncClient(*args: Any, **kwargs: Any) -> Any:  # noqa: N802 - mirrors httpx
        raise EgressRefused("network egress refused inside the synthetic boundary")

    @staticmethod
    def Client(*args: Any, **kwargs: Any) -> Any:  # noqa: N802 - mirrors httpx
        raise EgressRefused("network egress refused inside the synthetic boundary")


def _feed_document(feed: dict[str, Any]) -> dict[str, Any]:
    entries = [
        {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "description": entry.get("description", ""),
            "published": entry.get("published", ""),
            "source": "Unknown Source",
            "content": entry.get("content", ""),
        }
        for entry in feed["entries"]
    ]
    return {
        "title": feed.get("title", "Unknown Feed"),
        "description": feed.get("description", ""),
        "link": feed.get("link", ""),
        "last_updated": feed.get("last_updated", ""),
        "entry_count": len(entries),
        "entries": entries,
    }


@contextmanager
def install_boundaries(
    fixture: dict[str, Any], *, attempt: int, record: Callable[[str], None]
) -> Iterator[None]:
    """Install this fixture's boundaries for one attempt, then restore the originals."""
    import importlib

    from core import workflow as workflow_mod
    from core.report_plan import ReportQualityError, parse_report_plan, render_report_plan
    from services.model_service import GRCModelService, GRCReportGeneration

    feed = fixture["feed"]
    behaviour = fixture.get("feed_behaviour", {})
    model = fixture["model"]
    delay = model.get("delay_seconds", 0)

    async def fetch_feed(feed_url: str) -> dict[str, Any]:
        record("feed")
        if behaviour.get("permanent_failure") or attempt <= behaviour.get("transient_failures", 0):
            return {"error": SYNTHETIC_FEED_ERROR, "entries": []}
        return _feed_document(feed)

    async def enrich_articles(articles):
        record("enrichment")
        return articles

    class SyntheticPlanModelService:
        def __init__(self, model_name=None, max_tokens=None, model_deadline=None):
            record("model_init")

        async def analyze_articles_for_grc(self, articles):
            record("model_analysis")
            if delay:
                await asyncio.sleep(delay)
            return {
                "grc_articles": [{"title": item.title, "url": item.url} for item in articles],
                "summary": {
                    "total_articles": len(articles),
                    "grc_relevant_count": len(articles),
                    "confidence_score": 0.9,
                },
                "analysis": {
                    "regulations_mentioned": [],
                    "frameworks_referenced": [],
                    "industries_affected": [],
                    "regulatory_bodies": [],
                    "risk_categories": [],
                },
            }

        async def generate_grc_report(self, analysis_data, feed_info):
            record("model_report")
            sources = analysis_data.get("source_evidence", [])
            try:
                plan = parse_report_plan(json.dumps(model["plan"]), sources)
                content = render_report_plan(plan, sources)
            except ValueError as error:
                return GRCReportGeneration(
                    content=f"# GRC Intelligence Report - Error\n\nUnable to generate report: {error}",
                    resolved_model="",
                    failure_reason=str(error) if isinstance(error, ReportQualityError) else None,
                )
            return GRCReportGeneration(
                content=content, resolved_model=model["resolved_model"], report_plan=plan
            )

    class CountingRealModelService(GRCModelService):
        """The real class: without a configured key its constructor raises ValueError."""

        def __init__(self, *args, **kwargs):
            record("model_init")
            super().__init__(*args, **kwargs)

    model_class = SyntheticPlanModelService if model["mode"] == "plan" else CountingRealModelService
    guarded = [importlib.import_module(name) for name in GUARDED_MODULES]

    with _INSTALL_LOCK:
        originals = (
            workflow_mod.rss_service.fetch_feed,
            workflow_mod.rss_service.enrich_articles,
            workflow_mod.GRCModelService,
        )
        had_instance_attrs = {
            name: name in vars(workflow_mod.rss_service)
            for name in ("fetch_feed", "enrich_articles")
        }
        # Seam patching replaces attributes with synthetic stand-ins of other types.
        setattr(workflow_mod.rss_service, "fetch_feed", fetch_feed)
        setattr(workflow_mod.rss_service, "enrich_articles", enrich_articles)
        setattr(workflow_mod, "GRCModelService", model_class)
        for module in guarded:
            setattr(module, "httpx", _RefusingHttpx())
        try:
            yield
        finally:
            for module in guarded:
                setattr(module, "httpx", httpx)
            setattr(workflow_mod, "GRCModelService", originals[2])
            for name, original in zip(("fetch_feed", "enrich_articles"), originals[:2]):
                if had_instance_attrs[name]:
                    setattr(workflow_mod.rss_service, name, original)
                else:
                    delattr(workflow_mod.rss_service, name)
