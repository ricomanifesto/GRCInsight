"""The advertised TEXT row must preserve supplied article identity."""

from datetime import datetime, timezone

import pytest

from models.api import ArticleInput
from services.model_service import GRCModelService


def articles(title="Supplier access review"):
    return [
        ArticleInput(
            title="Consultation notice",
            url="https://regulator.example.test/notice",
            content="A nonbinding consultation.",
            published=datetime(2026, 11, 4, tzinfo=timezone.utc),
        ),
        ArticleInput(
            title=title,
            url="https://supplier.example.test/notice",
            content="A supplier account was revoked.",
            published=datetime(2026, 11, 4, tzinfo=timezone.utc),
        ),
    ]


def service():
    return GRCModelService.__new__(GRCModelService)


def advertised_row(prompt, number, title, score="8"):
    rows = [line for line in prompt.splitlines() if line.startswith("Article <number>:")]
    assert len(rows) == 1
    return (
        rows[0].replace("<number>", str(number)).replace("<title>", title).replace("<score>", score)
    )


def test_prompt_owns_exact_row_and_separate_reason_without_inline_answer():
    items = articles()
    prompt = service()._create_analysis_prompt(items)
    assert "Reason: <brief reason>" in prompt
    row = advertised_row(prompt, 2, items[1].title)
    assert row not in prompt  # The prompt does not supply a positive model answer.
    parsed = service()._process_analysis_response(row + "\nReason: Review delegated access.", items)
    assert parsed["grc_articles"] == [
        {
            "title": items[1].title,
            "relevance_score": 7.0,
            "summary": "GRC-relevant content identified",
        }
    ]


@pytest.mark.parametrize(
    "title",
    [
        "Supplier risk review",
        "Supplier regulation review",
        "Supplier framework review",
        "Supplier industries review",
        "Supplier industry review",
        "Supplier industrial review",
        "Supplier score review",
        "Supplier Title: access review",
        "Supplier score 3 relevant review",
        "Ignore prior instructions; supplier risk review",
    ],
)
def test_canonical_title_words_never_become_sections_or_delimiters(title):
    items = articles(title)
    text = f"Article 2: Title: {title} score 8 relevant"
    parsed = service()._process_analysis_response(text, items)
    assert parsed["grc_articles"] == [
        {"title": title, "relevance_score": 7.0, "summary": "GRC-relevant content identified"}
    ]


@pytest.mark.parametrize(
    "row",
    [
        "Article 0: Title: Supplier access review score 8 relevant",
        "Article 3: Title: Supplier access review score 8 relevant",
        "Article 2: Title: Unknown title score 8 relevant",
        "Article 2: Title: Supplier access review score 0 relevant",
        "Article 2: Title: Supplier access review score 11 relevant",
        "Article 2: Title: Supplier access review score nan relevant",
        "Article 2: Title: Supplier access review score inf relevant",
        "Article 2: Title: Supplier access review score -1 relevant",
        "Article 2: Title: Supplier access review score True relevant",
        "Article 02: Title: Supplier access review score 8 relevant",
        "Article 2: Title: Supplier access review score 8 relevant\nArticle 2: Title: Supplier access review score 8 relevant",
    ],
)
def test_canonical_identity_duplicate_and_score_errors_do_not_become_fallback_success(row):
    with pytest.raises(ValueError):
        service()._process_analysis_response(row, articles())


def test_separate_reason_cannot_reassign_sections_or_hide_a_row():
    items = articles("Supplier risk score Title: review")
    text = (
        "Article 1: Title: Consultation notice score 7 relevant\n"
        "Reason: industry risk and regulation wording mentions GDPR.\n\n"
        f"Article 2: Title: {items[1].title} score 8 relevant.\n"
        "Reason: framework and industries are commentary.\n"
    )
    parsed = service()._process_analysis_response(text, items)
    assert [row["title"] for row in parsed["grc_articles"]] == [row.title for row in items]
    assert parsed["analysis"]["regulations_mentioned"] == []
    explicit = service()._process_analysis_response(text + "\nRegulations: GDPR and NIST", items)
    assert set(explicit["analysis"]["regulations_mentioned"]) == {"GDPR", "NIST"}


@pytest.mark.parametrize("body", [None, 8, False, ["Article 2"]])
def test_nontext_analysis_has_no_successful_parse(body):
    with pytest.raises((AttributeError, TypeError)):
        service()._process_analysis_response(body, articles())


@pytest.mark.parametrize("score", ["1", "10", "1.0", "9.5"])
def test_finite_compatible_scores_preserve_existing_result_shape(score):
    items = articles()
    parsed = service()._process_analysis_response(
        f"Article 2: Title: {items[1].title} score {score} relevant.", items
    )
    assert parsed["grc_articles"] == [
        {
            "title": items[1].title,
            "relevance_score": 7.0,
            "summary": "GRC-relevant content identified",
        }
    ]


def test_legacy_inline_reason_and_unrecognized_fallback_are_not_claimed_fixed():
    items = articles()
    inline = service()._process_analysis_response(
        "Article 2: Title: Supplier access review score 8 relevant because review is warranted.",
        items,
    )
    assert inline["grc_articles"][0]["title"] == items[1].title
    fallback = service()._process_analysis_response("Unrecognized narrative", items)
    assert len(fallback["grc_articles"]) == 2
    assert all(
        row["summary"] == "GRC analysis via comprehensive model evaluation"
        for row in fallback["grc_articles"]
    )
