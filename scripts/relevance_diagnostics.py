#!/usr/bin/env python3
"""Surface one report's article relevance diagnostics in its report run.

In shadow or enabled mode the Python Lambda stores a bounded relevance summary
(counts, route, labels and cost, never article text) in the report's own
metadata. Given the stored report response the run retrieved, this checks that
it belongs to the run's report handle, re-serializes the summary, and bounds the
output in bytes. It never fails the run: a missing or unreadable response is
reported as unavailable.
"""

import argparse
import json
from pathlib import Path
import re

REPORT_ID = re.compile(r"report_[0-9]{8}_[0-9]{6}_[0-9]{3}")
TRUNCATED = " [truncated]"


def summary_line(report: object, report_id: str) -> tuple[str | None, str | None]:
    """Return (line, None) for this report's summary, or (None, reason)."""
    if not isinstance(report, dict) or report.get("id") != report_id:
        return None, "response_for_another_report"
    metadata = report.get("metadata")
    diagnostics = (
        metadata.get("relevance_diagnostics") if isinstance(metadata, dict) else None
    )
    if diagnostics is None:
        return None, None
    if not isinstance(diagnostics, dict):
        return None, "malformed_summary"
    # ASCII-only, compact and fence-safe: a value cannot close the code block.
    text = json.dumps(diagnostics, sort_keys=True, separators=(",", ":")).replace(
        "`", "'"
    )
    return f"Article relevance report {text}", None


def bounded(line: str, max_bytes: int) -> str:
    """Fit the line, plus the code block's two newlines, within max_bytes."""
    if len(line.encode()) + 2 <= max_bytes:
        return line
    room = max(0, max_bytes - len(TRUNCATED) - 2)
    return line.encode()[:room].decode(errors="ignore") + TRUNCATED


def append_summary(path: Path | None, text: str) -> None:
    if path is not None:
        with path.open("a", encoding="utf-8") as summary:
            summary.write(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--report-data", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--max-bytes", type=int, default=8000)
    args = parser.parse_args()

    report_id = args.report_id
    if not REPORT_ID.fullmatch(report_id):
        print("Skipping article relevance diagnostics: unexpected report handle.")
        return 0

    try:
        report = json.loads(args.report_data.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        line, reason = None, "no_report_data"
    else:
        line, reason = summary_line(report, report_id)

    if reason is not None:
        message = f"Relevance diagnostics unavailable ({reason}) for {report_id}."
    elif line is None:
        message = (
            f"No article relevance diagnostics for {report_id} (relevance mode off)."
        )
    else:
        message = None
    if message is not None:
        print(message)
        append_summary(args.summary, f"## Relevance diagnostics\n\n{message}\n\n")
        return 0

    assert line is not None
    line = bounded(line, args.max_bytes)
    print(f"Relevance diagnostics for {report_id}:")
    print(line)
    append_summary(
        args.summary,
        f"## Relevance diagnostics\n\nReport `{report_id}`:\n\n```\n{line}\n```\n\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
