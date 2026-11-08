"""Tagged virtual-event promotions are excluded before analysis; ordinary reporting is kept."""

import asyncio

import pytest

from core import workflow as workflow_mod
from core.content_policy import contains_virtual_event
from models.api import GRCAnalysisConfig

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


@pytest.mark.parametrize("marker", MARKERS)
def test_bracketed_promotion_marker_is_recognized_in_every_encoding(marker):
    assert contains_virtual_event(f"{marker} Register for our webinar")
    assert contains_virtual_event({"title": "Webinar", "description": f"Join us {marker}"})


@pytest.mark.parametrize(
    "text",
    [
        "NIST guidance for security teams attending virtual events.",
        "Attackers targeted a Virtual Event platform used by insurers.",
        "[Virtual] Event review",
        "",
    ],
)
def test_ordinary_event_related_reporting_is_not_excluded(text):
    assert not contains_virtual_event(text)
    assert not contains_virtual_event(None)


def test_workflow_skips_tagged_promotions_before_analysis(monkeypatch):
    analyzed = []

    async def fake_fetch_feed(_feed_url):
        return {
            "title": "SentryDigest",
            "link": "https://digest.example/",
            "last_updated": "Thu, 20 Mar 2026 01:00:00 GMT",
            "entries": [
                {
                    "title": "CISA issues gateway guidance",
                    "link": "https://example.com/guidance",
                    "description": "Compliance controls for gateways.",
                    "published": "Thu, 20 Mar 2026 00:00:00 GMT",
                    "content": "CISA compliance guidance for regulated teams.",
                },
                {
                    "title": "Compliance summit webinar",
                    "link": "https://example.com/webinar",
                    "description": "&#91;Virtual Event&#93; Register now.",
                    "published": "Thu, 20 Mar 2026 00:00:00 GMT",
                    "content": "Join our compliance summit.",
                },
            ],
        }

    async def fake_enrich_articles(articles):
        analyzed.extend(article.url for article in articles)
        return articles

    class Unavailable:
        def __init__(self, *args, **kwargs):
            raise ValueError("model unavailable")

    monkeypatch.setattr(workflow_mod.rss_service, "fetch_feed", fake_fetch_feed)
    monkeypatch.setattr(workflow_mod.rss_service, "enrich_articles", fake_enrich_articles)
    monkeypatch.setattr(workflow_mod, "GRCModelService", Unavailable)

    response = asyncio.run(
        workflow_mod.run_grc_analysis_endpoint("https://example.com/feed.xml", GRCAnalysisConfig())
    )

    assert analyzed == ["https://example.com/guidance"]
    assert response.metadata is not None and response.metadata.article_count == 1
    assert all(
        source["url"] != "https://example.com/webinar"
        for source in response.metadata.source_articles
    )
