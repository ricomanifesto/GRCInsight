"""Stable identities and digests for report and article history.

Every digest is SHA-256 over canonical JSON (sorted keys, no insignificant
whitespace, UTF-8). Identities derived from digests change exactly when the
content they name changes, so replaying the same revision is idempotent and a
changed source is a distinct revision.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit, urlunsplit

REPORT_OUTCOME_SCHEMA = "grcinsight.report-outcome.v1"
ARTICLE_REVISION_SCHEMA = "grcinsight.article-revision.v1"
APPEARANCE_SCHEMA = "grcinsight.report-article-appearance.v1"

REVISION_KIND = "article_revision"
APPEARANCE_KIND = "report_article_appearance"

# The legacy writer kept at most this many characters of feed content.
MAX_RETAINED_CONTENT = 50_000
KEY_DIGEST_LENGTH = 32


def json_safe(value: Any) -> Any:
    """Normalize a value to plain JSON types; DynamoDB numbers come back as Decimal."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def canonical_json(value: Any) -> str:
    return json.dumps(json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    data = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def canonical_url(url: str) -> str:
    """Lowercase scheme and host and drop the fragment; path and query are kept verbatim."""
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))


def source_key(url: str) -> str:
    return sha256_hex(canonical_url(url))[:KEY_DIGEST_LENGTH]


def revision_payload(*, url: str, title: str, summary: str, content: str) -> dict[str, str]:
    """The retained fields a revision digest covers."""
    return {"url": url, "title": title, "summary": summary, "content": content}


def revision_digest(payload: dict[str, str]) -> str:
    return sha256_hex(payload)


def revision_id(url: str, content_sha256: str) -> str:
    return f"arev#{source_key(url)}#{content_sha256[:KEY_DIGEST_LENGTH]}"


def appearance_set_digest(report_id: str, entries: list[dict[str, Any]]) -> str:
    """Digest of one report's ordered appearances: revision plus generated classification."""
    return sha256_hex({"report_id": report_id, "entries": entries})


def appearance_id(report_id: str, set_digest: str, position: int) -> str:
    return f"aapp#{report_id}#{set_digest[:16]}#{position:04d}"


def evidence_kind(*, summary: str, content: str, truncated: bool) -> str:
    """Classify retained source text without overstating it.

    ``full_text`` means the complete feed-item content as captured, not the
    publisher's web page; ``excerpt`` is a summary or a truncated body.
    """
    if content.strip() and not truncated:
        return "full_text"
    if content.strip() or summary.strip():
        return "excerpt"
    return "metadata_only"


def outcome_digest(fields: dict[str, Any]) -> str:
    return sha256_hex(fields)
