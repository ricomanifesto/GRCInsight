"""Replay article analysis without report generation or publication."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import median
import time
from typing import Any

import httpx

from core.article_selection import (
    analyze_selected,
    local_overrides,
    selected_article_mask,
    workflow_selected,
)
from core.entities import analyze_article_grc_content
from core.relevance_corpus import SPLITS, CorpusCase, CorpusValidation
from models.api import ArticleInput
from services.model_service import GRCModelService
from services.relevance_decisions import ENDPOINT, LABELS, MAX_BATCH_ARTICLES, RelevanceClient
from services.relevance_selection import (
    ACCEPTED_RELEVANT,
    INTERNAL_ERROR,
    KEPT_UNDECIDED,
    LEGACY_FULL,
    SELECTION_POLICY,
    SelectionRecord,
    article_key,
    candidate_fingerprint,
)


def classification_metrics(expected: list[str], predicted: list[str | None]) -> dict[str, Any]:
    """Include unavailable predictions in denominators instead of inflating recall."""
    if (
        len(expected) != len(predicted)
        or not expected
        or any(label not in LABELS for label in expected)
    ):
        raise ValueError("Expected and predicted labels must describe the same nonempty cases")
    relevant = sum(label == "relevant" for label in expected)
    irrelevant = sum(label == "irrelevant" for label in expected)
    return {
        "accuracy": sum(wanted == actual for wanted, actual in zip(expected, predicted))
        / len(expected),
        "relevant_recall": (
            sum(wanted == actual == "relevant" for wanted, actual in zip(expected, predicted))
            / relevant
            if relevant
            else None
        ),
        "false_positive_rate": (
            sum(
                wanted == "irrelevant" and actual == "relevant"
                for wanted, actual in zip(expected, predicted)
            )
            / irrelevant
            if irrelevant
            else None
        ),
        "missing_predictions": predicted.count(None),
        "predicted_insufficient_evidence": predicted.count("insufficient_evidence"),
    }


def _latencies(values: list[float]) -> dict[str, float]:
    return {
        "p50_seconds": median(values),
        "p95_seconds": sorted(values)[math.ceil(len(values) * 0.95) - 1],
    }


async def run_comparison(
    articles: list[ArticleInput],
    expected: list[str],
    model_factory: Callable[[], GRCModelService],
    *,
    repeats: int = 3,
) -> dict[str, Any]:
    """Measure the actual enabled policy, including any subset fallback."""
    if not 1 <= repeats <= 10 or len(articles) != len(expected):
        raise ValueError("Use one label per article and 1-10 repeats")
    classification_metrics(expected, [None] * len(expected))
    local_started = time.perf_counter()
    local = [
        bool(analyze_article_grc_content(article.model_dump()).get("has_grc_content"))
        for article in articles
    ]
    local_elapsed = time.perf_counter() - local_started
    predictions: dict[str, list[str | None]] = {"legacy": [], "enabled": []}
    decision_predictions: list[str | None] = []
    times: dict[str, list[float]] = {"legacy": [], "enabled": []}
    runs = []
    diagnostics = []
    for repeat in range(repeats):
        # Alternate paired order. Expected labels never enter either request.
        order = ["legacy", "enabled"] if repeat % 2 == 0 else ["enabled", "legacy"]
        run: dict[str, Any] = {"order": order}
        for path in order:
            # Each path is an independent workflow. Never share its cumulative
            # model deadline with another baseline, candidate or repetition.
            model = model_factory()
            if model.relevance_mode != "enabled" or model.relevance_client is None:
                raise ValueError("Benchmark requires an enabled relevance service")
            started = time.perf_counter()
            analysis = (
                await model._analyze_articles_with_model(articles)
                if path == "legacy"
                else await model.analyze_articles_for_grc(articles)
            )
            elapsed = time.perf_counter() - started
            times[path].append(elapsed)
            selected = selected_article_mask(articles, analysis)
            predicted: list[str | None] = (
                [
                    "relevant" if chosen or signal else "irrelevant"
                    for chosen, signal in zip(selected, local)
                ]
                if "error" not in analysis
                else [None] * len(articles)
            )
            predictions[path].extend(predicted)
            run[path] = {"elapsed_seconds": elapsed, "predictions": predicted}
            if path == "enabled":
                diagnostic = dict(model.last_relevance_diagnostics or {})
                diagnostics.append(diagnostic)
                run["decisions"] = diagnostic
                raw_decisions = model.last_relevance_result
                raw_predictions: list[str | None] = (
                    [item.label for item in raw_decisions.decisions]
                    if raw_decisions is not None
                    else [None] * len(articles)
                )
                decision_predictions.extend(raw_predictions)
                run["decision_predictions"] = raw_predictions
        runs.append(run)
    labels = expected * repeats
    costs = [item.get("cost") for item in diagnostics]
    fallback_sizes = [item.get("uncertain_count", len(articles)) for item in diagnostics]
    return {
        "cases": len(articles),
        "repeats": repeats,
        "runs": runs,
        "local_entities": {
            "elapsed_seconds": local_elapsed,
            **classification_metrics(
                expected, ["relevant" if value else "irrelevant" for value in local]
            ),
        },
        **{
            path: {
                **_latencies(times[path]),
                **classification_metrics(labels, predictions[path]),
                # The prose client does not expose billed usage.
                "cost": None,
            }
            for path in predictions
        },
        "decisions": {
            **classification_metrics(labels, decision_predictions),
            "statuses": dict(Counter(item.get("status", "unavailable") for item in diagnostics)),
            "fallback_batch_rate": sum(size > 0 for size in fallback_sizes) / repeats,
            "fallback_article_rate": sum(fallback_sizes) / (repeats * len(articles)),
            "models": sorted({name for item in diagnostics for name in item.get("models", [])}),
            "input_tokens_from_completed_batches": sum(
                item.get("input_tokens", 0) for item in diagnostics
            ),
            "output_tokens_from_completed_batches": sum(
                item.get("output_tokens", 0) for item in diagnostics
            ),
            "cost": sum(costs) if all(cost is not None for cost in costs) else None,
        },
        "limits": [
            "Measured article-analysis calls, not whole reports, Lambda latency or page loads.",
            "Paired order alternates with a fresh service and workflow budget for each path.",
            "Small replay samples do not establish production p95.",
            "Decisions statistics describe the same enabled calls, not a separate inference run.",
            "Effective selections include local entities; workflow risk overrides are not measured.",
            "Legacy and total enabled cost are unavailable from the client, not zero.",
            "Failed multi-batch calls may incur cost not included in completed-call usage.",
            "Quality depends on independent review of expected labels and representative inputs.",
        ],
    }


# Offline replay of recorded decision responses -----------------------------------

RECORDING_SCHEMA = "grc-relevance-recording-v1"
RECORDING_FIELDS = frozenset(
    {"schema", "request_sha256", "model", "captured_at", "status_code", "body"}
)
GATE_SPEC_SCHEMA = "grc-relevance-gate-spec-v1"
SUMMARY_SCHEMA = "grc-relevance-replay-summary-v1"
SELECTIONS = ("model_selected", "workflow_selected", "analyze_selected")
REFERENCES = ("relevant", "irrelevant", "insufficient_evidence")
STRATA = ("local_negative", "local_positive")
WILSON_Z = 1.959963984540054
# Replay never authenticates anywhere; this value only satisfies the client.
REPLAY_KEY = "offline-replay"
SHA256_HEX = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class Recording:
    """One captured decision response, bound to the exact request bytes."""

    request_sha256: str
    model: str
    captured_at: str
    status_code: int
    body: str


def request_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def recording_line(
    raw_request: bytes, *, body: str, model: str, captured_at: str, status_code: int = 200
) -> dict[str, Any]:
    """Format a capture with the raw body only: no headers, keys or article text."""
    return {
        "schema": RECORDING_SCHEMA,
        "request_sha256": request_sha256(raw_request),
        "model": model,
        "captured_at": captured_at,
        "status_code": status_code,
        "body": body,
    }


def load_recordings(lines: Iterable[str]) -> dict[str, Recording]:
    recordings: dict[str, Recording] = {}
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except ValueError as error:
            raise ValueError(f"recording line {number}: invalid JSON") from error
        if (
            not isinstance(raw, dict)
            or set(raw) != RECORDING_FIELDS
            or raw["schema"] != RECORDING_SCHEMA
            or not isinstance(raw["request_sha256"], str)
            or not SHA256_HEX.fullmatch(raw["request_sha256"])
            or not isinstance(raw["model"], str)
            or not isinstance(raw["captured_at"], str)
            or type(raw["status_code"]) is not int
            or not isinstance(raw["body"], str)
        ):
            raise ValueError(f"recording line {number}: expected {sorted(RECORDING_FIELDS)}")
        if raw["request_sha256"] in recordings:
            raise ValueError(f"recording line {number}: duplicate request_sha256")
        recordings[raw["request_sha256"]] = Recording(
            raw["request_sha256"], raw["model"], raw["captured_at"], raw["status_code"], raw["body"]
        )
    return recordings


class RecordedResponses:
    """Serve recorded bodies by request hash; nothing reaches the network."""

    def __init__(self, recordings: dict[str, Recording]) -> None:
        self.recordings = recordings
        self.requests: list[bytes] = []
        self.missing: list[str] = []
        self.served: list[Recording] = []
        self.transport = httpx.MockTransport(self._respond)

    def _respond(self, request: httpx.Request) -> httpx.Response:
        if request.method != "POST" or str(request.url) != ENDPOINT:
            raise RuntimeError("Replay received an unexpected request")
        raw = request.content
        self.requests.append(raw)
        recording = self.recordings.get(request_sha256(raw))
        if recording is None:
            self.missing.append(request_sha256(raw))
            return httpx.Response(404)
        self.served.append(recording)
        return httpx.Response(recording.status_code, content=recording.body.encode("utf-8"))


class _ReplayService(GRCModelService):
    """The real enabled route with recorded decisions and no generative calls."""

    def __init__(self, relevance_client: RelevanceClient, threshold: float) -> None:
        # Deliberately skip the provider client: replay has no generative path.
        self.relevance_mode = "enabled"
        self.relevance_min_probability = threshold
        self.relevance_client = relevance_client
        self.last_relevance_diagnostics = None
        self.last_relevance_result = None
        self.last_selection_records = None
        self._batch_size = 0

    async def replay(self, articles: list[ArticleInput]) -> dict[str, Any]:
        self._batch_size = len(articles)
        return await self.analyze_articles_for_grc(articles)

    async def _analyze_articles_with_model(self, articles: list[ArticleInput]) -> dict[str, Any]:
        if len(articles) == self._batch_size:
            # A full legacy decision cannot be replayed: its selections stay unknown.
            return {"error": "generative analysis is not replayed"}
        # Aggregate enrichment does not affect selection under keep-uncertain-v1.
        return {"grc_articles": [], "summary": {}, "analysis": {}}


def wilson_interval(successes: int, total: int, z: float = WILSON_Z) -> list[float] | None:
    if total == 0:
        return None
    rate = successes / total
    denominator = 1 + z * z / total
    centre = (rate + z * z / (2 * total)) / denominator
    half = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, centre - half), min(1.0, centre + half)]


def _rate(successes: int, total: int) -> dict[str, Any]:
    return {
        "successes": successes,
        "total": total,
        "value": successes / total if total else None,
        "wilson95": wilson_interval(successes, total),
    }


def _confusion(rows: list[dict[str, Any]], selection: str) -> dict[str, Any]:
    """Unknown selections stay in every denominator and never count as hits."""
    counts: dict[str, Any] = {}
    for reference in REFERENCES:
        values = [row[selection] for row in rows if row["reference_label"] == reference]
        counts[reference] = {
            "total": len(values),
            "selected": values.count(True),
            "not_selected": values.count(False),
            "unknown": values.count(None),
        }
    relevant, irrelevant = counts["relevant"], counts["irrelevant"]
    counts["recall"] = _rate(relevant["selected"], relevant["total"])
    counts["false_positive_rate"] = _rate(irrelevant["selected"], irrelevant["total"])
    counts["precision_benefit"] = _rate(irrelevant["not_selected"], irrelevant["total"])
    return counts


def _metrics(rows: list[dict[str, Any]], weights: dict[str, Any] | None) -> dict[str, Any]:
    strata = {
        stratum: {
            "cases": sum(row["stratum"] == stratum for row in rows),
            **{
                selection: _confusion([row for row in rows if row["stratum"] == stratum], selection)
                for selection in ("model_selected", "workflow_selected")
            },
        }
        for stratum in STRATA
    }
    weighted = None
    if weights and all(isinstance(weights.get(name), (int, float)) for name in STRATA):
        recalls = [strata[name]["workflow_selected"]["recall"]["value"] for name in STRATA]
        if all(value is not None for value in recalls):
            weighted = sum(weights[name] * value for name, value in zip(STRATA, recalls))
    return {
        "cases": len(rows),
        "review_status": dict(Counter(row["review_status"] for row in rows)),
        "reference": dict(Counter(row["reference_label"] or "none" for row in rows)),
        "raw_labels": {
            reference: dict(
                Counter(
                    row["label"] or "missing" for row in rows if row["reference_label"] == reference
                )
            )
            for reference in REFERENCES
        },
        "selections": {selection: _confusion(rows, selection) for selection in SELECTIONS},
        "strata": strata,
        "stratum_weighted_workflow_recall": weighted,
    }


def _invariant_failures(
    batch: list[CorpusCase], records: tuple[SelectionRecord, ...] | None
) -> list[str]:
    if records is None:
        return ["missing selection records"]
    failures = []
    if [record.index for record in records] != list(range(len(batch))):
        failures.append("records are not total and ordered")
    for record in records:
        if record.disposition in KEPT_UNDECIDED and record.model_selected is False:
            failures.append(f"position {record.index}: kept disposition was dropped")
        if record.disposition == ACCEPTED_RELEVANT and record.model_selected is False:
            failures.append(f"position {record.index}: accepted relevant was dropped")
        if record.model_selected is None and record.workflow_selected is False:
            failures.append(f"position {record.index}: unknown selection became a drop")
    return failures


def _unrecorded(case: CorpusCase) -> dict[str, Any]:
    """A case the route left without a record stays in every denominator as unknown."""
    entity, risk = local_overrides(case.article)
    return {
        "article_key": article_key(case.article.url),
        "route": None,
        "disposition": None,
        "reason": "missing_record",
        "label": None,
        "probabilities": None,
        "confidence": None,
        "model_selected": None,
        "entity_override": entity,
        "risk_override": risk,
        "workflow_selected": workflow_selected(entity=entity, risk=risk, model=None),
        "analyze_selected": analyze_selected(entity=entity, model=None),
    }


def _usage_missing(recording: Recording) -> bool:
    try:
        usage = json.loads(recording.body).get("usage")
        return not isinstance(usage, dict) or usage.get("cost") is None
    except (ValueError, AttributeError):
        return True


def _verdict(passed: bool, enough: bool) -> str:
    if not enough:
        return "insufficient_evidence"
    return "pass" if passed else "fail"


def evaluate_gates(
    rows: list[dict[str, Any]], batches: list[dict[str, Any]], spec: dict[str, Any]
) -> dict[str, Any]:
    """Return a verdict per gate; the overall verdict stays remain_off unless all pass."""
    gates = spec["gates"]
    eligible = [row for row in rows if row["gate_eligible"]]
    relevant = [row for row in eligible if row["reference_label"] == "relevant"]
    results: dict[str, Any] = {}

    g1 = gates["G1"]
    critical = [row for row in relevant if row["critical"]]
    misses = sum(row["workflow_selected"] is not True for row in critical)
    results["G1"] = {
        "cases": len(critical),
        "misses": misses,
        "rule_of_three_upper": 3 / len(critical) if critical else None,
        "verdict": (
            "fail"
            if misses > g1["max_misses"]
            else _verdict(True, len(critical) >= g1["min_cases"])
        ),
    }
    for name, population in (
        ("G2", [row for row in relevant if row["stratum"] == "local_negative"]),
        ("G3", relevant),
    ):
        gate = gates[name]
        hits = sum(row["workflow_selected"] is True for row in population)
        rate = _rate(hits, len(population))
        lower = rate["wilson95"][0] if rate["wilson95"] else None
        results[name] = {
            **rate,
            "verdict": _verdict(
                lower is not None and lower >= gate["min_lower_bound"],
                len(population) >= gate["min_cases"],
            ),
        }
    irrelevant_stratum = [
        row
        for row in eligible
        if row["reference_label"] == "irrelevant" and row["stratum"] == "local_negative"
    ]
    results["G4"] = {
        **_rate(
            sum(row["workflow_selected"] is False for row in irrelevant_stratum),
            len(irrelevant_stratum),
        ),
        "verdict": "reported",
    }
    invariant_failures = sum(len(batch["invariant_failures"]) for batch in batches)
    results["G5"] = {
        "failures": invariant_failures,
        "verdict": _verdict(invariant_failures == 0, bool(batches)),
    }
    g8 = gates["G8"]
    errors = sum(
        batch["route"] == LEGACY_FULL
        and (batch["reason"] or "").startswith(("jev_", INTERNAL_ERROR))
        for batch in batches
    )
    recordings_missing = sum(batch["missing_recordings"] > 0 for batch in batches)
    results["G8"] = {
        "batches": len(batches),
        "jev_error_batches": errors,
        "batches_missing_recordings": recordings_missing,
        "verdict": (
            "fail"
            if invariant_failures
            else _verdict(
                errors <= g8["max_jev_error_rate"] * len(batches),
                len(batches) >= g8["min_batches"] and not recordings_missing,
            )
        ),
    }
    requests = sum(batch["requests"] for batch in batches)
    missing_usage = sum(batch["missing_usage"] for batch in batches)
    results["G10"] = {
        "requests": requests,
        "missing_usage": missing_usage,
        "verdict": _verdict(
            missing_usage <= gates["G10"]["max_missing_rate"] * requests, requests > 0
        ),
    }
    for name in ("G6", "G7", "G9", "G11"):
        results[name] = {"source": gates[name]["source"], "verdict": "not_evaluated"}
    passed = all(item["verdict"] in ("pass", "reported") for item in results.values())
    return {
        "spec_status": spec["status"],
        "gates": dict(sorted(results.items(), key=lambda item: int(item[0][1:]))),
        "overall": "all_gates_passed" if passed else "remain_off",
    }


def load_gate_spec(path: Path) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(spec, dict)
        or spec.get("schema") != GATE_SPEC_SCHEMA
        or not isinstance(spec.get("gates"), dict)
        or {f"G{number}" for number in range(1, 12)} - set(spec["gates"])
    ):
        raise ValueError("Gate spec must define G1-G11 in the expected schema")
    return spec


def _check_holdout(
    validation: CorpusValidation,
    spec: dict[str, Any] | None,
    thresholds: Sequence[float],
    fingerprint: str,
    batch_size: int,
) -> None:
    if spec is None or spec.get("status") != "accepted":
        raise ValueError("Holdout replay refused: it needs an accepted gate spec")
    if list(thresholds) != [spec.get("threshold")]:
        raise ValueError("Holdout replay refused: only the frozen threshold may run")
    if batch_size != spec.get("batch_size"):
        raise ValueError("Holdout replay refused: batch size differs from the spec")
    if fingerprint != spec.get("candidate_fingerprint"):
        raise ValueError("Holdout replay refused: candidate fingerprint differs from the spec")
    if validation.holdout_sha256 is None or validation.holdout_sha256 != spec.get("holdout_sha256"):
        raise ValueError("Holdout replay refused: holdout hash differs from the spec")


async def replay_corpus(
    validation: CorpusValidation,
    responses: RecordedResponses,
    *,
    split: str,
    thresholds: Sequence[float],
    focus_areas: Sequence[str],
    generative_model: str,
    decision_timeout: float,
    batch_size: int = MAX_BATCH_ARTICLES,
    gate_spec: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Replay one split through the enabled route; return per-article rows and a summary."""
    if validation.errors:
        raise ValueError("Corpus is invalid; fix its errors before replay")
    if split not in SPLITS:
        raise ValueError(f"Split must be one of {SPLITS}")
    if not thresholds or any(not 0.5 <= value <= 1 for value in thresholds):
        raise ValueError("Thresholds must be between 0.5 and 1")
    if not 1 <= batch_size <= 64:
        raise ValueError("Batch size must be between 1 and 64")

    def fingerprint(threshold: float) -> str:
        return candidate_fingerprint(
            threshold,
            focus_areas,
            batch_size=batch_size,
            generative_model=generative_model,
            decision_timeout=decision_timeout,
        )

    if split == "holdout":
        _check_holdout(validation, gate_spec, thresholds, fingerprint(thresholds[0]), batch_size)
    cases = [case for case in validation.cases if case.split == split]
    if not cases:
        raise ValueError(f"No {split} cases to replay")
    weights = (gate_spec or {}).get("stratum_weights")
    rows: list[dict[str, Any]] = []
    results = []
    for threshold in thresholds:
        threshold_rows: list[dict[str, Any]] = []
        batches = []
        for start in range(0, len(cases), batch_size):
            batch = cases[start : start + batch_size]
            requests_before = len(responses.requests)
            missing_before = len(responses.missing)
            served_before = len(responses.served)
            client = RelevanceClient(
                api_key=REPLAY_KEY,
                timeout=10.0,
                focus_areas=tuple(focus_areas),
                transport=responses.transport,
            )
            service = _ReplayService(client, threshold)
            await service.replay([case.article for case in batch])
            records = service.last_selection_records
            diagnostics = service.last_relevance_diagnostics or {}
            batch_number = start // batch_size
            batches.append(
                {
                    "batch": batch_number,
                    "cases": len(batch),
                    "route": diagnostics.get("route"),
                    "reason": diagnostics.get("reason"),
                    "fallback_status": diagnostics.get("fallback_status"),
                    "requests": len(responses.requests) - requests_before,
                    "missing_recordings": len(responses.missing) - missing_before,
                    # An unrecorded request has no cost receipt either.
                    "missing_usage": len(responses.missing)
                    - missing_before
                    + sum(_usage_missing(item) for item in responses.served[served_before:]),
                    "cost": diagnostics.get("cost"),
                    "invariant_failures": _invariant_failures(batch, records),
                }
            )
            by_position = {record.index: record for record in records or ()}
            for position, case in enumerate(batch):
                record = by_position.get(position)
                fields = (
                    {key: value for key, value in record.as_dict().items() if key != "index"}
                    if record is not None
                    else _unrecorded(case)
                )
                threshold_rows.append(
                    {
                        "case_id": case.case_id,
                        "split": case.split,
                        "threshold": threshold,
                        "batch": batch_number,
                        "position": position,
                        **fields,
                        "stratum": (
                            "local_positive"
                            if fields["entity_override"] or fields["risk_override"]
                            else "local_negative"
                        ),
                        "reference_label": case.reference_label,
                        "review_status": case.review_status,
                        "gate_eligible": case.gate_eligible,
                        "critical": case.critical,
                        "categories": list(case.categories),
                    }
                )
        costs = [batch["cost"] for batch in batches]
        missing_usage = sum(batch["missing_usage"] for batch in batches)
        results.append(
            {
                "threshold": threshold,
                "candidate_fingerprint": fingerprint(threshold),
                "batches": batches,
                "route_mix": {
                    "dispositions": dict(Counter(row["disposition"] for row in threshold_rows)),
                    "routes": dict(Counter(batch["route"] for batch in batches)),
                    "legacy_full_reasons": dict(
                        Counter(batch["reason"] for batch in batches if batch["reason"])
                    ),
                    "fallback_status": dict(Counter(batch["fallback_status"] for batch in batches)),
                },
                "requests": {
                    "replayed": sum(batch["requests"] for batch in batches),
                    "missing_recordings": sum(batch["missing_recordings"] for batch in batches),
                    "missing_usage": missing_usage,
                    # Missing receipts make the total unknown, never zero.
                    "cost": (
                        sum(costs)
                        if not missing_usage and all(cost is not None for cost in costs)
                        else None
                    ),
                },
                "all_cases": _metrics(threshold_rows, weights),
                "gate_eligible": _metrics(
                    [row for row in threshold_rows if row["gate_eligible"]], weights
                ),
                "gates": (
                    evaluate_gates(threshold_rows, batches, gate_spec) if gate_spec else None
                ),
            }
        )
        rows.extend(threshold_rows)
    summary = {
        "schema": SUMMARY_SCHEMA,
        "split": split,
        "verdict_scope": ("frozen holdout" if split == "holdout" else "development, informational"),
        "selection_policy": SELECTION_POLICY,
        "batch_size": batch_size,
        "corpus": validation.summary(),
        "network_calls": 0,
        "results": results,
        "limits": [
            "Replays recorded decision bodies; generative analysis is stubbed, not measured.",
            "A legacy_full batch has unknown selections: no generative output is replayed.",
            "Batches follow corpus order within the split; recordings bind to exact requests.",
            "Provisional and disputed cases appear in all_cases only, never in gates.",
            "Latency, deployment and rollback gates are outside this replay.",
        ],
    }
    return rows, summary
