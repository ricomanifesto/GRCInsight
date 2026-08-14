#!/usr/bin/env python3
"""Create and validate public report-publication outcome artifacts."""

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
HISTORY_SCHEMA_VERSION = 1
HISTORY_MAX_ENTRIES = 30
REGULAR_SCHEDULE = {"cadence": "daily", "time_utc": "13:00"}
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
HISTORY_FIELDS = {
    "schema_version",
    "max_entries",
    "history_started_at",
    "schedule",
    "events",
}
PUBLISHED_EVENT_FIELDS = {
    "event_at",
    "outcome",
    "report_generated_at",
    "evidence_manifest_sha256",
}
RETAINED_EVENT_FIELDS = PUBLISHED_EVENT_FIELDS | {"refusal_category"}


class PublicationStateError(ValueError):
    """The public publication-state contract is invalid."""


class StaleRetainedAttempt(PublicationStateError):
    """A newer report has already superseded the refused attempt."""


class StalePublicationEvent(PublicationStateError):
    """A newer terminal publication event already exists."""


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


def parse_journal_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PublicationStateError(f"{field} must be a canonical UTC timestamp")
    return parse_utc_timestamp(value, field)


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


def state_event(state: dict[str, object], event_at: str) -> dict[str, object]:
    """Build the journal event corresponding to an already validated state."""
    event_time = parse_journal_timestamp(event_at, "event_at")
    generated = parse_journal_timestamp(
        state["report_generated_at"], "report_generated_at"
    )
    if event_time < generated:
        raise StalePublicationEvent("publication event predates its report")
    event: dict[str, object] = {
        "event_at": event_at,
        "outcome": state["outcome"],
        "report_generated_at": state["report_generated_at"],
        "evidence_manifest_sha256": state["evidence_manifest_sha256"],
    }
    if state["outcome"] == "retained":
        if event_at != state["attempted_at"]:
            raise PublicationStateError(
                "retained event time must match the refused attempt"
            )
        event["refusal_category"] = state["refusal_category"]
    return event


def validate_publication_history_shape(history: object) -> dict[str, object]:
    """Validate the bounded journal independently of the latest-state binding."""
    if not isinstance(history, dict):
        raise PublicationStateError("publication history must be an object")
    if set(history) != HISTORY_FIELDS:
        raise PublicationStateError("publication history fields are invalid")
    if history.get("schema_version") != HISTORY_SCHEMA_VERSION:
        raise PublicationStateError("publication history schema_version is unsupported")
    if history.get("max_entries") != HISTORY_MAX_ENTRIES:
        raise PublicationStateError("publication history maximum is invalid")
    if history.get("schedule") != REGULAR_SCHEDULE:
        raise PublicationStateError("publication history schedule is invalid")
    history_started = parse_journal_timestamp(
        history.get("history_started_at"), "history_started_at"
    )
    events = history.get("events")
    if not isinstance(events, list) or not events:
        raise PublicationStateError("publication history events must be non-empty")
    if len(events) > HISTORY_MAX_ENTRIES:
        raise PublicationStateError("publication history exceeds its maximum")

    previous_event_at: datetime | None = None
    oldest_event_at: datetime | None = None
    for event in events:
        if not isinstance(event, dict):
            raise PublicationStateError("publication history event must be an object")
        outcome = event.get("outcome")
        expected_fields = (
            PUBLISHED_EVENT_FIELDS
            if outcome == "published"
            else RETAINED_EVENT_FIELDS if outcome == "retained" else None
        )
        if expected_fields is None:
            raise PublicationStateError("publication history outcome is unsupported")
        if set(event) != expected_fields:
            raise PublicationStateError(
                "publication history event fields do not match its outcome"
            )
        event_at = parse_journal_timestamp(event["event_at"], "event_at")
        generated = parse_journal_timestamp(
            event["report_generated_at"], "report_generated_at"
        )
        if event_at < generated:
            raise PublicationStateError("publication history event predates its report")
        if previous_event_at is not None and event_at >= previous_event_at:
            raise PublicationStateError(
                "publication history events must be unique and newest first"
            )
        previous_event_at = event_at
        oldest_event_at = event_at
        digest = event.get("evidence_manifest_sha256")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise PublicationStateError(
                "publication history evidence manifest digest is invalid"
            )
        if outcome == "retained":
            category_label(event["refusal_category"])

    if oldest_event_at is not None and history_started > oldest_event_at:
        raise PublicationStateError(
            "publication history start is newer than its oldest retained event"
        )
    return history


def state_matches_event(state: dict[str, object], event: dict[str, object]) -> bool:
    event_at = (
        str(state["attempted_at"])
        if state["outcome"] == "retained"
        else str(event["event_at"])
    )
    try:
        return state_event(state, event_at) == event
    except PublicationStateError:
        return False


def validate_publication_history(
    history: object, state: object, manifest_bytes: bytes
) -> dict[str, object]:
    validated_state = validate_publication_state(state, manifest_bytes)
    validated_history = validate_publication_history_shape(history)
    events = validated_history["events"]
    assert isinstance(events, list)
    if not state_matches_event(validated_state, events[0]):
        raise PublicationStateError(
            "publication history latest event does not match publication state"
        )
    return validated_history


def append_publication_event(
    history: object, state: dict[str, object], event_at: str
) -> dict[str, object]:
    validated_history = validate_publication_history_shape(history)
    event = state_event(state, event_at)
    events = validated_history["events"]
    assert isinstance(events, list)
    newest = events[0]
    if event["event_at"] == newest["event_at"]:
        if event == newest:
            return validated_history
        raise PublicationStateError("publication history timestamp is conflicting")
    if parse_journal_timestamp(event["event_at"], "event_at") < parse_journal_timestamp(
        newest["event_at"], "latest event_at"
    ):
        raise StalePublicationEvent("publication event was superseded")
    updated = dict(validated_history)
    updated["events"] = [event, *events][:HISTORY_MAX_ENTRIES]
    return validate_publication_history_shape(updated)


def read_json(path: Path, artifact: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PublicationStateError(f"missing {artifact}") from error
    except json.JSONDecodeError as error:
        raise PublicationStateError(f"{artifact} must be valid JSON") from error


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
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
        record_parser.add_argument("--history", type=Path, required=True)
        if command == "record-published":
            record_parser.add_argument("--event-at", required=True)
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
        history = read_json(args.history, "publication history")
        event_at = (
            args.event_at if args.command == "record-published" else args.attempted_at
        )
        updated_history = append_publication_event(history, state, event_at)
        validate_publication_history(updated_history, state, manifest_bytes)
        write_json(args.history, updated_history)
        write_json(args.output, state)
        print(f"publication state recorded: {state['outcome']}")
        return 0
    except FileNotFoundError:
        print("publication state failed: missing evidence manifest", file=sys.stderr)
        return 2
    except (StaleRetainedAttempt, StalePublicationEvent):
        print(
            "publication state skipped: publication event was superseded",
            file=sys.stderr,
        )
        return 4
    except PublicationStateError as error:
        print(f"publication state failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
