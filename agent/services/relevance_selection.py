"""Per-article relevance dispositions and selection records.

Selection policy keep-uncertain-v2: when the decision model returns a complete,
valid result, every insufficient-evidence or below-threshold position stays
selected, including when every position is uncertain. Only accepted irrelevant
labels are not selected. Unavailable or invalid results keep the full legacy
selection. keep-uncertain-v1 routed an all-uncertain result to the full legacy
path, where the prose parser could still drop those articles.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
import hashlib
from typing import Any

from core.article_selection import analyze_selected, local_overrides, workflow_selected
from models.api import ArticleInput
from services.relevance_decisions import ArticleDecision, RelevanceResult

SELECTION_POLICY = "keep-uncertain-v2"

DECISION_ROUTE = "decision"
LEGACY_FULL = "legacy_full"

ACCEPTED_RELEVANT = "accepted_relevant"
ACCEPTED_IRRELEVANT = "accepted_irrelevant"
UNCERTAIN_KEPT = "uncertain_kept"
INSUFFICIENT_EVIDENCE_KEPT = "insufficient_evidence_kept"
KEPT_UNDECIDED = frozenset({UNCERTAIN_KEPT, INSUFFICIENT_EVIDENCE_KEPT})

INTERNAL_ERROR = "internal_error"
FALLBACK_ERROR = "fallback_error"


def disposition(decision: ArticleDecision, threshold: float) -> str:
    """Classify one decision; only an accepted irrelevant label is not selected."""
    if decision.label == "insufficient_evidence":
        return INSUFFICIENT_EVIDENCE_KEPT
    if decision.probability < threshold:
        return UNCERTAIN_KEPT
    return ACCEPTED_RELEVANT if decision.label == "relevant" else ACCEPTED_IRRELEVANT


@dataclass(frozen=True)
class SelectionPlan:
    """How the enabled route decides one batch before any generative call."""

    route: str
    reason: str | None
    decisions: tuple[ArticleDecision, ...] | None
    dispositions: tuple[str, ...]
    # Set only on the decision route; a legacy_full batch is decided by legacy output.
    model_selected: tuple[bool, ...] | None
    # Positions sent to the subset generative call, which enriches aggregates only.
    fallback_indices: tuple[int, ...]


def _ordered(result: RelevanceResult, count: int) -> tuple[ArticleDecision, ...] | None:
    by_index: dict[int, ArticleDecision] = {}
    for item in result.decisions:
        if not 0 <= item.index < count or item.index in by_index:
            return None
        by_index[item.index] = item
    if len(by_index) != count:
        return None
    return tuple(by_index[index] for index in range(count))


def _legacy(reason: str, count: int) -> SelectionPlan:
    return SelectionPlan(LEGACY_FULL, reason, None, (LEGACY_FULL,) * count, None, ())


def plan_selection(
    result: RelevanceResult | None, failure: str | None, count: int, threshold: float
) -> SelectionPlan:
    """Apply keep-uncertain-v2 to one batch of decisions or a decision failure."""
    if result is None:
        if failure is None or failure == INTERNAL_ERROR:
            return _legacy(INTERNAL_ERROR, count)
        return _legacy(f"jev_{failure}", count)
    decisions = _ordered(result, count)
    if decisions is None:
        # A missing or duplicate position is an invariant failure, never a drop.
        return _legacy(INTERNAL_ERROR, count)
    dispositions = tuple(disposition(item, threshold) for item in decisions)
    # An all-uncertain result is still a complete decision: every position stays
    # selected and the whole group is enriched, never parsed for selection.
    return SelectionPlan(
        DECISION_ROUTE,
        None,
        decisions,
        dispositions,
        tuple(item != ACCEPTED_IRRELEVANT for item in dispositions),
        tuple(index for index, item in enumerate(dispositions) if item in KEPT_UNDECIDED),
    )


def article_key(url: str) -> str:
    """A stable article identity that carries no article text."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SelectionRecord:
    """One position's selection, with no article text."""

    index: int
    article_key: str
    route: str
    disposition: str
    reason: str | None
    label: str | None
    probabilities: dict[str, float] | None
    confidence: float | None
    model_selected: bool | None
    entity_override: bool
    risk_override: bool
    workflow_selected: bool | None
    analyze_selected: bool | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def selection_records(
    articles: Sequence[ArticleInput],
    plan: SelectionPlan,
    *,
    legacy_selected: Sequence[bool] | None = None,
    analysis_failed: bool = False,
) -> tuple[SelectionRecord, ...]:
    """Build one record per position for the enabled route or its shadow counterfactual.

    ``legacy_selected`` is the legacy mask for a legacy_full plan. A failed analysis
    leaves every model selection unknown.
    """
    model = plan.model_selected if plan.route == DECISION_ROUTE else legacy_selected
    if model is not None and len(model) != len(articles):
        raise ValueError("Selection mask does not cover every position")
    reason = FALLBACK_ERROR if analysis_failed and plan.route == DECISION_ROUTE else plan.reason
    records = []
    for index, article in enumerate(articles):
        entity, risk = local_overrides(article)
        chosen = None if analysis_failed or model is None else model[index]
        decision = plan.decisions[index] if plan.decisions is not None else None
        records.append(
            SelectionRecord(
                index=index,
                article_key=article_key(article.url),
                route=plan.route,
                disposition=plan.dispositions[index],
                reason=reason,
                label=decision.label if decision else None,
                probabilities=dict(decision.probabilities) if decision else None,
                confidence=decision.confidence if decision else None,
                model_selected=chosen,
                entity_override=entity,
                risk_override=risk,
                workflow_selected=workflow_selected(entity=entity, risk=risk, model=chosen),
                analyze_selected=analyze_selected(entity=entity, model=chosen),
            )
        )
    return tuple(records)


def keep_violations(records: Sequence[SelectionRecord], threshold: float) -> tuple[int, ...]:
    """Positions that break the keep contract, judged from raw labels.

    A record carrying a raw decision must be on the decision route, so an
    all-uncertain result cannot hide as ``legacy_full``. Every raw
    insufficient-evidence or below-threshold label must keep an undecided
    disposition and stay selected unless the enrichment call failed, which
    leaves its selection unknown rather than dropped.
    """
    violations = []
    for record in records:
        if record.label is None or record.probabilities is None:
            continue
        undecided = (
            record.label == "insufficient_evidence"
            or record.probabilities[record.label] < threshold
        )
        if record.route != DECISION_ROUTE:
            violations.append(record.index)
        elif undecided and (
            record.disposition not in KEPT_UNDECIDED
            or record.model_selected is False
            or (record.model_selected is None and record.reason != FALLBACK_ERROR)
        ):
            violations.append(record.index)
    return tuple(violations)
