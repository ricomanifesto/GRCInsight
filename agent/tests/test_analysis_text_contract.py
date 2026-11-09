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
            "url": items[1].url,
            "relevance_score": 7.0,
            "summary": "GRC-relevant content identified",
        }
    ]
    assert parsed["grc_article_indices"] == [1]


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
        {
            "title": title,
            "url": items[1].url,
            "relevance_score": 7.0,
            "summary": "GRC-relevant content identified",
        }
    ]
    assert parsed["grc_article_indices"] == [1]


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
    ],
)
def test_a_response_whose_rows_are_all_invalid_selects_no_article(row):
    # With no usable row the model selects nothing. It must never fall through to
    # selecting every supplied article, and it credits no article.
    parsed = service()._process_analysis_response(row, articles())
    assert parsed["grc_articles"] == [] and parsed["grc_article_indices"] == []
    assert parsed["analysis_rows"] == {"accepted": 0, "skipped": 1}
    assert parsed["summary"]["grc_relevant_count"] == 0
    assert parsed["summary"]["confidence_score"] == 0.0


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
            "url": items[1].url,
            "relevance_score": 7.0,
            "summary": "GRC-relevant content identified",
        }
    ]


def test_inline_commentary_is_skipped_and_unrecognized_text_selects_nothing():
    items = articles()
    # Reasons belong on a separate Reason: line; inline commentary is not a row.
    inline = service()._process_analysis_response(
        "Article 2: Title: Supplier access review score 8 relevant because review is warranted.",
        items,
    )
    assert inline["grc_article_indices"] == []
    assert inline["analysis_rows"] == {"accepted": 0, "skipped": 1}
    # Prose with no row selects no article instead of every article.
    prose = service()._process_analysis_response("Unrecognized narrative", items)
    assert prose["grc_articles"] == [] and prose["grc_article_indices"] == []
    assert prose["analysis_rows"] == {"accepted": 0, "skipped": 0}


def test_invalid_rows_are_skipped_and_counted_while_valid_rows_are_kept():
    items = articles()
    text = "\n".join(
        [
            "Article 3: Title: Supplier access review score 8 relevant",  # out of range
            "Article 1: Title: Consultation notice score 11 relevant",  # score out of bounds
            f"Article 2: Title: {items[1].title} score 8 relevant.",  # valid
            "Article 02: Title: Consultation notice score 7 relevant",  # non-canonical number
        ]
    )
    parsed = service()._process_analysis_response(text, items)
    assert [row["title"] for row in parsed["grc_articles"]] == [items[1].title]
    assert parsed["grc_article_indices"] == [1]
    assert parsed["analysis_rows"] == {"accepted": 1, "skipped": 3}
    assert parsed["summary"]["grc_relevant_count"] == 1


def test_a_misattributed_row_never_credits_either_article():
    items = articles()
    # Article 1's number with article 2's title: neither identity is credited.
    text = "Article 1: Title: Supplier access review score 8 relevant\n" + (
        "Article 1: Title: Consultation notice score 6 relevant"
    )
    parsed = service()._process_analysis_response(text, items)
    assert [row["title"] for row in parsed["grc_articles"]] == ["Consultation notice"]
    assert parsed["analysis_rows"] == {"accepted": 1, "skipped": 1}


def test_a_repeated_identity_is_kept_once():
    items = articles()
    row = f"Article 2: Title: {items[1].title} score 8 relevant"
    parsed = service()._process_analysis_response(f"{row}\n{row}.", items)
    assert [r["title"] for r in parsed["grc_articles"]] == [items[1].title]
    assert parsed["analysis_rows"] == {"accepted": 1, "skipped": 1}


def test_a_fully_valid_response_reports_no_skipped_rows():
    items = articles()
    text = (
        f"Article 1: Title: {items[0].title} score 5 relevant\n"
        f"Article 2: Title: {items[1].title} score 9 relevant"
    )
    parsed = service()._process_analysis_response(text, items)
    assert parsed["analysis_rows"] == {"accepted": 2, "skipped": 0}


def test_malformed_rows_never_fail_the_analysis_or_select_every_article():
    import asyncio
    from types import SimpleNamespace

    items = articles()
    model = service()

    def answering(text):
        async def invoke(**_kwargs):
            return SimpleNamespace(text=text)

        return invoke

    model._invoke = answering(
        f"Article 2: Title: {items[1].title} score 8 relevant\n"
        "Article 1: Title: Not the supplied title score 8 relevant"
    )
    mixed = asyncio.run(model._analyze_articles_with_model(items))
    assert "error" not in mixed
    assert [row["title"] for row in mixed["grc_articles"]] == [items[1].title]

    model._invoke = answering("Article 1: Title: Not the supplied title score 8 relevant")
    unusable = asyncio.run(model._analyze_articles_with_model(items))
    assert "error" not in unusable
    assert unusable["grc_articles"] == [] and unusable["grc_article_indices"] == []
    assert unusable["analysis_rows"] == {"accepted": 0, "skipped": 1}


@pytest.mark.parametrize(
    "decorated",
    [
        "- Article 2: Title: Supplier access review score 8 relevant",
        "* Article 2: Title: Supplier access review score 8 relevant",
        "1. Article 2: Title: Supplier access review score 8 relevant",
        "**Article 2**: Title: Supplier access review score 8 relevant",
        "Article 2: Title: Supplier access review score 10.0 relevant.",
    ],
)
def test_list_markers_and_emphasis_do_not_change_identity(decorated):
    parsed = service()._process_analysis_response(decorated, articles())
    assert parsed["grc_article_indices"] == [1]
    assert parsed["analysis_rows"] == {"accepted": 1, "skipped": 0}


@pytest.mark.parametrize(
    "decorated",
    [
        "- Article 1: Title: Supplier access review score 8 relevant",
        "Article 1: Title: Supplier access review score 8 relevant, because supplier",
        "Article \u0661: Title: Consultation notice score 8 relevant",
    ],
)
def test_decorated_or_commented_claims_still_bind_exactly(decorated):
    parsed = service()._process_analysis_response(decorated, articles())
    assert parsed["grc_article_indices"] == []
    assert parsed["analysis_rows"] == {"accepted": 0, "skipped": 1}


def test_an_undeclared_empty_answer_selects_nothing_but_is_not_known():
    parsed = service()._process_analysis_response(
        "No supplied article has clear GRC implications.\nRegulations: none", articles()
    )
    assert parsed["grc_articles"] == [] and parsed["grc_article_indices"] == []
    assert parsed["selection_known"] is False


def test_the_prompt_owns_the_declared_empty_answer():
    prompt = service()._create_analysis_prompt(articles())
    assert "reply with exactly this single line and nothing else: No articles selected" in prompt


def test_mixed_valid_rows_and_mismatched_claims_never_credit_the_wrong_article():
    items = articles()
    text = (
        f"Article 1: Title: {items[0].title} score 7 relevant\n"
        "Article 1: Title: Supplier access review score 9 relevant, dup\n"
        "Article 5 of GDPR is cited in the notice.\n"
    )
    parsed = service()._process_analysis_response(text, items)
    assert parsed["grc_article_indices"] == [0]
    assert parsed["analysis_rows"] == {"accepted": 1, "skipped": 1}


def test_positions_not_titles_select_when_supplied_titles_collide():
    from core.article_selection import selected_article_mask

    items = articles() + [articles()[1].model_copy(update={"url": "https://other.example.test/x"})]
    parsed = service()._process_analysis_response(
        f"Article 2: Title: {items[1].title} score 8 relevant", items
    )
    assert selected_article_mask(items, parsed) == [False, True, False]


def test_unusable_fallback_rows_never_refuse_an_enabled_relevance_selection(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from config.settings import settings
    from services.relevance_decisions import ArticleDecision, RelevanceResult

    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "grc_relevance_mode", "enabled")
    model = GRCModelService()
    decisions = RelevanceResult(
        (
            ArticleDecision(0, "relevant", {"relevant": 0.99}, 0.95),
            ArticleDecision(1, "insufficient_evidence", {"insufficient_evidence": 0.6}, 0.95),
        ),
        ("typesafe/jev-1.13",),
        10,
        0,
        0.0,
        0.01,
    )
    monkeypatch.setattr(model.relevance_client, "classify", AsyncMock(return_value=decisions))

    async def invoke(**_kwargs):
        return SimpleNamespace(text="Article 9: Title: Nothing supplied score 8 relevant")

    monkeypatch.setattr(model, "_invoke", invoke)
    analysis = asyncio.run(model.analyze_articles_for_grc(articles()))
    assert "error" not in analysis
    # The uncertain article stays selected; the confident one is kept too.
    assert analysis["grc_article_indices"] == [0, 1]
    diagnostics = model.last_relevance_diagnostics
    assert diagnostics is not None and diagnostics["fallback_status"] == "ok"


@pytest.mark.parametrize(
    "line",
    [
        # Two rows on one line: neither is a single exact row.
        "Article 1: Title: Consultation notice score 8 relevant. "
        "Article 2: Title: Supplier access review score 9 relevant",
        "Article 2: Title: Supplier access review score 8 relevant? No - not relevant",
    ],
)
def test_text_after_relevant_cannot_hide_a_row_or_reverse_the_claim(line):
    parsed = service()._process_analysis_response(line, articles())
    assert parsed["grc_article_indices"] == []
    assert parsed["analysis_rows"] == {"accepted": 0, "skipped": 1}


def test_emphasis_inside_a_title_is_part_of_the_title():
    items = articles("Python __init__ **flaw** review")
    parsed = service()._process_analysis_response(
        f"**Article 2: Title: {items[1].title} score 8 relevant**", items
    )
    assert parsed["grc_article_indices"] == [1]


def test_decorated_reason_lines_stay_commentary():
    items = articles()
    text = (
        f"Article 2: Title: {items[1].title} score 8 relevant\n"
        "- Reason: regulation and risk wording mentions GDPR."
    )
    parsed = service()._process_analysis_response(text, items)
    assert parsed["analysis"]["regulations_mentioned"] == []


def test_skipped_claims_keep_their_regulation_notes():
    text = "Regulations:\nArticle 33: GDPR breach notification applies to the notice."
    parsed = service()._process_analysis_response(text, articles())
    assert parsed["analysis_rows"] == {"accepted": 0, "skipped": 1}
    assert parsed["analysis"]["regulations_mentioned"] == ["GDPR"]


def enabled_model(monkeypatch, decisions, response):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from config.settings import settings

    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "grc_relevance_mode", "enabled")
    model = GRCModelService()
    monkeypatch.setattr(model.relevance_client, "classify", AsyncMock(return_value=decisions))

    async def invoke(**_kwargs):
        return SimpleNamespace(text=response)

    monkeypatch.setattr(model, "_invoke", invoke)
    return model


def three_articles():
    return articles() + [
        ArticleInput(
            title="Payments regulator fine",
            url="https://payments.example.test/fine",
            content="A regulator fined a payments firm.",
            published=datetime(2026, 11, 4, tzinfo=timezone.utc),
        )
    ]


def test_enrichment_row_positions_are_subset_relative_and_never_change_selection(monkeypatch):
    import asyncio

    from services.relevance_decisions import ArticleDecision, RelevanceResult

    items = three_articles()
    decisions = RelevanceResult(
        (
            ArticleDecision(0, "irrelevant", {"irrelevant": 0.99}, 0.95),
            ArticleDecision(1, "relevant", {"relevant": 0.99}, 0.95),
            ArticleDecision(2, "insufficient_evidence", {"insufficient_evidence": 0.6}, 0.95),
        ),
        ("typesafe/jev-1.13",),
        10,
        0,
        0.0,
        0.01,
    )
    # The enrichment call sees only the uncertain article, as its article 1.
    model = enabled_model(
        monkeypatch, decisions, f"Article 1: Title: {items[2].title} score 8 relevant"
    )
    analysis = asyncio.run(model.analyze_articles_for_grc(items))
    assert analysis["grc_article_indices"] == [1, 2]


def test_all_invalid_rows_on_the_full_legacy_route_are_unknown_not_rejections(monkeypatch):
    import asyncio

    from services.relevance_decisions import DecisionError

    items = three_articles()
    model = enabled_model(monkeypatch, None, "Article 1: Title: Garbled title score 8 relevant")
    from unittest.mock import AsyncMock

    monkeypatch.setattr(
        model.relevance_client, "classify", AsyncMock(side_effect=DecisionError("timeout"))
    )
    analysis = asyncio.run(model.analyze_articles_for_grc(items))
    assert "error" not in analysis
    records = model.last_selection_records
    assert records is not None and [r.model_selected for r in records] == [None, None, None]
    summary = model.relevance_summary()
    assert summary is not None
    assert summary["route"] == "legacy_full" and summary["dropped_positions"] == 0
    assert summary["analysis_rows"] == {"accepted": 0, "skipped": 1, "selection_known": False}


@pytest.mark.parametrize(
    "line",
    [
        "Article 2: Title: Supplier access review score 8 relevant (not relevant)",
        "Article 2: Title: Supplier access review score 8 relevant (correction: ignore)",
    ],
)
def test_a_parenthetical_cannot_reverse_or_amend_a_row(line):
    parsed = service()._process_analysis_response(line, articles())
    assert parsed["grc_article_indices"] == []
    assert parsed["analysis_rows"] == {"accepted": 0, "skipped": 1}


@pytest.mark.parametrize(
    "reason",
    [
        "**Reason:** NIST",
        "**Reason**: NIST",
        "*Reason:* NIST",
        "- **Reason:** NIST",
        "Reason: NIST",
    ],
)
def test_emphasized_reason_lines_are_commentary(reason):
    text = "Regulations: GDPR\n" + reason
    parsed = service()._process_analysis_response(text, articles())
    assert parsed["analysis"]["regulations_mentioned"] == ["GDPR"]


def legacy_full_model(monkeypatch, mode, response):
    from unittest.mock import AsyncMock

    from services.relevance_decisions import DecisionError

    model = enabled_model(monkeypatch, None, response)
    monkeypatch.setattr(model, "relevance_mode", mode)
    monkeypatch.setattr(
        model.relevance_client, "classify", AsyncMock(side_effect=DecisionError("timeout"))
    )
    return model


def test_shadow_legacy_full_records_unusable_rows_as_unknown(monkeypatch):
    import asyncio

    items = three_articles()
    model = legacy_full_model(
        monkeypatch, "shadow", "Article 2: Title: Garbled title score 8 relevant"
    )
    analysis = asyncio.run(model.analyze_articles_for_grc(items))
    assert "error" not in analysis
    records = model.last_selection_records
    assert records is not None and [r.model_selected for r in records] == [None, None, None]


def test_legacy_full_with_a_usable_row_records_the_normal_mask(monkeypatch):
    import asyncio

    items = three_articles()
    model = legacy_full_model(
        monkeypatch,
        "enabled",
        f"Article 3: Title: {items[2].title} score 8 relevant\n"
        "Article 1: Title: Garbled title score 8 relevant",
    )
    asyncio.run(model.analyze_articles_for_grc(items))
    records = model.last_selection_records
    assert records is not None
    assert [r.model_selected for r in records] == [False, False, True]
    summary = model.relevance_summary()
    assert summary is not None
    assert summary["analysis_rows"] == {"accepted": 1, "skipped": 1, "selection_known": True}

    def storage_safe(value):
        if isinstance(value, dict):
            return all(isinstance(k, str) and storage_safe(v) for k, v in value.items())
        if isinstance(value, list):
            return all(storage_safe(v) for v in value)
        return value is None or isinstance(value, (str, int, bool))

    assert storage_safe(summary)


VALID_2 = "Article 2: Title: Supplier access review score 8 relevant"
VALID_1 = "Article 1: Title: Consultation notice score 7 relevant"

# Every counterexample from the earlier review rounds, with the invariant's expectation:
# (response, credited positions, whether the response is a known selection).
REGRESSION_MATRIX = [
    (VALID_2, [1], True),
    (f"{VALID_1}\n{VALID_2}", [0, 1], True),
    (f"- {VALID_2}", [1], True),
    (f"1. {VALID_2}", [1], True),
    (f"**{VALID_2}**", [1], True),
    ("**Article 2**: Title: Supplier access review score 8 relevant", [1], True),
    (f"{VALID_2}\n{VALID_2}.", [1], True),
    (f"{VALID_2}\nArticle 3: Title: Supplier access review score 8 relevant", [1], True),
    # Zero accepted rows without the declared empty answer: unknown, never a drop.
    ("Article 3: Title: Supplier access review score 8 relevant", [], False),
    ("Article 2: Title: Unknown title score 8 relevant", [], False),
    ("Article 02: Title: Supplier access review score 8 relevant", [], False),
    ("Article 2: Title: Supplier access review score 11 relevant", [], False),
    ("Article 2: Title: Supplier access review score nan relevant", [], False),
    ("Article 1: Title: Supplier access review score 8 relevant", [], False),
    (
        "Article 2: Title: Supplier access review score 8 relevant because review is warranted.",
        [],
        False,
    ),
    ("Article 2: Title: Supplier access review score 8 relevant? No - not relevant", [], False),
    ("Article 2: Title: Supplier access review score 8 relevant (not relevant)", [], False),
    (f"{VALID_1}. {VALID_2}", [], False),
    ("> Article 9: Title: Nothing supplied score 8 relevant", [], False),
    (f"> {VALID_2}", [], False),
    ("### Article 1: Title: Consultation notice score 8 relevant", [], False),
    ("| Article 1: Title: Consultation notice score 8 relevant |", [], False),
    ("*Article 1: Title: Consultation notice score 8 relevant*", [], False),
    ("Article 1 - Title: Consultation notice score 8 relevant", [], False),
    ("Unrecognized narrative", [], False),
    ("", [], False),
    # Known empty only when the whole response is exactly the owned sentinel.
    ("No articles selected", [], True),
    ("  No articles selected\n", [], True),
    ("No articles selected.", [], False),
    ("- No articles selected", [], False),
    ("no articles selected", [], False),
    ("No articles selected\nArticle 3: Title: Supplier access review score 8 relevant", [], False),
    ("No articles selected\n> Article 9: Title: Nothing supplied score 8 relevant", [], False),
    ("No articles selected\nRegulations: none", [], False),
    (f"No articles selected\n{VALID_2}", [1], True),
]


@pytest.mark.parametrize(("response", "positions", "known"), REGRESSION_MATRIX)
def test_regression_matrix_credits_only_owned_rows_and_marks_unknown_answers(
    response, positions, known
):
    parsed = service()._process_analysis_response(response, articles())
    assert parsed["grc_article_indices"] == positions
    assert [row["title"] for row in parsed["grc_articles"]] == [
        articles()[i].title for i in positions
    ]
    assert parsed["selection_known"] is known
    assert len(parsed["grc_articles"]) <= len(articles())


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("> Article 9: Title: Nothing supplied score 8 relevant", [None, None, None]),
        ("Unrecognized narrative", [None, None, None]),
        ("No articles selected", [False, False, False]),
    ],
)
def test_the_evidence_layer_records_only_declared_empty_answers_as_drops(
    monkeypatch, response, expected
):
    import asyncio

    model = legacy_full_model(monkeypatch, "enabled", response)
    asyncio.run(model.analyze_articles_for_grc(three_articles()))
    records = model.last_selection_records
    assert records is not None and [r.model_selected for r in records] == expected
