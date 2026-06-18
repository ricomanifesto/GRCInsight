import asyncio
import json

import httpx

from services.opencode_client import OpenCodeClient, parse_model_selection


def test_opencode_client_posts_explicit_provider_model():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/session":
            return httpx.Response(200, json={"id": "session-1"})
        if request.url.path == "/session/session-1/message":
            payload = json.loads(request.content.decode())
            assert payload["model"] == {
                "providerID": "anthropic",
                "modelID": "claude-sonnet-4-5-20250929",
            }
            return httpx.Response(
                200,
                json={
                    "info": {"id": "message-1"},
                    "parts": [{"type": "text", "text": "Generated report"}],
                },
            )
        return httpx.Response(404)

    client = OpenCodeClient(
        base_url="http://opencode.test",
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(
        client.generate(
            system_prompt="system",
            user_prompt="user",
            model=parse_model_selection("anthropic/claude-sonnet-4-5-20250929"),
            title="test",
        )
    )

    assert result == "Generated report"
    assert [request.url.path for request in requests] == [
        "/session",
        "/session/session-1/message",
    ]


def test_parse_model_selection_rejects_bare_model():
    try:
        parse_model_selection("claude-sonnet-4-5-20250929")
    except ValueError as exc:
        assert "provider/model" in str(exc)
    else:
        raise AssertionError("bare models must be rejected")


def test_opencode_error_redacts_response_body():
    def handler(request):
        if request.url.path == "/session":
            return httpx.Response(503, text="provider leaked request payload")
        return httpx.Response(404)

    client = OpenCodeClient(
        base_url="http://opencode.test",
        transport=httpx.MockTransport(handler),
    )

    try:
        asyncio.run(
            client.generate(
                system_prompt="system",
                user_prompt="user",
                model=parse_model_selection("anthropic/claude-sonnet-4-5-20250929"),
                title="test",
            )
        )
    except Exception as exc:
        assert "Failed to create OpenCode session: HTTP 503" in str(exc)
        assert "provider leaked request payload" not in str(exc)
    else:
        raise AssertionError("failed OpenCode responses must raise")
