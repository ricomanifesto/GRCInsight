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
from services.relevance_decisions import LABELS


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
    *,
    repeats: int = 3,
) -> dict[str, Any]:
    """Measure the actual enabled policy, including any subset fallback."""
    if not 1 <= repeats <= 10 or len(articles) != len(expected):
        raise ValueError("Use one label per article and 1-10 repeats")
    if model.relevance_mode != "enabled" or model.relevance_client is None:
        raise ValueError("Benchmark requires an enabled relevance service")
    classification_metrics(expected, [None] * len(expected))
    local_started = time.perf_counter()
    local = [
        bool(analyze_article_grc_content(article.model_dump()).get("has_grc_content"))
        for article in articles
    ]
    local_elapsed = time.perf_counter() - local_started
    predictions: dict[str, list[str | None]] = {"legacy": [], "enabled": []}
    times: dict[str, list[float]] = {"legacy": [], "enabled": []}
    runs = []
    diagnostics = []
    for repeat in range(repeats):
        # Alternate paired order. Expected labels never enter either request.
        order = ["legacy", "enabled"] if repeat % 2 == 0 else ["enabled", "legacy"]
        run: dict[str, Any] = {"order": order}
        for path in order:
            started = time.perf_counter()
            analysis = (
                await model._analyze_articles_with_model(articles)
                if path == "legacy"
                else await model.analyze_articles_for_grc(articles)
            )
            elapsed = time.perf_counter() - started
            times[path].append(elapsed)
            selected = selected_article_mask(articles, analysis)
            predicted: list[str | None] = (
                [
                    "relevant" if chosen or signal else "irrelevant"
                    for chosen, signal in zip(selected, local)
                ]
                if "error" not in analysis
                else [None] * len(articles)
            )
            predictions[path].extend(predicted)
            run[path] = {"elapsed_seconds": elapsed, "predictions": predicted}
            if path == "enabled":
                diagnostic = dict(model.last_relevance_diagnostics or {})
                diagnostics.append(diagnostic)
                run["decisions"] = diagnostic
        runs.append(run)
    labels = expected * repeats
    costs = [item.get("cost") for item in diagnostics]
    fallback_sizes = [item.get("uncertain_count", len(articles)) for item in diagnostics]
    return {
        "cases": len(articles),
        "repeats": repeats,
        "runs": runs,
        "local_entities": {
            "elapsed_seconds": local_elapsed,
            **classification_metrics(
                expected, ["relevant" if value else "irrelevant" for value in local]
            ),
        },
        **{
            path: {
                **_latencies(times[path]),
                **classification_metrics(labels, predictions[path]),
                # The prose client does not expose billed usage.
                "cost": None,
            }
            for path in predictions
        },
        "decisions": {
            "statuses": dict(Counter(item.get("status", "unavailable") for item in diagnostics)),
            "fallback_batch_rate": sum(size > 0 for size in fallback_sizes) / repeats,
            "fallback_article_rate": sum(fallback_sizes) / (repeats * len(articles)),
            "models": sorted({name for item in diagnostics for name in item.get("models", [])}),
            "input_tokens_from_completed_batches": sum(
                item.get("input_tokens", 0) for item in diagnostics
            ),
            "output_tokens_from_completed_batches": sum(
                item.get("output_tokens", 0) for item in diagnostics
            ),
            "cost": sum(costs) if all(cost is not None for cost in costs) else None,
        },
        "limits": [
            "Measured article-analysis calls, not whole reports, Lambda latency or page loads.",
            "Paired order alternates; small replay samples do not establish production p95.",
            "Decisions statistics describe the same enabled calls, not a separate inference run.",
            "Effective selections include local entities; workflow risk overrides are not measured.",
            "Legacy and total enabled cost are unavailable from the client, not zero.",
            "Failed multi-batch calls may incur cost not included in completed-call usage.",
            "Quality depends on independent review of expected labels and representative inputs.",
        ],
    }
