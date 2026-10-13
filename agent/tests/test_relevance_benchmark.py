import asyncio
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

from core.relevance_benchmark import classification_metrics, run_comparison
from tests.test_relevance_policy import articles, result, service


def test_missing_predictions_count_against_recall_and_accuracy():
    metrics = classification_metrics(
        ["relevant", "relevant", "irrelevant"], ["relevant", None, "relevant"]
    )
    assert metrics["accuracy"] == 1 / 3
    assert metrics["relevant_recall"] == 0.5
    assert metrics["false_positive_rate"] == 1
    assert metrics["missing_predictions"] == 1


def test_replay_separates_labels_and_measures_fallback_cost_in_time(monkeypatch):
    model = service(monkeypatch, "off")
    model._analyze_articles_with_model = AsyncMock(
        return_value={"grc_articles": [], "summary": {"grc_relevant_count": 0}}
    )
    decision_client = AsyncMock()
    decision_client.classify.return_value = result(probability=0.6)
    summary = asyncio.run(
        run_comparison(articles(), ["relevant", "irrelevant"], model, decision_client, repeats=2)
    )
    assert summary["repeats"] == 2
    assert summary["jev"]["fallback_rate"] == 1
    assert summary["jev"]["p50_seconds"] > 0
    assert summary["enabled_estimate"]["p50_seconds"] >= summary["legacy"]["p50_seconds"]
    assert all(call.args == (articles(),) for call in decision_client.classify.await_args_list)


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
