import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json

import httpx
import pytest

from models.api import ArticleInput
from services.relevance_decisions import DecisionError, RelevanceClient


def article(index=0, **overrides):
    return ArticleInput.model_validate(
        {
            "title": "Shared headline",
            "url": f"https://example.com/{index}",
            "content": "A board must review an audit finding and document its control response.",
            "published": datetime(2026, 10, 1, tzinfo=timezone.utc),
            **overrides,
        }
    )


def answer(label="relevant", probability=0.98):
    labels = ("relevant", "irrelevant", "insufficient_evidence")
    return {
        "type": "choice",
        "choice": label,
        "probabilities": {
            key: probability if key == label else (1 - probability) / 2 for key in labels
        },
        "confidence": 0.95,
    }


def payload(ids=("article_0",), **overrides):
    return {
        "model": "typesafe/jev-1.13-20260917",
        "answers": {key: answer() for key in ids},
        "usage": {"input_tokens": 100, "output_tokens": 0, "cost": 0.0000042},
        **overrides,
    }


def client(handler, **kwargs):
    return RelevanceClient(api_key="test-key", transport=httpx.MockTransport(handler), **kwargs)


def test_choices_use_decisions_endpoint_and_explicit_article_identity():
    def respond(request):
        assert str(request.url) == "https://openrouter.ai/api/alpha/decisions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "typesafe/jev-1.13"
        assert "messages" not in body
        assert set(body["state"]) == {"article_0", "article_1"}
        assert body["state"]["article_0"]["text"] == "first"
        assert body["state"]["article_1"]["text"] == "second"
        assert "article_1" in body["questions"]["article_1"]["instructions"]
        assert set(body["questions"]["article_0"]["criteria"]) == {
            "relevant",
            "irrelevant",
            "insufficient_evidence",
        }
        # Response key order must not change article identity.
        return httpx.Response(
            200, json=payload(answers={"article_1": answer("irrelevant"), "article_0": answer()})
        )

    result = asyncio.run(
        client(respond).classify([article(content="first"), article(1, content="second")])
    )
    assert [(item.index, item.label) for item in result.decisions] == [
        (0, "relevant"),
        (1, "irrelevant"),
    ]
    assert result.models == ("typesafe/jev-1.13-20260917",)
    assert result.input_tokens == 100
    assert result.cost == 0.0000042
    assert result.elapsed_seconds >= 0


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["answers"].clear(),
        lambda p: p["answers"].update(article_99=answer()),
        lambda p: p.update(model="unrelated/model"),
        lambda p: p["answers"]["article_0"].update(type="noul"),
        lambda p: p["answers"]["article_0"].update(choice="invented"),
        lambda p: p["answers"]["article_0"].update(choice="irrelevant"),
        lambda p: p["answers"]["article_0"]["probabilities"].update(relevant=float("nan")),
        lambda p: p["answers"]["article_0"]["probabilities"].update(relevant=True),
        lambda p: p["answers"]["article_0"]["probabilities"].update(relevant=-0.2),
        lambda p: p["answers"]["article_0"]["probabilities"].update(relevant=0.3),
        lambda p: p["answers"]["article_0"]["probabilities"].pop("irrelevant"),
        lambda p: p["answers"]["article_0"].update(confidence=2),
        lambda p: p["usage"].update(input_tokens=True),
        lambda p: p["usage"].update(cost=-1),
        lambda p: p["usage"].update(cost=10**400),
        lambda p: p.update(error={"message": "private source text"}),
    ],
)
def test_malformed_response_is_rejected_without_provider_content(change):
    value = deepcopy(payload())
    change(value)
    with pytest.raises(DecisionError) as error:
        asyncio.run(
            client(lambda _: httpx.Response(200, text=json.dumps(value))).classify([article()])
        )
    assert "private source text" not in str(error.value)


def test_duplicate_json_keys_are_rejected():
    value = json.dumps(payload()).replace(
        '"choice": "relevant"', '"choice": "irrelevant", "choice": "relevant"'
    )
    with pytest.raises(DecisionError):
        asyncio.run(client(lambda _: httpx.Response(200, text=value)).classify([article()]))


@pytest.mark.parametrize("status", [401, 429, 500, 503])
def test_http_failure_does_not_retry_or_echo_body(status):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status, text="private provider response")

    with pytest.raises(DecisionError) as error:
        asyncio.run(client(respond).classify([article()]))
    assert len(requests) == 1
    assert "private" not in str(error.value)


def test_total_timeout_cancels_slow_request():
    async def respond(request):
        await asyncio.sleep(0.1)
        return httpx.Response(200, json=payload())

    with pytest.raises(DecisionError, match="timeout"):
        asyncio.run(client(respond, timeout=0.01).classify([article()]))


def test_expired_caller_deadline_and_empty_input_do_not_call_provider():
    def unexpected(_):
        raise AssertionError("unexpected HTTP call")

    assert asyncio.run(client(unexpected).classify([])).decisions == ()
    with pytest.raises(DecisionError, match="deadline"):
        asyncio.run(client(unexpected, deadline=0).classify([article()]))


def test_bounded_batches_and_concurrency_preserve_all_indices():
    active = 0
    peak = 0
    sizes = []

    async def respond(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        body = json.loads(request.content)
        sizes.append(len(request.content))
        assert len(body["state"]) <= 12
        assert all(len(value["text"]) <= 500 for value in body["state"].values())
        await asyncio.sleep(0.005)
        active -= 1
        return httpx.Response(200, json=payload(tuple(body["state"])))

    result = asyncio.run(
        client(respond).classify([article(i, content="字" * 900) for i in range(30)])
    )
    assert [item.index for item in result.decisions] == list(range(30))
    assert max(sizes) <= 24000
    assert peak <= 3
    assert result.input_tokens == 100 * len(sizes)


def test_large_input_and_response_fail_closed():
    def unexpected(_):
        raise AssertionError("network called")

    with pytest.raises(DecisionError, match="input_limit"):
        asyncio.run(client(unexpected).classify([article(i) for i in range(65)]))
    with pytest.raises(DecisionError, match="response_limit"):
        asyncio.run(client(lambda _: httpx.Response(200, text="x" * 131073)).classify([article()]))


def test_failed_batch_cancels_other_requests_before_return():
    active = 0
    started = 0

    async def respond(request):
        nonlocal active, started
        active += 1
        started += 1
        try:
            if "article_0" in json.loads(request.content)["state"]:
                await asyncio.sleep(0.005)
                return httpx.Response(503)
            await asyncio.sleep(0.5)
            raise AssertionError("Sibling request was not cancelled")
        finally:
            active -= 1

    with pytest.raises(DecisionError, match="http_error"):
        asyncio.run(client(respond).classify([article(i) for i in range(60)]))
    assert active == 0
    assert started <= 4
