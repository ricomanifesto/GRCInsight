"""Provider-owned document dates, independent of generated prose."""

import asyncio
from copy import deepcopy
import json
from pathlib import Path
import runpy
import time

import httpx
import pytest

from core.report_evidence import validate_regulatory_evidence

ROOT = Path(__file__).resolve().parents[2]
URL = "https://www.federalregister.gov/documents/2026/10/05/2026-20374/reporting-rule"
API_URL = "https://www.federalregister.gov/api/v1/documents/2026-20374.json"
DOCUMENT = {
    "document_number": "2026-20374",
    "html_url": URL,
    "type": "Rule",
    "effective_on": "2026-11-04",
}
SOURCE = {
    "title": "Final reporting rule",
    "url": URL,
    "snippet": "The United States final reporting rule updates reporting requirements.",
    "effective_date_evidence": {
        "provider": "federal-register-api-v1",
        "api_url": API_URL,
        "retrieved_at": "2026-10-05T22:00:00Z",
        "document": DOCUMENT,
    },
}


def report(value="2026-11-04"):
    return f"""## Executive Summary
Review the cited rule.

## Sourced Regulatory Changes
| Change | Jurisdiction | Document effective date | Source | Evidence excerpt |
|---|---|---|---|---|
| final reporting rule | United States | {value} | [Final reporting rule]({URL}) | {SOURCE['snippet']} |

## Inferred Control and Governance Implications
Inference: review controls.

## Industry Impact Analysis
Review applicability.

## Risk Assessment
Review controls.

## Recommendations for Action
Check applicability.

## Source Highlights
- [Final reporting rule]({URL})
"""


def test_document_date_is_selected_from_retained_provider_field_not_prose():
    changes = validate_regulatory_evidence(report(), [SOURCE])
    assert changes[0].document_effective_date == "2026-11-04"
    for claimed in ("2026-10-05", "2027-01-01", "Unknown"):
        with pytest.raises(ValueError, match="effective date"):
            validate_regulatory_evidence(report(claimed), [SOURCE])


@pytest.mark.parametrize(
    "mutation",
    [
        {"provider": "model"},
        {"api_url": "https://evil.example/api"},
        {"retrieved_at": "yesterday"},
        {"retrieved_at": "2026-10-05T22:00:00"},
        {"document": {**DOCUMENT, "document_number": "2026-20375"}},
        {"document": {**DOCUMENT, "html_url": URL.replace("20374", "20375")}},
        {"document": {**DOCUMENT, "type": "Proposed Rule"}},
        {"document": {**DOCUMENT, "effective_on": "2026-02-30"}},
        {"document": {**DOCUMENT, "effective_on": "20261104"}},
        {"document": {**DOCUMENT, "effective_on": None}},
        {"document": "not an object"},
    ],
)
def test_invalid_or_mismatched_attestation_is_rejected(mutation):
    source = deepcopy(SOURCE)
    assert isinstance(source["effective_date_evidence"], dict)
    source["effective_date_evidence"].update(mutation)
    with pytest.raises(ValueError, match="effective date"):
        validate_regulatory_evidence(report(), [source])


def install_http(monkeypatch, handler):
    from services import regulatory_sources

    real_client = httpx.AsyncClient

    def client(**kwargs):
        assert kwargs["follow_redirects"] is False
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(regulatory_sources.httpx, "AsyncClient", client)
    return regulatory_sources.enrich_regulatory_sources


def test_ingestion_fetches_fixed_endpoint_and_does_not_trust_supplied_attestation(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url).split("?")[0] == API_URL
        assert set(request.url.params.get_list("fields[]")) == set(DOCUMENT)
        return httpx.Response(200, json=DOCUMENT)

    enrich = install_http(monkeypatch, handler)
    original = {**SOURCE, "effective_date_evidence": {"provider": "forged"}}
    sources = asyncio.run(enrich([original, {**original, "url": "https://news.example/a"}]))
    assert len(calls) == 1
    assert original["effective_date_evidence"] == {"provider": "forged"}
    evidence = sources[0]["effective_date_evidence"]
    assert evidence["document"] == DOCUMENT
    assert evidence["api_url"] == API_URL
    assert evidence["retrieved_at"]
    assert sources[1]["effective_date_evidence"] is None
    assert (
        validate_regulatory_evidence(report(), sources)[0].document_effective_date == "2026-11-04"
    )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503),
        httpx.Response(302, headers={"location": "https://evil.example/"}),
        httpx.Response(200, text="not JSON"),
        httpx.Response(200, json={**DOCUMENT, "effective_on": None}),
        httpx.Response(200, json={**DOCUMENT, "document_number": "2026-99999"}),
        httpx.Response(200, json={**DOCUMENT, "type": "Proposed Rule"}),
    ],
)
def test_unavailable_or_unusable_provider_record_leaves_date_unknown(monkeypatch, response):
    enrich = install_http(monkeypatch, lambda request: response)
    sources = asyncio.run(enrich([SOURCE]))
    assert sources[0]["effective_date_evidence"] is None
    assert (
        validate_regulatory_evidence(report("Unknown"), sources)[0].document_effective_date is None
    )


def test_expired_deadline_and_unsupported_urls_never_make_requests(monkeypatch):
    def handler(request):
        raise AssertionError("unexpected provider request")

    enrich = install_http(monkeypatch, handler)
    expired = asyncio.run(enrich([SOURCE], model_deadline=time.monotonic() - 1))
    assert expired[0]["effective_date_evidence"] is None
    for url in [
        "https://federalregister.gov.evil.example/documents/2026/10/05/2026-20374/a",
        "http://www.federalregister.gov/documents/2026/10/05/2026-20374/a",
        "https://www.federalregister.gov:444/documents/2026/10/05/2026-20374/a",
    ]:
        sources = asyncio.run(enrich([{**SOURCE, "url": url}]))
        assert sources[0]["effective_date_evidence"] is None
    sources = asyncio.run(enrich([{**SOURCE, "url": "https://news.example/"}]))
    assert sources[0]["effective_date_evidence"] is None


def test_provider_timeout_preserves_reportable_sources(monkeypatch):
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=DOCUMENT)

    enrich = install_http(monkeypatch, handler)
    sources = asyncio.run(enrich([SOURCE], model_deadline=time.monotonic() + 0.02))
    assert sources[0]["url"] == URL
    assert sources[0]["effective_date_evidence"] is None


def test_date_provenance_survives_workflow_prompt_composer_and_manifest(monkeypatch):
    from core import workflow
    from models.api import GRCAnalysisConfig
    from services.model_service import GRCModelService
    from services.openrouter_client import OpenRouterGeneration

    install_http(monkeypatch, lambda request: httpx.Response(200, json=DOCUMENT))

    async def feed(_url):
        return {
            "title": "SentryDigest",
            "link": "https://digest.example/",
            "last_updated": "Mon, 05 Oct 2026 21:00:00 GMT",
            "entries": [{"title": SOURCE["title"], "link": URL, "content": SOURCE["snippet"]}],
        }

    async def enrich(articles):
        return articles

    service = GRCModelService.__new__(GRCModelService)
    prompts = []

    async def analysis(articles):
        return {"summary": {"grc_relevant_count": 1, "total_articles": 1}, "analysis": {}}

    plan = {
        "regulatory_changes": [
            {
                "source_id": 1,
                "change": "final reporting rule",
                "jurisdiction": "United States",
                "evidence_excerpt": SOURCE["snippet"],
            }
        ],
        "control_implications": [
            {"control_id": "governance", "priority": "medium", "source_ids": [1]}
        ],
        "industry_impacts": [],
    }

    async def invoke(**kwargs):
        prompts.append(kwargs["user_prompt"])
        return OpenRouterGeneration(text=json.dumps(plan), resolved_model="example/model")

    service.analyze_articles_for_grc = analysis
    service._invoke = invoke
    monkeypatch.setattr(workflow.rss_service, "fetch_feed", feed)
    monkeypatch.setattr(workflow.rss_service, "enrich_articles", enrich)
    monkeypatch.setattr(workflow, "GRCModelService", lambda **kwargs: service)
    response = asyncio.run(
        workflow.run_grc_analysis_endpoint(
            "https://digest.example/feed.xml", GRCAnalysisConfig(model="openrouter/example/model")
        )
    )
    assert response.status == "completed"
    assert response.metadata is not None
    assert response.metadata.analysis_mode == "model"
    assert "Document effective date: 2026-11-04" in prompts[0]
    assert API_URL in prompts[0]
    record = response.metadata.source_articles[0]["effective_date_evidence"]
    assert record["document"] == DOCUMENT
    assert response.metadata.report_plan == plan
    data = response.model_dump(mode="json")
    stored_body = data.pop("report")
    data.update({key: stored_body[key] for key in ("title", "content", "generated_at")})
    composer = runpy.run_path(str(ROOT / "scripts/compose_site_report.py"))
    checker = runpy.run_path(str(ROOT / "scripts/check_site_report.py"))
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    markdown = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    manifest = composer["evidence_manifest"](data, composer["source_articles"](data["metadata"]))
    assert manifest["sources"][0]["effective_date_evidence"] == record
    assert manifest["report_plan"] == plan
    assert manifest["report_contract_version"] == 3
    checker["validate_evidence_manifest"](
        markdown, builder["report_fields"](markdown), json.dumps(manifest)
    )
    manifest["sources"][0]["effective_date_evidence"]["document"]["effective_on"] = "2026-12-01"
    with pytest.raises(SystemExit, match="effective date"):
        checker["validate_evidence_manifest"](
            markdown, builder["report_fields"](markdown), json.dumps(manifest)
        )
