import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import runpy

import pytest

from api.routes import analysis as analysis_route
from core import workflow
from models.api import ArticleInput, GRCAnalysisConfig
from services.model_service import GRCModelService, GRCReportGeneration
from services.openrouter_client import OpenRouterGeneration
from services.rss_service import RSSService
from test_report_workflow_contract import complete_report_body
from test_routes import request
from test_workflow_fallback import StaticFeedAsyncClient

ROOT = Path(__file__).resolve().parents[2]
MARKERS = (
    "[Virtual Event]",
    "[vIrTuAl eVeNt]",
    "[ \tVirtual\n Event \n]",
    "&#91;Virtual&#32;Event&#93;",
    "&lbrack;Virtual&nbsp;Event&rbrack;",
    "&amp;#91;Virtual&amp;nbsp;Event&amp;#93;",
    r"\[Virtual Event\]",
    r"&#92;[Virtual Event&#92;]",
    "[<strong>Virtual</strong><br>Event]",
    r"\\[Virtual Event\\]",
    "\\[Virtual\\\nEvent\\]",
    "[**Virtual** Event]",
    r"\[**Virtual** Event\]",
    "[Virtual _Event_]",
)


def article(**changes):
    fields = {
        "title": "Security controls after incident response events",
        "url": "https://example.com/security",
        "content": "NIST guidance for security teams attending virtual events.",
        "published": datetime(2026, 9, 8, tzinfo=timezone.utc),
    }
    return ArticleInput.model_validate(fields | changes)


def feed_entries(articles):
    return {
        "title": "SentryDigest",
        "link": "https://digest.example/",
        "last_updated": "Tue, 08 Sep 2026 01:00:00 GMT",
        "entries": [
            {
                "title": item.title,
                "link": item.url,
                "description": item.summary,
                "content": item.content,
            }
            for item in articles
        ],
    }


@pytest.mark.parametrize("marker", MARKERS)
@pytest.mark.parametrize("field", ["title", "summary", "content"])
def test_workflow_excludes_entire_record_before_enrichment_and_fallback(monkeypatch, marker, field):
    clean = article()
    promotion = article(url="https://example.com/promotion", **{field: f"{marker} Promotion"})

    async def fetch(_url):
        return feed_entries([promotion, clean])

    enriched_inputs = []

    async def enrich(articles):
        enriched_inputs.extend(articles)
        return articles

    class UnavailableModel:
        def __init__(self, **_kwargs):
            raise ValueError("Model unavailable")

    monkeypatch.setattr(workflow.rss_service, "fetch_feed", fetch)
    monkeypatch.setattr(workflow.rss_service, "enrich_articles", enrich)
    monkeypatch.setattr(workflow, "GRCModelService", UnavailableModel)
    result = asyncio.run(
        workflow.run_grc_analysis_endpoint("https://digest.example/feed.xml", GRCAnalysisConfig())
    )
    assert [item.url for item in enriched_inputs] == [clean.url]
    assert result.status == "completed"
    assert result.metadata is not None and result.report is not None
    assert result.metadata.article_count == 1
    assert result.metadata.grc_article_count == 1
    assert result.metadata.analysis_mode == "fallback"
    assert [item.url for item in result.articles or []] == [clean.url]
    assert [item["url"] for item in result.metadata.source_articles] == [clean.url]
    assert "promotion" not in result.report.content.lower()


def test_workflow_all_excluded_stops_before_enrichment_or_model(monkeypatch):
    async def fetch(_url):
        return feed_entries([article(title="[Virtual Event] Promotion")])

    async def unexpected(*_args):
        raise AssertionError("excluded records reached enrichment")

    monkeypatch.setattr(workflow.rss_service, "fetch_feed", fetch)
    monkeypatch.setattr(workflow.rss_service, "enrich_articles", unexpected)
    result = asyncio.run(
        workflow.run_grc_analysis_endpoint("https://digest.example/feed.xml", GRCAnalysisConfig())
    )
    assert result.status == "failed"
    assert result.error is not None and result.error.code == "NO_LINKED_ARTICLES"
    assert result.report is None


@pytest.mark.parametrize("model_output", [False, True])
def test_workflow_rechecks_enrichment_and_rejects_contaminated_model_report(
    monkeypatch, model_output
):
    clean = article()
    changed = article(url="https://example.com/enriched")

    async def fetch(_url):
        return feed_entries([clean, changed])

    async def enrich(articles):
        articles[1].content = "[Virtual Event] Revealed by enrichment"
        return articles

    class Model:
        def __init__(self, **_kwargs):
            pass

        async def analyze_articles_for_grc(self, articles):
            assert [item.url for item in articles] == [clean.url]
            return {"summary": {"grc_relevant_count": 1}, "analysis": {}}

        async def generate_grc_report(self, analysis, _feed):
            assert [item["url"] for item in analysis["source_evidence"]] == [clean.url]
            assert [item["link"] for item in _feed["entries"]] == [clean.url]
            assert _feed["entry_count"] == 1
            return GRCReportGeneration(
                content=complete_report_body(
                    r"\[Virtual Event\] Promotion" if model_output else "Security analysis.",
                    f"- [{clean.title}]({clean.url})",
                ),
                resolved_model="provider/test-model",
            )

    monkeypatch.setattr(workflow.rss_service, "fetch_feed", fetch)
    monkeypatch.setattr(workflow.rss_service, "enrich_articles", enrich)
    monkeypatch.setattr(workflow, "GRCModelService", Model)
    result = asyncio.run(
        workflow.run_grc_analysis_endpoint("https://digest.example/feed.xml", GRCAnalysisConfig())
    )
    assert result.status == "completed"
    assert result.metadata is not None and result.report is not None
    assert result.metadata.article_count == 1
    assert result.metadata.analysis_mode == ("fallback" if model_output else "model")
    assert "Virtual Event" not in result.report.content
    if model_output:
        assert result.metadata.fallback_reason == "excluded virtual-event promotion"
        assert result.metadata.resolved_model == ""


@pytest.mark.parametrize("marker", MARKERS)
@pytest.mark.parametrize("field", ["title", "description", "content:encoded"])
def test_rss_parser_excludes_tagged_records(monkeypatch, marker, field):
    body = f"<{field}>{escape(marker)} Promotion</{field}>"
    if field != "title":
        body += "<title>Promotion</title>"
    StaticFeedAsyncClient.response_text = (
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">'
        "<channel><title>News</title><link>https://example.com/</link><description>News</description>"
        f"<item>{body}<link>https://example.com/promotion</link></item>"
        "<item><title>Security event monitoring</title><link>https://example.com/security</link></item>"
        "</channel></rss>"
    )
    monkeypatch.setattr("services.rss_service.httpx.AsyncClient", StaticFeedAsyncClient)
    result = asyncio.run(RSSService().fetch_feed("https://example.com/feed.xml"))
    assert result["entry_count"] == 1
    assert [item["link"] for item in result["entries"]] == ["https://example.com/security"]


def test_enrichment_excludes_before_fetch_and_before_content_truncation(monkeypatch):
    calls = []

    class Client(StaticFeedAsyncClient):
        response_text = "Security information. " * 300 + "[Virtual Event] Promotion"

        async def get(self, _url, timeout=None):
            calls.append(_url)
            return await super().get(_url, timeout)

    monkeypatch.setattr("services.rss_service.httpx.AsyncClient", Client)
    clean = article()
    result = asyncio.run(
        RSSService().enrich_articles(
            [
                article(title=r"\[Virtual Event\] Promotion", content=""),
                article(url="https://example.com/revealed", content=""),
                clean,
            ]
        )
    )
    assert calls == ["https://example.com/revealed"]
    assert result == [clean]


@pytest.mark.parametrize("all_excluded", [False, True])
def test_direct_model_analysis_filters_before_invocation(monkeypatch, all_excluded):
    service = GRCModelService.__new__(GRCModelService)
    prompts = []

    async def invoke(**kwargs):
        prompts.append(kwargs["user_prompt"])
        return OpenRouterGeneration(text="Security analysis.", resolved_model="provider/test")

    monkeypatch.setattr(service, "_invoke", invoke)
    articles = [article(title=r"\[Virtual Event\] Promotion")]
    if not all_excluded:
        articles.append(article())
    result = asyncio.run(service.analyze_articles_for_grc(articles))
    assert result["summary"]["total_articles"] == (0 if all_excluded else 1)
    assert len(result["grc_articles"]) == (0 if all_excluded else 1)
    assert len(prompts) == (0 if all_excluded else 1)
    assert all("Promotion" not in prompt for prompt in prompts)


def test_direct_api_excludes_records_from_model_and_local_results(monkeypatch):
    seen = []

    class Model:
        def __init__(self, **_kwargs):
            pass

        async def analyze_articles_for_grc(self, articles):
            seen.extend(articles)
            return {
                "summary": {"total_articles": len(articles), "grc_relevant_count": len(articles)},
                "analysis": {},
            }

    monkeypatch.setattr(analysis_route, "GRCModelService", Model)
    clean = article()
    response = request(
        "POST",
        "/api/v1/analyze",
        json={
            "articles": [
                article(summary="&#91;Virtual Event&#93; Promotion").model_dump(mode="json"),
                clean.model_dump(mode="json"),
            ]
        },
    )
    data = response.json()
    assert data["status"] == "success"
    assert seen == [clean]
    assert data["summary"]["total_articles"] == 1
    assert [item["article_url"] for item in data["results"]] == [clean.url]


@pytest.mark.parametrize("all_excluded", [False, True])
def test_direct_api_with_no_eligible_articles_skips_model_initialization(monkeypatch, all_excluded):
    initialized = []

    class UnavailableModel:
        def __init__(self, **_kwargs):
            initialized.append(True)
            raise ValueError("Model unavailable")

    monkeypatch.setattr(analysis_route, "GRCModelService", UnavailableModel)
    articles = (
        [
            article(title=r"\[Virtual Event\] Promotion").model_dump(mode="json"),
            article(summary="&#91;Virtual Event&#93; Promotion").model_dump(mode="json"),
        ]
        if all_excluded
        else []
    )
    response = request("POST", "/api/v1/analyze", json={"articles": articles})
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "results": [],
        "summary": {
            "total_articles": 0,
            "grc_articles": 0,
            "top_regulations": [],
            "top_frameworks": [],
            "affected_industries": [],
        },
        "error": None,
    }
    assert initialized == []


@pytest.mark.parametrize("marker", MARKERS)
def test_final_model_report_rejects_visible_markers(monkeypatch, marker):
    service = GRCModelService.__new__(GRCModelService)

    async def invoke(**_kwargs):
        return OpenRouterGeneration(
            text=complete_report_body(
                "Security analysis.", f"- [{marker} Promotion](https://example.com/promotion)"
            ),
            resolved_model="provider/test",
        )

    monkeypatch.setattr(service, "_invoke", invoke)
    result = asyncio.run(service.generate_grc_report({}, {}))
    assert result.content.startswith("# GRC Intelligence Report - Error")
    assert result.resolved_model == ""


def test_direct_model_report_refuses_contaminated_evidence_before_invocation(monkeypatch):
    service = GRCModelService.__new__(GRCModelService)
    calls = []

    async def invoke(**kwargs):
        calls.append(kwargs)
        return OpenRouterGeneration(
            text=complete_report_body("Analysis.", "- [Evidence](https://example.com/)"),
            resolved_model="provider/test",
        )

    monkeypatch.setattr(service, "_invoke", invoke)
    result = asyncio.run(
        service.generate_grc_report(
            {
                "source_evidence": [
                    {"title": "[Virtual Event] Promotion", "url": "https://example.com/"}
                ]
            },
            {},
        )
    )
    assert not calls
    assert result.resolved_model == ""


def stored_report():
    return {
        "status": "completed",
        "title": "GRC Intelligence Report",
        "generated_at": "2026-09-08T01:00:00Z",
        "content": complete_report_body(
            "Security analysis.", "- [Evidence](https://example.com/evidence)"
        ),
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-09-08",
            "source_issue_url": "https://digest.example/archive/2026-09-08/",
            "source_articles": [{"title": "Evidence", "url": "https://example.com/evidence"}],
            "analysis_period": "September 2026",
            "article_count": 2,
            "grc_article_count": 1,
            "requested_model": "openrouter/example/model",
            "resolved_model": "provider/test",
        },
    }


@pytest.mark.parametrize("marker", MARKERS)
@pytest.mark.parametrize("location", ["content", "source"])
def test_composer_rejects_contamination_without_rewriting_original(marker, location):
    composer = runpy.run_path(str(ROOT / "scripts/compose_site_report.py"))
    data = stored_report()
    if location == "content":
        data["content"] += f"\n{marker} Promotion"
    else:
        data["metadata"]["source_articles"].append(
            {"title": f"{marker} Promotion", "url": "https://example.com/promotion"}
        )
    original = deepcopy(data)
    with pytest.raises(SystemExit, match="excluded virtual-event promotion"):
        composer["compose_report"](data, "https://example.com/feed.xml", "openrouter/example/model")
    assert data == original


@pytest.mark.parametrize("marker", MARKERS)
def test_public_validator_rejects_escaped_and_linked_markers(marker):
    checker = runpy.run_path(str(ROOT / "scripts/check_site_report.py"))
    body = complete_report_body(
        "Security analysis.", f"- [{marker} Promotion](https://example.com/promotion)"
    )
    assert (
        checker["find_public_report_integrity_failure"](body) == "excluded virtual-event promotion"
    )


def test_public_validator_rejects_unused_contaminated_manifest_source():
    composer = runpy.run_path(str(ROOT / "scripts/compose_site_report.py"))
    checker = runpy.run_path(str(ROOT / "scripts/check_site_report.py"))
    data = stored_report()
    report = composer["compose_report"](
        data, "https://example.com/feed.xml", "openrouter/example/model"
    )
    sources = composer["source_articles"](data["metadata"])
    manifest = composer["evidence_manifest"](data, sources)
    manifest["sources"].append(
        {
            "title": r"\[Virtual Event\] Unused promotion",
            "url": "https://example.com/promotion",
            "cves": [],
        }
    )
    with pytest.raises(SystemExit, match="excluded virtual-event promotion"):
        checker["validate_evidence_manifest"](
            report, checker["report_metadata"](report), json.dumps(manifest)
        )


def test_generic_events_remain_valid_and_unresolved_reference_guard_stays_strict():
    checker = runpy.run_path(str(ROOT / "scripts/check_site_report.py"))
    body = complete_report_body(
        "Incident response events and virtual events require security controls.",
        "- [Security event monitoring](https://example.com/security)",
    )
    assert checker["find_public_report_integrity_failure"](body) is None
    assert checker["find_reader_surface_defect"](body) is None
    assert "unresolved bracketed reference" in checker["find_reader_surface_defect"](
        body + "\n[Unresolved reference]"
    )


@pytest.mark.parametrize("atom", [False, True])
def test_rss_record_filter_keeps_feed_identity_and_html_sanitization(monkeypatch, atom):
    marker = "&lbrack;Virtual&nbsp;Event&rbrack; Promotion"
    if atom:
        xml = (
            '<feed xmlns="http://www.w3.org/2005/Atom"><title>News</title>'
            '<link href="https://digest.example/"/><updated>2026-09-08T01:00:00Z</updated>'
            f'<entry><title>Promotion</title><content type="html"><![CDATA[{marker}]]></content></entry>'
            '<entry><title>Security events</title><link href="https://example.com/security"/>'
            '<content type="html"><![CDATA[<p>Security controls.</p><script>alert(1)</script>]]></content></entry></feed>'
        )
    else:
        xml = (
            '<rss version="2.0"><channel><title>News</title><link>https://digest.example/</link>'
            "<lastBuildDate>Tue, 08 Sep 2026 01:00:00 GMT</lastBuildDate>"
            f"<item><title>Promotion</title><description><![CDATA[{marker}]]></description></item>"
            "<item><title>Security events</title><link>https://example.com/security</link>"
            "<description><![CDATA[<p>Security controls.</p><script>alert(1)</script>]]></description></item></channel></rss>"
        )
    monkeypatch.setattr(StaticFeedAsyncClient, "response_text", xml)
    monkeypatch.setattr("services.rss_service.httpx.AsyncClient", StaticFeedAsyncClient)
    result = asyncio.run(RSSService().fetch_feed("https://digest.example/feed.xml"))
    assert result["entry_count"] == 1
    assert result["link"] == "https://digest.example/"
    assert workflow._sentrydigest_issue_date(result) == "2026-09-08"
    assert result["entries"][0]["link"] == "https://example.com/security"
    assert "<script>" not in result["entries"][0]["content"]
    assert "Security controls." in result["entries"][0]["content"]


def test_model_analysis_rejects_tagged_output_without_echoing_it(monkeypatch):
    service = GRCModelService.__new__(GRCModelService)

    async def invoke(**_kwargs):
        return OpenRouterGeneration(
            text=r"Article 1: Title: \[Virtual Event\] Promotion score 9 relevant",
            resolved_model="provider/test",
        )

    monkeypatch.setattr(service, "_invoke", invoke)
    result = asyncio.run(service.analyze_articles_for_grc([article()]))
    assert result["error"] == "excluded virtual-event promotion"
    assert result["grc_articles"] == []
    assert "Promotion" not in json.dumps(result)


def test_report_retry_can_only_return_clean_text_and_its_attested_model(monkeypatch):
    service = GRCModelService.__new__(GRCModelService)
    clean = complete_report_body("Security analysis.", "- [Evidence](https://example.com/)")
    responses = iter(
        [
            OpenRouterGeneration(
                text=complete_report_body(
                    "[Virtual Event] Promotion", "- [Evidence](https://example.com/)"
                ),
                resolved_model="provider/rejected",
            ),
            OpenRouterGeneration(text=clean, resolved_model="provider/accepted"),
        ]
    )

    async def invoke(**_kwargs):
        return next(responses)

    monkeypatch.setattr(service, "_invoke", invoke)
    result = asyncio.run(service.generate_grc_report({}, {}))
    assert result.content == clean
    assert result.resolved_model == "provider/accepted"


def test_source_evidence_excludes_whole_record_even_when_called_directly():
    clean = article()
    evidence = workflow._build_source_evidence(
        [
            article(title="[Virtual Event] Promotion", content="CVE-2026-12345"),
            clean,
        ]
    )
    assert [item["url"] for item in evidence] == [clean.url]
    assert "CVE-2026-12345" not in json.dumps(evidence)
