from copy import deepcopy
import json

import pytest

from core.relevance_corpus import load_corpus, validate_corpus, visible_sha256
from models.api import ArticleInput
from tests.relevance_fixtures import CORPUS, case_dicts, corpus_lines


def validate(cases):
    return validate_corpus(corpus_lines(cases))


def rehash(case):
    case["visible_sha256"] = visible_sha256(ArticleInput.model_validate(case["article"]))
    return case


def by_id(cases, case_id):
    return next(case for case in cases if case["case_id"] == case_id)


def test_committed_fixture_is_valid_and_generated_from_code():
    assert CORPUS.read_text(encoding="utf-8").splitlines() == corpus_lines()
    validation = load_corpus(CORPUS)
    assert validation.errors == ()
    assert validation.flags == ()
    assert validation.holdout_sha256 is not None
    statuses = {case.case_id: case.review_status for case in validation.cases}
    assert statuses["dev-03"] == "dual_reviewed"
    assert statuses["dev-07"] == "disputed"
    assert statuses["dev-08"] == "provisional"


def test_provisional_and_disputed_cases_cannot_satisfy_gates():
    validation = validate(case_dicts())
    eligible = {case.case_id: case.gate_eligible for case in validation.cases}
    assert eligible["dev-08"] is False
    assert eligible["dev-07"] is False
    assert eligible["dev-01"] is True
    cases = {case.case_id: case for case in validation.cases}
    # Adjudication decides a disagreement; a dispute has no reference label.
    assert cases["dev-03"].reference_label == "relevant"
    assert cases["dev-07"].reference_label is None


def test_events_cannot_cross_splits():
    cases = case_dicts()
    by_id(cases, "hold-02")["event_id"] = "evt-webinar"
    errors = validate(cases).errors
    assert "event evt-webinar spans development and holdout" in errors


def test_shared_cves_and_normalized_urls_are_flagged():
    cases = case_dicts()
    holdout = by_id(cases, "hold-03")
    holdout["article"]["content"] += " It cites CVE-2026-11111."
    holdout["article"]["url"] = "HTTPS://www.news.example/dev-01/#top"
    rehash(holdout)
    flags = validate(cases).flags
    assert "CVE-2026-11111 appears in development and holdout" in flags
    assert any(flag.startswith("normalized URL https://news.example/dev-01") for flag in flags)


def test_holdout_must_come_after_the_development_window():
    cases = case_dicts()
    holdout = by_id(cases, "hold-01")
    holdout["article"]["published"] = "2026-09-05T00:00:00+00:00"
    errors = validate([rehash(case) for case in cases]).errors
    assert "holdout window must start after the development window ends" in errors


def test_holdout_hash_freezes_holdout_labels_only():
    base = validate(case_dicts()).holdout_sha256
    cases = case_dicts()
    by_id(cases, "dev-01")["labels"][0]["rationale"] = "Changed development rationale."
    assert validate(cases).holdout_sha256 == base
    by_id(cases, "hold-01")["labels"][0]["label"] = "irrelevant"
    assert validate(cases).holdout_sha256 != base


@pytest.mark.parametrize(
    "mutate",
    [
        lambda case: case.update(extra=True),
        lambda case: case.update(visible_sha256="0" * 64),
        lambda case: case.update(split="test"),
        lambda case: case.update(review_status="reviewed"),
        lambda case: case.update(categories=["unknown"]),
        lambda case: case["labels"][0].update(labeler="person@example.com"),
        lambda case: case["labels"][0].update(label="maybe"),
        lambda case: case["labels"][0].update(labeled_at="2026-10-15"),
        lambda case: case["article"].update(published="2026-09-01T08:00:00"),
        lambda case: case["article"].update(secret="value"),
        # A single label cannot be reported as dual review.
        lambda case: case.update(review_status="dual_reviewed"),
    ],
)
def test_invalid_cases_are_rejected(mutate):
    cases = case_dicts()
    mutate(cases[0])
    validation = validate(cases)
    assert validation.errors
    assert "dev-01" not in {case.case_id for case in validation.cases}


def test_disagreeing_dual_review_needs_adjudication():
    cases = case_dicts()
    by_id(cases, "dev-03")["adjudication"] = None
    assert any("need adjudication" in error for error in validate(cases).errors)


def test_duplicate_case_ids_and_invalid_json_are_errors():
    lines = corpus_lines()
    validation = validate_corpus([*lines, lines[0], "{"])
    assert any("duplicate case_id dev-01" in error for error in validation.errors)
    assert any("invalid JSON" in error for error in validation.errors)


def test_rubric_dispute_rate_and_category_coverage_are_flagged():
    cases = [deepcopy(case) for case in case_dicts() if case["split"] == "development"]
    for case in cases[:2]:
        case["labels"] = [
            {**case["labels"][0], "role": "primary", "label": "relevant"},
            {**case["labels"][0], "role": "second", "label": "irrelevant"},
        ]
        case["adjudication"] = None
        case["review_status"] = "disputed"
    flags = validate(cases).flags
    assert any("disputed" in flag for flag in flags)
    assert any(flag.startswith("categories without cases:") for flag in flags)


def test_visible_hash_covers_only_inference_visible_text():
    article = ArticleInput.model_validate(json.loads(corpus_lines()[0])["article"])
    longer = article.model_copy(update={"content": article.content + " " * 600 + "tail"})
    assert visible_sha256(article) != visible_sha256(longer)
    beyond = article.model_copy(update={"content": article.content.ljust(500) + "tail"})
    trimmed = article.model_copy(update={"content": article.content.ljust(500) + "other"})
    assert visible_sha256(beyond) == visible_sha256(trimmed)
