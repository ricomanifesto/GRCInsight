#!/usr/bin/env python3
"""Create and validate the public report-publication outcome artifact."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

SCHEMA_VERSION = 1
CATEGORY_LABELS = {
    "provider_authentication": "provider authentication",
    "provider_quota": "provider quota",
    "provider_rate_limit": "provider rate limit",
    "provider_deadline": "provider deadline",
    "provider_provenance": "provider provenance",
    "unclassified_provider_failure": "unclassified provider failure",
}
PUBLISHED_FIELDS = {
    "schema_version",
    "outcome",
    "report_generated_at",
    "evidence_manifest_sha256",
}
RETAINED_FIELDS = PUBLISHED_FIELDS | {"attempted_at", "refusal_category"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class PublicationStateError(ValueError):
    """The public publication-state contract is invalid."""


class StaleRetainedAttempt(PublicationStateError):
    """A newer report has already superseded the refused attempt."""


def parse_utc_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PublicationStateError(f"{field} must be a non-empty UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PublicationStateError(f"{field} must be an ISO timestamp") from error
    if parsed.tzinfo is None:
        raise PublicationStateError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def manifest_identity(manifest_bytes: bytes) -> tuple[str, datetime, str]:
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PublicationStateError("evidence manifest must be valid JSON") from error
    if not isinstance(manifest, dict):
        raise PublicationStateError("evidence manifest must be an object")
    generated_at = manifest.get("generated_at")
    generated = parse_utc_timestamp(generated_at, "manifest generated_at")
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    return str(generated_at), generated, digest


def classify_fallback_reason(reason: object) -> str:
    text = reason.lower() if isinstance(reason, str) else ""
    if "http 401" in text or "api_key" in text:
        return "provider_authentication"
    if "http 402" in text or "insufficient_quota" in text:
        return "provider_quota"
    if "http 429" in text:
        return "provider_rate_limit"
    if any(term in text for term in ("deadline", "timed out", "timeout")):
        return "provider_deadline"
    if "model identity" in text:
        return "provider_provenance"
    return "unclassified_provider_failure"


def category_label(category: object) -> str:
    if not isinstance(category, str) or category not in CATEGORY_LABELS:
        raise PublicationStateError("refusal_category is not recognized")
    return CATEGORY_LABELS[category]


def build_published_state(manifest_bytes: bytes) -> dict[str, object]:
    generated_at, _generated, digest = manifest_identity(manifest_bytes)
    return {
        "schema_version": SCHEMA_VERSION,
        "outcome": "published",
        "report_generated_at": generated_at,
        "evidence_manifest_sha256": digest,
    }


def build_retained_state(
    manifest_bytes: bytes, attempted_at: str, refusal_category: str
) -> dict[str, object]:
    generated_at, generated, digest = manifest_identity(manifest_bytes)
    attempted = parse_utc_timestamp(attempted_at, "attempted_at")
    category_label(refusal_category)
    if attempted < generated:
        raise StaleRetainedAttempt(
            "refused attempt was superseded by the current published report"
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "outcome": "retained",
        "attempted_at": attempted_at,
        "refusal_category": refusal_category,
        "report_generated_at": generated_at,
        "evidence_manifest_sha256": digest,
    }


def validate_publication_state(
    state: object, manifest_bytes: bytes
) -> dict[str, object]:
    if not isinstance(state, dict):
        raise PublicationStateError("publication state must be an object")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise PublicationStateError("publication state schema_version is unsupported")
    outcome = state.get("outcome")
    expected_fields = (
        PUBLISHED_FIELDS
        if outcome == "published"
        else RETAINED_FIELDS if outcome == "retained" else None
    )
    if expected_fields is None:
        raise PublicationStateError("publication state outcome is unsupported")
    if set(state) != expected_fields:
        raise PublicationStateError("publication state fields do not match its outcome")

    generated_at, generated, digest = manifest_identity(manifest_bytes)
    if state.get("report_generated_at") != generated_at:
        raise PublicationStateError(
            "publication state does not identify the current report"
        )
    manifest_sha = state.get("evidence_manifest_sha256")
    if not isinstance(manifest_sha, str) or not SHA256_PATTERN.fullmatch(manifest_sha):
        raise PublicationStateError(
            "publication state evidence manifest digest is invalid"
        )
    if manifest_sha != digest:
        raise PublicationStateError(
            "publication state does not match the current evidence manifest"
        )

    parse_utc_timestamp(state["report_generated_at"], "report_generated_at")
    if outcome == "retained":
        attempted = parse_utc_timestamp(state["attempted_at"], "attempted_at")
        category_label(state["refusal_category"])
        if attempted < generated:
            raise PublicationStateError(
                "retained attempt predates the current published report"
            )
    return state


def read_json(path: Path, artifact: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PublicationStateError(f"missing {artifact}") from error
    except json.JSONDecodeError as error:
        raise PublicationStateError(f"{artifact} must be valid JSON") from error


def write_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify_parser = subparsers.add_parser("classify")
    classify_parser.add_argument("--report-data", type=Path, required=True)

    for command in ("record-published", "record-retained"):
        record_parser = subparsers.add_parser(command)
        record_parser.add_argument("--manifest", type=Path, required=True)
        record_parser.add_argument("--output", type=Path, required=True)
        if command == "record-retained":
            record_parser.add_argument("--attempted-at", required=True)
            record_parser.add_argument(
                "--category", choices=sorted(CATEGORY_LABELS), required=True
            )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "classify":
            report_data = read_json(args.report_data, "report data")
            metadata = (
                report_data.get("metadata", {}) if isinstance(report_data, dict) else {}
            )
            reason = (
                metadata.get("fallback_reason", "")
                if isinstance(metadata, dict)
                else ""
            )
            print(classify_fallback_reason(reason))
            return 0

        manifest_bytes = args.manifest.read_bytes()
        if args.command == "record-published":
            state = build_published_state(manifest_bytes)
        else:
            state = build_retained_state(
                manifest_bytes, args.attempted_at, args.category
            )
        validate_publication_state(state, manifest_bytes)
        write_state(args.output, state)
        print(f"publication state recorded: {state['outcome']}")
        return 0
    except FileNotFoundError:
        print("publication state failed: missing evidence manifest", file=sys.stderr)
        return 2
    except StaleRetainedAttempt:
        print(
            "publication state skipped: refused attempt was superseded", file=sys.stderr
        )
        return 4
    except PublicationStateError as error:
        print(f"publication state failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
