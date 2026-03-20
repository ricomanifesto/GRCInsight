import asyncio

from core import workflow as workflow_mod
from models.api import AnalysisConfig


def test_run_grc_analysis_endpoint_falls_back_when_openai_is_unavailable(monkeypatch):
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

    class FakeOpenAIService:
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
    monkeypatch.setattr(workflow_mod, "OpenAIService", FakeOpenAIService)

    response = asyncio.run(
        workflow_mod.run_grc_analysis_endpoint(
            "https://example.com/feed.xml",
            AnalysisConfig(),
        )
    )

    assert response.status == "completed"
    assert response.report is not None
    assert "deterministic local analysis" in response.report.content.lower()
    assert response.metadata is not None
    assert response.metadata.article_count == 1
    assert response.metadata.grc_article_count >= 1
