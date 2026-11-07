import asyncio
from dataclasses import replace
import hashlib
import itertools
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from config.settings import Settings
from core.article_selection import analyze_selected, local_overrides, workflow_selected
from models.api import ArticleInput
from services.relevance_decisions import RelevanceClient
from services.relevance_selection import (
    SELECTION_POLICY,
    SelectionRecord,
    disposition,
    keep_violations,
    plan_selection,
)
from tests.test_relevance_policy import articles, decided, decision, result, service

GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures" / "relevance" / "off-golden.json").read_text(
        encoding="utf-8"
    )
)
FOCUS_AREAS = tuple(Settings.model_fields["analysis_focus_areas"].default)


def test_policy_version_is_explicit():
    assert SELECTION_POLICY == "keep-uncertain-v2"


@pytest.mark.parametrize(
    ("label", "probability", "expected"),
    [
        ("relevant", 0.95, "accepted_relevant"),
        ("irrelevant", 0.95, "accepted_irrelevant"),
        ("relevant", 0.949, "uncertain_kept"),
        ("irrelevant", 0.5, "uncertain_kept"),
        ("insufficient_evidence", 0.99, "insufficient_evidence_kept"),
        ("insufficient_evidence", 0.4, "insufficient_evidence_kept"),
    ],
)
def test_dispositions(label, probability, expected):
    assert disposition(decision(0, label, probability), 0.95) == expected


def test_plan_keeps_uncertain_positions_and_sends_them_to_aggregate_enrichment():
    plan = plan_selection(
        decided(
            decision(0, "irrelevant"),
            decision(1, "relevant", 0.6),
            decision(2, "insufficient_evidence"),
            decision(3, "relevant"),
        ),
        None,
        4,
        0.95,
    )
    assert plan.route == "decision"
    assert plan.model_selected == (False, True, True, True)
    assert plan.fallback_indices == (1, 2)


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        ("timeout", "jev_timeout"),
        ("deadline", "jev_deadline"),
        ("internal_error", "internal_error"),
    ],
)
def test_failed_decisions_plan_a_full_legacy_batch(failure, reason):
    plan = plan_selection(None, failure, 2, 0.95)
    assert (plan.route, plan.reason, plan.model_selected) == ("legacy_full", reason, None)
    assert plan.dispositions == ("legacy_full", "legacy_full")


@pytest.mark.parametrize(
    "decisions",
    [
        (decision(0, "relevant"),),
        (decision(0, "relevant"), decision(0, "relevant")),
        (decision(0, "relevant"), decision(2, "relevant")),
        (decision(0, "relevant"), decision(-1, "relevant")),
    ],
)
def test_incomplete_or_duplicate_positions_are_internal_errors(decisions):
    plan = plan_selection(decided(*decisions), None, 2, 0.95)
    assert (plan.route, plan.reason) == ("legacy_full", "internal_error")


def test_missing_result_without_failure_code_is_an_internal_error():
    assert plan_selection(None, None, 1, 0.95).reason == "internal_error"


@pytest.mark.parametrize(
    "decisions",
    [result(probability=0.6), result(labels=("insufficient_evidence",) * 2)],
)
def test_all_uncertain_complete_result_stays_on_the_decision_route(decisions):
    """keep-uncertain-v2 corrects v1, which routed this case to legacy selection."""
    plan = plan_selection(decisions, None, 2, 0.95)
    assert (plan.route, plan.reason) == ("decision", None)
    assert plan.model_selected == (True, True)
    assert plan.fallback_indices == (0, 1)
    assert plan.decisions is not None and len(plan.decisions) == 2


BASE_RECORD = SelectionRecord(
    index=0,
    article_key="0" * 64,
    route="decision",
    disposition="uncertain_kept",
    reason=None,
    label="irrelevant",
    probabilities={"relevant": 0.2, "irrelevant": 0.6, "insufficient_evidence": 0.2},
    confidence=0.9,
    model_selected=True,
    entity_override=False,
    risk_override=False,
    workflow_selected=True,
    analyze_selected=True,
)


def record(**overrides):
    return replace(BASE_RECORD, **overrides)


def test_keep_invariant_reads_raw_labels_not_dispositions():
    assert keep_violations([record()], 0.95) == ()
    # An all-uncertain raw result relabeled legacy_full cannot pass.
    assert keep_violations([record(route="legacy_full", disposition="legacy_full")], 0.95) == (0,)
    # A raw low-probability label must not be dropped, whatever its disposition says.
    assert keep_violations([record(disposition="accepted_irrelevant")], 0.95) == (0,)
    assert keep_violations([record(model_selected=False)], 0.95) == (0,)
    insufficient = record(
        label="insufficient_evidence",
        probabilities={"relevant": 0.0, "irrelevant": 0.01, "insufficient_evidence": 0.99},
        disposition="insufficient_evidence_kept",
    )
    assert keep_violations([insufficient], 0.95) == ()
    assert keep_violations([replace(insufficient, model_selected=False)], 0.95) == (0,)
    # A failed enrichment leaves selection unknown, which is not a drop.
    assert keep_violations([record(model_selected=None, reason="fallback_error")], 0.95) == ()
    assert keep_violations([record(model_selected=None)], 0.95) == (0,)
    # A confident irrelevant drop and a decision-less legacy record are allowed.
    confident = record(
        disposition="accepted_irrelevant",
        model_selected=False,
        probabilities={"relevant": 0.01, "irrelevant": 0.98, "insufficient_evidence": 0.01},
    )
    assert keep_violations([confident], 0.95) == ()
    legacy = record(
        route="legacy_full",
        disposition="legacy_full",
        label=None,
        probabilities=None,
        confidence=None,
        model_selected=False,
    )
    assert keep_violations([legacy], 0.95) == ()


def previous_workflow_rule(local_has_grc, risk_categories, model_selected):
    """The inline workflow expression before extraction."""
    has_grc = local_has_grc or bool(risk_categories)
    return has_grc or model_selected


@pytest.mark.parametrize(
    ("entity", "risk", "model"), list(itertools.product([False, True], repeat=3))
)
def test_extracted_workflow_rule_matches_previous_inline_logic(entity, risk, model):
    risks = ["Vulnerability and patch management"] if risk else []
    assert workflow_selected(entity=entity, risk=risk, model=model) == previous_workflow_rule(
        entity, risks, model
    )
    assert analyze_selected(entity=entity, model=model) == (entity or model)


@pytest.mark.parametrize(("entity", "risk"), list(itertools.product([False, True], repeat=2)))
def test_unknown_model_selection_is_never_a_drop(entity, risk):
    expected = True if entity or risk else None
    assert workflow_selected(entity=entity, risk=risk, model=None) is expected
    assert analyze_selected(entity=entity, model=None) is (True if entity else None)


def test_local_overrides_match_the_workflow_local_analysis():
    from core.workflow import _build_local_analysis

    inputs = [ArticleInput.model_validate(item) for item in GOLDEN["articles"]] + articles()
    inputs[-1].content = "The vendor requires a patch for the product vulnerability."
    signals, _ = _build_local_analysis(inputs)
    for article, signal in zip(inputs, signals):
        entity, risk = local_overrides(article)
        assert workflow_selected(entity=entity, risk=risk, model=False) == signal["has_grc_content"]
        assert risk == bool(signal["risk_categories"])


def test_decision_requests_match_pre_change_bytes():
    inputs = [ArticleInput.model_validate(item) for item in GOLDEN["articles"]]
    client = RelevanceClient(api_key="test-key", focus_areas=FOCUS_AREAS)
    assert [
        {"indices": list(indices), "sha256": hashlib.sha256(raw).hexdigest()}
        for raw, indices in client._batches(inputs)
    ] == GOLDEN["decision_requests_sha256"]


def test_records_describe_effective_selections_separately(monkeypatch):
    model = service(monkeypatch, "enabled")
    inputs = articles() + articles()
    inputs[1].content = "GDPR Article 5 applies."
    inputs[2].content = "The vendor requires a patch for the product vulnerability."
    model.relevance_client.classify = AsyncMock(
        return_value=replace(result(), decisions=tuple(decision(i, "irrelevant") for i in range(4)))
    )
    asyncio.run(model.analyze_articles_for_grc(inputs))
    records = model.last_selection_records
    assert [(r.entity_override, r.risk_override) for r in records] == [
        (False, False),
        (True, False),
        (False, True),
        (False, False),
    ]
    assert [r.workflow_selected for r in records] == [False, True, True, False]
    # The /analyze rule has no risk-category override.
    assert [r.analyze_selected for r in records] == [False, True, False, False]
