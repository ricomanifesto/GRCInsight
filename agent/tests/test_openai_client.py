import asyncio
from types import SimpleNamespace

import httpx
import openai

from services.openai_client import OpenAIClient, OpenAIClientError


class FakeResponses:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class FakeAsyncOpenAI:
    def __init__(self, outcome):
        self.responses = FakeResponses(outcome)


def test_openai_client_uses_responses_api_with_sol_and_xhigh_reasoning():
    sdk_client = FakeAsyncOpenAI(SimpleNamespace(output_text="Generated report"))
    client = OpenAIClient(
        max_output_tokens=16_000,
        reasoning_effort="xhigh",
        sdk_client=sdk_client,
    )

    result = asyncio.run(
        client.generate(
            system_prompt="system",
            user_prompt="user",
            model="gpt-5.6-sol",
            title="GRC report",
        )
    )

    assert result == "Generated report"
    assert sdk_client.responses.calls == [
        {
            "model": "gpt-5.6-sol",
            "instructions": "system",
            "input": "user",
            "max_output_tokens": 16_000,
            "reasoning": {"effort": "xhigh"},
            "metadata": {"request_title": "GRC report"},
        }
    ]


def test_openai_client_redacts_failed_response_body():
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(401, request=request)
    error = openai.AuthenticationError(
        "leaked api key", response=response, body={"error": "leaked api key"}
    )
    client = OpenAIClient(
        max_output_tokens=16_000,
        reasoning_effort="xhigh",
        sdk_client=FakeAsyncOpenAI(error),
    )

    try:
        asyncio.run(
            client.generate(
                system_prompt="system",
                user_prompt="user",
                model="gpt-5.6-sol",
                title="GRC report",
            )
        )
    except OpenAIClientError as exc:
        assert str(exc) == "OpenAI response failed: HTTP 401"
        assert "leaked api key" not in str(exc)
    else:
        raise AssertionError("failed OpenAI responses must raise")


def test_openai_client_rejects_empty_output():
    client = OpenAIClient(
        max_output_tokens=16_000,
        reasoning_effort="xhigh",
        sdk_client=FakeAsyncOpenAI(SimpleNamespace(output_text="")),
    )

    try:
        asyncio.run(
            client.generate(
                system_prompt="system",
                user_prompt="user",
                model="gpt-5.6-sol",
                title="GRC report",
            )
        )
    except OpenAIClientError as exc:
        assert str(exc) == "OpenAI response did not include text output"
    else:
        raise AssertionError("empty OpenAI responses must raise")
