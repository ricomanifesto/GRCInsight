import asyncio

from core import workflow as workflow_mod
from models.api import GRCAnalysisConfig
from services.rss_service import RSSService


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
        def __init__(self):
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
    async def fake_fetch_feed(_feed_url):
        return {
            "title": "Test Feed",
            "entries": [
                {
                    "title": "NIST publishes new control guidance",
                    "link": "https://example.com/nist",
                    "description": "Framework control update",
                    "published": "Thu, 20 Mar 2026 00:00:00 GMT",
                    "content": "NIST control guidance for regulated teams.",
                }
            ],
        }

    async def fake_enrich_articles(articles):
        return articles

    class FakeGRCModelService:
        def __init__(self):
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

        async def generate_grc_report(self, _analysis_results, _feed_data):
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
