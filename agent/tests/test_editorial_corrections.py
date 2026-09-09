from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def correction_fixture(tmp_path):
    ns = runpy.run_path(str(ROOT / "scripts/publication_state.py"))
    generated = "2026-09-08T21:01:17Z"
    correction = {
        "report_generated_at": generated,
        "corrected_at": "2026-09-09T01:15:00Z",
        "original_report_sha256": "1" * 64,
        "original_evidence_manifest_sha256": "2" * 64,
        "removed_source_count": 2,
        "removed_narrative_units": 0,
    }
    report = (
        "# Report\n**Generated:** "
        + generated
        + "\n\n## Executive Summary\n"
        + ns["editorial_correction_note"](correction)
        + "\n\nOriginal analysis.\n"
    ).encode()
    manifest = json.dumps(
        {
            "generated_at": generated,
            "editorial_correction": {
                "corrected_at": correction["corrected_at"],
                "original_evidence_manifest_sha256": correction[
                    "original_evidence_manifest_sha256"
                ],
                "record": "/GRCInsight/editorial-corrections.json",
            },
        }
    ).encode()
    correction["corrected_report_sha256"] = sha(report)
    correction["corrected_evidence_manifest_sha256"] = sha(manifest)
    snapshot = tmp_path / "archive/2026-09-08T21-01-17Z"
    snapshot.mkdir(parents=True)
    (snapshot / "report.md").write_bytes(report)
    (snapshot / "evidence-manifest.json").write_bytes(manifest)
    (tmp_path / "editorial-corrections.json").write_text(
        json.dumps({"schema_version": 1, "corrections": [correction]})
    )
    return ns, correction, manifest, snapshot


def test_correction_binds_new_bytes_without_rewriting_original_publication_event(tmp_path):
    ns, correction, manifest, _snapshot = correction_fixture(tmp_path)
    corrections = ns["load_editorial_corrections"](tmp_path)
    state = ns["build_published_state"](manifest)
    event = ns["state_event"](state, "2026-09-08T21:01:27Z")
    event["evidence_manifest_sha256"] = correction["original_evidence_manifest_sha256"]
    history = {
        "schema_version": 1,
        "max_entries": 30,
        "history_started_at": "2026-09-08T21:01:27Z",
        "schedule": {"cadence": "daily", "time_utc": "13:00"},
        "events": [event],
    }
    original = deepcopy(history)
    ns["validate_publication_history"](history, state, manifest, corrections=corrections)
    assert history == original
    with pytest.raises(ValueError, match="latest event"):
        ns["validate_publication_history"](history, state, manifest)
    history["events"][0]["evidence_manifest_sha256"] = "3" * 64
    with pytest.raises(ValueError, match="latest event"):
        ns["validate_publication_history"](history, state, manifest, corrections=corrections)


@pytest.mark.parametrize("artifact", ["report.md", "evidence-manifest.json"])
def test_correction_rejects_changed_corrected_bytes(tmp_path, artifact):
    ns, _correction, _manifest, snapshot = correction_fixture(tmp_path)
    path = snapshot / artifact
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="digest"):
        ns["load_editorial_corrections"](tmp_path)


@pytest.mark.parametrize(
    "mutation",
    ["missing_note", "predates", "unknown_field", "duplicate", "invalid_hash", "missing_snapshot"],
)
def test_correction_record_fails_closed(tmp_path, mutation):
    ns, correction, _manifest, snapshot = correction_fixture(tmp_path)
    if mutation == "missing_note":
        report = b"## Executive Summary\nNo correction note.\n"
        (snapshot / "report.md").write_bytes(report)
        correction["corrected_report_sha256"] = sha(report)
    elif mutation == "predates":
        correction["corrected_at"] = "2020-01-01T00:00:00Z"
    elif mutation == "unknown_field":
        correction["ignored"] = True
    elif mutation == "invalid_hash":
        correction["original_report_sha256"] = "invalid"
    elif mutation == "missing_snapshot":
        (snapshot / "report.md").unlink()
    entries = [correction, correction] if mutation == "duplicate" else [correction]
    (tmp_path / "editorial-corrections.json").write_text(
        json.dumps({"schema_version": 1, "corrections": entries})
    )
    with pytest.raises(ValueError):
        ns["load_editorial_corrections"](tmp_path)


def test_no_correction_record_leaves_existing_contract_unchanged(tmp_path):
    ns = runpy.run_path(str(ROOT / "scripts/publication_state.py"))
    assert ns["load_editorial_corrections"](tmp_path) == {}


def test_missing_ledger_cannot_orphan_corrections_after_journal_rollover(tmp_path):
    ns, _correction, _manifest, _snapshot = correction_fixture(tmp_path)
    (tmp_path / "editorial-corrections.json").unlink()
    with pytest.raises(ValueError, match="missing editorial correction record"):
        ns["load_editorial_corrections"](tmp_path)
