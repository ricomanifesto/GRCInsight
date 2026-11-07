"""Report runs surface only their own relevance diagnostics, bounded and sanitized."""

import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "relevance_diagnostics.py"
REPORT = "report_20261107_181614_123"
OTHER = "report_20261107_150412_987"


def event(kind, payload, prefix="2026-11-07 18:16:20.123 | INFO | services.model_service - "):
    return {"timestamp": 1, "message": f"{prefix}Article relevance {kind} {json.dumps(payload)}\n"}


def run(tmp_path, events=None, *args):
    summary = tmp_path / "summary.md"
    command = [sys.executable, str(SCRIPT), "--report-id", REPORT, "--summary", str(summary)]
    if events is not None:
        path = tmp_path / "events.json"
        path.write_text(json.dumps({"events": events}))
        command += ["--events", str(path)]
    command += list(args)
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return result, summary.read_text() if summary.exists() else ""


def test_only_the_requested_reports_lines_are_surfaced(tmp_path):
    result, summary = run(
        tmp_path,
        [
            event("pilot", {"mode": "shadow", "status": "shadow", "report_id": REPORT}),
            event("pilot", {"mode": "shadow", "status": "used", "report_id": OTHER}),
            event("selection", {"route": "decision", "records": []}),
            event("selection", {"route": "decision", "keep_violations": 0, "report_id": REPORT}),
        ],
    )
    assert result.returncode == 0
    assert result.stdout.count("Article relevance ") == 2
    assert OTHER not in result.stdout + summary
    assert '"status":"used"' not in result.stdout
    assert "Article relevance selection" in summary and '"keep_violations":0' in summary


def test_malformed_or_foreign_messages_never_reach_the_output(tmp_path):
    result, summary = run(
        tmp_path,
        [
            {"message": f"Article relevance pilot not-json {REPORT}"},
            {"message": f"Article relevance pilot [1, 2] {REPORT}"},
            {"message": f"Traceback mentioning {REPORT}: secret article text"},
            {"no_message": True},
            event("pilot", {"report_id": REPORT, "status": "shadow", "note": "``` breakout"}),
        ],
    )
    assert result.returncode == 0
    output = result.stdout + summary
    assert "secret article text" not in output and "not-json" not in output
    assert output.count("Article relevance ") == 2
    # Model-free fields are re-serialized; fences in values cannot close the block.
    assert summary.count("```") == 2


def test_total_output_is_bounded_in_lines_and_bytes(tmp_path):
    records = [{"index": i, "article_key": "a" * 64} for i in range(64)]
    events = [
        event("selection", {"report_id": REPORT, "records": records, "n": n}) for n in range(30)
    ]
    result, summary = run(tmp_path, events, "--max-bytes", "6000", "--max-lines", "5")
    assert result.returncode == 0
    block = summary.split("```")[1]
    assert len(block.encode()) <= 6000
    assert len(result.stdout.encode()) <= 6000 + 400
    assert "omitted" in result.stdout and "omitted" in summary
    lines = [line for line in block.splitlines() if line.startswith("Article relevance")]
    assert 1 <= len(lines) <= 5


def test_a_single_oversized_line_is_truncated_to_the_bound(tmp_path):
    records = [{"index": i, "article_key": "b" * 64} for i in range(500)]
    result, summary = run(tmp_path, [event("selection", {"report_id": REPORT, "records": records})])
    block = summary.split("```")[1]
    assert len(block.encode()) <= 8000
    assert "truncated" in summary


def test_no_matching_diagnostics_is_reported_explicitly(tmp_path):
    result, summary = run(tmp_path, [event("pilot", {"report_id": OTHER})])
    assert result.returncode == 0
    assert f"No article relevance diagnostics for {REPORT}" in result.stdout
    assert "relevance mode off" in result.stdout
    assert "```" not in summary


@pytest.mark.parametrize("contents", ["", "not json", '{"events": "nope"}'])
def test_missing_or_unreadable_query_results_do_not_fail(tmp_path, contents):
    path = tmp_path / "events.json"
    path.write_text(contents)
    result, _ = run(tmp_path, None, "--events", str(path))
    assert result.returncode == 0
    assert "unavailable" in result.stdout


def test_query_failure_reports_only_its_error_code(tmp_path):
    result, summary = run(tmp_path, None, "--unavailable", "AccessDeniedException")
    assert result.returncode == 0
    assert "unavailable (AccessDeniedException)" in result.stdout
    assert "AccessDeniedException" in summary
    unsafe, _ = run(tmp_path, None, "--unavailable", "arn:aws:iam::123456789012:user/x")
    assert "123456789012" not in unsafe.stdout
    assert "unavailable (query_failed)" in unsafe.stdout


def test_an_unexpected_report_handle_is_refused_before_any_output(tmp_path):
    summary = tmp_path / "summary.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--report-id", "report_x' OR 1", "--summary", str(summary)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "unexpected report handle" in result.stdout
    assert not summary.exists()


def test_filter_pattern_matches_only_this_report():
    pattern = runpy.run_path(str(SCRIPT))["filter_pattern"](REPORT)
    assert pattern == f'"Article relevance" "{REPORT}"'
