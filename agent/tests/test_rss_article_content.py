import asyncio

import pytest

from core import workflow
from models.api import GRCAnalysisConfig
from services.rss_service import RSSService
from test_virtual_event_policy import MARKERS, article, feed_entries
from test_workflow_fallback import StaticFeedAsyncClient

CONTAINERS = (
    ("<article>", "</article>"),
    ("<main>", "</main>"),
    ('<div itemprop="articleBody">', "</div>"),
    ("", ""),
)
CHROME = (
    "<aside>[Virtual Event] Shared promotion</aside>",
    "<footer>[Virtual Event] Shared promotion</footer>",
    '<script>const ad = "[Virtual Event] Shared promotion";</script>',
    "<nav>[Virtual Event] Shared promotion</nav>",
    '<style>.ad::after { content: "[Virtual Event] Shared promotion"; }</style>',
    "<template>[Virtual Event] Shared promotion</template>",
    '<div role="complementary">[Virtual Event] Shared promotion</div>',
    '<div class="sidebar">[Virtual Event] Shared promotion</div>',
    '<div class="advertisement">[Virtual Event] Shared promotion</div>',
)
BODY = "<h1>Security guidance</h1><p>NIST compliance controls protect regulated information.</p>"


def enrich(monkeypatch, html):
    class Client(StaticFeedAsyncClient):
        response_text = html

    monkeypatch.setattr("services.rss_service.httpx.AsyncClient", Client)
    return asyncio.run(RSSService().enrich_articles([article(content="")]))


@pytest.mark.parametrize("container", CONTAINERS)
@pytest.mark.parametrize("chrome", CHROME)
def test_shared_page_promotions_do_not_exclude_article(monkeypatch, container, chrome):
    opening, closing = container
    result = enrich(monkeypatch, f"<html><body>{opening}{BODY}{closing}{chrome}</body></html>")
    assert len(result) == 1
    assert result[0].content is not None
    assert "NIST compliance controls" in result[0].content
    assert "Shared promotion" not in result[0].content
    assert "<" not in result[0].content


@pytest.mark.parametrize("container", CONTAINERS)
@pytest.mark.parametrize("marker", MARKERS)
def test_owned_markers_exclude_whole_record(monkeypatch, container, marker):
    opening, closing = container
    assert (
        enrich(monkeypatch, f"<body>{opening}{BODY}<p>{marker} Promotion.</p>{closing}</body>")
        == []
    )


@pytest.mark.parametrize("container", CONTAINERS)
def test_complete_owned_text_is_checked_before_truncation(monkeypatch, container):
    opening, closing = container
    large_body = "Security information. " * 300 + "[Virtual Event] Promotion"
    assert enrich(monkeypatch, f"<body>{opening}<p>{large_body}</p>{closing}</body>") == []


def test_boilerplate_size_does_not_hide_owned_body(monkeypatch):
    chrome = "<nav>Site navigation. " + "menu " * 1500 + "</nav>"
    result = enrich(monkeypatch, f"<body>{chrome}<article>{BODY}</article></body>")
    assert len(result) == 1
    assert "NIST compliance controls" in result[0].content
    assert "menu" not in result[0].content
    assert len(result[0].content) <= 5000


@pytest.mark.parametrize("chrome", [CHROME[0], CHROME[2], CHROME[6], CHROME[7], CHROME[8]])
def test_embedded_shared_widgets_are_not_article_text(monkeypatch, chrome):
    result = enrich(monkeypatch, f"<article>{BODY}{chrome}</article>")
    assert len(result) == 1
    assert "Shared promotion" not in result[0].content


@pytest.mark.parametrize(
    "html",
    [
        f"<article><header><h1>[Virtual Event] Promotion</h1></header>{BODY}</article>",
        f"<article>{BODY}<footer>[Virtual Event] Registration</footer></article>",
        f"<head><title>[Virtual Event] Promotion</title></head><article>{BODY}</article>",
        f'<head><meta property="og:title" content="[Virtual Event] Promotion"></head><main>{BODY}</main>',
        f'<div class="event-content">{BODY}<p>[Virtual Event] Promotion</p></div>',
    ],
)
def test_article_titles_and_owned_footer_cannot_bypass_exclusion(monkeypatch, html):
    assert enrich(monkeypatch, html) == []


def test_empty_owned_container_does_not_fall_back_to_unrelated_page_text(monkeypatch):
    result = enrich(
        monkeypatch, "<article></article><div>[Virtual Event] Unrelated promotion</div>"
    )
    assert len(result) == 1
    assert not result[0].content


def test_containerless_chrome_only_page_never_becomes_raw_content(monkeypatch):
    result = enrich(monkeypatch, "<body>" + "".join(CHROME) + "</body>")
    assert len(result) == 1
    assert not result[0].content


def test_primary_article_is_not_a_sidebar_article_card(monkeypatch):
    result = enrich(
        monkeypatch,
        "<aside><article>[Virtual Event] Shared promotion</article></aside>"
        f"<main><article>{BODY}</article></main>",
    )
    assert len(result) == 1
    assert "NIST compliance controls" in result[0].content


def test_article_heading_disambiguates_related_cards(monkeypatch):
    result = enrich(
        monkeypatch,
        "<main><article><h2>[Virtual Event] Related promotion</h2></article>"
        f"<article>{BODY}</article></main>",
    )
    assert len(result) == 1
    assert "Related promotion" not in result[0].content


def test_conflicting_main_and_card_headings_do_not_select_the_card(monkeypatch):
    result = enrich(
        monkeypatch,
        f"<main>{BODY}<article><h2>[Virtual Event] Unrelated card</h2></article></main>",
    )
    assert len(result) == 1
    assert "Unrelated card" not in (result[0].content or "")


def test_owned_main_heading_is_checked_when_body_ownership_is_ambiguous(monkeypatch):
    assert (
        enrich(
            monkeypatch,
            "<main><h1>[Virtual Event] Promotion</h1>"
            "<article><h2>Unrelated card</h2></article></main>",
        )
        == []
    )


def test_shared_promotion_does_not_remove_source_from_workflow_fallback(monkeypatch):
    async def fetch(_url):
        return feed_entries([article(content="")])

    class Client(StaticFeedAsyncClient):
        response_text = f"<article>{BODY}</article>{CHROME[0]}"

    class UnavailableModel:
        def __init__(self, **_kwargs):
            raise ValueError("Model unavailable")

    monkeypatch.setattr(workflow.rss_service, "fetch_feed", fetch)
    monkeypatch.setattr("services.rss_service.httpx.AsyncClient", Client)
    monkeypatch.setattr(workflow, "GRCModelService", UnavailableModel)
    result = asyncio.run(
        workflow.run_grc_analysis_endpoint("https://digest.example/feed.xml", GRCAnalysisConfig())
    )
    assert result.status == "completed"
    assert result.metadata is not None and result.report is not None
    assert result.metadata.analysis_mode == "fallback"
    assert result.metadata.article_count == 1
    assert [source["url"] for source in result.metadata.source_articles] == [article().url]
    assert "Shared promotion" not in result.report.content
