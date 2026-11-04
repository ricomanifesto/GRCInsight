"""Real service checks; require the project's installed runtime dependencies."""

import asyncio
from copy import deepcopy
import json
from pathlib import Path
from datetime import datetime, timezone
import runpy
from unittest.mock import patch

import httpx
import pytest

from models.api import ArticleInput
from services.model_service import GRCModelService
from services.model_route import ARGON_ROUTE, ModelRouteError, RouteActivation
from core.report_plan import validate_rendered_report

CASE = json.loads((Path(__file__).parent / "fixtures/selected_model_case.json").read_text())


@pytest.mark.parametrize(
    "model_id",
    [
        ARGON_ROUTE.model_id,
        ARGON_ROUTE.model_id + ":online",
        ARGON_ROUTE.model_id + ":floor",
        "~google/gemini-pro-latest",
    ],
)
def test_selected_constructor_stops_before_key_attribute_or_client(monkeypatch, model_id):
    class NoCredentialSettings:
        @property
        def openrouter_api_key(self):
            raise AssertionError("credential attribute accessed")

    monkeypatch.setattr("services.model_service.settings", NoCredentialSettings())
    with pytest.raises(ModelRouteError, match="disabled"):
        GRCModelService(model_name="openrouter/" + model_id, max_tokens=8000)


@pytest.mark.parametrize("raw_cap", [0, False, True, 0.0, 16000.0, "16000", "", 16001])
def test_selected_service_rejects_raw_cap_before_falsey_default_or_coercion(raw_cap):
    with pytest.raises(ModelRouteError, match="output allowance"):
        GRCModelService(
            model_name="openrouter/" + ARGON_ROUTE.model_id,
            max_tokens=raw_cap,
            activation=RouteActivation.OFFLINE,
            transport=httpx.MockTransport(lambda _: None),
        )


@pytest.mark.parametrize("valid", [True, False])
def test_real_selected_service_uses_one_plan_post_and_host_grounded_rendering(valid):
    requests = []
    plan = deepcopy(CASE["calibration_plan"])
    if not valid:
        plan["control_implications"] = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": ARGON_ROUTE.model_id,
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(plan)}}],
            },
        )

    service = GRCModelService(
        model_name="openrouter/" + ARGON_ROUTE.model_id,
        max_tokens=8000,
        activation=RouteActivation.OFFLINE,
        transport=httpx.MockTransport(handler),
    )
    generation = asyncio.run(service.generate_grc_report(CASE["analysis_data"], CASE["feed_info"]))
    assert len(requests) == 1
    payload = json.loads(requests[0].content)
    assert payload["max_tokens"] == 8000
    assert payload["response_format"]["type"] == "json_schema"
    assert service.relevance_client is None
    if valid:
        assert generation.report_plan == CASE["calibration_plan"]
        assert generation.report_plan["regulatory_changes"] == []
        assert generation.report_plan["control_implications"][0]["source_ids"] == [2]
        validate_rendered_report(
            generation.content, generation.report_plan, CASE["analysis_data"]["source_evidence"]
        )
    else:
        assert generation.report_plan is None
        assert generation.resolved_model == ""
        assert generation.failure_reason


def test_real_legacy_article_analysis_remains_text_without_report_schema(monkeypatch):
    monkeypatch.setattr(
        "services.model_service.settings.openrouter_api_key", "offline-synthetic-key"
    )
    service = GRCModelService()
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": service.model.model_id,
                "choices": [{"message": {"content": "Article 1: GRC relevant score 7"}}],
            },
        )

    service.client.transport = httpx.MockTransport(handler)
    article = ArticleInput(
        title="Fictional compliance notice",
        url="https://example.test/notice",
        content="A fictional consultation proposes access reviews.",
        published="2026-11-04T00:00:00Z",
    )
    result = asyncio.run(service.analyze_articles_for_grc([article]))
    assert result["summary"]["total_articles"] == 1
    assert len(requests) == 1
    assert "response_format" not in json.loads(requests[0].content)


def test_fixed_report_rehearsal_request_is_independent_of_ambient_date():
    runner = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "scripts/rehearse_selected_model_offline.py")
    )

    class AmbientDate(datetime):
        day = 1

        @classmethod
        def now(cls, tz=None):
            return datetime(2030, 1, cls.day, tzinfo=timezone.utc)

    with patch("services.model_service.datetime", AmbientDate):
        first = asyncio.run(runner["rehearse"]())
        AmbientDate.day = 2
        second = asyncio.run(runner["rehearse"]())
    assert first["request_sha256"] == second["request_sha256"]
    assert first["wire_request_sha256"] == second["wire_request_sha256"]
    assert first["prompt_date"] == second["prompt_date"] == "2026-11-04"
    assert first["conservative_input_bound"] == sum(
        first[key]
        for key in (
            "input_message_bytes",
            "input_schema_bytes",
            "input_serialization_wrapper_bytes",
            "input_framing_reserve",
        )
    )
