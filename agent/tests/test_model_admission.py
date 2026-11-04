"""Unowned model requests cannot evade the server's free policy or output cap."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

import lambda_main
from models.api import GRCAnalysisConfig
from services.openrouter_client import OpenRouterClient, parse_openrouter_model
from services import model_service


@pytest.mark.parametrize(
    "model_id",
    [
        "vendor/paid",
        "openrouter/auto",
        "openrouter/free",
        "vendor/model:free",
        "~vendor/alias",
    ],
)
def test_every_unowned_chat_route_has_zero_price_and_no_fallback(model_id):
    calls = []

    def respond(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert payload["provider"] == {
            "allow_fallbacks": False,
            "max_price": {"prompt": 0, "completion": 0, "request": 0, "image": 0},
        }
        return httpx.Response(
            200, json={"model": "vendor/resolved", "choices": [{"message": {"content": "answer"}}]}
        )

    client = OpenRouterClient(
        api_key="synthetic", max_tokens=8000, transport=httpx.MockTransport(respond)
    )
    asyncio.run(
        client.generate(
            system_prompt="system",
            user_prompt="user",
            model=parse_openrouter_model("openrouter/" + model_id),
            title="synthetic",
        )
    )
    assert len(calls) == 1


@pytest.mark.parametrize("cap", [16001, 1000000, 0, -1, False, True, 8000.5, "8000"])
def test_direct_client_output_override_refuses_before_post(cap):
    calls = []

    def forbidden_post(request):
        calls.append(request)
        raise AssertionError("Unexpected POST")

    client = OpenRouterClient(
        api_key="synthetic",
        max_tokens=8000,
        transport=httpx.MockTransport(forbidden_post),
    )
    client.max_tokens = cap
    with pytest.raises(ValueError):
        asyncio.run(
            client.generate(
                system_prompt="system",
                user_prompt="user",
                model=parse_openrouter_model("openrouter/vendor/paid"),
                title="synthetic",
            )
        )
    assert not calls


def test_direct_lambda_rejects_oversized_output_before_workflow_or_writeback(monkeypatch):
    calls = []

    async def forbidden(*_args, **_kwargs):
        calls.append(True)
        raise AssertionError("workflow invoked")

    monkeypatch.setattr("core.workflow.run_grc_analysis_endpoint", forbidden)
    response = lambda_main.handler(
        {
            "feed_url": "https://feed.example.test/rss",
            "config": {"model": "openrouter/vendor/paid", "max_tokens": 16001},
        },
        object(),
    )
    assert response["statusCode"] != 200
    assert not calls


def test_api_output_default_is_preserved_and_strictly_server_bounded():
    assert GRCAnalysisConfig().max_tokens == 16000
    for value in (16001, True, "16000"):
        with pytest.raises(ValueError):
            GRCAnalysisConfig.model_validate({"max_tokens": value})


@pytest.mark.parametrize("value", [16001, 0, False, float("inf"), "16000"])
def test_direct_constructor_refuses_unbounded_allowances(value):
    with pytest.raises(ValueError):
        OpenRouterClient(api_key="synthetic", max_tokens=value)


@pytest.mark.parametrize(
    "identifier",
    [
        "vendor/model:online",
        "vendor/model:free:online",
        "vendor/model:ONLINE",
        " vendor/model : online ",
        "vendor/model:free: Online :floor",
        "@preset/example",
        "vendor/model@preset/example",
        "@PRESET/example",
        "vendor/model@ preset / example",
    ],
)
def test_implicit_billable_search_and_presets_refuse_before_transport(identifier):
    calls = []

    def forbidden(request):
        calls.append(request)
        raise AssertionError("Unexpected POST")

    client = OpenRouterClient(
        api_key="synthetic", max_tokens=8000, transport=httpx.MockTransport(forbidden)
    )
    with pytest.raises(ValueError, match="indirect"):
        asyncio.run(
            client.generate(
                system_prompt="system",
                user_prompt="user",
                model=parse_openrouter_model("openrouter/" + identifier),
                title="synthetic",
            )
        )
    assert not calls


def test_direct_service_rejects_oversize_before_key_attribute(monkeypatch):
    class NoKey:
        @property
        def openrouter_api_key(self):
            raise AssertionError("key attribute accessed")

    monkeypatch.setattr(model_service, "settings", NoKey())
    with pytest.raises(ValueError, match="server policy"):
        model_service.GRCModelService(model_name="openrouter/vendor/paid", max_tokens=16001)


def test_direct_python_event_cannot_override_unowned_zero_price_policy(monkeypatch):
    from core import workflow

    case = json.loads((Path(__file__).parent / "fixtures/selected_model_case.json").read_text())
    feed_url = "https://digest.example.test/rss.xml"
    feed = {
        "title": case["feed_info"]["title"],
        "link": "https://digest.example.test/",
        "last_updated": "Wed, 04 Nov 2026 12:00:00 GMT",
        "entries": [
            {
                "title": source["title"],
                "link": source["url"],
                "description": source["snippet"],
                "content": "",
            }
            for source in case["analysis_data"]["source_evidence"]
        ],
    }
    payloads = []

    async def fetch(_url):
        return feed

    async def enrich(articles):
        return articles

    def respond(request):
        payload = json.loads(request.content)
        index = len(payloads)
        payloads.append(payload)
        answer = (
            "Article 1: Title: Fictional compliance notice score 8 relevant\n"
            "Article 2: Title: Fictional supplier access incident score 8 relevant"
            if index == 0
            else json.dumps(case["calibration_plan"])
        )
        return httpx.Response(
            200, json={"model": payload["model"], "choices": [{"message": {"content": answer}}]}
        )

    def service(**kwargs):
        value = model_service.GRCModelService(**kwargs)
        value.client.transport = httpx.MockTransport(respond)
        return value

    monkeypatch.setattr(model_service.settings, "openrouter_api_key", "synthetic")
    monkeypatch.setattr(workflow, "GRCModelService", service)
    monkeypatch.setattr(workflow.rss_service, "fetch_feed", fetch)
    monkeypatch.setattr(workflow.rss_service, "enrich_articles", enrich)
    response = lambda_main.handler(
        {
            "feed_url": feed_url,
            "config": {
                "model": "openrouter/vendor/paid",
                "max_tokens": 8000,
                "provider": {"allow_fallbacks": True, "max_price": {"prompt": 100}},
            },
        },
        object(),
    )
    assert response["statusCode"] == 200 and len(payloads) == 2
    assert all(
        payload["provider"]
        == {
            "allow_fallbacks": False,
            "max_price": {"prompt": 0, "completion": 0, "request": 0, "image": 0},
        }
        for payload in payloads
    )
