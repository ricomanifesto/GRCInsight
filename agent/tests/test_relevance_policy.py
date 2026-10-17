import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock

from loguru import logger
import pytest

from config.settings import Settings, settings
from models.api import ArticleInput
from services.model_service import GRCModelService
from services.openrouter_client import OpenRouterGeneration
from services.relevance_decisions import ArticleDecision, DecisionError, RelevanceResult


def articles():
    return [
        ArticleInput(
            title="Same title",
            url=f"https://example.com/{i}",
            content="A story about a local garden.",
            published=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
        for i in range(2)
    ]


def result(labels=("relevant", "irrelevant"), probability=0.99):
    return RelevanceResult(
        tuple(
            ArticleDecision(
                i,
                label,
                {
                    key: probability if key == label else (1 - probability) / 2
                    for key in ("relevant", "irrelevant", "insufficient_evidence")
                },
                0.95,
            )
            for i, label in enumerate(labels)
        ),
        ("typesafe/jev-1.13",),
        100,
        0,
        0.0000042,
        0.01,
    )


def service(monkeypatch, mode):
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "grc_relevance_mode", mode)
    model = GRCModelService()
    monkeypatch.setattr(
        model, "_analyze_articles_with_model", AsyncMock(return_value={"legacy": True})
    )
    return model


def test_default_is_off_and_does_not_construct_or_call_decision_client(monkeypatch):
    assert Settings.model_fields["grc_relevance_mode"].default == "off"
    model = service(monkeypatch, "off")
    assert model.relevance_client is None
    assert asyncio.run(model.analyze_articles_for_grc(articles())) == {"legacy": True}
    assert model.last_relevance_diagnostics is None


def test_enabled_uses_positions_and_preserves_local_entities(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(return_value=result())
    inputs = articles()
    inputs[1].content = "GDPR Article 5 requires a review of a vendor vulnerability."
    analysis = asyncio.run(model.analyze_articles_for_grc(inputs))
    assert analysis["grc_article_indices"] == [0, 1]
    assert analysis["summary"]["grc_relevant_count"] == 2
    assert analysis["analysis"]["regulations_mentioned"]
    assert analysis["analysis"]["risk_categories"] == [
        "Third-party and supply chain exposure",
        "Vulnerability and patch management",
    ]
    assert "relevance_score" not in analysis["grc_articles"][0]
    assert model.last_relevance_diagnostics["status"] == "used"
    model._analyze_articles_with_model.assert_not_called()


@pytest.mark.parametrize(
    "decision_result",
    [result(probability=0.6), result(labels=("insufficient_evidence",) * 2)],
)
def test_uncertainty_falls_back_for_the_whole_batch(monkeypatch, decision_result):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(return_value=decision_result)
    assert asyncio.run(model.analyze_articles_for_grc(articles())) == {"legacy": True}
    assert model.last_relevance_diagnostics["status"] == "uncertain"
    model._analyze_articles_with_model.assert_awaited_once()


def test_mixed_decisions_only_fall_back_for_uncertain_positions(monkeypatch):
    model = service(monkeypatch, "enabled")
    inputs = articles() + articles()
    # All identities collide deliberately; a subset selection must not select
    # a confident negative outside that subset.
    for item in inputs:
        item.url = inputs[0].url
    typed = result(labels=("irrelevant", "relevant", "insufficient_evidence", "relevant"))
    typed = replace(typed, decisions=typed.decisions[:3] + (result(probability=0.6).decisions[0],))
    typed = replace(typed, decisions=typed.decisions[:3] + (replace(typed.decisions[3], index=3),))
    model.relevance_client.classify = AsyncMock(return_value=typed)
    # The subset call selects nothing. Under keep-uncertain-v1 it only enriches
    # aggregates; both uncertain positions stay selected.
    model._analyze_articles_with_model.return_value = {
        "grc_articles": [],
        "analysis": {"risk_categories": ["Operational continuity"]},
    }
    analysis = asyncio.run(model.analyze_articles_for_grc(inputs))
    model._analyze_articles_with_model.assert_awaited_once_with(inputs[2:])
    assert analysis["grc_article_indices"] == [1, 2, 3]
    assert analysis["summary"] == {"total_articles": 4, "grc_relevant_count": 3}
    assert analysis["analysis"]["risk_categories"] == ["Operational continuity"]
    assert model.last_relevance_diagnostics["uncertain_count"] == 2
    assert model.last_relevance_diagnostics["status"] == "partial"
    assert [record.disposition for record in model.last_selection_records] == [
        "accepted_irrelevant",
        "accepted_relevant",
        "insufficient_evidence_kept",
        "uncertain_kept",
    ]
    assert model.last_relevance_diagnostics["fallback_status"] == "ok"
    assert model.last_relevance_diagnostics["fallback_size"] == 2


def test_subset_failure_remains_an_error_for_the_original_batch(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("relevant", "insufficient_evidence"))
    )
    model._analyze_articles_with_model.return_value = {
        "error": "Analysis unavailable",
        "grc_articles": [],
        "summary": {"total_articles": 1, "grc_relevant_count": 0},
    }
    analysis = asyncio.run(model.analyze_articles_for_grc(articles()))
    assert analysis["error"] == "Analysis unavailable"
    assert analysis["summary"]["total_articles"] == 2
    assert "grc_article_indices" not in analysis
    model._analyze_articles_with_model.assert_awaited_once_with(articles()[1:])


def test_noncontiguous_subset_positions_and_local_context_are_preserved(monkeypatch):
    model = service(monkeypatch, "enabled")
    inputs = articles() + articles()
    inputs[2].content = "GDPR applies to the vendor vulnerability."
    model.relevance_client.classify = AsyncMock(
        return_value=result(
            labels=("relevant", "insufficient_evidence", "irrelevant", "insufficient_evidence")
        )
    )
    model._analyze_articles_with_model.return_value = {
        "grc_article_indices": [1],
        "analysis": {"regulations_mentioned": ["GDPR", "SOX"]},
    }
    analysis = asyncio.run(model.analyze_articles_for_grc(inputs))
    # Position 1 stays selected although the subset output chose only position 3.
    assert analysis["grc_article_indices"] == [0, 1, 2, 3]
    assert analysis["summary"]["grc_relevant_count"] == 4
    assert "SOX" in analysis["analysis"]["regulations_mentioned"]
    assert "Vulnerability and patch management" in analysis["analysis"]["risk_categories"]
    model._analyze_articles_with_model.assert_awaited_once_with([inputs[1], inputs[3]])


def test_subset_cancellation_propagates_without_retry(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("irrelevant", "insufficient_evidence"))
    )
    model._analyze_articles_with_model.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(model.analyze_articles_for_grc(articles()))
    model._analyze_articles_with_model.assert_awaited_once_with(articles()[1:])


def test_provider_failure_falls_back_and_does_not_leak_inputs(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(side_effect=DecisionError("timeout"))
    assert asyncio.run(model.analyze_articles_for_grc(articles())) == {"legacy": True}
    assert model.last_relevance_diagnostics["status"] == "timeout"
    assert "garden" not in str(model.last_relevance_diagnostics)


def test_shadow_returns_legacy_result_even_when_jev_disagrees(monkeypatch):
    model = service(monkeypatch, "shadow")
    model.relevance_client.classify = AsyncMock(return_value=result())
    assert asyncio.run(model.analyze_articles_for_grc(articles())) == {"legacy": True}
    assert model.last_relevance_diagnostics["status"] == "shadow"
    model.relevance_client.classify.assert_awaited_once()


def test_cancellation_propagates(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(model.analyze_articles_for_grc(articles()))
    model._analyze_articles_with_model.assert_not_called()


def test_empty_input_skips_pilot(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(side_effect=AssertionError("not called"))
    asyncio.run(model.analyze_articles_for_grc([]))
    model.relevance_client.classify.assert_not_called()


def test_analyze_api_keeps_same_title_articles_distinct(monkeypatch):
    from api.routes import analysis as route
    from tests.test_routes import request

    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(return_value=result())
    monkeypatch.setattr(route, "GRCModelService", lambda **_: model)
    response = request(
        "POST",
        "/api/v1/analyze",
        json={"articles": [item.model_dump(mode="json") for item in articles()]},
    )
    assert response.status_code == 200
    value = response.json()
    assert [item["has_grc_content"] for item in value["results"]] == [True, False]
    assert value["summary"]["grc_articles"] == 1


def test_selection_rejects_invalid_position_mapping():
    from core.article_selection import selected_article_mask

    for indices in ([0, 0], [99], [-1], [True], "0"):
        with pytest.raises(ValueError):
            selected_article_mask(articles(), {"grc_article_indices": indices})


@pytest.mark.parametrize("second_label", ["irrelevant", "insufficient_evidence"])
def test_workflow_keeps_sources_and_reconciles_local_positive_counts(monkeypatch, second_label):
    from core import workflow
    from models.api import GRCAnalysisConfig
    from services.model_service import GRCReportGeneration

    model = service(monkeypatch, "enabled")
    inputs = articles()
    # The workflow's existing local risk signal remains positive even if Jev says no.
    inputs[1].content = "The vendor requires a patch for the product vulnerability."
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("irrelevant", second_label))
    )
    captured = {}

    async def report(analysis, feed):
        captured.update(analysis)
        return GRCReportGeneration("# A report", "test/report-writer")

    model.generate_grc_report = report
    monkeypatch.setattr(workflow, "GRCModelService", lambda **_: model)
    monkeypatch.setattr(
        workflow.rss_service,
        "fetch_feed",
        AsyncMock(
            return_value={
                "title": "Example",
                "link": "https://digest.example/",
                "last_updated": "Thu, 01 Oct 2026 01:00:00 GMT",
                "entries": [
                    {"title": item.title, "link": item.url, "content": item.content}
                    for item in inputs
                ],
            }
        ),
    )
    monkeypatch.setattr(
        workflow.rss_service,
        "enrich_articles",
        AsyncMock(side_effect=lambda items: items),
    )
    monkeypatch.setattr(
        workflow,
        "enrich_regulatory_sources",
        AsyncMock(
            side_effect=lambda items, **_: [
                {**item, "effective_date_evidence": None} for item in items
            ]
        ),
    )
    response = asyncio.run(
        workflow.run_grc_analysis_endpoint("https://example.com/feed", GRCAnalysisConfig())
    )
    assert response.status == "completed"
    assert response.articles is not None
    assert response.metadata is not None
    assert [item.has_grc_content for item in response.articles] == [False, True]
    assert response.metadata.grc_article_count == 1
    assert captured["summary"]["grc_relevant_count"] == 1
    assert {source["url"] for source in captured["source_evidence"]} == {
        item.url for item in inputs
    }
    assert response.metadata.resolved_model == "test/report-writer"


def test_shadow_failure_keeps_legacy_analysis(monkeypatch):
    model = service(monkeypatch, "shadow")
    model.relevance_client.classify = AsyncMock(side_effect=DecisionError("invalid_response"))
    assert asyncio.run(model.analyze_articles_for_grc(articles())) == {"legacy": True}
    assert model.last_relevance_diagnostics["status"] == "invalid_response"


def test_failed_decisions_do_not_reuse_previous_raw_result(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(side_effect=[result(), DecisionError("timeout")])
    asyncio.run(model.analyze_articles_for_grc(articles()))
    assert model.last_relevance_result is not None
    asyncio.run(model.analyze_articles_for_grc(articles()))
    assert model.last_relevance_result is None


GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures" / "relevance" / "off-golden.json").read_text(
        encoding="utf-8"
    )
)


def golden_articles():
    return [ArticleInput.model_validate(item) for item in GOLDEN["articles"]]


def prose_service(monkeypatch, mode, prose):
    """Run the real prose parser over a fixed generative response."""
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "grc_relevance_mode", mode)
    model = GRCModelService()
    monkeypatch.setattr(
        model,
        "_invoke",
        AsyncMock(return_value=OpenRouterGeneration(text=prose, resolved_model="test/model")),
    )
    return model


def normalized(analysis):
    return {
        **analysis,
        "analysis": {key: sorted(values) for key, values in analysis["analysis"].items()},
    }


@pytest.mark.parametrize("prose", ["recognized", "unrecognized"])
def test_off_output_matches_pre_change_golden_and_records_nothing(monkeypatch, prose):
    model = prose_service(monkeypatch, "off", GOLDEN["prose"][prose])
    analysis = asyncio.run(model.analyze_articles_for_grc(golden_articles()))
    assert normalized(analysis) == GOLDEN["off"][prose]
    assert model.relevance_client is None
    assert model.last_selection_records is None
    assert model.last_relevance_diagnostics is None


def decision(index, label, probability=0.99):
    return ArticleDecision(
        index,
        label,
        {
            key: probability if key == label else (1 - probability) / 2
            for key in ("relevant", "irrelevant", "insufficient_evidence")
        },
        0.95,
    )


def decided(*decisions):
    return replace(result(), decisions=decisions)


def test_recognized_fallback_format_no_longer_drops_uncertain_articles(monkeypatch):
    # Recognized lines carry trailing text and no URL, so title matching fails.
    model = prose_service(monkeypatch, "enabled", GOLDEN["prose"]["recognized"])
    model.relevance_client.classify = AsyncMock(
        return_value=decided(
            decision(0, "relevant"),
            decision(1, "irrelevant"),
            decision(2, "relevant", 0.7),
            decision(3, "insufficient_evidence"),
        )
    )
    analysis = asyncio.run(model.analyze_articles_for_grc(golden_articles()))
    model._invoke.assert_awaited_once()
    assert analysis["grc_article_indices"] == [0, 2, 3]
    assert [record.disposition for record in model.last_selection_records] == [
        "accepted_relevant",
        "accepted_irrelevant",
        "uncertain_kept",
        "insufficient_evidence_kept",
    ]
    # Aggregates from the subset response are still merged.
    assert "NIST" in analysis["analysis"]["regulations_mentioned"]


def test_unrecognized_fallback_text_keeps_uncertain_articles(monkeypatch):
    model = prose_service(monkeypatch, "enabled", "No structured output.")
    model.relevance_client.classify = AsyncMock(
        return_value=decided(
            decision(0, "irrelevant"),
            decision(1, "irrelevant"),
            decision(2, "relevant"),
            decision(3, "irrelevant", 0.6),
        )
    )
    analysis = asyncio.run(model.analyze_articles_for_grc(golden_articles()))
    records = model.last_selection_records
    assert records[3].disposition == "uncertain_kept"
    assert records[3].model_selected is True
    assert records[1].model_selected is False
    assert 3 in analysis["grc_article_indices"]
    assert 1 not in analysis["grc_article_indices"]


def test_fallback_listing_exact_titles_is_ignored_for_selection(monkeypatch):
    model = service(monkeypatch, "enabled")
    inputs = articles() + articles()
    for index, item in enumerate(inputs):
        item.title = f"Title {index}"
    decisions = result(labels=("irrelevant", "insufficient_evidence", "irrelevant", "relevant"))
    model.relevance_client.classify = AsyncMock(return_value=decisions)
    # The subset names a confident negative and omits the uncertain article.
    model._analyze_articles_with_model.return_value = {
        "grc_articles": [{"title": "Title 0", "url": inputs[0].url}],
        "analysis": {},
    }
    analysis = asyncio.run(model.analyze_articles_for_grc(inputs))
    model._analyze_articles_with_model.assert_awaited_once_with([inputs[1]])
    assert analysis["grc_article_indices"] == [1, 3]


def test_failed_fallback_keeps_error_and_records_unknown_selection(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("irrelevant", "insufficient_evidence"))
    )
    model._analyze_articles_with_model.return_value = {"error": "Analysis unavailable"}
    analysis = asyncio.run(model.analyze_articles_for_grc(articles()))
    assert analysis["error"] == "Analysis unavailable"
    assert analysis["summary"]["total_articles"] == 2
    records = model.last_selection_records
    assert [record.model_selected for record in records] == [None, None]
    # Unknown never becomes a drop.
    assert [record.workflow_selected for record in records] == [None, None]
    assert all(record.reason == "fallback_error" for record in records)
    assert model.last_relevance_diagnostics["fallback_status"] == "error"


def test_all_irrelevant_decisions_are_a_valid_zero_selection(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(return_value=result(labels=("irrelevant",) * 2))
    analysis = asyncio.run(model.analyze_articles_for_grc(articles()))
    model._analyze_articles_with_model.assert_not_called()
    assert "error" not in analysis
    assert analysis["grc_article_indices"] == []
    assert analysis["summary"] == {"total_articles": 2, "grc_relevant_count": 0}
    assert model.last_relevance_diagnostics["fallback_status"] == "not_needed"
    assert [record.workflow_selected for record in model.last_selection_records] == [False, False]


def test_high_probability_insufficient_evidence_is_kept(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("irrelevant", "insufficient_evidence"), probability=0.99)
    )
    model._analyze_articles_with_model.return_value = {"grc_articles": [], "analysis": {}}
    analysis = asyncio.run(model.analyze_articles_for_grc(articles()))
    assert analysis["grc_article_indices"] == [1]
    record = model.last_selection_records[1]
    assert record.disposition == "insufficient_evidence_kept"
    assert record.label == "insufficient_evidence"
    assert record.probabilities["insufficient_evidence"] == 0.99


@pytest.mark.parametrize(
    "code",
    [
        "input_limit",
        "deadline",
        "invalid_response",
        "http_error",
        "response_limit",
        "timeout",
        "transport_error",
    ],
)
def test_each_decision_error_maps_to_a_legacy_full_reason(monkeypatch, code):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(side_effect=DecisionError(code))
    model._analyze_articles_with_model.return_value = {
        "grc_articles": [{"url": articles()[1].url}],
        "analysis": {},
    }
    asyncio.run(model.analyze_articles_for_grc(articles()))
    model._analyze_articles_with_model.assert_awaited_once_with(articles())
    records = model.last_selection_records
    assert [record.route for record in records] == ["legacy_full", "legacy_full"]
    assert {record.reason for record in records} == {f"jev_{code}"}
    assert [record.model_selected for record in records] == [False, True]
    assert model.last_relevance_diagnostics["reason"] == f"jev_{code}"


def test_unexpected_failures_and_partial_decisions_fail_to_internal_error(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(side_effect=RuntimeError("boom"))
    asyncio.run(model.analyze_articles_for_grc(articles()))
    assert {record.reason for record in model.last_selection_records} == {"internal_error"}

    # A missing position is an invariant failure, never a drop.
    partial = result()
    model.relevance_client.classify = AsyncMock(
        return_value=replace(partial, decisions=partial.decisions[:1])
    )
    asyncio.run(model.analyze_articles_for_grc(articles()))
    records = model.last_selection_records
    assert [record.index for record in records] == [0, 1]
    assert {record.reason for record in records} == {"internal_error"}
    assert model._analyze_articles_with_model.await_count == 2


def test_all_uncertain_records_keep_raw_labels_for_the_legacy_batch(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(return_value=result(probability=0.6))
    asyncio.run(model.analyze_articles_for_grc(articles()))
    records = model.last_selection_records
    assert {record.reason for record in records} == {"all_uncertain"}
    assert [record.label for record in records] == ["relevant", "irrelevant"]


def test_records_are_total_and_ordered_for_noncontiguous_subsets_and_duplicate_titles(monkeypatch):
    model = service(monkeypatch, "enabled")
    inputs = articles() + articles() + articles()
    for index, item in enumerate(inputs):
        item.url = f"https://example.com/{index}"
    labels = (
        "insufficient_evidence",
        "relevant",
        "irrelevant",
        "insufficient_evidence",
        "relevant",
        "insufficient_evidence",
    )
    decisions = result(labels=labels)
    # Classifier output order must not change record order.
    model.relevance_client.classify = AsyncMock(
        return_value=replace(decisions, decisions=tuple(reversed(decisions.decisions)))
    )
    model._analyze_articles_with_model.return_value = {"grc_articles": [], "analysis": {}}
    analysis = asyncio.run(model.analyze_articles_for_grc(inputs))
    model._analyze_articles_with_model.assert_awaited_once_with([inputs[0], inputs[3], inputs[5]])
    records = model.last_selection_records
    assert [record.index for record in records] == list(range(6))
    assert len({record.article_key for record in records}) == 6
    assert records[2].article_key == hashlib.sha256(inputs[2].url.encode()).hexdigest()
    assert analysis["grc_article_indices"] == [0, 1, 3, 4, 5]


def test_records_and_logs_hold_no_article_text(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(return_value=result())
    messages = []
    handler = logger.add(lambda message: messages.append(str(message)), level="INFO")
    try:
        asyncio.run(model.analyze_articles_for_grc(articles()))
    finally:
        logger.remove(handler)
    serialized = json.dumps([record.as_dict() for record in model.last_selection_records])
    for text in ("garden", "Same title", "example.com"):
        assert text not in serialized
        assert not any(text in message for message in messages)
    assert any("Article relevance selection" in message for message in messages)


def test_cost_stays_none_when_usage_is_missing(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(return_value=replace(result(), cost=None))
    asyncio.run(model.analyze_articles_for_grc(articles()))
    assert model.last_relevance_diagnostics["cost"] is None


def test_shadow_returns_legacy_and_records_equal_enabled_records(monkeypatch):
    decisions = result(labels=("relevant", "insufficient_evidence", "irrelevant", "relevant"))
    inputs = articles() + articles()
    for index, item in enumerate(inputs):
        item.url = f"https://example.com/{index}"
    shadow = service(monkeypatch, "shadow")
    shadow.relevance_client.classify = AsyncMock(return_value=decisions)
    legacy = {"legacy": True, "grc_articles": [{"url": inputs[2].url}]}
    shadow._analyze_articles_with_model.return_value = legacy
    assert asyncio.run(shadow.analyze_articles_for_grc(inputs)) == legacy
    shadow._analyze_articles_with_model.assert_awaited_once_with(inputs)
    assert shadow.last_relevance_diagnostics["fallback_status"] == "not_run"

    enabled = service(monkeypatch, "enabled")
    enabled.relevance_client.classify = AsyncMock(return_value=decisions)
    enabled._analyze_articles_with_model.return_value = {"grc_articles": [], "analysis": {}}
    asyncio.run(enabled.analyze_articles_for_grc(inputs))
    assert shadow.last_selection_records == enabled.last_selection_records
    assert [record.model_selected for record in shadow.last_selection_records] == [
        True,
        True,
        False,
        True,
    ]


def test_shadow_counterfactual_for_failed_decisions_uses_the_legacy_selection(monkeypatch):
    model = service(monkeypatch, "shadow")
    model.relevance_client.classify = AsyncMock(side_effect=DecisionError("timeout"))
    legacy = {"grc_articles": [{"url": articles()[0].url}], "analysis": {}}
    model._analyze_articles_with_model.return_value = legacy
    assert asyncio.run(model.analyze_articles_for_grc(articles())) == legacy
    records = model.last_selection_records
    assert [record.model_selected for record in records] == [True, False]
    assert {record.reason for record in records} == {"jev_timeout"}


def test_shadow_record_failure_never_blocks_the_legacy_result(monkeypatch):
    from services import model_service

    model = service(monkeypatch, "shadow")
    model.relevance_client.classify = AsyncMock(return_value=result())
    monkeypatch.setattr(
        model_service, "selection_records", lambda *_, **__: (_ for _ in ()).throw(KeyError())
    )
    assert asyncio.run(model.analyze_articles_for_grc(articles())) == {"legacy": True}
    assert model.last_selection_records is None
    assert model.last_relevance_diagnostics["selection_status"] == "internal_error"


@pytest.mark.parametrize("failing", ["decisions", "subset"])
def test_cancellation_leaves_no_selection_record(monkeypatch, failing):
    model = service(monkeypatch, "enabled")
    if failing == "decisions":
        model.relevance_client.classify = AsyncMock(side_effect=asyncio.CancelledError())
    else:
        model.relevance_client.classify = AsyncMock(
            return_value=result(labels=("irrelevant", "insufficient_evidence"))
        )
        model._analyze_articles_with_model.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(model.analyze_articles_for_grc(articles()))
    assert model.last_selection_records is None


def run_workflow(monkeypatch, model, inputs):
    from core import workflow
    from models.api import GRCAnalysisConfig
    from services.model_service import GRCReportGeneration

    captured = {}

    async def report(analysis, feed):
        captured.update(analysis)
        return GRCReportGeneration("# A report", "test/report-writer")

    model.generate_grc_report = report
    monkeypatch.setattr(workflow, "GRCModelService", lambda **_: model)
    monkeypatch.setattr(
        workflow.rss_service,
        "fetch_feed",
        AsyncMock(
            return_value={
                "title": "Example",
                "link": "https://digest.example/",
                "last_updated": "Thu, 01 Oct 2026 01:00:00 GMT",
                "entries": [
                    {
                        "title": item.title,
                        "link": item.url,
                        "content": item.content,
                        "summary": item.summary,
                    }
                    for item in inputs
                ],
            }
        ),
    )
    monkeypatch.setattr(
        workflow.rss_service, "enrich_articles", AsyncMock(side_effect=lambda items: items)
    )
    monkeypatch.setattr(
        workflow,
        "enrich_regulatory_sources",
        AsyncMock(
            side_effect=lambda items, **_: [
                {**item, "effective_date_evidence": None} for item in items
            ]
        ),
    )
    response = asyncio.run(
        workflow.run_grc_analysis_endpoint("https://example.com/feed", GRCAnalysisConfig())
    )
    assert response.status == "completed"
    return response, captured


def test_source_evidence_is_identical_between_off_and_enabled(monkeypatch):
    inputs = golden_articles()
    evidence = {}
    for mode in ("off", "enabled"):
        model = prose_service(monkeypatch, mode, GOLDEN["prose"]["recognized"])
        if mode == "enabled":
            model.relevance_client.classify = AsyncMock(
                return_value=decided(
                    decision(0, "irrelevant"),
                    decision(1, "irrelevant"),
                    decision(2, "irrelevant"),
                    decision(3, "relevant", 0.6),
                )
            )
        response, captured = run_workflow(monkeypatch, model, inputs)
        evidence[mode] = captured["source_evidence"]
        if mode == "enabled":
            # The workflow and its records apply the same effective rule.
            assert [item.has_grc_content for item in response.articles] == [
                record.workflow_selected for record in model.last_selection_records
            ]
            assert response.metadata.grc_article_count == sum(
                record.workflow_selected for record in model.last_selection_records
            )
    assert evidence["off"] == evidence["enabled"]
    assert {item["url"] for item in evidence["enabled"]} == {item.url for item in inputs}
