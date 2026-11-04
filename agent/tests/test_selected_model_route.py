"""The selected report model is fixed and cannot activate paid network calls."""

import asyncio
from copy import deepcopy
import json

import httpx
import pytest

from services.model_route import ARGON_ROUTE, OFFLINE_KEY, ModelRouteError, RouteActivation
from services.openrouter_client import (
    GenerationMode,
    OpenRouterClient,
    OpenRouterModel,
    parse_openrouter_model,
)

MODEL = parse_openrouter_model("openrouter/" + ARGON_ROUTE.model_id)


def unexpected_post(_request: httpx.Request) -> httpx.Response:
    raise AssertionError("Unexpected POST")


def completion():
    return {
        "model": ARGON_ROUTE.model_id,
        "service_tier": "default",
        "choices": [{"finish_reason": "stop", "message": {"content": "report"}}],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 10,
            "total_tokens": 15,
            "completion_tokens_details": {"reasoning_tokens": 6},
            "cost": 0.00011,
        },
    }


def invoke(client, *, mode=GenerationMode.TEXT, prompt="user"):
    return asyncio.run(
        client.generate(
            system_prompt="system", user_prompt=prompt, model=MODEL, title="test", mode=mode
        )
    )


def offline(handler, **kwargs):
    return OpenRouterClient(
        api_key=OFFLINE_KEY,
        max_tokens=16000,
        activation=RouteActivation.OFFLINE,
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def test_selected_default_is_disabled_even_with_a_key_and_mock():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return unexpected_post(request)

    client = OpenRouterClient(
        api_key=OFFLINE_KEY,
        max_tokens=16000,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ModelRouteError, match="disabled"):
        invoke(client)
    assert requests == []


@pytest.mark.parametrize("mode", [GenerationMode.TEXT, GenerationMode.REPORT_PLAN])
def test_selected_payload_is_fixed_and_json_is_only_for_report_plan(mode):
    requests = []
    client = offline(
        lambda request: requests.append(request) or httpx.Response(200, json=completion())
    )
    result = invoke(client, mode=mode)
    payload = json.loads(requests[0].content)
    expected = {
        "model",
        "max_tokens",
        "messages",
        "provider",
        "reasoning",
        "service_tier",
        "stream",
    }
    assert set(payload) == expected | (
        {"response_format"} if mode is GenerationMode.REPORT_PLAN else set()
    )
    assert payload["provider"] == {
        "only": ["google-ai-studio"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
        "zdr": True,
        "max_price": {"prompt": 2, "completion": 10, "request": 0},
    }
    assert payload["service_tier"] == "default"
    assert payload["reasoning"] == {"effort": "low", "exclude": True}
    assert result.usage["completion_tokens"] == 10
    assert result.usage["reasoning_tokens"] == 6
    if mode is GenerationMode.REPORT_PLAN:
        schema = payload["response_format"]["json_schema"]
        assert schema["strict"] is True
        assert schema["schema"]["additionalProperties"] is False
        assert set(schema["schema"]["required"]) == {
            "executive_brief",
            "regulatory_changes",
            "control_implications",
            "industry_impacts",
        }


@pytest.mark.parametrize(
    "defect",
    [
        "length",
        "missing_finish",
        "error",
        "refusal",
        "model",
        "tier",
        "extra_choice",
        "reasoning_usage",
        "over_budget",
        "invalid_json",
        "timeout",
    ],
)
def test_selected_paid_attempt_is_not_retried(defect):
    value = deepcopy(completion())
    choice = value["choices"][0]
    if defect == "length":
        choice["finish_reason"] = "length"
    elif defect == "missing_finish":
        del choice["finish_reason"]
    elif defect == "error":
        choice["error"] = {"message": "provider secret"}
    elif defect == "refusal":
        choice["message"]["refusal"] = "provider secret"
    elif defect == "model":
        value["model"] = "google/gemini-test"
    elif defect == "tier":
        value["service_tier"] = "priority"
    elif defect == "extra_choice":
        value["choices"].append(deepcopy(choice))
    elif defect == "reasoning_usage":
        value["usage"]["completion_tokens_details"]["reasoning_tokens"] = 11
    elif defect == "over_budget":
        value["usage"]["completion_tokens"] = 16001
    requests = []

    def handler(request):
        requests.append(request)
        if defect == "invalid_json":
            return httpx.Response(200, text="provider secret")
        if defect == "timeout":
            raise httpx.ReadTimeout("provider secret")
        return httpx.Response(200, json=value)

    client = offline(handler)
    with pytest.raises(Exception) as failure:
        invoke(client)
    assert "provider secret" not in str(failure.value)
    assert len(requests) == 1


def test_context_derived_bound_allows_realistic_prompt_and_rejects_oversize_before_post():
    requests = []
    client = offline(
        lambda request: requests.append(request) or httpx.Response(200, json=completion())
    )
    # Ordinary full-evidence prompts may exceed 32k bytes without approaching context.
    assert (
        invoke(client, mode=GenerationMode.REPORT_PLAN, prompt="source evidence " * 10000).text
        == "report"
    )
    assert len(requests) == 1
    with pytest.raises(ModelRouteError, match="input"):
        invoke(client, mode=GenerationMode.REPORT_PLAN, prompt="x" * 1048576)
    assert len(requests) == 1


def test_offline_route_requires_exact_mock_and_synthetic_key():
    client = OpenRouterClient(
        api_key="not-the-offline-key",
        max_tokens=16000,
        activation=RouteActivation.OFFLINE,
        transport=httpx.MockTransport(unexpected_post),
    )
    with pytest.raises(ModelRouteError):
        invoke(client)


@pytest.mark.parametrize(
    "model_id",
    [
        "google/gemini-4-argon:online",
        "google/gemini-4-argon:nitro",
        "google/gemini-4-argon:floor",
        "google/gemini-4-argon-20261013",
        "Google/Gemini-4-Argon",
        "~google/gemini-pro-latest",
    ],
)
def test_selected_family_variants_and_known_alias_cannot_fall_through_legacy(model_id):
    requests = []
    client = offline(lambda request: requests.append(request))
    with pytest.raises(ModelRouteError):
        asyncio.run(
            client.generate(
                system_prompt="system",
                user_prompt="user",
                model=parse_openrouter_model("openrouter/" + model_id),
                title="test",
            )
        )
    assert not requests


def test_selected_top_level_error_cannot_log_untrusted_error_code():
    value = completion()
    value["error"] = {"code": "provider secret"}
    with pytest.raises(ModelRouteError) as error:
        invoke(offline(lambda _: httpx.Response(200, json=value)))
    assert "provider secret" not in str(error.value)


@pytest.mark.parametrize(
    "owner,identifier",
    [
        ("google", "gemini-4-argon"),
        ("anthropic", "google/gemini-4-argon"),
        ("anthropic", "gemini-4-argon"),
        (" openrouter ", "google/gemini-4-argon"),
        ("openrouter", " google/gemini-4-argon"),
        ("openrouter", "google/gemini-4-argon "),
        ("openrouter", "google / gemini-4-argon"),
        ("openrouter", "openrouter/google/gemini-4-argon"),
    ],
)
def test_selected_identity_ownership_cannot_escape_into_legacy_transport(owner, identifier):
    client = offline(unexpected_post)
    with pytest.raises(ModelRouteError):
        asyncio.run(
            client.generate(
                system_prompt="system",
                user_prompt="user",
                model=OpenRouterModel(model_id=identifier, provider_id=owner),
                title="test",
            )
        )


@pytest.mark.parametrize(
    "content",
    [
        [{"type": "image_url", "image_url": {"url": "https://example.test/a.png"}}],
        {"text": "user"},
        None,
    ],
)
def test_selected_route_refuses_non_text_content_before_post(content):
    requests = []
    client = offline(lambda request: requests.append(request))
    with pytest.raises(ModelRouteError, match="text-only"):
        invoke(client, prompt=content)
    assert not requests
