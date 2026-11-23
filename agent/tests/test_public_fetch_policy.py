"""Feed and article policy, using synthetic DNS results and an in-memory transport."""

import asyncio
from datetime import datetime, timezone
import socket

import httpx
import pytest

from models.api import ArticleInput
from services import public_fetch, rss_service


@pytest.fixture
def fetch_policy(monkeypatch):
    requests = []
    configurations = []
    resolutions = []
    addresses = {"publisher.example": ["93.184.216.34"]}
    responses = []
    real_client = httpx.AsyncClient

    async def resolve(_loop, host, port, **kwargs):
        resolutions.append(host)
        return [
            (
                socket.AF_INET6 if ":" in address else socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (address, port),
            )
            for address in addresses[host]
        ]

    def handle(request):
        requests.append(request)
        if responses:
            return responses.pop(0)
        return httpx.Response(200, text="Publisher article body")

    def client(**kwargs):
        configurations.append(kwargs)
        return real_client(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(asyncio.BaseEventLoop, "getaddrinfo", resolve)
    monkeypatch.setattr(public_fetch.httpx, "AsyncClient", client)
    return requests, configurations, resolutions, addresses, responses


def enrich(url="https://publisher.example/article"):
    article = ArticleInput(
        title="Synthetic article",
        url=url,
        content="",
        published=datetime(2026, 11, 23, tzinfo=timezone.utc),
    )
    return asyncio.run(rss_service.RSSService().enrich_articles([article]))[0]


def test_article_request_pins_public_address_and_preserves_hostname(fetch_policy):
    requests, configurations, resolutions, _, _ = fetch_policy
    article = enrich()

    assert article.content == "Publisher article body"
    assert article.content_origin == "publisher_page"
    assert resolutions == ["publisher.example"]
    assert requests[0].url.host == "93.184.216.34"
    assert requests[0].headers["host"] == "publisher.example"
    assert requests[0].extensions["sni_hostname"] == "publisher.example"
    assert configurations[0]["follow_redirects"] is False
    assert configurations[0]["trust_env"] is False
    assert configurations[0]["limits"].max_keepalive_connections == 0


def test_dual_stack_resolution_prefers_public_ipv4(fetch_policy):
    requests, _, _, addresses, _ = fetch_policy
    addresses["publisher.example"] = ["2606:4700:4700::1111", "93.184.216.34"]

    assert enrich().content == "Publisher article body"
    assert requests[0].url.host == "93.184.216.34"


@pytest.mark.parametrize(
    "addresses",
    [
        ["127.0.0.1"],
        ["10.0.0.1"],
        ["169.254.0.1"],
        ["100.64.0.1"],
        ["192.0.2.1"],
        ["224.0.0.1"],
        ["0.0.0.0"],
        ["::1"],
        ["fe80::1"],
        ["fc00::1"],
        ["::ffff:127.0.0.1"],
        ["ff02::1"],
        ["64:ff9b::a00:1"],
        ["2002:0a00:0001::1"],
        ["93.184.216.34", "10.0.0.1"],
        [],
    ],
)
def test_nonpublic_or_ambiguous_resolution_never_reaches_transport(fetch_policy, addresses):
    requests, _, _, host_addresses, _ = fetch_policy
    host_addresses["publisher.example"] = addresses

    article = enrich()

    assert requests == []
    assert article.content == ""
    assert article.content_origin == "feed_item"


@pytest.mark.parametrize(
    "url",
    [
        "https://publisher.example:8443/article",
        "https://reader:placeholder@publisher.example/article",
        "ftp://publisher.example/article",
        "/article",
        "https://[invalid/article",
    ],
)
def test_unsupported_article_destination_never_reaches_transport(fetch_policy, url):
    requests, _, resolutions, _, _ = fetch_policy
    assert enrich(url).content == ""
    assert requests == []
    assert resolutions == []


def test_each_redirect_is_checked_before_sending(fetch_policy):
    requests, _, resolutions, addresses, responses = fetch_policy
    addresses["next.example"] = ["10.0.0.1"]
    responses.append(httpx.Response(302, headers={"location": "https://next.example/article"}))

    assert enrich().content == ""
    assert len(requests) == 1
    assert resolutions == ["publisher.example", "next.example"]


def test_relative_redirect_retains_hostname_and_public_pinning(fetch_policy):
    requests, _, resolutions, _, responses = fetch_policy
    responses.append(httpx.Response(302, headers={"location": "/updated"}))

    assert enrich().content == "Publisher article body"
    assert resolutions == ["publisher.example", "publisher.example"]
    assert requests[1].url.path == "/updated"
    assert all(request.url.host == "93.184.216.34" for request in requests)
    assert all(request.headers["host"] == "publisher.example" for request in requests)


def test_redirect_loop_stops_without_using_partial_content(fetch_policy):
    requests, _, _, _, responses = fetch_policy
    responses.extend(httpx.Response(302, headers={"location": "/again"}) for _ in range(10))

    assert enrich().content == ""
    assert len(requests) == 4


def test_public_http_and_ipv6_destinations_keep_correct_authority(fetch_policy):
    requests, _, _, _, _ = fetch_policy
    assert enrich("http://publisher.example:80/article").content == "Publisher article body"
    assert requests[0].url.scheme == "http"
    assert requests[0].headers["host"] == "publisher.example"
    assert enrich("https://[2606:4700:4700::1111]/article").content == "Publisher article body"
    assert requests[1].url.host == "2606:4700:4700::1111"
    assert requests[1].headers["host"] == "[2606:4700:4700::1111]"


def test_redirects_do_not_share_cookies_or_tls_clients(fetch_policy):
    requests, configurations, _, addresses, responses = fetch_policy
    addresses["next.example"] = ["93.184.216.34"]
    responses.append(
        httpx.Response(
            302,
            headers={"location": "https://next.example/article", "set-cookie": "sample=value"},
        )
    )

    assert enrich().content == "Publisher article body"
    assert len(configurations) == 2
    assert requests[1].headers["host"] == "next.example"
    assert requests[1].extensions["sni_hostname"] == "next.example"
    assert "cookie" not in requests[1].headers
    assert "authorization" not in requests[1].headers


def test_article_response_read_is_bounded_and_records_truncation(fetch_policy):
    _, _, _, _, responses = fetch_policy
    chunks = []

    class Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(100):
                chunks.append(1)
                yield b"a" * 4096

    responses.append(httpx.Response(200, stream=Body()))
    article = enrich()

    assert article.content == "a" * 5000
    assert article.content_truncated is True
    assert len(chunks) == 17


def test_compressed_response_is_refused_before_reading(fetch_policy):
    _, _, _, _, responses = fetch_policy
    responses.append(httpx.Response(200, headers={"content-encoding": "gzip"}))
    assert enrich().content == ""


def test_total_fetch_deadline_includes_dns(fetch_policy, monkeypatch):
    requests, _, _, _, _ = fetch_policy

    async def delayed_resolution(_loop, _host, _port, **kwargs):
        await asyncio.sleep(1)

    monkeypatch.setattr(asyncio.BaseEventLoop, "getaddrinfo", delayed_resolution)
    monkeypatch.setattr(rss_service, "PAGE_FETCH_TIMEOUT", 0.01)

    assert enrich().content == ""
    assert requests == []


def test_public_feed_uses_checked_redirects_and_keeps_parsing_contract(fetch_policy):
    requests, _, resolutions, _, responses = fetch_policy
    responses.extend(
        [
            httpx.Response(302, headers={"location": "/current.xml"}),
            httpx.Response(
                200,
                text="<rss><channel><title>Synthetic feed</title><item>"
                "<title>Article</title><link>https://publisher.example/article</link>"
                "</item></channel></rss>",
            ),
        ]
    )

    result = asyncio.run(rss_service.RSSService().fetch_feed("https://publisher.example/feed.xml"))

    assert result["title"] == "Synthetic feed"
    assert result["entry_count"] == 1
    assert resolutions == ["publisher.example", "publisher.example"]
    assert all(request.url.host == "93.184.216.34" for request in requests)


def test_feed_refuses_nonpublic_destination_before_transport(fetch_policy):
    requests, _, _, addresses, _ = fetch_policy
    addresses["publisher.example"] = ["10.0.0.1"]

    result = asyncio.run(rss_service.RSSService().fetch_feed("https://publisher.example/feed.xml"))

    assert result["entries"] == []
    assert "not public" in result["error"]
    assert requests == []


def test_oversize_feed_is_refused_instead_of_parsing_partial_xml(fetch_policy, monkeypatch):
    _, _, _, _, responses = fetch_policy
    monkeypatch.setattr(rss_service, "FEED_BYTE_LIMIT", 32)
    responses.append(httpx.Response(200, text="<rss><channel><title>" + "x" * 100))

    result = asyncio.run(rss_service.RSSService().fetch_feed("https://publisher.example/feed.xml"))

    assert result["entries"] == []
    assert "byte limit" in result["error"]
