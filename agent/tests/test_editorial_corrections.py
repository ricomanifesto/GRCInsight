from copy import deepcopy
from datetime import datetime
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
    sources = [
        {"title": "Security report", "url": "https://example.com/report", "cves": []},
        {
            "title": "[Virtual Event] Promotion",
            "url": "https://example.com/promo",
            "cves": [],
        },
        {"title": "Security events", "url": "https://example.com/events", "cves": []},
        {
            "title": "[Virtual Event] Second",
            "url": "https://example.com/second",
            "cves": [],
        },
    ]
    original_manifest = (
        json.dumps(
            {
                "schema_version": 3,
                "generated_at": generated,
                "resolved_model": "original-model",
                "sources": sources,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode()
    retained_report = (
        f"# Report\n**Generated:** {generated}\n**Articles Analyzed:** 4\n"
        "**Model:** original-model\n\n## Executive Summary\n\n"
        "Original analysis.\n\nSecurity teams investigate generic events.\n\n"
        "## Source Highlights\n\n"
        "- [Security report](https://example.com/report)\n"
        "- [Security events](https://example.com/events)\n"
    )
    original_report = (
        retained_report.replace(
            "## Source Highlights\n\n",
            "Review [**Virtual** Event] Promotion.\n## Source Highlights\n\n",
        )
        .replace(
            "- [Security events](https://example.com/events)\n",
            "- [\\[Virtual Event\\] Promotion](https://example.com/promo)\n"
            "- [Security events](https://example.com/events)\n"
            "- [\\[Virtual Event\\] Second](https://example.com/second)\n",
        )
        .encode()
    )
    correction = {
        "report_generated_at": generated,
        "corrected_at": "2026-09-09T01:15:00Z",
        "original_report_sha256": sha(original_report),
        "original_evidence_manifest_sha256": sha(original_manifest),
        "removed_source_count": 2,
        "removed_narrative_units": 1,
    }
    report = retained_report.replace(
        "## Executive Summary\n\n",
        "## Executive Summary\n\n" + ns["editorial_correction_note"](correction) + "\n\n",
    ).encode()
    projected = json.loads(original_manifest)
    projected["sources"] = [sources[0], sources[2]]
    projected["editorial_correction"] = {
        "corrected_at": correction["corrected_at"],
        "original_evidence_manifest_sha256": correction["original_evidence_manifest_sha256"],
        "record": "/GRCInsight/editorial-corrections.json",
    }
    manifest = (json.dumps(projected, indent=2, ensure_ascii=False) + "\n").encode()
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
    original_path.with_name("evidence-manifest.json").write_bytes(original_manifest)
    return ns, correction, manifest, snapshot


def refresh_corrected_hashes(tmp_path, correction, snapshot):
    correction["corrected_report_sha256"] = sha((snapshot / "report.md").read_bytes())
    correction["corrected_evidence_manifest_sha256"] = sha(
        (snapshot / "evidence-manifest.json").read_bytes()
    )
    (tmp_path / "site/editorial-corrections.json").write_text(
        json.dumps({"schema_version": 1, "corrections": [correction]})
    )


def test_correction_binds_new_bytes_without_rewriting_original_publication_event(
    tmp_path,
):
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
        "retained_prose",
        "new_claim",
        "report_metadata",
        "partial_promotion",
        "removed_eligible_prose",
        "reordered_prose",
        "disclosure_suffix",
        "generic_events",
        "source_title",
        "source_url",
        "source_cves",
        "source_order",
        "added_source",
        "removed_eligible_source",
        "manifest_metadata",
        "manifest_numeric_type",
        "coherent_source_title",
        "coherent_model",
        "coherent_new_source",
        "source_count_low",
        "source_count_high",
        "narrative_count_low",
        "narrative_count_high",
    ],
)
def test_updated_hashes_cannot_authorize_non_exclusion_changes(tmp_path, mutation):
    ns, correction, _manifest, snapshot = correction_fixture(tmp_path)
    report = (snapshot / "report.md").read_text()
    manifest = json.loads((snapshot / "evidence-manifest.json").read_bytes())
    if mutation == "retained_prose":
        report = report.replace("Original analysis.", "Unsupported replacement analysis.")
    elif mutation == "new_claim":
        report = report.replace("Original analysis.", "Original analysis. A new claim is certain.")
    elif mutation == "report_metadata":
        report = report.replace("**Articles Analyzed:** 4", "**Articles Analyzed:** 40")
    elif mutation == "partial_promotion":
        report = report.replace("## Source Highlights", "Review Promotion.\n\n## Source Highlights")
    elif mutation == "removed_eligible_prose":
        report = report.replace("Original analysis.\n", "")
        correction["removed_narrative_units"] += 1
    elif mutation == "reordered_prose":
        report = report.replace(
            "Original analysis.\n\nSecurity teams investigate generic events.",
            "Security teams investigate generic events.\n\nOriginal analysis.",
        )
    elif mutation == "disclosure_suffix":
        report = report.replace(
            ns["editorial_correction_note"](correction),
            ns["editorial_correction_note"](correction) + " New conclusions were confirmed.",
        )
    elif mutation == "generic_events":
        report = report.replace("Security teams investigate generic events.\n", "")
        correction["removed_narrative_units"] += 1
    elif mutation == "source_title":
        manifest["sources"][0]["title"] = "New source claim"
    elif mutation == "source_url":
        manifest["sources"][0]["url"] = "https://example.com/substitute"
    elif mutation == "source_cves":
        manifest["sources"][0]["cves"] = ["CVE-2026-99999"]
    elif mutation == "source_order":
        manifest["sources"].reverse()
    elif mutation == "added_source":
        manifest["sources"].append(
            {"title": "New evidence", "url": "https://example.com/new", "cves": []}
        )
        correction["removed_source_count"] -= 1
    elif mutation == "removed_eligible_source":
        manifest["sources"].pop()
        correction["removed_source_count"] += 1
    elif mutation == "manifest_metadata":
        manifest["resolved_model"] = "different-model"
    elif mutation == "manifest_numeric_type":
        manifest["schema_version"] = 3.0
    elif mutation == "coherent_source_title":
        manifest["sources"][0]["title"] = "Rewritten security report"
        report = report.replace("[Security report]", "[Rewritten security report]")
    elif mutation == "coherent_model":
        manifest["resolved_model"] = "different-model"
        report = report.replace("original-model", "different-model")
    elif mutation == "coherent_new_source":
        manifest["sources"].append(
            {"title": "New evidence", "url": "https://example.com/new", "cves": []}
        )
        report += "- [New evidence](https://example.com/new)\n"
        correction["removed_source_count"] -= 1
    elif mutation == "source_count_low":
        correction["removed_source_count"] -= 1
    elif mutation == "source_count_high":
        correction["removed_source_count"] += 1
    elif mutation == "narrative_count_low":
        correction["removed_narrative_units"] -= 1
    elif mutation == "narrative_count_high":
        correction["removed_narrative_units"] += 1
    (snapshot / "report.md").write_text(report)
    (snapshot / "evidence-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    refresh_corrected_hashes(tmp_path, correction, snapshot)
    with pytest.raises(ValueError):
        ns["load_editorial_corrections"](tmp_path / "site")


@pytest.mark.parametrize("mutation", ["missing", "changed", "substituted_digest"])
def test_original_manifest_is_required_and_bound(tmp_path, mutation):
    ns, correction, _manifest, snapshot = correction_fixture(tmp_path)
    original = tmp_path / "audit/original-reports" / snapshot.name / "evidence-manifest.json"
    if mutation == "missing":
        original.unlink()
    elif mutation == "changed":
        original.write_bytes(original.read_bytes() + b" ")
    else:
        correction["original_evidence_manifest_sha256"] = "f" * 64
        manifest = json.loads((snapshot / "evidence-manifest.json").read_bytes())
        manifest["editorial_correction"]["original_evidence_manifest_sha256"] = "f" * 64
        (snapshot / "evidence-manifest.json").write_text(json.dumps(manifest))
        refresh_corrected_hashes(tmp_path, correction, snapshot)
    with pytest.raises(ValueError):
        ns["load_editorial_corrections"](tmp_path / "site")


def test_source_highlights_can_be_a_subset_of_original_evidence(tmp_path):
    ns, correction, _manifest, snapshot = correction_fixture(tmp_path)
    original = tmp_path / "audit/original-reports" / snapshot.name / "report.md"
    original.write_bytes(
        original.read_bytes().replace(
            b"- [\\[Virtual Event\\] Second](https://example.com/second)\n", b""
        )
    )
    correction["original_report_sha256"] = sha(original.read_bytes())
    refresh_corrected_hashes(tmp_path, correction, snapshot)
    assert len(ns["load_editorial_corrections"](tmp_path / "site")) == 1


@pytest.mark.parametrize("kind", ["paragraph", "list_item", "table_row"])
@pytest.mark.parametrize("partial", [False, True])
def test_correction_removes_complete_units_only(tmp_path, kind, partial):
    ns, correction, _manifest, snapshot = correction_fixture(tmp_path)
    original = tmp_path / "audit/original-reports" / snapshot.name / "report.md"
    if kind == "paragraph":
        unit = b"Review [Virtual Event] Promotion.\nContinuation text.\n"
        residue = "Continuation text.\n"
        table_header = ""
    elif kind == "list_item":
        unit = b"1. Review [Virtual Event] Promotion.\n   Continuation text.\n"
        residue = "   Continuation text.\n"
        table_header = ""
    else:
        table_header = "| Risk | Evidence |\n| --- | --- |\n"
        unit = table_header.encode() + b"| High | [Virtual Event] Promotion and context |\n"
        residue = "| High | Promotion and context |\n"
    original.write_bytes(
        original.read_bytes().replace(b"Review [**Virtual** Event] Promotion.\n", unit)
    )
    correction["original_report_sha256"] = sha(original.read_bytes())
    report = (
        (snapshot / "report.md")
        .read_text()
        .replace(
            "## Source Highlights",
            table_header + (residue if partial else "") + "## Source Highlights",
        )
    )
    (snapshot / "report.md").write_text(report)
    refresh_corrected_hashes(tmp_path, correction, snapshot)
    if partial:
        with pytest.raises(ValueError, match="exclusion-only transformation"):
            ns["load_editorial_corrections"](tmp_path / "site")
    else:
        assert len(ns["load_editorial_corrections"](tmp_path / "site")) == 1


def test_removed_source_reference_alone_does_not_authorize_deleting_prose(tmp_path):
    ns, correction, _manifest, snapshot = correction_fixture(tmp_path)
    original = tmp_path / "audit/original-reports" / snapshot.name / "report.md"
    original.write_bytes(
        original.read_bytes().replace(
            b"## Source Highlights",
            b"Independent analysis cites [background](https://example.com/promo).\n\n## Source Highlights",
        )
    )
    correction["original_report_sha256"] = sha(original.read_bytes())
    correction["removed_narrative_units"] += 1
    refresh_corrected_hashes(tmp_path, correction, snapshot)
    with pytest.raises(ValueError, match="narrative removal count"):
        ns["load_editorial_corrections"](tmp_path / "site")


@pytest.mark.parametrize("shape", ["unframed_table", "indented_code", "fenced_code"])
def test_ambiguous_blocks_cannot_authorize_partial_corrections(tmp_path, shape):
    ns, correction, _manifest, snapshot = correction_fixture(tmp_path)
    original = tmp_path / "audit/original-reports" / snapshot.name / "report.md"
    residue = ""
    if shape == "unframed_table":
        unit = b"| [Virtual Event] Promotion.\nContinuation text.\n"
        residue = "Continuation text.\n"
    elif shape == "indented_code":
        unit = b"    [Virtual Event] Promotion.\n"
    else:
        unit = b"Context.\n```\n[Virtual Event] Promotion.\n```\n"
    original.write_bytes(
        original.read_bytes().replace(b"Review [**Virtual** Event] Promotion.\n", unit)
    )
    correction["original_report_sha256"] = sha(original.read_bytes())
    report = (
        (snapshot / "report.md")
        .read_text()
        .replace("## Source Highlights", residue + "## Source Highlights")
    )
    (snapshot / "report.md").write_text(report)
    refresh_corrected_hashes(tmp_path, correction, snapshot)
    with pytest.raises(ValueError, match="unsupported"):
        ns["load_editorial_corrections"](tmp_path / "site")


@pytest.mark.parametrize("slug", ["2026-09-06T22-53-06Z", "2026-09-09T11-06-50Z"])
@pytest.mark.parametrize("mutation", ["none", "unit", "report", "snapshot"])
def test_untagged_exceptions_require_exact_units_report_and_snapshot(tmp_path, slug, mutation):
    ns = runpy.run_path(str(ROOT / "scripts/publication_state.py"))
    ledger = json.loads((ROOT / "site/editorial-corrections.json").read_bytes())
    correction = next(
        c
        for c in ledger["corrections"]
        if datetime.fromisoformat(c["report_generated_at"].replace("Z", "+00:00")).strftime(
            "%Y-%m-%dT%H-%M-%SZ"
        )
        == slug
    )
    correction = deepcopy(correction)
    snapshot = tmp_path / "site/archive" / slug
    original_dir = tmp_path / "audit/original-reports" / slug
    shutil.copytree(ROOT / "audit/original-reports" / slug, original_dir)
    snapshot.mkdir(parents=True)
    for name in ("report.md", "evidence-manifest.json"):
        shutil.copy2(ROOT / "site/archive" / slug / name, snapshot)
    if mutation in {"unit", "report"}:
        report_path = original_dir / "report.md"
        raw = report_path.read_bytes()
        if mutation == "unit":
            prefix = b"8. **Track cloud" if slug.startswith("2026-09-06") else b"6. **Establish AI"
            raw = raw.replace(prefix, prefix.replace(b"**", b"**Altered ", 1))
        else:
            raw = raw.replace(b"# GRC Intelligence Report", b"# Changed Report", 1)
            assert raw != report_path.read_bytes()
        report_path.write_bytes(raw)
        correction["original_report_sha256"] = sha(raw)
    elif mutation == "snapshot":
        old_generated = correction["report_generated_at"]
        changed_time = datetime.fromisoformat(old_generated.replace("Z", "+00:00")).replace(
            second=0
        )
        new_generated = changed_time.isoformat().replace("+00:00", "Z")
        assert new_generated != old_generated
        correction["report_generated_at"] = new_generated
        new_slug = changed_time.strftime("%Y-%m-%dT%H-%M-%SZ")
        new_snapshot = snapshot.with_name(new_slug)
        new_original = original_dir.with_name(new_slug)
        snapshot.rename(new_snapshot)
        original_dir.rename(new_original)
        snapshot, original_dir = new_snapshot, new_original
        for directory in (snapshot, original_dir):
            for name in ("report.md", "evidence-manifest.json"):
                path = directory / name
                path.write_bytes(
                    path.read_bytes().replace(old_generated.encode(), new_generated.encode())
                )
        correction["original_report_sha256"] = sha((original_dir / "report.md").read_bytes())
        correction["original_evidence_manifest_sha256"] = sha(
            (original_dir / "evidence-manifest.json").read_bytes()
        )
        manifest = json.loads((snapshot / "evidence-manifest.json").read_bytes())
        manifest["editorial_correction"]["original_evidence_manifest_sha256"] = correction[
            "original_evidence_manifest_sha256"
        ]
        (snapshot / "evidence-manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        )
    refresh_corrected_hashes(tmp_path, correction, snapshot)
    if mutation == "none":
        assert len(ns["load_editorial_corrections"](tmp_path / "site")) == 1
    else:
        with pytest.raises(
            ValueError, match="narrative removal count|exclusion-only transformation"
        ):
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
    core = package / "agent/core"
    core.mkdir(parents=True)
    shutil.copy2(ROOT / "agent/core/content_policy.py", core)
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
            ["git", "clone", "-q", "--depth=1", package.as_uri(), str(shallow)],
            check=True,
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
    originals = list((ROOT / "audit/original-reports").glob("*/*"))
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
