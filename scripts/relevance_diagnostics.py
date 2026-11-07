#!/usr/bin/env python3
"""Surface one report's article relevance diagnostics in its report run.

The Python Lambda logs bounded relevance diagnostics (counts, labels,
probabilities and URL hashes, never article text) and names the report each
line belongs to. Given CloudWatch Logs query results, this keeps only valid
diagnostics for the requested report, re-serializes them, and bounds the total
output in lines and bytes. It never fails the run: missing or unreadable
results are reported as unavailable.
"""

import argparse
import json
from pathlib import Path
import re

REPORT_ID = re.compile(r"report_[0-9]{8}_[0-9]{6}_[0-9]{3}")
MARKER = re.compile(r"Article relevance (pilot|selection) ")
ERROR_CODE = re.compile(r"[A-Za-z]{1,64}")
TRUNCATED = " [truncated]"


def filter_pattern(report_id: str) -> str:
    """CloudWatch Logs filter pattern for this report's diagnostics lines."""
    return f'"Article relevance" "{report_id}"'


def report_lines(events: list, report_id: str) -> list[str]:
    lines = []
    for event in events:
        message = event.get("message") if isinstance(event, dict) else None
        if not isinstance(message, str):
            continue
        match = MARKER.search(message)
        if match is None:
            continue
        try:
            payload, _ = json.JSONDecoder().raw_decode(message, match.end())
        except ValueError:
            continue
        if not isinstance(payload, dict) or payload.get("report_id") != report_id:
            continue
        # ASCII-only, compact and fence-safe: a value cannot close the code block.
        text = json.dumps(payload, sort_keys=True, separators=(",", ":")).replace(
            "`", "'"
        )
        lines.append(f"Article relevance {match.group(1)} {text}")
    return lines


def bounded(lines: list[str], max_lines: int, max_bytes: int) -> tuple[list[str], int]:
    """Keep whole lines within both bounds; truncate only a lone oversized first line."""
    kept: list[str] = []
    used = 1  # The code block opens with a newline; each kept line ends with one.
    for line in lines[:max_lines]:
        size = len(line.encode()) + 1
        if used + size > max_bytes:
            if not kept:
                room = max(0, max_bytes - len(TRUNCATED) - 2)
                kept.append(line.encode()[:room].decode(errors="ignore") + TRUNCATED)
            break
        kept.append(line)
        used += size
    return kept, len(lines) - len(kept)


def append_summary(path: Path | None, text: str) -> None:
    if path is not None:
        with path.open("a", encoding="utf-8") as summary:
            summary.write(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--unavailable")
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--print-filter-pattern", action="store_true")
    parser.add_argument("--max-lines", type=int, default=20)
    parser.add_argument("--max-bytes", type=int, default=8000)
    args = parser.parse_args()

    report_id = args.report_id
    if not REPORT_ID.fullmatch(report_id):
        print("Skipping article relevance diagnostics: unexpected report handle.")
        return 0
    if args.print_filter_pattern:
        print(filter_pattern(report_id))
        return 0

    events = None
    reason = None
    if args.unavailable is not None:
        reason = (
            args.unavailable
            if ERROR_CODE.fullmatch(args.unavailable)
            else "query_failed"
        )
    else:
        try:
            data = (
                json.loads(args.events.read_text(encoding="utf-8"))
                if args.events
                else None
            )
            events = data.get("events") if isinstance(data, dict) else None
        except (OSError, ValueError):
            events = None
        if not isinstance(events, list):
            reason = "unreadable_query_result"
    if reason is not None or events is None:
        message = f"Relevance diagnostics unavailable ({reason}) for {report_id}."
        print(message)
        append_summary(args.summary, f"## Relevance diagnostics\n\n{message}\n\n")
        return 0

    lines = report_lines(events, report_id)
    if not lines:
        message = (
            f"No article relevance diagnostics for {report_id} "
            "(relevance mode off, not reached, or not yet logged)."
        )
        print(message)
        append_summary(args.summary, f"## Relevance diagnostics\n\n{message}\n\n")
        return 0

    kept, omitted = bounded(lines, args.max_lines, args.max_bytes)
    note = (
        f"{omitted} more line(s) omitted (bound: {args.max_lines} lines, {args.max_bytes} bytes)."
        if omitted
        else ""
    )
    print(f"Relevance diagnostics for {report_id}:")
    print("\n".join(kept))
    if note:
        print(note)
    append_summary(
        args.summary,
        "## Relevance diagnostics\n\n"
        f"Report `{report_id}`:\n\n```\n"
        + "\n".join(kept)
        + "\n```\n\n"
        + (f"{note}\n\n" if note else ""),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
