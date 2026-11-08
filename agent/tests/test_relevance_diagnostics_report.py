"""Report runs surface only their own relevance diagnostics, bounded and sanitized."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "relevance_diagnostics.py"
REPORT = "report_20261107_181614_123"
OTHER = "report_20261107_150412_987"


def run(tmp_path, report=None, *args, report_id=REPORT, raw=None):
    summary = tmp_path / "summary.md"
    data = tmp_path / "report-data.json"
    if raw is not None:
        data.write_text(raw)
    elif report is not None:
        data.write_text(json.dumps(report))
    command = [
        sys.executable,
        str(SCRIPT),
        "--report-id",
        report_id,
        "--report-data",
        str(data),
        "--summary",
        str(summary),
        *args,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return result, summary.read_text() if summary.exists() else ""


def stored(report_id=REPORT, diagnostics=None):
    metadata = {"analysis_mode": "model"}
    if diagnostics is not None:
        metadata["relevance_diagnostics"] = diagnostics
    return {"id": report_id, "status": "completed", "metadata": metadata}


def test_the_reports_own_summary_is_surfaced(tmp_path):
    result, summary = run(
        tmp_path,
        stored(diagnostics={"mode": "enabled", "dropped_positions": 2, "cost": "0.001"}),
    )
    assert result.returncode == 0
    assert '"dropped_positions":2' in result.stdout and '"mode":"enabled"' in summary
    assert f"Report `{REPORT}`" in summary and summary.count("```") == 2


def test_a_response_for_another_report_is_never_surfaced(tmp_path):
    result, summary = run(tmp_path, stored(report_id=OTHER, diagnostics={"mode": "enabled"}))
    assert result.returncode == 0
    assert "unavailable (response_for_another_report)" in result.stdout
    assert '"mode"' not in result.stdout + summary


def test_values_cannot_break_out_of_the_summary_block(tmp_path):
    result, summary = run(tmp_path, stored(diagnostics={"status": "``` breakout\n## heading"}))
    assert result.returncode == 0
    assert summary.count("```") == 2
    assert "\n## heading" not in summary


def test_output_is_bounded_in_bytes(tmp_path):
    big = {"models": ["m" * 64] * 400}
    result, summary = run(tmp_path, stored(diagnostics=big), "--max-bytes", "3000")
    block = summary.split("```")[1]
    assert len(block.encode()) <= 3000
    assert "truncated" in summary
    assert len(result.stdout.encode()) <= 3000 + 200


def test_absent_summary_means_the_pilot_was_off(tmp_path):
    result, summary = run(tmp_path, stored())
    assert result.returncode == 0
    assert f"No article relevance diagnostics for {REPORT} (relevance mode off)" in summary


@pytest.mark.parametrize("raw", ["", "not json", "[]"])
def test_missing_or_unreadable_report_data_does_not_fail(tmp_path, raw):
    result, _ = run(tmp_path, raw=raw if raw else None)
    assert result.returncode == 0
    assert "unavailable" in result.stdout


def test_a_malformed_summary_is_reported_not_echoed(tmp_path):
    result, _ = run(tmp_path, stored(diagnostics=["secret"]))
    assert "unavailable (malformed_summary)" in result.stdout
    assert "secret" not in result.stdout


def test_an_unexpected_report_handle_is_refused_before_any_output(tmp_path):
    result, summary = run(tmp_path, stored(), report_id="report_x' OR 1")
    assert result.returncode == 0
    assert "unexpected report handle" in result.stdout
    assert summary == ""
