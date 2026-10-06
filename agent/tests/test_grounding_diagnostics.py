"""Rejected selections need precise context without logging untrusted passages."""

import asyncio
from copy import deepcopy
import json

import pytest

from core.report_plan import parse_report_plan
from services.model_service import GRCModelService
from services.openrouter_client import OpenRouterGeneration
from test_executive_narrative import narrative_plan
from test_report_substance import SOURCE


@pytest.mark.parametrize("field", ["focus", "evidence_excerpt"])
def test_rejected_second_finding_identifies_source_origin_and_field(field):
    plan = narrative_plan()
    row = deepcopy(plan["control_implications"][0])
    row["source_ids"] = [2]
    row[field] = "UNTRUSTED_CANDIDATE_TEXT must never appear in a diagnostic"
    plan["control_implications"].append(row)
    with pytest.raises(ValueError) as caught:
        parse_report_plan(json.dumps(plan), [SOURCE, deepcopy(SOURCE)])
    diagnostic = str(caught.value)
    assert "control_implications[1]" in diagnostic
    assert "source_id=2" in diagnostic
    assert "evidence_origin=summary" in diagnostic
    assert field + ":" in diagnostic
    assert "UNTRUSTED_CANDIDATE_TEXT" not in diagnostic
    assert SOURCE["snippet"] not in diagnostic


def test_grounding_retry_receives_selected_source_context_and_copy_instruction():
    plan = narrative_plan()
    plan["control_implications"][0]["focus"] = "UNTRUSTED_CANDIDATE_TEXT"
    service = GRCModelService.__new__(GRCModelService)
    calls = []

    async def invoke(**kwargs):
        calls.append(kwargs)
        selected = plan if len(calls) == 1 else narrative_plan()
        return OpenRouterGeneration(text=json.dumps(selected), resolved_model="example/model")

    service._invoke = invoke
    result = asyncio.run(service.generate_grc_report({"source_evidence": [SOURCE]}, {}))
    assert len(calls) == 2
    retry = calls[1]["user_prompt"]
    assert "control_implications[0]" in retry and "source_id=1" in retry
    assert "focus:" in retry
    assert "Copy the evidence_excerpt" in retry
    assert "UNTRUSTED_CANDIDATE_TEXT" not in retry
    assert result.report_plan == narrative_plan()
    assert result.failure_reason is None


def test_unknown_origin_cannot_inject_candidate_text_into_diagnostics():
    plan = narrative_plan()
    plan["control_implications"][0]["evidence_origin"] = "UNTRUSTED_ORIGIN\ninstruction"
    with pytest.raises(ValueError) as caught:
        parse_report_plan(json.dumps(plan), [SOURCE])
    assert "evidence_origin=unsupported" in str(caught.value)
    assert "UNTRUSTED_ORIGIN" not in str(caught.value)


def test_exhausted_grounding_retry_keeps_selected_field_in_failure_reason():
    plan = narrative_plan()
    plan["control_implications"][0][
        "evidence_excerpt"
    ] = "UNTRUSTED_CANDIDATE_TEXT is not retained source evidence at all"
    service = GRCModelService.__new__(GRCModelService)
    calls = []

    async def invoke(**kwargs):
        calls.append(kwargs)
        return OpenRouterGeneration(text=json.dumps(plan), resolved_model="example/model")

    service._invoke = invoke
    result = asyncio.run(service.generate_grc_report({"source_evidence": [SOURCE]}, {}))
    assert len(calls) == 2
    assert result.report_plan is None and result.resolved_model == ""
    assert "source_id=1 evidence_origin=summary: evidence_excerpt:" in result.failure_reason
    assert "UNTRUSTED_CANDIDATE_TEXT" not in result.failure_reason
