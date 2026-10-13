import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from config.settings import Settings, settings
from models.api import ArticleInput
from services.model_service import GRCModelService
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
    model._analyze_articles_with_model.return_value = {
        "grc_articles": [{"url": inputs[0].url}],
        "analysis": {"risk_categories": ["Operational continuity"]},
    }
    analysis = asyncio.run(model.analyze_articles_for_grc(inputs))
    model._analyze_articles_with_model.assert_awaited_once_with(inputs[2:])
    assert analysis["grc_article_indices"] == [1, 2, 3]
    assert analysis["summary"] == {"total_articles": 4, "grc_relevant_count": 3}
    assert analysis["analysis"]["risk_categories"] == ["Operational continuity"]
    assert model.last_relevance_diagnostics["uncertain_count"] == 2
    assert model.last_relevance_diagnostics["status"] == "partial"


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
    assert analysis["grc_article_indices"] == [0, 2, 3]
    assert analysis["summary"]["grc_relevant_count"] == 3
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
