"""Labeled relevance cases: JSONL contract, split rules and holdout identity.

Each line is one case. Labels, rationales and adjudication stay in the corpus;
only the article fields reach a decision request.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import ValidationError

from models.api import ArticleInput
from services.relevance_decisions import LABELS, visible_article

CASE_SCHEMA = "grc-relevance-case-v1"
SPLITS = ("development", "holdout")
ROLES = ("provisional", "primary", "second")
BASES = ("full_source", "visible")
REVIEW_STATUSES = ("provisional", "single_reviewed", "dual_reviewed", "disputed")
# Provisional and disputed cases are reported but never satisfy a gate.
GATE_STATUSES = frozenset({"single_reviewed", "dual_reviewed"})
CATEGORIES = (
    "promotion_or_event_invitation",
    "commentary_or_opinion",
    "vendor_advice",
    "concrete_incident",
    "flaw_or_patch",
    "enforcement_or_regulatory_change",
    "policy_proposal",
    "ambiguous_snippet",
    "duplicate_event",
    "embedded_instructions",
)
CASE_FIELDS = frozenset(
    {
        "schema",
        "case_id",
        "article",
        "visible_sha256",
        "event_id",
        "split",
        "labels",
        "adjudication",
        "review_status",
        "critical",
        "categories",
    }
)
LABEL_FIELDS = frozenset(
    {"labeler", "role", "label", "rationale", "basis", "visible_sufficient", "labeled_at"}
)
ADJUDICATION_FIELDS = frozenset({"labeler", "label", "rationale", "labeled_at"})
OPAQUE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
CVE_PATTERN = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE)
DISPUTE_LIMIT = 0.15


def visible_sha256(article: ArticleInput) -> str:
    """Hash the exact inference-visible text, so labels can record its sufficiency."""
    encoded = json.dumps(visible_article(article), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def normalized_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/"), parts.query, ""))


def canonical_case(case: dict[str, Any]) -> str:
    return json.dumps(case, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class CorpusCase:
    case_id: str
    article: ArticleInput
    event_id: str
    split: str
    review_status: str
    reference_label: str | None
    critical: bool
    categories: tuple[str, ...]
    canonical: str

    @property
    def gate_eligible(self) -> bool:
        return self.review_status in GATE_STATUSES and self.reference_label is not None


@dataclass(frozen=True)
class CorpusValidation:
    cases: tuple[CorpusCase, ...]
    errors: tuple[str, ...]
    flags: tuple[str, ...]
    holdout_sha256: str | None

    def summary(self) -> dict[str, Any]:
        return {
            "cases": len(self.cases),
            "splits": dict(Counter(case.split for case in self.cases)),
            "review_status": dict(Counter(case.review_status for case in self.cases)),
            "gate_eligible": sum(case.gate_eligible for case in self.cases),
            "categories": dict(
                Counter(category for case in self.cases for category in case.categories)
            ),
            "errors": list(self.errors),
            "flags": list(self.flags),
            "holdout_sha256": self.holdout_sha256,
        }


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def _check_label(value: Any, fields: frozenset[str], where: str, errors: list[str]) -> bool:
    if not isinstance(value, dict) or set(value) != fields:
        errors.append(f"{where}: expected fields {sorted(fields)}")
        return False
    if not isinstance(value["labeler"], str) or not OPAQUE_ID.fullmatch(value["labeler"]):
        errors.append(f"{where}: labeler must be an opaque ID")
    if value["label"] not in LABELS:
        errors.append(f"{where}: unknown label")
    if not isinstance(value["rationale"], str):
        errors.append(f"{where}: rationale must be text")
    if not _timestamp(value["labeled_at"]):
        errors.append(f"{where}: labeled_at must be a timezone-aware ISO timestamp")
    if "role" in fields:
        if value["role"] not in ROLES:
            errors.append(f"{where}: unknown role")
        if value["basis"] not in BASES:
            errors.append(f"{where}: unknown basis")
        if type(value["visible_sufficient"]) is not bool:
            errors.append(f"{where}: visible_sufficient must be true or false")
    return True


def _reference(raw: dict[str, Any], where: str, errors: list[str]) -> str | None:
    """Resolve the reference label the review status allows."""
    labels = raw["labels"]
    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for label in labels:
        by_role[label["role"]].append(label)
    primary, second = by_role["primary"], by_role["second"]
    adjudication = raw["adjudication"]
    status = raw["review_status"]
    if len(primary) > 1 or len(second) > 1 or (second and not primary):
        errors.append(f"{where}: at most one primary and one second label, second needs primary")
        return None
    if status == "provisional":
        if primary or second or adjudication is not None or not by_role["provisional"]:
            errors.append(f"{where}: provisional cases carry provisional labels only")
            return None
        return by_role["provisional"][0]["label"]
    if status == "single_reviewed":
        if not primary or second or adjudication is not None:
            errors.append(f"{where}: single_reviewed needs exactly one primary label")
            return None
        return primary[0]["label"]
    if not primary or not second:
        errors.append(f"{where}: {status} needs primary and second labels")
        return None
    agree = primary[0]["label"] == second[0]["label"]
    if status == "disputed":
        if agree or adjudication is not None:
            errors.append(f"{where}: disputed needs disagreeing labels without adjudication")
        return None
    if adjudication is not None:
        if agree:
            errors.append(f"{where}: adjudication only resolves a reviewer disagreement")
            return None
        return adjudication["label"]
    if not agree:
        errors.append(f"{where}: disagreeing labels need adjudication")
        return None
    return primary[0]["label"]


def _parse_case(raw: Any, where: str, errors: list[str]) -> CorpusCase | None:
    if not isinstance(raw, dict) or set(raw) != CASE_FIELDS:
        errors.append(f"{where}: expected fields {sorted(CASE_FIELDS)}")
        return None
    start = len(errors)
    if raw["schema"] != CASE_SCHEMA:
        errors.append(f"{where}: schema must be {CASE_SCHEMA}")
    for key in ("case_id", "event_id"):
        if not isinstance(raw[key], str) or not OPAQUE_ID.fullmatch(raw[key]):
            errors.append(f"{where}: {key} must be an opaque ID")
    if raw["split"] not in SPLITS:
        errors.append(f"{where}: unknown split")
    if raw["review_status"] not in REVIEW_STATUSES:
        errors.append(f"{where}: unknown review_status")
    if type(raw["critical"]) is not bool:
        errors.append(f"{where}: critical must be true or false")
    categories = raw["categories"]
    if not isinstance(categories, list) or any(item not in CATEGORIES for item in categories):
        errors.append(f"{where}: unknown category")
    try:
        article = ArticleInput.model_validate(raw["article"])
    except ValidationError:
        errors.append(f"{where}: invalid article")
        return None
    if not isinstance(raw["article"], dict) or set(raw["article"]) - set(ArticleInput.model_fields):
        errors.append(f"{where}: article has unknown fields")
    if article.published.tzinfo is None:
        errors.append(f"{where}: article.published must include a timezone")
    if raw["visible_sha256"] != visible_sha256(article):
        errors.append(f"{where}: visible_sha256 does not match the article")
    labels = raw["labels"]
    if not isinstance(labels, list) or not labels:
        errors.append(f"{where}: labels must be a nonempty list")
        return None
    for position, label in enumerate(labels):
        _check_label(label, LABEL_FIELDS, f"{where} label {position}", errors)
    if raw["adjudication"] is not None:
        _check_label(raw["adjudication"], ADJUDICATION_FIELDS, f"{where} adjudication", errors)
    if len(errors) > start:
        return None
    reference = _reference(raw, where, errors)
    if len(errors) > start:
        return None
    return CorpusCase(
        case_id=raw["case_id"],
        article=article,
        event_id=raw["event_id"],
        split=raw["split"],
        review_status=raw["review_status"],
        reference_label=reference,
        critical=raw["critical"],
        categories=tuple(categories),
        canonical=canonical_case(raw),
    )


def holdout_sha256(cases: Iterable[CorpusCase]) -> str | None:
    """Identity of the frozen holdout, labels included."""
    holdout = sorted((case for case in cases if case.split == "holdout"), key=lambda c: c.case_id)
    if not holdout:
        return None
    return hashlib.sha256("\n".join(case.canonical for case in holdout).encode("utf-8")).hexdigest()


def validate_corpus(lines: Iterable[str]) -> CorpusValidation:
    errors: list[str] = []
    flags: list[str] = []
    cases: list[CorpusCase] = []
    seen: set[str] = set()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        where = f"line {number}"
        try:
            raw = json.loads(line)
        except ValueError:
            errors.append(f"{where}: invalid JSON")
            continue
        case = _parse_case(raw, where, errors)
        if case is None:
            continue
        if case.case_id in seen:
            errors.append(f"{where}: duplicate case_id {case.case_id}")
            continue
        seen.add(case.case_id)
        cases.append(case)
    if not cases and not errors:
        errors.append("corpus has no cases")

    event_splits: dict[str, set[str]] = defaultdict(set)
    cve_splits: dict[str, set[str]] = defaultdict(set)
    url_splits: dict[str, set[str]] = defaultdict(set)
    for case in cases:
        event_splits[case.event_id].add(case.split)
        text = "\n".join([case.article.title, case.article.summary, case.article.content])
        for cve in {match.upper() for match in CVE_PATTERN.findall(text)}:
            cve_splits[cve].add(case.split)
        url_splits[normalized_url(case.article.url)].add(case.split)
    errors.extend(
        f"event {event} spans development and holdout"
        for event, splits in sorted(event_splits.items())
        if len(splits) > 1
    )
    flags.extend(
        f"{cve} appears in development and holdout"
        for cve, splits in sorted(cve_splits.items())
        if len(splits) > 1
    )
    flags.extend(
        f"normalized URL {url} appears in development and holdout"
        for url, splits in sorted(url_splits.items())
        if len(splits) > 1
    )
    development = [case.article.published for case in cases if case.split == "development"]
    holdout = [case.article.published for case in cases if case.split == "holdout"]
    if development and holdout and max(development) >= min(holdout):
        errors.append("holdout window must start after the development window ends")
    disputed = sum(case.review_status == "disputed" for case in cases)
    if cases and disputed / len(cases) > DISPUTE_LIMIT:
        flags.append("more than 15% of cases are disputed; revise the rubric before freezing")
    missing = sorted(set(CATEGORIES) - {item for case in cases for item in case.categories})
    if missing:
        flags.append(f"categories without cases: {', '.join(missing)}")
    return CorpusValidation(tuple(cases), tuple(errors), tuple(flags), holdout_sha256(cases))


def load_corpus(path: Path) -> CorpusValidation:
    return validate_corpus(path.read_text(encoding="utf-8").splitlines())
