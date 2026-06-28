import asyncio
from datetime import datetime, timezone

from core import workflow as workflow_mod
from models.api import ArticleInput, GRCAnalysisConfig
from services.rss_service import RSSService


def test_source_evidence_preserves_later_cve_articles():
    published = datetime(2026, 3, 20, tzinfo=timezone.utc)
    articles = [
        ArticleInput(
            title=f"Governance update {index}",
            url=f"https://example.com/governance-{index}",
            summary="Compliance governance update without a vulnerability identifier.",
            published=published,
            content="Risk oversight and control monitoring guidance.",
        )
        for index in range(12)
    ]
    articles.append(
        ArticleInput(
            title="Vendor patch advisory",
            url="https://example.com/cve",
            summary="Emergency patch guidance for CVE-2026-9999.",
            published=published,
            content="CVE-2026-9999 affects regulated environments.",
        )
    )

    evidence = workflow_mod._build_source_evidence(articles)

    assert len(evidence) == 12
    assert evidence[0]["title"] == "Vendor patch advisory"
    assert evidence[0]["cves"] == ["CVE-2026-9999"]


def test_source_evidence_preserves_actor_articles_when_cve_volume_is_high():
    published = datetime(2026, 3, 20, tzinfo=timezone.utc)
    articles = [
        ArticleInput(
            title=f"Vendor patch advisory {index}",
            url=f"https://example.com/cve-{index}",
            summary=f"Patch guidance for CVE-2026-{1000 + index}.",
            published=published,
            content=f"CVE-2026-{1000 + index} affects regulated environments.",
        )
        for index in range(12)
    ]
    articles.append(
        ArticleInput(
            title="Threat group activity update",
            url="https://example.com/actor",
            summary="Threat actor APT99 targeted regulated environments.",
            published=published,
            content="APT99 used credential theft against compliance teams.",
        )
    )

    evidence = workflow_mod._build_source_evidence(articles)

    assert len(evidence) == 12
    assert any(item["threat_actors"] == ["APT99"] for item in evidence)


def test_source_evidence_skips_duplicate_cve_articles_for_new_cve_sources():
    published = datetime(2026, 3, 20, tzinfo=timezone.utc)
    articles = [
        ArticleInput(
            title=f"Duplicate vendor advisory {index}",
            url=f"https://example.com/duplicate-cve-{index}",
            summary="Patch guidance for CVE-2026-1000.",
            published=published,
            content="CVE-2026-1000 affects regulated environments.",
        )
        for index in range(12)
    ]
    articles.append(
        ArticleInput(
            title="Different CVE advisory",
            url="https://example.com/new-cve",
            summary="Patch guidance for CVE-2026-2000.",
            published=published,
            content="CVE-2026-2000 affects regulated environments.",
        )
    )

    evidence = workflow_mod._build_source_evidence(articles)

    assert any(item["cves"] == ["CVE-2026-2000"] for item in evidence)


def test_source_evidence_uses_full_multiword_actor_names():
    published = datetime(2026, 3, 20, tzinfo=timezone.utc)
    article = ArticleInput(
        title="Threat Actor Volt Typhoon Targets Agencies",
        url="https://example.com/actor",
        summary="Threat actor Volt Typhoon targeted regulated environments.",
        published=published,
        content="Volt Typhoon used credential theft against compliance teams.",
    )

    evidence = workflow_mod._build_source_evidence([article])

    assert evidence[0]["threat_actors"] == ["Volt Typhoon"]


def test_source_evidence_does_not_overcapture_headline_words_as_actor_names():
    published = datetime(2026, 3, 20, tzinfo=timezone.utc)
    article = ArticleInput(
        title="Threat Actor APT99 Targets Banks",
        url="https://example.com/actor-headline",
        summary="APT99 targeted regulated banks.",
        published=published,
        content="APT99 used credential theft against compliance teams.",
    )

    evidence = workflow_mod._build_source_evidence([article])

    assert evidence[0]["threat_actors"] == ["APT99"]


def test_source_evidence_ignores_non_actor_storm_center_mentions():
    published = datetime(2026, 3, 20, tzinfo=timezone.utc)
    article = ArticleInput(
        title="SANS Internet Storm Center update",
        url="https://example.com/storm-center",
        summary="SANS Internet Storm Center published a defensive update.",
        published=published,
        content="No threat actor activity was attributed in the article.",
    )

    evidence = workflow_mod._build_source_evidence([article])

    assert evidence[0]["threat_actors"] == []


def test_source_evidence_does_not_classify_finra_as_actor():
    published = datetime(2026, 3, 20, tzinfo=timezone.utc)
    article = ArticleInput(
        title="SEC and FINRA issue cybersecurity guidance",
        url="https://example.com/finra",
        summary="SEC and FINRA issued routine cybersecurity guidance.",
        published=published,
        content="The regulatory update did not attribute threat actor activity.",
    )

    evidence = workflow_mod._build_source_evidence([article])

    assert evidence[0]["threat_actors"] == []


def test_source_evidence_accepts_long_cve_identifiers():
    published = datetime(2026, 3, 20, tzinfo=timezone.utc)
    article = ArticleInput(
        title="Long CVE advisory",
        url="https://example.com/long-cve",
        summary="Patch guidance for CVE-2026-12345678.",
        published=published,
        content="CVE-2026-12345678 affects regulated environments.",
    )

    evidence = workflow_mod._build_source_evidence([article])

    assert evidence[0]["cves"] == ["CVE-2026-12345678"]


def test_run_grc_analysis_endpoint_falls_back_when_model_is_unavailable(monkeypatch):
    async def fake_fetch_feed(_feed_url):
        return {
            "title": "Test Feed",
            "entries": [
                {
                    "title": "CISA orders vendors to strengthen compliance controls",
                    "link": "https://example.com/article",
                    "description": "Regulatory compliance and risk management update",
                    "published": "Thu, 20 Mar 2026 00:00:00 GMT",
                    "content": "CISA issued new guidance for vendors covering compliance obligations and risk monitoring.",
                }
            ],
        }

    async def fake_enrich_articles(articles):
        return articles

    class FakeGRCModelService:
        def __init__(self, model_name=None, max_tokens=None):
            pass

        async def analyze_articles_for_grc(self, articles):
            return {
                "error": "Error code: 429 - insufficient_quota",
                "grc_articles": [],
                "summary": {
                    "total_articles": len(articles),
                    "grc_relevant_count": 0,
                    "confidence_score": 0.0,
                },
                "analysis": {
                    "regulations_mentioned": [],
                    "frameworks_referenced": [],
                    "industries_affected": [],
                    "risk_categories": [],
                },
            }

    monkeypatch.setattr(workflow_mod.rss_service, "fetch_feed", fake_fetch_feed)
    monkeypatch.setattr(workflow_mod.rss_service, "enrich_articles", fake_enrich_articles)
    monkeypatch.setattr(workflow_mod, "GRCModelService", FakeGRCModelService)

    response = asyncio.run(
        workflow_mod.run_grc_analysis_endpoint(
            "https://example.com/feed.xml",
            GRCAnalysisConfig(),
        )
    )

    assert response.status == "completed"
    assert response.report is not None
    assert "deterministic local analysis" in response.report.content.lower()
    assert response.metadata is not None
    assert response.metadata.article_count == 1
    assert response.metadata.grc_article_count >= 1
    assert response.metadata.analysis_mode == "fallback"
    assert response.metadata.fallback_reason == "Error code: 429 - insufficient_quota"


def test_run_grc_analysis_endpoint_marks_model_backed_reports(monkeypatch):
    captured_report_inputs = []

    async def fake_fetch_feed(_feed_url):
        return {
            "title": "Test Feed",
            "entries": [
                {
                    "title": "NIST publishes new control guidance",
                    "link": "https://example.com/nist",
                    "description": "Framework control update",
                    "published": "Thu, 20 Mar 2026 00:00:00 GMT",
                    "content": "NIST control guidance for regulated teams references CVE-2026-1234.",
                }
            ],
        }

    async def fake_enrich_articles(articles):
        return articles

    class FakeGRCModelService:
        def __init__(self, model_name=None, max_tokens=None):
            pass

        async def analyze_articles_for_grc(self, articles):
            return {
                "grc_articles": [{"title": articles[0].title, "url": articles[0].url}],
                "summary": {
                    "total_articles": len(articles),
                    "grc_relevant_count": 1,
                    "confidence_score": 0.9,
                },
                "analysis": {
                    "regulations_mentioned": [],
                    "frameworks_referenced": ["NIST"],
                    "industries_affected": [],
                    "regulatory_bodies": ["NIST"],
                    "risk_categories": ["Control governance"],
                },
            }

        async def generate_grc_report(self, analysis_results, _feed_data):
            captured_report_inputs.append(analysis_results)
            return "# Model-backed GRC Intelligence Report\n\n1) Executive Summary\n- Model output."

    monkeypatch.setattr(workflow_mod.rss_service, "fetch_feed", fake_fetch_feed)
    monkeypatch.setattr(workflow_mod.rss_service, "enrich_articles", fake_enrich_articles)
    monkeypatch.setattr(workflow_mod, "GRCModelService", FakeGRCModelService)

    response = asyncio.run(
        workflow_mod.run_grc_analysis_endpoint(
            "https://example.com/feed.xml",
            GRCAnalysisConfig(),
        )
    )

    assert response.status == "completed"
    assert response.metadata is not None
    assert response.metadata.analysis_mode == "model"
    assert response.metadata.fallback_reason is None
    assert captured_report_inputs
    assert captured_report_inputs[0]["source_evidence"][0]["cves"] == ["CVE-2026-1234"]
    assert (
        "NIST publishes new control guidance"
        in captured_report_inputs[0]["source_evidence"][0]["title"]
    )


def test_run_grc_analysis_endpoint_passes_request_model_config(monkeypatch):
    captured_configs = []

    async def fake_fetch_feed(_feed_url):
        return {
            "title": "Test Feed",
            "entries": [
                {
                    "title": "SEC updates cyber disclosure expectations",
                    "link": "https://example.com/sec",
                    "description": "Disclosure and risk governance update",
                    "published": "Thu, 20 Mar 2026 00:00:00 GMT",
                    "content": "SEC disclosure guidance for cyber governance and risk oversight.",
                }
            ],
        }

    async def fake_enrich_articles(articles):
        return articles

    class FakeGRCModelService:
        def __init__(self, model_name=None, max_tokens=None):
            captured_configs.append((model_name, max_tokens))

        async def analyze_articles_for_grc(self, articles):
            return {
                "grc_articles": [{"title": articles[0].title, "url": articles[0].url}],
                "summary": {
                    "total_articles": len(articles),
                    "grc_relevant_count": 1,
                    "confidence_score": 0.9,
                },
                "analysis": {
                    "regulations_mentioned": ["SEC"],
                    "frameworks_referenced": [],
                    "industries_affected": ["Financial services"],
                    "regulatory_bodies": ["SEC"],
                    "risk_categories": ["Disclosure"],
                },
            }

        async def generate_grc_report(self, _analysis_results, _feed_data):
            return "# Model-backed GRC Intelligence Report\n\n1) Executive Summary\n- Model output."

    monkeypatch.setattr(workflow_mod.rss_service, "fetch_feed", fake_fetch_feed)
    monkeypatch.setattr(workflow_mod.rss_service, "enrich_articles", fake_enrich_articles)
    monkeypatch.setattr(workflow_mod, "GRCModelService", FakeGRCModelService)

    response = asyncio.run(
        workflow_mod.run_grc_analysis_endpoint(
            "https://example.com/feed.xml",
            GRCAnalysisConfig(
                model="openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
                max_tokens=4096,
            ),
        )
    )

    assert response.status == "completed"
    assert captured_configs == [("openrouter/nvidia/nemotron-3-ultra-550b-a55b:free", 4096)]


def test_rss_service_fetch_feed_survives_multiple_event_loops(monkeypatch):
    class FakeResponse:
        status_code = 200

        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    class LoopBoundAsyncClient:
        def __init__(self, *args, **kwargs):
            self.bound_loop = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

        async def get(self, _url, timeout=None):
            current_loop = asyncio.get_running_loop()
            if self.bound_loop is None:
                self.bound_loop = current_loop
            elif self.bound_loop is not current_loop:
                raise RuntimeError("Event loop is closed")

            return FakeResponse("""<?xml version="1.0" encoding="UTF-8"?>
                <rss version="2.0">
                    <channel>
                        <title>Test Feed</title>
                        <item>
                            <title>Test Article</title>
                            <link>https://example.com/article</link>
                            <description>Test summary</description>
                        </item>
                    </channel>
                </rss>""")

    monkeypatch.setattr("services.rss_service.httpx.AsyncClient", LoopBoundAsyncClient)

    service = RSSService()

    first_result = asyncio.run(service.fetch_feed("https://example.com/feed.xml"))
    second_result = asyncio.run(service.fetch_feed("https://example.com/feed.xml"))

    assert first_result["entry_count"] == 1
    assert second_result["entry_count"] == 1
