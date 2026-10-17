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
from services import relevance_decisions
from services.relevance_decisions import RelevanceClient
from services.relevance_selection import (
    SELECTION_POLICY,
    candidate_fingerprint,
    disposition,
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
    assert SELECTION_POLICY == "keep-uncertain-v1"


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


def test_all_uncertain_plans_a_full_legacy_batch_with_raw_decisions():
    plan = plan_selection(result(probability=0.6), None, 2, 0.95)
    assert (plan.route, plan.reason) == ("legacy_full", "all_uncertain")
    assert plan.decisions is not None and len(plan.decisions) == 2


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


def test_fingerprint_is_stable_and_covers_candidate_identity(monkeypatch):
    from services import relevance_selection

    def fingerprint(threshold=0.95, focus_areas=FOCUS_AREAS, batch_size=12):
        return candidate_fingerprint(threshold, focus_areas, batch_size=batch_size)

    base = fingerprint()
    assert base == fingerprint(focus_areas=list(FOCUS_AREAS))
    assert len(base) == 64
    changed = {fingerprint(threshold=0.9), fingerprint(focus_areas=FOCUS_AREAS[:-1])}
    # The replay batch changes request bytes and positions.
    changed.add(fingerprint(batch_size=4))
    for name, value in (
        ("MODEL", "typesafe/jev-2"),
        ("CRITERIA", {**relevance_decisions.CRITERIA, "relevant": "changed"}),
        ("INSTRUCTIONS", relevance_decisions.INSTRUCTIONS + " "),
        ("MAX_TITLE_CHARS", 201),
        ("MAX_TEXT_CHARS", 501),
        ("MAX_BATCH_ARTICLES", 11),
        ("MAX_ARTICLES", 63),
        ("MAX_REQUEST_BYTES", 23999),
    ):
        with monkeypatch.context() as patch:
            patch.setattr(relevance_decisions, name, value)
            changed.add(fingerprint())
    with monkeypatch.context() as patch:
        patch.setattr(relevance_selection, "SELECTION_POLICY", "other")
        changed.add(fingerprint())
    # Every implementation that decides a selection is bound by its source, so a
    # behavior change cannot reuse an accepted fingerprint.
    sources = relevance_selection.selection_sources()
    assert {
        "services.relevance_decisions",
        "services.relevance_selection",
        "core.entities",
        "core.article_selection",
        "GRCModelService.analyze_articles_for_grc",
        "GRCModelService._try_relevance",
        "GRCModelService._analysis_from_selection",
    } <= set(sources)
    original = relevance_selection.source_sha256
    for changed_source in sources:
        with monkeypatch.context() as patch:
            patch.setattr(
                relevance_selection,
                "source_sha256",
                lambda value, name=changed_source: (
                    "0" * 64 if relevance_selection.source_name(value) == name else original(value)
                ),
            )
            changed.add(fingerprint())
    assert base not in changed
    assert len(changed) == 12 + len(sources)


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
