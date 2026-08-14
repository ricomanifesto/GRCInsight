import json
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
