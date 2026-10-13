import asyncio
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest
import httpx

from config.settings import settings
from core.relevance_benchmark import classification_metrics, run_comparison
from services.model_service import GRCModelService
from tests.test_relevance_policy import articles, result, service


def test_missing_predictions_count_against_recall_and_accuracy():
    metrics = classification_metrics(
        ["relevant", "relevant", "irrelevant"], ["relevant", None, "relevant"]
    )
    assert metrics["accuracy"] == 1 / 3
    assert metrics["relevant_recall"] == 0.5
    assert metrics["false_positive_rate"] == 1
    assert metrics["missing_predictions"] == 1


def test_replay_measures_actual_subset_fallback_and_alternates_order(monkeypatch):
    model = service(monkeypatch, "enabled")
    model._analyze_articles_with_model = AsyncMock(
        return_value={"grc_articles": [], "summary": {"grc_relevant_count": 0}}
    )
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("relevant", "insufficient_evidence"))
    )
    summary = asyncio.run(
        run_comparison(articles(), ["relevant", "irrelevant"], lambda: model, repeats=2)
    )
    assert summary["repeats"] == 2
    assert summary["decisions"]["fallback_batch_rate"] == 1
    assert summary["decisions"]["fallback_article_rate"] == 0.5
    assert summary["enabled"]["p50_seconds"] > 0
    assert summary["enabled"]["accuracy"] == 1
    assert summary["decisions"]["accuracy"] == 0.5
    assert summary["decisions"]["predicted_insufficient_evidence"] == 2
    assert summary["runs"][0]["decision_predictions"] == [
        "relevant",
        "insufficient_evidence",
    ]
    assert summary["enabled"]["cost"] is None
    assert summary["decisions"]["cost"] == 0.0000084
    calls = model._analyze_articles_with_model.await_args_list
    assert [call.args[0] for call in calls] == [
        articles(),
        articles()[1:],
        articles()[1:],
        articles(),
    ]
    assert all(
        call.args == (articles(),) for call in model.relevance_client.classify.await_args_list
    )


def test_replay_counts_failed_subset_as_missing_predictions(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("relevant", "insufficient_evidence"))
    )
    model._analyze_articles_with_model.return_value = {"error": "unavailable"}
    summary = asyncio.run(
        run_comparison(articles(), ["relevant", "irrelevant"], lambda: model, repeats=1)
    )
    assert summary["enabled"]["missing_predictions"] == 2
    assert summary["enabled"]["relevant_recall"] == 0


def test_replay_scores_insufficient_evidence_decisions(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("relevant", "insufficient_evidence"))
    )
    summary = asyncio.run(
        run_comparison(articles(), ["relevant", "insufficient_evidence"], lambda: model, repeats=1)
    )
    assert summary["decisions"]["accuracy"] == 1
    assert summary["decisions"]["predicted_insufficient_evidence"] == 1


def test_replay_requires_enabled_policy(monkeypatch):
    with pytest.raises(ValueError, match="enabled"):
        asyncio.run(
            run_comparison(
                articles(), ["relevant", "irrelevant"], lambda: service(monkeypatch, "off")
            )
        )


def test_replay_uses_independent_workflow_deadlines(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "grc_relevance_mode", "enabled")
    clock = [0.0]
    created = []
    requests = []

    async def complete(request):
        requests.append(request)
        clock[0] += 2
        return httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [{"message": {"content": "Analysis complete"}}],
            },
        )

    def factory():
        model = GRCModelService()
        model.client.clock = lambda: clock[0]
        model.client.total_timeout = 1
        model.client.transport = httpx.MockTransport(complete)
        assert model.relevance_client is not None
        monkeypatch.setattr(
            model.relevance_client, "classify", AsyncMock(return_value=result(probability=0.6))
        )
        created.append(model)
        return model

    summary = asyncio.run(
        run_comparison(articles(), ["relevant", "irrelevant"], factory, repeats=3)
    )
    assert len(created) == len(requests) == 6
    assert summary["legacy"]["missing_predictions"] == 0
    assert summary["enabled"]["missing_predictions"] == 0


def test_replay_defaults_to_validation_without_credentials_or_network(tmp_path):
    cases = tmp_path / "cases.json"
    cases.write_text(
        json.dumps(
            [
                {"article": item.model_dump(mode="json"), "expected": label}
                for item, label in zip(articles(), ["relevant", "irrelevant"])
            ]
        )
    )
    script = Path(__file__).resolve().parents[2] / "scripts" / "benchmark_relevance.py"
    process = subprocess.run(
        [sys.executable, str(script), str(cases)],
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(process.stdout)
    assert report == {"cases": 2, "status": "validated_only", "network_calls": 0}
