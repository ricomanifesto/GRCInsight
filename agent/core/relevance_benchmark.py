"""Replay article analysis without report generation or publication."""

from __future__ import annotations

from collections import Counter
import math
from statistics import median
import time
from typing import Any

from core.article_selection import selected_article_mask
from core.entities import analyze_article_grc_content
from models.api import ArticleInput
from services.model_service import GRCModelService
from services.relevance_decisions import DecisionError, LABELS, RelevanceClient


def classification_metrics(expected: list[str], predicted: list[str | None]) -> dict[str, Any]:
    """Include unavailable predictions in denominators instead of inflating recall."""
    if (
        len(expected) != len(predicted)
        or not expected
        or any(label not in LABELS for label in expected)
    ):
        raise ValueError("Expected and predicted labels must describe the same nonempty cases")
    relevant = sum(label == "relevant" for label in expected)
    irrelevant = sum(label == "irrelevant" for label in expected)
    return {
        "accuracy": sum(wanted == actual for wanted, actual in zip(expected, predicted))
        / len(expected),
        "relevant_recall": (
            sum(wanted == actual == "relevant" for wanted, actual in zip(expected, predicted))
            / relevant
            if relevant
            else None
        ),
        "false_positive_rate": (
            sum(
                wanted == "irrelevant" and actual == "relevant"
                for wanted, actual in zip(expected, predicted)
            )
            / irrelevant
            if irrelevant
            else None
        ),
        "missing_predictions": predicted.count(None),
        "predicted_insufficient_evidence": predicted.count("insufficient_evidence"),
    }


def _latencies(values: list[float]) -> dict[str, float]:
    return {
        "p50_seconds": median(values),
        "p95_seconds": sorted(values)[math.ceil(len(values) * 0.95) - 1],
    }


async def run_comparison(
    articles: list[ArticleInput],
    expected: list[str],
    model: GRCModelService,
    decisions: RelevanceClient,
    *,
    repeats: int = 3,
) -> dict[str, Any]:
    """Measure both stages; estimate enabled latency including whole-batch fallback."""
    if not 1 <= repeats <= 10 or len(articles) != len(expected):
        raise ValueError("Use one label per article and 1-10 repeats")
    classification_metrics(expected, [None] * len(expected))
    local_started = time.perf_counter()
    local = [
        bool(analyze_article_grc_content(article.model_dump()).get("has_grc_content"))
        for article in articles
    ]
    local_elapsed = time.perf_counter() - local_started
    legacy_predictions: list[str | None] = []
    jev_predictions: list[str | None] = []
    enabled_predictions: list[str | None] = []
    legacy_times, jev_times, enabled_times = [], [], []
    jev_costs: list[float | None] = []
    errors: Counter[str] = Counter()
    models: set[str] = set()
    fallback_count = 0
    input_tokens = 0
    output_tokens = 0
    for _ in range(repeats):
        # Expected labels never enter either model request.
        started = time.perf_counter()
        baseline = await model._analyze_articles_with_model(articles)
        legacy_elapsed = time.perf_counter() - started
        legacy_times.append(legacy_elapsed)
        selected = selected_article_mask(articles, baseline)
        legacy: list[str | None] = (
            [
                "relevant" if chosen or signal else "irrelevant"
                for chosen, signal in zip(selected, local)
            ]
            if "error" not in baseline
            else [None] * len(articles)
        )
        legacy_predictions.extend(legacy)
        started = time.perf_counter()
        eligible = False
        predicted: list[str | None] = [None] * len(articles)
        try:
            result = await decisions.classify(articles)
            predicted = [item.label for item in result.decisions]
            eligible = result.usable(model.relevance_min_probability)
            jev_costs.append(result.cost)
            input_tokens += result.input_tokens
            output_tokens += result.output_tokens
            models.update(result.models)
        except DecisionError as error:
            errors[str(error)] += 1
            jev_costs.append(None)
        jev_elapsed = time.perf_counter() - started
        jev_times.append(jev_elapsed)
        jev_predictions.extend(predicted)
        if eligible:
            enabled_predictions.extend(
                "relevant" if label == "relevant" or signal else "irrelevant"
                for label, signal in zip(predicted, local)
            )
            enabled_times.append(jev_elapsed + local_elapsed)
        else:
            fallback_count += 1
            enabled_predictions.extend(legacy)
            enabled_times.append(jev_elapsed + legacy_elapsed)
    labels = expected * repeats
    return {
        "cases": len(articles),
        "repeats": repeats,
        "local_entities": {
            "elapsed_seconds": local_elapsed,
            **classification_metrics(
                expected, ["relevant" if value else "irrelevant" for value in local]
            ),
        },
        "legacy": {
            **_latencies(legacy_times),
            **classification_metrics(labels, legacy_predictions),
            "cost": None,
        },
        "jev": {
            **_latencies(jev_times),
            **classification_metrics(labels, jev_predictions),
            "fallback_rate": fallback_count / repeats,
            "models": sorted(models),
            "errors": dict(errors),
            "input_tokens_from_completed_batches": input_tokens,
            "output_tokens_from_completed_batches": output_tokens,
            "cost": (
                sum(value or 0 for value in jev_costs)
                if all(value is not None for value in jev_costs)
                else None
            ),
        },
        "enabled_estimate": {
            **_latencies(enabled_times),
            **classification_metrics(labels, enabled_predictions),
        },
        "limits": [
            "Stage-only timings, not a whole report or page-load benchmark.",
            "Enabled timings are estimates from separately measured calls; baseline runs first.",
            "Legacy client does not expose billed usage; unavailable cost is null, never zero.",
            "Failed multi-batch calls may incur cost not included in completed-call usage.",
            "Quality depends on independent review of expected labels and representative inputs.",
        ],
    }
