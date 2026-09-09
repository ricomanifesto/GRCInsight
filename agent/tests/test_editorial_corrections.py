from copy import deepcopy
from functools import partial
import hashlib
from http.client import HTTPConnection
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
from threading import Thread

import pytest

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def correction_fixture(tmp_path):
    ns = runpy.run_path(str(ROOT / "scripts/publication_state.py"))
    generated = "2026-09-08T21:01:17Z"
    original_report = b"# Original report\n\nOriginal analysis.\n[Virtual Event] Promotion.\n"
    correction = {
        "report_generated_at": generated,
        "corrected_at": "2026-09-09T01:15:00Z",
        "original_report_sha256": sha(original_report),
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
    snapshot = tmp_path / "site/archive/2026-09-08T21-01-17Z"
    snapshot.mkdir(parents=True)
    (snapshot / "report.md").write_bytes(report)
    (snapshot / "evidence-manifest.json").write_bytes(manifest)
    (tmp_path / "site/editorial-corrections.json").write_text(
        json.dumps({"schema_version": 1, "corrections": [correction]})
    )
    original_path = tmp_path / "audit/original-reports/2026-09-08T21-01-17Z/report.md"
    original_path.parent.mkdir(parents=True)
    original_path.write_bytes(original_report)
    return ns, correction, manifest, snapshot


def test_correction_binds_new_bytes_without_rewriting_original_publication_event(tmp_path):
    ns, correction, manifest, _snapshot = correction_fixture(tmp_path)
    corrections = ns["load_editorial_corrections"](tmp_path / "site")
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
        ns["load_editorial_corrections"](tmp_path / "site")


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_note",
        "predates",
        "unknown_field",
        "duplicate",
        "invalid_hash",
        "missing_snapshot",
        "substituted_original_hash",
        "missing_original",
        "changed_original",
    ],
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
    elif mutation == "substituted_original_hash":
        correction["original_report_sha256"] = "f" * 64
    elif mutation == "missing_original":
        (tmp_path / "audit/original-reports/2026-09-08T21-01-17Z/report.md").unlink()
    elif mutation == "changed_original":
        (tmp_path / "audit/original-reports/2026-09-08T21-01-17Z/report.md").write_bytes(
            b"Replacement original.\n"
        )
    entries = [correction, correction] if mutation == "duplicate" else [correction]
    (tmp_path / "site/editorial-corrections.json").write_text(
        json.dumps({"schema_version": 1, "corrections": entries})
    )
    with pytest.raises(ValueError):
        ns["load_editorial_corrections"](tmp_path / "site")


def test_no_correction_record_leaves_existing_contract_unchanged(tmp_path):
    ns = runpy.run_path(str(ROOT / "scripts/publication_state.py"))
    assert ns["load_editorial_corrections"](tmp_path) == {}


def test_missing_ledger_cannot_orphan_corrections_after_journal_rollover(tmp_path):
    ns, _correction, _manifest, _snapshot = correction_fixture(tmp_path)
    (tmp_path / "site/editorial-corrections.json").unlink()
    with pytest.raises(ValueError, match="missing editorial correction record"):
        ns["load_editorial_corrections"](tmp_path / "site")


@pytest.mark.parametrize("layout", ["offline", "shallow"])
def test_correction_validation_needs_original_files_not_git_history(tmp_path, layout):
    package = tmp_path / "package"
    package.mkdir()
    correction_fixture(package)
    scripts = package / "scripts"
    scripts.mkdir()
    shutil.copy2(ROOT / "scripts/publication_state.py", scripts)
    if layout == "shallow":
        subprocess.run(["git", "init", "-q", str(package)], check=True)
        for message in ("Initial fixture", "Packaged fixture"):
            subprocess.run(["git", "-C", str(package), "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(package),
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-q",
                    "--allow-empty",
                    "-m",
                    message,
                ],
                check=True,
            )
        shallow = tmp_path / "shallow"
        subprocess.run(
            ["git", "clone", "-q", "--depth=1", package.as_uri(), str(shallow)], check=True
        )
        assert (shallow / ".git/shallow").is_file()
        package = shallow
    else:
        assert not (package / ".git").exists()
    command = (
        "from pathlib import Path; import runpy; "
        "ns = runpy.run_path('scripts/publication_state.py'); "
        "assert len(ns['load_editorial_corrections'](Path('site'))) == 1"
    )
    result = subprocess.run(
        [sys.executable, "-c", command],
        cwd=package,
        env={"PATH": "", "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_pages_payload_does_not_serve_audit_originals():
    workflow = (ROOT / ".github/workflows/deploy-site.yml").read_text()
    upload_step = workflow.split("- name: Upload Pages artifact\n", 1)[1].split("\n      - ", 1)[0]
    assert "path: site" in [line.strip() for line in upload_step.splitlines()]
    site = ROOT / "site"
    assert not any(path.is_symlink() for path in site.rglob("*"))
    originals = list((ROOT / "audit/original-reports").glob("*/report.md"))
    assert originals

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A002
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(site)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for original in originals:
            connection = HTTPConnection("127.0.0.1", server.server_port)
            try:
                connection.request("GET", "/" + original.relative_to(ROOT).as_posix())
                response = connection.getresponse()
                assert response.status == 404
                response.read()
            finally:
                connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
