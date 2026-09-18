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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from core.content_policy import contains_virtual_event  # noqa: E402

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
        raise PublicationStateError("publication event predates its report")
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
    history: object,
    state: object,
    manifest_bytes: bytes,
    *,
    corrections: dict[str, dict[str, Any]] | None = None,
) -> dict[str, object]:
    validated_state = validate_publication_state(state, manifest_bytes)
    validated_history = validate_publication_history_shape(history)
    events = validated_history["events"]
    assert isinstance(events, list)
    comparison_state = validated_state
    if corrections and publication_manifest_matches(
        events[0]["evidence_manifest_sha256"],
        validated_state["evidence_manifest_sha256"],
        str(validated_state["report_generated_at"]),
        corrections,
    ):
        comparison_state = {
            **validated_state,
            "evidence_manifest_sha256": events[0]["evidence_manifest_sha256"],
        }
    if not state_matches_event(comparison_state, events[0]):
        raise PublicationStateError(
            "publication history latest event does not match publication state"
        )
    return validated_history


def editorial_correction_note(correction: dict[str, Any]) -> str:
    date = str(correction["corrected_at"])[:10]
    return (
        f"**Editorial correction ({date}):** Promotional source records and associated "
        "content were removed. Generation time, model identity, and analyzed-article "
        "counts refer to the original run; the model was not rerun. The evidence "
        "manifest now lists the retained public sources."
    )


# These three reviewed whole units have no marker. Permission is bound to both
# the immutable report and the exact unit, never to a phrase or a source URL.
UNTAGGED_CORRECTION_UNITS = {
    (
        "2026-09-06T22-53-06Z",
        "11f3e37ad6e15eb9861a2b73a7f1723615a6998dc7711deb48f62e8be6476a0e",
    ): {
        "40a0afb85f63de617d6ce6c2e98043ff9a3c95c43c83e99f7f406afa07a7171e",
    },
    (
        "2026-09-09T11-06-50Z",
        "744b68fdad83e5eb3a3f984c4896a73359a7bf35e579a554129edfecb2d41eb8",
    ): {
        "d255408ac79d33a00d6ecb627b29478de2c265f6153bc136781820c0a2006146",
        "8272975f914f6961822c012582f51906545c9a5fa348fe0c6ea096eb767bcf0a",
    },
}
REPORT_LIST_ITEM = re.compile(r"^( *)(?:[-+*]|\d+[.)])\s+")
REPORT_HEADING = re.compile(r"^#{1,6}\s+")
REPORT_TABLE_RULE = re.compile(r"^\s*\|[\s:|\-]+\|\s*$")


def exclusion_only_report(
    original: bytes, snapshot_name: str, correction: dict[str, Any]
) -> tuple[bytes, int, list[str]]:
    """Replay whole-unit deletions without normalizing any retained Markdown."""
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PublicationStateError("original report must be UTF-8") from error
    heading = "## Executive Summary\n\n"
    lines = text.splitlines(keepends=True)
    if text.count(heading) != 1 or lines.count("## Source Highlights\n") != 1:
        raise PublicationStateError("original report correction sections are invalid")
    body_start = lines.index("## Executive Summary\n") + 1
    sources_start = lines.index("## Source Highlights\n")
    if sources_start <= body_start or "**Editorial correction (" in text:
        raise PublicationStateError("original report is not an uncorrected report")
    approved = UNTAGGED_CORRECTION_UNITS.get(
        (snapshot_name, hashlib.sha256(original).hexdigest()), set()
    )
    used_approvals: set[str] = set()
    retained = []
    narrative_count = 0
    removed_highlights: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if index < body_start or not line.strip() or REPORT_HEADING.match(line):
            retained.append(line)
            index += 1
            continue
        # Corrections support ordinary prose, list items and table rows. Refuse
        # ambiguous code/HTML blocks instead of silently removing part of one.
        item = REPORT_LIST_ITEM.match(line)
        if line.lstrip().startswith(("```", "~~~", "<", ">")) or (
            not item and line.startswith(("    ", "\t"))
        ):
            raise PublicationStateError("unsupported original report correction block")
        table_row = line.lstrip().startswith("|")
        end = index + 1
        if not table_row:
            while end < len(lines):
                following = lines[end]
                if (
                    not following.strip()
                    or REPORT_HEADING.match(following)
                    or REPORT_LIST_ITEM.match(following)
                    or following.lstrip().startswith("|")
                    or following.lstrip().startswith(("```", "~~~", "<", ">"))
                ):
                    break
                end += 1
        unit = "".join(lines[index:end])
        digest = hashlib.sha256(unit.encode("utf-8")).hexdigest()
        excluded = contains_virtual_event(unit) or digest in approved
        if excluded:
            if table_row:
                preceding = index - 1
                while preceding >= 0 and lines[preceding].lstrip().startswith("|"):
                    preceding -= 1
                if not line.strip().endswith("|") or not any(
                    REPORT_TABLE_RULE.fullmatch(value)
                    for value in lines[preceding + 1 : index]
                ):
                    raise PublicationStateError("unsupported original report table row")
            if table_row and (
                REPORT_TABLE_RULE.fullmatch(line)
                or (end < len(lines) and REPORT_TABLE_RULE.fullmatch(lines[end]))
            ):
                raise PublicationStateError("cannot remove a report table heading")
            if item:
                following = next((value for value in lines[end:] if value.strip()), "")
                indentation = len(following) - len(following.lstrip(" "))
                if following and indentation > len(item.group(1)):
                    raise PublicationStateError(
                        "cannot partially remove a nested report item"
                    )
            if digest in approved:
                used_approvals.add(digest)
            if index < sources_start:
                narrative_count += 1
            else:
                if not item or end != index + 1:
                    raise PublicationStateError(
                        "source highlight must be a whole list entry"
                    )
                removed_highlights.append(unit)
        else:
            retained.append(unit)
        index = end
    if used_approvals != approved:
        raise PublicationStateError("approved original correction units are missing")
    expected = "".join(retained)
    if contains_virtual_event(expected):
        raise PublicationStateError("promotion remains outside a removable report unit")
    expected = expected.replace(
        heading, heading + editorial_correction_note(correction) + "\n\n", 1
    )
    return expected.encode("utf-8"), narrative_count, removed_highlights


def validate_exclusion_only_correction(
    original_report: bytes,
    original_manifest: bytes,
    report: bytes,
    manifest: bytes,
    snapshot_name: str,
    correction: dict[str, Any],
) -> None:
    try:
        original = json.loads(original_manifest)
    except (ValueError, UnicodeDecodeError) as error:
        raise PublicationStateError(
            "original evidence manifest must be valid JSON"
        ) from error
    if (
        not isinstance(original, dict)
        or "editorial_correction" in original
        or not isinstance(original.get("sources"), list)
        or not original["sources"]
        or any(not isinstance(source, dict) for source in original["sources"])
    ):
        raise PublicationStateError("original evidence sources are invalid")
    if manifest_identity(original_manifest)[0] != correction["report_generated_at"]:
        raise PublicationStateError("original evidence manifest names the wrong report")
    retained_sources = [
        source for source in original["sources"] if not contains_virtual_event(source)
    ]
    removed_sources = len(original["sources"]) - len(retained_sources)
    if removed_sources != correction["removed_source_count"]:
        raise PublicationStateError(
            "editorial correction source removal count does not match"
        )
    expected_manifest = {
        **original,
        "sources": retained_sources,
        "editorial_correction": {
            "corrected_at": correction["corrected_at"],
            "original_evidence_manifest_sha256": correction[
                "original_evidence_manifest_sha256"
            ],
            "record": "/GRCInsight/editorial-corrections.json",
        },
    }
    expected_manifest_bytes = (
        json.dumps(expected_manifest, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    if manifest != expected_manifest_bytes:
        raise PublicationStateError(
            "evidence correction is not the source-exclusion projection"
        )
    expected_report, narrative_count, removed_highlights = exclusion_only_report(
        original_report, snapshot_name, correction
    )
    if narrative_count != correction["removed_narrative_units"]:
        raise PublicationStateError(
            "editorial correction narrative removal count does not match"
        )
    excluded_urls = {
        source["url"]
        for source in original["sources"]
        if contains_virtual_event(source) and isinstance(source.get("url"), str)
    }
    highlighted_urls: set[str] = set()
    for highlight in removed_highlights:
        matched_urls = {url for url in excluded_urls if f"]({url})" in highlight}
        if len(matched_urls) != 1 or matched_urls & highlighted_urls:
            raise PublicationStateError(
                "removed highlight does not identify one excluded source"
            )
        highlighted_urls.update(matched_urls)
    if report != expected_report:
        raise PublicationStateError(
            "report correction is not the exclusion-only transformation"
        )


def load_editorial_corrections(site_dir: Path) -> dict[str, dict[str, Any]]:
    """Validate explicit original-to-corrected bindings, never a hash exemption."""
    path = site_dir / "editorial-corrections.json"
    if not path.exists():
        require_editorial_correction_records(site_dir, {})
        return {}
    ledger = read_json(path, "editorial corrections")
    if (
        not isinstance(ledger, dict)
        or set(ledger) != {"schema_version", "corrections"}
        or ledger["schema_version"] != 1
        or not isinstance(ledger["corrections"], list)
        or not ledger["corrections"]
    ):
        raise PublicationStateError("editorial corrections shape is invalid")
    fields = {
        "report_generated_at",
        "corrected_at",
        "original_report_sha256",
        "original_evidence_manifest_sha256",
        "corrected_report_sha256",
        "corrected_evidence_manifest_sha256",
        "removed_source_count",
        "removed_narrative_units",
    }
    corrections = {}
    for entry in ledger["corrections"]:
        if not isinstance(entry, dict) or set(entry) != fields:
            raise PublicationStateError("editorial correction fields are invalid")
        generated_at = entry["report_generated_at"]
        generated = parse_journal_timestamp(generated_at, "report_generated_at")
        corrected = parse_journal_timestamp(entry["corrected_at"], "corrected_at")
        if corrected <= generated or generated_at in corrections:
            raise PublicationStateError(
                "editorial correction time or identity is invalid"
            )
        for field in fields:
            if field.endswith("_sha256") and (
                not isinstance(entry[field], str)
                or not SHA256_PATTERN.fullmatch(entry[field])
            ):
                raise PublicationStateError("editorial correction digest is invalid")
        for field, minimum in (
            ("removed_source_count", 1),
            ("removed_narrative_units", 0),
        ):
            if type(entry[field]) is not int or entry[field] < minimum:
                raise PublicationStateError(
                    "editorial correction removal count is invalid"
                )
        if (
            entry["original_evidence_manifest_sha256"]
            == entry["corrected_evidence_manifest_sha256"]
        ):
            raise PublicationStateError(
                "editorial correction must change the evidence manifest"
            )
        snapshot = site_dir / "archive" / generated.strftime("%Y-%m-%dT%H-%M-%SZ")
        original_path = (
            site_dir.parent / "audit" / "original-reports" / snapshot.name / "report.md"
        )
        try:
            original_report = original_path.read_bytes()
        except OSError as error:
            raise PublicationStateError(
                "editorial correction original report is missing"
            ) from error
        if (
            hashlib.sha256(original_report).hexdigest()
            != entry["original_report_sha256"]
        ):
            raise PublicationStateError(
                "editorial correction does not match original report digest"
            )
        try:
            original_manifest = original_path.with_name(
                "evidence-manifest.json"
            ).read_bytes()
        except OSError as error:
            raise PublicationStateError(
                "editorial correction original manifest is missing"
            ) from error
        if (
            hashlib.sha256(original_manifest).hexdigest()
            != entry["original_evidence_manifest_sha256"]
        ):
            raise PublicationStateError(
                "editorial correction does not match original manifest digest"
            )
        try:
            report = (snapshot / "report.md").read_bytes()
            manifest = (snapshot / "evidence-manifest.json").read_bytes()
        except OSError as error:
            raise PublicationStateError(
                "editorial correction snapshot is missing"
            ) from error
        for data, field in (
            (report, "corrected_report_sha256"),
            (manifest, "corrected_evidence_manifest_sha256"),
        ):
            if hashlib.sha256(data).hexdigest() != entry[field]:
                raise PublicationStateError(
                    "editorial correction does not match artifact digest"
                )
        if manifest_identity(manifest)[0] != generated_at:
            raise PublicationStateError("editorial correction names the wrong report")
        expected_metadata = {
            "corrected_at": entry["corrected_at"],
            "original_evidence_manifest_sha256": entry[
                "original_evidence_manifest_sha256"
            ],
            "record": "/GRCInsight/editorial-corrections.json",
        }
        if json.loads(manifest).get("editorial_correction") != expected_metadata:
            raise PublicationStateError(
                "evidence manifest does not identify its editorial correction"
            )
        if report.decode("utf-8").count(editorial_correction_note(entry)) != 1:
            raise PublicationStateError(
                "corrected report must disclose its editorial correction"
            )
        validate_exclusion_only_correction(
            original_report, original_manifest, report, manifest, snapshot.name, entry
        )
        corrections[generated_at] = entry
    require_editorial_correction_records(site_dir, corrections)
    return corrections


def require_editorial_correction_records(
    site_dir: Path, corrections: dict[str, dict[str, Any]]
) -> None:
    for path in (site_dir / "archive").glob("*/evidence-manifest.json"):
        manifest = read_json(path, "archived evidence manifest")
        if (
            isinstance(manifest, dict)
            and "editorial_correction" in manifest
            and manifest.get("generated_at") not in corrections
        ):
            raise PublicationStateError("missing editorial correction record")


def publication_manifest_matches(
    published_digest: object,
    current_digest: object,
    generated_at: str,
    corrections: dict[str, dict[str, Any]],
) -> bool:
    if published_digest == current_digest:
        return True
    correction = corrections.get(generated_at)
    return bool(
        correction
        and correction["original_evidence_manifest_sha256"] == published_digest
        and correction["corrected_evidence_manifest_sha256"] == current_digest
    )


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
