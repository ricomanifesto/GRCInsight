"""Commit one workflow result to the existing GRCInsight DynamoDB tables.

Lifecycle ownership is unchanged: the Go service creates the report row
(``processing``) and this writeback is the only path that completes it. The
completion is a single conditional update that succeeds only while the row is
open and carries no outcome yet, so a completed outcome is never rewritten.

Evidence is written first and is immutable:

* each analyzed article becomes an ``article_revision`` item keyed by its URL
  and content digest (created only if absent);
* each report/article pairing becomes a ``report_article_appearance`` item
  keyed by the report and the digest of its ordered appearance set.

The report completion then binds that appearance set. If the writer dies
between evidence and completion, a retry reuses identical evidence and
completes; a diverged retry writes a different, unbound appearance set and
only one completion can win.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from history.identity import (
    APPEARANCE_KIND,
    APPEARANCE_SCHEMA,
    ARTICLE_REVISION_SCHEMA,
    MAX_RETAINED_CONTENT,
    REPORT_OUTCOME_SCHEMA,
    REVISION_KIND,
    appearance_id,
    appearance_set_digest,
    canonical_url,
    capture_digest,
    evidence_kind,
    json_safe,
    outcome_digest,
    revision_digest,
    revision_id,
    revision_payload,
    sha256_hex,
    source_key,
)
from history.table import ConditionFailed, HistoryTable, to_dynamo

OPEN_STATUSES = ("pending", "processing")
OUTCOME_GUARD = "outcome_sha256"
ACCEPTED = frozenset({"committed", "reused"})

METADATA_FIELDS = (
    "article_count",
    "grc_article_count",
    "analysis_mode",
    "fallback_reason",
    "source_name",
    "source_url",
    "source_home_url",
    "source_issue_date",
    "source_issue_url",
    "analysis_period",
    "requested_model",
    "resolved_model",
    "source_articles",
    "report_plan",
    "regulations_mentioned",
    "frameworks_referenced",
    "industries_affected",
    "regulatory_bodies",
    "relevance_diagnostics",
)
CLASSIFICATION_FIELDS = ("regulations", "frameworks", "industries", "regulatory_bodies")


@dataclass(frozen=True)
class CompletionReceipt:
    report_id: str
    run_id: str
    decision: str
    terminal_outcome: str
    outcome_sha256: str
    revisions_written: int = 0
    revisions_reused: int = 0
    appearances_written: int = 0
    appearances_reused: int = 0
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def accepted(self) -> bool:
        return self.decision in ACCEPTED


def normalized(value: Any) -> Any:
    """The exact form a value has after a DynamoDB round trip."""
    return json_safe(to_dynamo(value))


def terminal_outcome_for(result: Any) -> tuple[str, str | None]:
    """Only an attested model report is intelligence; fallback is a recorded refusal."""
    if getattr(result, "status", None) != "completed" or getattr(result, "report", None) is None:
        error = getattr(result, "error", None)
        detail = getattr(error, "details", None) or getattr(error, "message", None)
        return "failed", str(detail or "workflow did not complete")
    metadata = getattr(result, "metadata", None)
    mode = getattr(metadata, "analysis_mode", None)
    if mode != "model":
        reason = getattr(metadata, "fallback_reason", None)
        return "refused_fallback", str(reason or "model analysis was not attested")
    return "model_completed", None


def report_metadata(result: Any) -> dict[str, Any] | None:
    metadata = getattr(result, "metadata", None)
    if metadata is None:
        return None
    dumped = metadata.model_dump(mode="json")
    out = {name: dumped.get(name) for name in METADATA_FIELDS}
    for name in (
        "source_articles",
        "regulations_mentioned",
        "frameworks_referenced",
        "industries_affected",
        "regulatory_bodies",
    ):
        out[name] = out[name] or []
    return normalized(out)


def _fnv1a_32(data: str) -> int:
    h = 2166136261
    for ch in data.encode("utf-8"):
        h ^= ch
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _article_dicts(result: Any) -> list[dict[str, Any]]:
    articles = getattr(result, "articles", None) or []
    return [a if isinstance(a, dict) else a.model_dump(mode="json") for a in articles]


def build_revision(
    article: dict[str, Any], *, report_id: str, run_id: str, now: str
) -> dict[str, Any]:
    url = str(article.get("url") or "")
    title = str(article.get("title") or "")
    summary = str(article.get("summary") or "")
    captured = str(article.get("content") or "")
    origin = "publisher_page" if article.get("content_origin") == "publisher_page" else "feed_item"
    truncated = bool(article.get("content_truncated")) or len(captured) > MAX_RETAINED_CONTENT
    content = captured[:MAX_RETAINED_CONTENT]
    payload = revision_payload(url=url, title=title, summary=summary, content=content)
    digest = revision_digest(payload)
    published_known = bool(article.get("published_known", True)) and bool(article.get("published"))
    item: dict[str, Any] = {
        "article_id": "",
        "record_kind": REVISION_KIND,
        "history_schema": ARTICLE_REVISION_SCHEMA,
        **payload,
        "canonical_url": canonical_url(url),
        "source_key": source_key(url),
        "content_sha256": digest,
        "content_truncated": truncated,
        "captured_content_length": len(captured),
        "captured_content_sha256": sha256_hex(captured),
        "evidence_kind": evidence_kind(summary=summary, content=content, truncated=truncated),
        "full_text_scope": (
            "publisher_page_html" if origin == "publisher_page" else "feed_item_content"
        ),
        "content_origin": origin,
        "source": str(article.get("source") or ""),
        "digest_url": str(article.get("digest_url") or ""),
        "published_at_known": published_known,
        "first_captured_at": now,
        "first_run_id": run_id,
        "first_report_id": report_id,
    }
    if published_known:
        item["published_at"] = str(article["published"])
    item["capture_sha256"] = capture_digest(item)
    item["article_id"] = revision_id(url, item["capture_sha256"])
    return item


def revision_problems(item: dict[str, Any]) -> list[str]:
    """Re-derive a stored revision's identity from its retained fields."""
    problems: list[str] = []
    fields = {}
    for name in ("url", "title", "summary", "content"):
        value = item.get(name)
        if not isinstance(value, str):
            problems.append(f"retained {name} is not text")
            value = ""
        fields[name] = value
    digest = revision_digest(revision_payload(**fields))
    if item.get("content_sha256") != digest:
        problems.append("content digest does not match retained text")
    capture = capture_digest(item)
    if item.get("capture_sha256") != capture:
        problems.append("capture digest does not match retained provenance")
    if item.get("article_id") != revision_id(fields["url"], capture):
        problems.append("revision identity does not match retained evidence")
    return problems


def _appearance_entry(revision: dict[str, Any], article: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "revision_id": revision["article_id"],
        "has_grc_content": bool(article.get("has_grc_content", False)),
    }
    for name in CLASSIFICATION_FIELDS:
        entry[name] = [str(v) for v in (article.get(name) or [])]
    return entry


def build_appearance(
    entry: dict[str, Any],
    revision: dict[str, Any],
    *,
    report_id: str,
    run_id: str,
    set_digest: str,
    position: int,
    now: str,
) -> dict[str, Any]:
    # The legacy article fields stay present so existing per-report readers keep working;
    # the retained text lives once, on the revision.
    return {
        "article_id": appearance_id(report_id, set_digest, position),
        "record_kind": APPEARANCE_KIND,
        "history_schema": APPEARANCE_SCHEMA,
        "report_id": report_id,
        "run_id": run_id,
        "position": position,
        "appearance_set_sha256": set_digest,
        "revision_id": revision["article_id"],
        "content_sha256": revision["content_sha256"],
        "numeric_id": _fnv1a_32(revision["url"]),
        "url": revision["url"],
        "title": revision["title"],
        "summary": "",
        "content": "",
        "source": revision["source"],
        "digest_url": revision["digest_url"],
        "published": revision.get("published_at", ""),
        "classification_provenance": "generated",
        **entry,
        "created_at": now,
        "updated_at": now,
    }


def _same_appearance(existing: dict[str, Any], wanted: dict[str, Any]) -> bool:
    keys = ("report_id", "position", "appearance_set_sha256", "revision_id", "has_grc_content")
    keys += CLASSIFICATION_FIELDS
    return all(existing.get(k) == wanted.get(k) for k in keys)


def outcome_fields(
    *,
    report_id: str,
    run_id: str,
    result: Any,
    revision_ids: list[str],
    set_digest: str,
    now: str,
) -> dict[str, Any]:
    outcome, reason = terminal_outcome_for(result)
    report = getattr(result, "report", None)
    generated = getattr(report, "generated_at", None)
    fields: dict[str, Any] = {
        "history_schema": REPORT_OUTCOME_SCHEMA,
        "status": "completed" if getattr(result, "status", None) == "completed" else "failed",
        "terminal_outcome": outcome,
        "terminal_reason": reason,
        "completion_run_id": run_id,
        "title": report.title if report else f"GRC Intelligence Report - {now[:10]}",
        "content": report.content if report else "# No content",
        "generated_at": generated.isoformat() if generated is not None else now,
        "metadata": report_metadata(result),
        "article_revision_ids": revision_ids,
        "appearance_set_sha256": set_digest,
    }
    return normalized(fields)


def outcome_digest_fields(report_id: str, item: dict[str, Any]) -> dict[str, Any]:
    names = (
        "history_schema",
        "status",
        "terminal_outcome",
        "terminal_reason",
        "completion_run_id",
        "title",
        "content",
        "generated_at",
        "metadata",
        "article_revision_ids",
        "appearance_set_sha256",
    )
    return {"report_id": report_id, **{n: item.get(n) for n in names}}


def completion_identity(current: dict[str, Any], report_id: str, job_id: str | None) -> str:
    """The admitted job a completion belongs to; never a transient invocation id."""
    stored = current.get("job_id")
    if isinstance(stored, str) and stored:
        return stored
    return job_id or report_id


def admission_problem(
    current: dict[str, Any] | None,
    *,
    job_id: str | None,
    feed_url: str | None,
    require_job: bool,
) -> str | None:
    """Why a completion request may not complete this admitted report, if it may not.

    A row the Go service admitted with a job id accepts only that exact job id; an
    omitted id never adopts it. Rows without a job id (admitted before job ids
    existed) are completed only from a trusted channel (``require_job=False``,
    the IAM-authorized Lambda invocation). The requested feed must be the one the
    report was admitted for.
    """
    if current is None:
        return None
    stored_job = current.get("job_id") or None
    if stored_job:
        if job_id != stored_job:
            return "completion job does not match the admitted job"
    elif require_job:
        return "report has no admitted job identity for this channel"
    stored_feed = current.get("source_url") or None
    if feed_url is not None and stored_feed and feed_url != stored_feed:
        return "requested feed does not match the admitted report"
    return None


def failure_fields(*, result: Any, reason: str, now: str) -> dict[str, Any]:
    """A recorded, explained terminal failure; publication treats ``failed`` as not current."""
    report = getattr(result, "report", None)
    return normalized(
        {
            "history_schema": REPORT_OUTCOME_SCHEMA,
            "status": "failed",
            "terminal_outcome": "failed",
            "terminal_reason": reason,
            "title": report.title if report else f"GRC Intelligence Report - {now[:10]}",
            "content": "",
            "generated_at": now,
            "metadata": report_metadata(result),
            "article_revision_ids": [],
            "appearance_set_sha256": None,
        }
    )


def commit_workflow_result(
    *,
    reports: HistoryTable,
    articles: HistoryTable,
    report_id: str,
    result: Any,
    now: str,
    job_id: str | None = None,
    invocation_id: str | None = None,
    feed_url: str | None = None,
    require_job: bool = False,
) -> CompletionReceipt:
    """Commit one result for an admitted report job.

    ``job_id`` is the durable identity the Go service stored on the row when it
    admitted the job; ``invocation_id`` (for example a Lambda request id) is
    recorded for diagnosis only and never decides ownership, because retries
    and duplicate deliveries may or may not reuse it.
    """
    if not report_id:
        raise ValueError("report_id is required")
    problems: list[str] = []
    counts = {"rw": 0, "rr": 0, "aw": 0, "ar": 0}

    current = reports.get(report_id)
    run_id = completion_identity(current or {}, report_id, job_id)

    pairs = []
    for article in _article_dicts(result):
        if not article.get("url"):
            problems.append("article without url was not retained")
            continue
        pairs.append(
            (build_revision(article, report_id=report_id, run_id=run_id, now=now), article)
        )

    entries = [_appearance_entry(rev, art) for rev, art in pairs]
    set_digest = appearance_set_digest(report_id, entries)
    revision_ids = [e["revision_id"] for e in entries]
    fields = outcome_fields(
        report_id=report_id,
        run_id=run_id,
        result=result,
        revision_ids=revision_ids,
        set_digest=set_digest,
        now=now,
    )
    digest = outcome_digest(outcome_digest_fields(report_id, fields))

    def receipt(decision: str, outcome: str | None = None, sha: str | None = None):
        return CompletionReceipt(
            report_id=report_id,
            run_id=run_id,
            decision=decision,
            terminal_outcome=outcome or fields["terminal_outcome"],
            outcome_sha256=sha or digest,
            revisions_written=counts["rw"],
            revisions_reused=counts["rr"],
            appearances_written=counts["aw"],
            appearances_reused=counts["ar"],
            problems=tuple(problems),
        )

    def classify(existing: dict[str, Any] | None) -> CompletionReceipt:
        if existing is None:
            return receipt("report_missing")
        if existing.get(OUTCOME_GUARD) == digest:
            # Never re-acknowledge a stored outcome whose retained fields no longer match.
            if outcome_digest(outcome_digest_fields(report_id, existing)) != digest:
                problems.append("stored outcome does not match its digest")
                return receipt("integrity_failure")
            return receipt("reused")
        if existing.get(OUTCOME_GUARD) and existing.get("completion_run_id") == run_id:
            return receipt("stale_completion_refused")
        if existing.get(OUTCOME_GUARD):
            return receipt("foreign_completion_refused")
        return receipt("already_terminal_refused")

    problem = admission_problem(current, job_id=job_id, feed_url=feed_url, require_job=require_job)
    if problem:
        problems.append(problem)
        return receipt("foreign_completion_refused")
    # A row that is already terminal gets no new evidence; the conditional completion
    # below stays authoritative for rows that change between this read and the write.
    if current is None or current.get("status") not in OPEN_STATUSES or OUTCOME_GUARD in current:
        return classify(current)

    extra = {"updated_at": now, "completed_at": now, "completion_run_id": run_id}
    if invocation_id:
        extra["completion_invocation_id"] = invocation_id

    def record_failure(reason: str) -> CompletionReceipt:
        failed = {**failure_fields(result=result, reason=reason, now=now)}
        failed["completion_run_id"] = run_id
        failed_digest = outcome_digest(outcome_digest_fields(report_id, failed))
        try:
            reports.complete_if_open(
                report_id,
                {**failed, **extra, OUTCOME_GUARD: failed_digest},
                open_statuses=OPEN_STATUSES,
                guard_attribute=OUTCOME_GUARD,
            )
        except ConditionFailed as refused:
            return classify(refused.existing)
        return receipt("evidence_failure_recorded", "failed", failed_digest)

    try:
        for revision, _ in pairs:
            try:
                articles.put_if_absent(revision)
                counts["rw"] += 1
            except ConditionFailed as refused:
                existing = refused.existing or {}
                if existing.get("capture_sha256") == revision["capture_sha256"] and not (
                    revision_problems(existing)
                ):
                    counts["rr"] += 1
                else:
                    problems.append(f"revision identity conflict: {revision['article_id']}")
        if any(p.startswith("revision identity conflict") for p in problems):
            return record_failure("evidence_conflict: a retained source revision does not verify")

        for position, ((revision, _), entry) in enumerate(zip(pairs, entries)):
            appearance = build_appearance(
                entry,
                revision,
                report_id=report_id,
                run_id=run_id,
                set_digest=set_digest,
                position=position,
                now=now,
            )
            try:
                articles.put_if_absent(appearance)
                counts["aw"] += 1
            except ConditionFailed as refused:
                if _same_appearance(refused.existing or {}, normalized(appearance)):
                    counts["ar"] += 1
                else:
                    problems.append(f"appearance identity conflict: {appearance['article_id']}")
        if any(p.startswith("appearance identity conflict") for p in problems):
            return record_failure("evidence_conflict: a report appearance does not verify")
    except Exception as err:  # the store refused or failed after its own retries
        problems.append(f"evidence write failed: {type(err).__name__}")
        return record_failure("evidence_persistence_failed")

    try:
        reports.complete_if_open(
            report_id,
            {**fields, OUTCOME_GUARD: digest, **extra},
            open_statuses=OPEN_STATUSES,
            guard_attribute=OUTCOME_GUARD,
        )
        return receipt("committed")
    except ConditionFailed as refused:
        return classify(refused.existing)
