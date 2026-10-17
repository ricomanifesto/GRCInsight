"""Per-article relevance dispositions, selection records and candidate identity."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
from types import ModuleType
from typing import Any

from core import article_selection, entities
from core.article_selection import analyze_selected, local_overrides, workflow_selected
from models.api import ArticleInput
from services import relevance_decisions
from services.relevance_decisions import ArticleDecision, RelevanceResult

SELECTION_POLICY = "keep-uncertain-v1"

DECISION_ROUTE = "decision"
LEGACY_FULL = "legacy_full"

ACCEPTED_RELEVANT = "accepted_relevant"
ACCEPTED_IRRELEVANT = "accepted_irrelevant"
UNCERTAIN_KEPT = "uncertain_kept"
INSUFFICIENT_EVIDENCE_KEPT = "insufficient_evidence_kept"
KEPT_UNDECIDED = frozenset({UNCERTAIN_KEPT, INSUFFICIENT_EVIDENCE_KEPT})

INTERNAL_ERROR = "internal_error"
ALL_UNCERTAIN = "all_uncertain"
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


def _legacy(
    reason: str, count: int, decisions: tuple[ArticleDecision, ...] | None = None
) -> SelectionPlan:
    return SelectionPlan(LEGACY_FULL, reason, decisions, (LEGACY_FULL,) * count, None, ())


def plan_selection(
    result: RelevanceResult | None, failure: str | None, count: int, threshold: float
) -> SelectionPlan:
    """Apply keep-uncertain-v1 to one batch of decisions or a decision failure."""
    if result is None:
        if failure is None or failure == INTERNAL_ERROR:
            return _legacy(INTERNAL_ERROR, count)
        return _legacy(f"jev_{failure}", count)
    decisions = _ordered(result, count)
    if decisions is None:
        # A missing or duplicate position is an invariant failure, never a drop.
        return _legacy(INTERNAL_ERROR, count)
    dispositions = tuple(disposition(item, threshold) for item in decisions)
    if all(item in KEPT_UNDECIDED for item in dispositions):
        return _legacy(ALL_UNCERTAIN, count, decisions)
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


def _source_sha256(module: ModuleType) -> str:
    return hashlib.sha256(inspect.getsource(module).encode("utf-8")).hexdigest()


def candidate_fingerprint(threshold: float, focus_areas: Sequence[str], *, batch_size: int) -> str:
    """Hash everything that changes which articles a replayed candidate selects.

    The replay batch size fixes request bytes and positions. The local rule sources
    decide entity and risk overrides and the effective selections.
    """
    identity = {
        "model": relevance_decisions.MODEL,
        "criteria": relevance_decisions.CRITERIA,
        "instructions": relevance_decisions.INSTRUCTIONS,
        "focus_areas": relevance_decisions.focus_text(list(focus_areas))
        or relevance_decisions.DEFAULT_FOCUS,
        "limits": {
            "title_chars": relevance_decisions.MAX_TITLE_CHARS,
            "text_chars": relevance_decisions.MAX_TEXT_CHARS,
            "articles": relevance_decisions.MAX_ARTICLES,
            "batch_articles": relevance_decisions.MAX_BATCH_ARTICLES,
            "request_bytes": relevance_decisions.MAX_REQUEST_BYTES,
        },
        "threshold": threshold,
        "selection_policy": SELECTION_POLICY,
        "batch_size": batch_size,
        "local_rules": {
            module.__name__: _source_sha256(module) for module in (entities, article_selection)
        },
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
