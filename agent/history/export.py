"""Bounded, replayable export of report and article history.

Each call reads one bounded scan page of one table and returns verified
records plus an opaque cursor. Records carry a stable ``record_id`` and a
``record_revision``; replaying the same revision yields byte-identical records,
and changed content yields a new revision rather than a rewrite. Nothing here
writes to a table.
"""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone
from typing import Any

from history.identity import (
    APPEARANCE_KIND,
    MAX_RETAINED_CONTENT,
    REPORT_OUTCOME_SCHEMA,
    REVISION_KIND,
    canonical_json,
    evidence_kind,
    outcome_digest,
    sha256_hex,
    source_key,
)
from history.table import HistoryTable
from history.writeback import (
    CLASSIFICATION_FIELDS,
    OPEN_STATUSES,
    OUTCOME_GUARD,
    outcome_digest_fields,
    revision_problems,
)

EXPORT_SCHEMA = "grcinsight.intelligence-export.v1"
PRODUCT = "grcinsight"
PIPELINE = "grc-intelligence-report"
STREAMS = ("reports", "articles")
MAX_PAGE = 200
EXCERPT_CHARS = 600
NOT_PUBLISHED = {"status": "not_established_by_store"}


class CursorError(ValueError):
    pass


def encode_cursor(stream: str, start_key: dict[str, Any] | None) -> str | None:
    if start_key is None:
        return None
    raw = canonical_json({"schema": EXPORT_SCHEMA, "stream": stream, "start_key": start_key})
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(stream: str, cursor: str | None) -> dict[str, Any] | None:
    if cursor is None:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    except (ValueError, binascii.Error, UnicodeDecodeError) as err:
        raise CursorError("cursor is not readable") from err
    if not isinstance(data, dict) or data.get("schema") != EXPORT_SCHEMA:
        raise CursorError("cursor belongs to another export schema")
    if data.get("stream") != stream:
        raise CursorError("cursor belongs to another stream")
    start_key = data.get("start_key")
    if not isinstance(start_key, dict) or not start_key:
        raise CursorError("cursor has no start key")
    return start_key


def _finish(record: dict[str, Any]) -> dict[str, Any]:
    record = {"schema_version": EXPORT_SCHEMA, "product": PRODUCT, "pipeline": PIPELINE, **record}
    record["record_digest"] = sha256_hex(record)
    return record


def _excerpt(text: str) -> str:
    return text[:EXCERPT_CHARS]


def _support(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for source in metadata.get("source_articles") or []:
        if not isinstance(source, dict):
            continue
        segments = source.get("article_evidence") or []
        out.append(
            {
                "url": source.get("url") or None,
                "title": source.get("title") or None,
                "digest_url": source.get("digest_url") or None,
                "support_excerpts": [
                    {"origin": s.get("origin"), "text": s.get("text")}
                    for s in segments
                    if isinstance(s, dict) and isinstance(s.get("text"), str)
                ],
                "cves": source.get("cves") or [],
            }
        )
    return out


def report_record(item: dict[str, Any]) -> dict[str, Any]:
    report_id = str(item.get("report_id"))
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    status = item.get("status")
    problems: list[str] = []

    if item.get("history_schema") == REPORT_OUTCOME_SCHEMA and item.get(OUTCOME_GUARD):
        provenance = "history_v1"
        revision = item[OUTCOME_GUARD]
        basis = "outcome_digest"
        if outcome_digest(outcome_digest_fields(report_id, item)) != revision:
            problems.append("stored outcome does not match its digest")
        outcome = item.get("terminal_outcome")
        reason = item.get("terminal_reason")
        integrity = "corrupt" if problems else "intact"
        if outcome == "model_completed" and not problems:
            conclusion_status = "verified"
        else:
            conclusion_status = "not_intelligence"
    else:
        provenance = "legacy_unknown"
        revision = sha256_hex({k: v for k, v in item.items() if k != "updated_at"})
        basis = "computed_at_export"
        integrity = "unverifiable_legacy"
        mode = metadata.get("analysis_mode")
        # A reason the service recorded (for example a failed invocation) is kept, but
        # without a digest the outcome stays unverifiable.
        reason = item.get("terminal_reason") or metadata.get("fallback_reason")
        if status in OPEN_STATUSES:
            outcome, conclusion_status = "incomplete", "not_intelligence"
        elif status == "completed" and mode == "model":
            outcome, conclusion_status = "legacy_completed_unverified", "legacy_unverified"
        elif status == "completed" and mode == "fallback":
            outcome, conclusion_status = "refused_fallback", "not_intelligence"
        elif status == "completed":
            outcome, conclusion_status = "legacy_completed_unknown_mode", "not_intelligence"
        else:
            outcome, conclusion_status = "failed", "not_intelligence"

    record: dict[str, Any] = {
        "record_type": "report_outcome",
        "record_id": f"grcinsight:report:{report_id}",
        "record_revision": revision,
        "record_revision_basis": basis,
        "report_id": report_id,
        "run_id": item.get("completion_run_id"),
        "outcome": outcome,
        "outcome_reason": reason,
        "conclusion_status": conclusion_status,
        "provenance_class": provenance,
        "integrity": {"status": integrity, "problems": problems},
        "timestamps": {
            "created_at": item.get("created_at"),
            "generated_at": item.get("generated_at"),
            "completed_at": item.get("completed_at"),
        },
        "source_feed": {
            "url": metadata.get("source_url") or item.get("source_url") or None,
            "name": metadata.get("source_name") or None,
            "home_url": metadata.get("source_home_url") or None,
            "issue_date": metadata.get("source_issue_date") or None,
            "issue_url": metadata.get("source_issue_url") or None,
        },
        "model": {
            "requested": metadata.get("requested_model") or None,
            "resolved": metadata.get("resolved_model") or None,
        },
        "source_revision_ids": item.get("article_revision_ids"),
        "appearance_set_sha256": item.get("appearance_set_sha256"),
        "publication": NOT_PUBLISHED,
    }
    if conclusion_status != "not_intelligence":
        content = item.get("content") if isinstance(item.get("content"), str) else ""
        record["generated_conclusions"] = {
            "kind": "generated_conclusion",
            "title": item.get("title"),
            "content_markdown": content,
            "content_sha256": sha256_hex(content),
            "report_plan": metadata.get("report_plan"),
            "source_attribution": _support(metadata),
        }
    return _finish(record)


def _revision_record(table: str, item: dict[str, Any], include_text: bool) -> dict[str, Any]:
    problems = revision_problems(item)
    content = item.get("content") if isinstance(item.get("content"), str) else ""
    summary = item.get("summary") if isinstance(item.get("summary"), str) else ""
    evidence: dict[str, Any] = {
        "kind": item.get("evidence_kind"),
        "full_text_scope": item.get("full_text_scope"),
        "retained_content_location": f"dynamodb://{table}/{item.get('article_id')}#content",
        "retained_length": len(content),
        "truncated": item.get("content_truncated"),
        "captured_content_length": item.get("captured_content_length"),
        "captured_content_sha256": item.get("captured_content_sha256"),
        "excerpt": _excerpt(content or summary),
    }
    if include_text:
        evidence["text"] = content
        evidence["summary"] = summary
    return _finish(
        {
            "record_type": "source_article_revision",
            "record_id": f"grcinsight:article:{item.get('source_key')}",
            "record_revision": item.get("content_sha256"),
            "record_revision_basis": "content_digest",
            "revision_id": item.get("article_id"),
            "source_key": item.get("source_key"),
            "corroboration_unit": item.get("source_key"),
            "canonical_url": item.get("canonical_url"),
            "url": item.get("url"),
            "publisher": item.get("source") or None,
            "title": item.get("title"),
            "digest_url": item.get("digest_url") or None,
            "evidence": evidence,
            "timestamps": {
                "published_at": item.get("published_at"),
                "published_at_known": bool(item.get("published_at_known")),
                "first_captured_at": item.get("first_captured_at"),
            },
            "origin": {
                "first_run_id": item.get("first_run_id"),
                "first_report_id": item.get("first_report_id"),
            },
            "provenance_class": "history_v1",
            "integrity": {"status": "corrupt" if problems else "intact", "problems": problems},
        }
    )


def _appearance_record(item: dict[str, Any]) -> dict[str, Any]:
    classification = {"has_grc_content": bool(item.get("has_grc_content"))}
    for name in CLASSIFICATION_FIELDS:
        classification[name] = item.get(name) or []
    identity = {
        k: item.get(k) for k in ("report_id", "position", "appearance_set_sha256", "revision_id")
    }
    return _finish(
        {
            "record_type": "report_article_appearance",
            "record_id": f"grcinsight:appearance:{item.get('article_id')}",
            "record_revision": sha256_hex({**identity, "classification": classification}),
            "record_revision_basis": "appearance_digest",
            **identity,
            "run_id": item.get("run_id"),
            "content_sha256": item.get("content_sha256"),
            "generated_classification": {**classification, "provenance": "generated"},
            "binding": "bound only when the report lists this appearance_set_sha256",
            "timestamps": {"created_at": item.get("created_at")},
            "provenance_class": "history_v1",
        }
    )


def _legacy_article_record(table: str, item: dict[str, Any]) -> dict[str, Any]:
    content = item.get("content") if isinstance(item.get("content"), str) else ""
    summary = item.get("summary") if isinstance(item.get("summary"), str) else ""
    url = item.get("url") if isinstance(item.get("url"), str) else ""
    return _finish(
        {
            "record_type": "legacy_article_snapshot",
            "record_id": f"grcinsight:legacy-article:{item.get('article_id')}",
            "record_revision": sha256_hex({k: v for k, v in item.items() if k != "updated_at"}),
            "record_revision_basis": "computed_at_export",
            "article_id": item.get("article_id"),
            "report_id": item.get("report_id") or None,
            "source_key": source_key(url) if url else None,
            "corroboration_unit": source_key(url) if url else None,
            "url": url or None,
            "publisher": item.get("source") or None,
            "title": item.get("title"),
            "evidence": {
                "kind": evidence_kind(
                    summary=summary,
                    content=content,
                    truncated=len(content) >= MAX_RETAINED_CONTENT,
                ),
                "retained_content_location": f"dynamodb://{table}/{item.get('article_id')}#content",
                "retained_length": len(content),
                "excerpt": _excerpt(content or summary),
            },
            "timestamps": {
                "published_raw": item.get("published") or None,
                "published_reliability": "legacy_unverified",
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            },
            "provenance_class": "legacy_unknown",
            "integrity": {"status": "unverifiable_legacy", "problems": []},
        }
    )


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 timestamp; naive values are UTC."""
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _changed_at(stream: str, item: dict[str, Any]) -> datetime | None:
    """When an item last changed, or None when it carries no readable time."""
    # Immutable history items change once (capture/creation); legacy rows are mutable,
    # so their latest update time decides.
    if stream == "reports":
        names: tuple[str, ...] = ("completed_at", "updated_at", "created_at")
    elif item.get("record_kind") == REVISION_KIND:
        names = ("first_captured_at",)
    elif item.get("record_kind") == APPEARANCE_KIND:
        names = ("created_at",)
    else:
        names = ("updated_at", "created_at")
    for name in names:
        value = item.get(name)
        if isinstance(value, str) and value:
            try:
                return parse_timestamp(value)
            except ValueError:
                return None
    return None


def export_page(
    table: HistoryTable,
    *,
    stream: str,
    cursor: str | None = None,
    limit: int = 50,
    updated_since: str | None = None,
    include_text: bool = False,
) -> dict[str, Any]:
    if stream not in STREAMS:
        raise ValueError(f"stream must be one of {STREAMS}")
    if not 1 <= limit <= MAX_PAGE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE}")
    since = parse_timestamp(updated_since) if updated_since is not None else None
    start_key = decode_cursor(stream, cursor)
    items, last = table.scan_page(limit, start_key)
    records: list[dict[str, Any]] = []
    unknown = filtered = 0
    for item in items:
        if since is not None:
            # Compare instants, not strings; an item without a readable time is kept,
            # because it cannot be shown to be older than the cutoff.
            changed = _changed_at(stream, item)
            if changed is not None and changed < since:
                filtered += 1
                continue
        if stream == "reports":
            records.append(report_record(item))
        elif item.get("record_kind") == REVISION_KIND:
            records.append(_revision_record(table.name, item, include_text))
        elif item.get("record_kind") == APPEARANCE_KIND:
            records.append(_appearance_record(item))
        elif item.get("record_kind") is None and isinstance(item.get("article_id"), str):
            records.append(_legacy_article_record(table.name, item))
        else:
            unknown += 1
    next_cursor = encode_cursor(stream, last)
    return {
        "schema_version": EXPORT_SCHEMA,
        "stream": stream,
        "cursor": cursor,
        "next_cursor": next_cursor,
        "records": records,
        "coverage": {
            "scanned_items": len(items),
            "emitted_records": len(records),
            "filtered_out": filtered,
            "unknown_record_kinds": unknown,
            "integrity_problems": sum(
                1 for r in records if r.get("integrity", {}).get("status") == "corrupt"
            ),
            "updated_since": updated_since,
            "stream_complete": next_cursor is None,
        },
    }


def export_all(table: HistoryTable, *, stream: str, limit: int = 50, **kwargs: Any):
    """Iterate every page; a deliberate historical backfill, bounded per page."""
    cursor = None
    while True:
        page = export_page(table, stream=stream, cursor=cursor, limit=limit, **kwargs)
        yield page
        cursor = page["next_cursor"]
        if cursor is None:
            return
