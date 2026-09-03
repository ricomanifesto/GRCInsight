import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_STATE = REPO_ROOT / "scripts" / "publication_state.py"


def publication_namespace() -> dict:
    return runpy.run_path(str(PUBLICATION_STATE))


def manifest_bytes(generated_at: str = "2026-08-14T10:12:05.649488Z") -> bytes:
    return (
        json.dumps(
            {
                "schema_version": 3,
                "generated_at": generated_at,
                "sources": [],
            },
            indent=2,
        )
        + "\n"
    ).encode()


def history_for(namespace: dict, state: dict, event_at: str) -> dict:
    return {
        "schema_version": 1,
        "max_entries": 30,
        "history_started_at": event_at,
        "schedule": {"cadence": "daily", "time_utc": "13:00"},
        "events": [namespace["state_event"](state, event_at)],
    }


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("provider returned HTTP 401", "provider_authentication"),
        ("insufficient_quota from provider", "provider_quota"),
        ("provider returned HTTP 429", "provider_rate_limit"),
        ("request timed out", "provider_deadline"),
        ("missing model identity", "provider_provenance"),
        ("unexpected provider response", "unclassified_provider_failure"),
    ],
)
def test_classification_returns_only_safe_tokens(reason, expected):
    namespace = publication_namespace()

    assert namespace["classify_fallback_reason"](reason) == expected


def test_classify_cli_never_echoes_raw_provider_text(tmp_path):
    secret_reason = "HTTP 402 provider-secret-do-not-log"
    report_data = tmp_path / "report-data.json"
    report_data.write_text(
        json.dumps({"metadata": {"fallback_reason": secret_reason}}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(PUBLICATION_STATE),
            "classify",
            "--report-data",
            str(report_data),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "provider_quota"
    assert secret_reason not in result.stdout
    assert secret_reason not in result.stderr


def test_published_state_is_bound_to_the_current_manifest():
    namespace = publication_namespace()
    manifest = manifest_bytes()

    state = namespace["build_published_state"](manifest)

    assert state["outcome"] == "published"
    assert state["report_generated_at"] == "2026-08-14T10:12:05.649488Z"
    assert "attempted_at" not in state
    assert namespace["validate_publication_state"](state, manifest) == state


def test_retained_state_carries_only_safe_public_fields():
    namespace = publication_namespace()
    manifest = manifest_bytes()

    state = namespace["build_retained_state"](
        manifest,
        "2026-08-14T14:07:22Z",
        "provider_quota",
    )

    assert set(state) == namespace["RETAINED_FIELDS"]
    assert state["refusal_category"] == "provider_quota"
    assert "reason" not in state
    assert namespace["validate_publication_state"](state, manifest) == state


def test_retained_state_rejects_attempt_superseded_by_current_report():
    namespace = publication_namespace()

    with pytest.raises(namespace["StaleRetainedAttempt"]):
        namespace["build_retained_state"](
            manifest_bytes("2026-08-14T15:00:00Z"),
            "2026-08-14T14:07:22Z",
            "provider_quota",
        )


def test_state_rejects_manifest_drift_and_extra_fields():
    namespace = publication_namespace()
    manifest = manifest_bytes()
    state = namespace["build_published_state"](manifest)

    with pytest.raises(namespace["PublicationStateError"]):
        namespace["validate_publication_state"](state, manifest_bytes("2026-08-14T15:00:00Z"))

    state["raw_provider_error"] = "must never be public"
    with pytest.raises(namespace["PublicationStateError"]):
        namespace["validate_publication_state"](state, manifest)


def test_history_is_bounded_newest_first_and_bound_to_latest_state():
    namespace = publication_namespace()
    manifest = manifest_bytes()
    state = namespace["build_published_state"](manifest)
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    events = [
        namespace["state_event"](
            state, (start - timedelta(hours=index)).isoformat().replace("+00:00", "Z")
        )
        for index in range(30)
    ]
    history = {
        "schema_version": 1,
        "max_entries": 30,
        "history_started_at": "2026-08-14T10:12:06Z",
        "schedule": {"cadence": "daily", "time_utc": "13:00"},
        "events": events,
    }
    newer_at = "2026-09-02T00:00:00Z"

    updated = namespace["append_publication_event"](history, state, newer_at)

    assert len(updated["events"]) == 30
    assert updated["events"][0]["event_at"] == newer_at
    assert events[-1] not in updated["events"]
    assert namespace["validate_publication_history"](updated, state, manifest) == updated


def test_history_append_is_idempotent_and_rejects_conflicting_timestamp():
    namespace = publication_namespace()
    manifest = manifest_bytes()
    state = namespace["build_published_state"](manifest)
    event_at = "2026-08-14T14:07:22Z"
    history = history_for(namespace, state, event_at)

    assert namespace["append_publication_event"](history, state, event_at) == history

    retained = namespace["build_retained_state"](manifest, event_at, "provider_quota")
    with pytest.raises(namespace["PublicationStateError"]):
        namespace["append_publication_event"](history, retained, event_at)


def test_history_rejects_malformed_unbounded_and_misordered_events():
    namespace = publication_namespace()
    manifest = manifest_bytes()
    state = namespace["build_published_state"](manifest)
    history = history_for(namespace, state, "2026-08-14T14:07:22Z")

    history["events"] = history["events"] * 31
    with pytest.raises(namespace["PublicationStateError"]):
        namespace["validate_publication_history_shape"](history)

    history = history_for(namespace, state, "2026-08-14T14:07:22Z")
    history["events"].append(dict(history["events"][0]))
    with pytest.raises(namespace["PublicationStateError"]):
        namespace["validate_publication_history_shape"](history)


def test_history_rejects_unknown_category_and_event_before_report():
    namespace = publication_namespace()
    manifest = manifest_bytes()
    retained = namespace["build_retained_state"](manifest, "2026-08-14T14:07:22Z", "provider_quota")
    history = history_for(namespace, retained, "2026-08-14T14:07:22Z")
    history["events"][0]["refusal_category"] = "raw_provider_error"
    with pytest.raises(namespace["PublicationStateError"]):
        namespace["validate_publication_history_shape"](history)

    published = namespace["build_published_state"](manifest)
    with pytest.raises(namespace["PublicationStateError"]):
        namespace["state_event"](published, "2026-08-14T10:00:00Z")
    with pytest.raises(namespace["PublicationStateError"]):
        namespace["state_event"](published, "2026-08-14T16:00:00+00:00")


def test_recovery_appends_published_event_and_clears_latest_retained_state():
    namespace = publication_namespace()
    retained_manifest = manifest_bytes()
    retained = namespace["build_retained_state"](
        retained_manifest, "2026-08-14T14:07:22Z", "provider_provenance"
    )
    history = history_for(namespace, retained, "2026-08-14T14:07:22Z")
    published_manifest = manifest_bytes("2026-08-14T15:00:00Z")
    published = namespace["build_published_state"](published_manifest)

    recovered = namespace["append_publication_event"](history, published, "2026-08-14T16:00:00Z")

    assert [event["outcome"] for event in recovered["events"]] == [
        "published",
        "retained",
    ]
    assert (
        namespace["validate_publication_history"](recovered, published, published_manifest)
        == recovered
    )


def test_superseded_event_does_not_mutate_history():
    namespace = publication_namespace()
    manifest = manifest_bytes()
    state = namespace["build_published_state"](manifest)
    history = history_for(namespace, state, "2026-08-14T16:00:00Z")
    before = json.dumps(history, sort_keys=True)

    with pytest.raises(namespace["StalePublicationEvent"]):
        namespace["append_publication_event"](history, state, "2026-08-14T15:00:00Z")

    assert json.dumps(history, sort_keys=True) == before


def test_record_cli_exit_four_preserves_state_and_history_on_supersession(tmp_path):
    namespace = publication_namespace()
    manifest = manifest_bytes()
    manifest_path = tmp_path / "evidence-manifest.json"
    manifest_path.write_bytes(manifest)
    state_path = tmp_path / "publication-state.json"
    published = namespace["build_published_state"](manifest)
    state_path.write_text(json.dumps(published), encoding="utf-8")
    history_path = tmp_path / "publication-history.json"
    history = history_for(namespace, published, "2026-08-14T16:00:00Z")
    history_path.write_text(json.dumps(history), encoding="utf-8")
    state_before = state_path.read_bytes()
    history_before = history_path.read_bytes()

    result = subprocess.run(
        [
            sys.executable,
            str(PUBLICATION_STATE),
            "record-retained",
            "--manifest",
            str(manifest_path),
            "--output",
            str(state_path),
            "--history",
            str(history_path),
            "--attempted-at",
            "2026-08-14T15:00:00Z",
            "--category",
            "provider_quota",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 4
    assert "superseded" in result.stderr
    assert state_path.read_bytes() == state_before
    assert history_path.read_bytes() == history_before


def test_record_cli_rejects_publication_event_before_report(tmp_path):
    namespace = publication_namespace()
    manifest = manifest_bytes()
    manifest_path = tmp_path / "evidence-manifest.json"
    manifest_path.write_bytes(manifest)
    state_path = tmp_path / "publication-state.json"
    published = namespace["build_published_state"](manifest)
    state_path.write_text(json.dumps(published), encoding="utf-8")
    history_path = tmp_path / "publication-history.json"
    history = history_for(namespace, published, "2026-08-14T16:00:00Z")
    history_path.write_text(json.dumps(history), encoding="utf-8")
    state_before = state_path.read_bytes()
    history_before = history_path.read_bytes()

    result = subprocess.run(
        [
            sys.executable,
            str(PUBLICATION_STATE),
            "record-published",
            "--manifest",
            str(manifest_path),
            "--output",
            str(state_path),
            "--history",
            str(history_path),
            "--event-at",
            "2026-08-14T10:00:00Z",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "predates its report" in result.stderr
    assert "superseded" not in result.stderr
    assert state_path.read_bytes() == state_before
    assert history_path.read_bytes() == history_before
