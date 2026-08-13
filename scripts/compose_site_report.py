#!/usr/bin/env python3
"""Compose the public Markdown report from a completed stored report response."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from urllib.parse import quote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_MD = REPO_ROOT / "site" / "index.md"
SECTION_TITLES = (
    "Executive Summary",
    "Key Regulatory Developments",
    "Industry Impact Analysis",
    "Risk Assessment",
    "Recommendations for Action",
    "Source Highlights",
)


def fail(message: str) -> None:
    raise SystemExit(f"site report composition failed: {message}")


def single_line(value: object, field: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        fail(f"missing {field}")
    return text


def markdown_link_label(value: object, field: str) -> str:
    return single_line(value, field).replace("[", "(").replace("]", ")")


def http_url(value: object, field: str) -> str:
    url = single_line(value, field)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        fail(f"{field} must be an http(s) URL")
    if re.search(r"[\s<>'\"]", url):
        fail(f"{field} contains unsafe Markdown URL characters")
    # Parentheses are valid URL characters but delimit a Markdown destination.
    # Percent-encode them while preserving the remaining RFC 3986 delimiters.
    return quote(url, safe=":/?#[]@!$&*+,;=%")


def integer(value: object, field: str) -> int:
    if isinstance(value, bool):
        fail(f"{field} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError):
        fail(f"{field} must be an integer")
    if number < 0:
        fail(f"{field} must not be negative")
    return number


def canonical_section_title(line: str) -> str | None:
    candidate = line.strip()
    has_section_marker = False
    heading = re.match(r"^#{1,6}\s+(.+?)\s*$", candidate)
    if heading:
        candidate = heading.group(1).strip()
        has_section_marker = True
    # Models commonly nest bold and numeric section markers in either order:
    # `## 1. **Title**`, `## **1. Title**`, or `**1. Title**`.
    # Peel those wrappers iteratively before comparing the canonical title.
    for _ in range(4):
        previous = candidate
        for marker in ("**", "__"):
            if candidate.startswith(marker) and candidate.endswith(marker):
                candidate = candidate[len(marker) : -len(marker)].strip()
                break
        numbered = re.match(r"^\d{1,2}[\).]\s+(.+?)\s*$", candidate)
        if numbered:
            candidate = numbered.group(1).strip()
            has_section_marker = True
        if candidate == previous:
            break
    candidate = re.sub(r"[\s:;.!?–—-]+$", "", candidate).strip()
    canonical_titles = {title.casefold(): title for title in SECTION_TITLES}
    return canonical_titles.get(candidate.casefold()) if has_section_marker else None


def canonical_body(content: object) -> str:
    text = str(content or "").replace("\r\n", "\n").strip()
    if not text:
        fail("report content is empty")

    known = set(SECTION_TITLES)
    lines = text.splitlines()
    body_start = None
    for index, line in enumerate(lines):
        if canonical_section_title(line) in known:
            body_start = index
            break
    if body_start is None:
        fail("report content has no recognized top-level section")

    body_lines = []
    for line in lines[body_start:]:
        section_title = canonical_section_title(line)
        if section_title in known:
            line = f"## {section_title}"
        if line.strip() in {"---", "___", "***"}:
            continue
        body_lines.append(line.rstrip())
    return "\n".join(body_lines).strip()


def compose_report(data: dict, expected_feed_url: str, expected_model: str) -> str:
    if data.get("status") != "completed":
        fail("stored report status is not completed")

    metadata = data.get("metadata") or {}
    if metadata.get("analysis_mode") != "model":
        fail("stored report is not model-backed")

    generated_at = single_line(data.get("generated_at"), "generated_at")
    title = single_line(data.get("title"), "title").lstrip("# ")
    source_name = markdown_link_label(
        metadata.get("source_name"), "metadata.source_name"
    )
    source_url = http_url(metadata.get("source_url"), "metadata.source_url")
    analysis_period = single_line(
        metadata.get("analysis_period"), "metadata.analysis_period"
    )
    article_count = integer(metadata.get("article_count"), "metadata.article_count")
    grc_article_count = integer(
        metadata.get("grc_article_count"), "metadata.grc_article_count"
    )
    model = single_line(metadata.get("model"), "metadata.model")

    if source_url != http_url(expected_feed_url, "expected feed URL"):
        fail("stored source URL does not match the requested feed URL")
    if model != single_line(expected_model, "expected model"):
        fail("stored model does not match the requested model")

    date_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", generated_at)
    if date_match is None:
        fail("generated_at must begin with an ISO date")
    year, month, _ = (int(part) for part in date_match.groups())
    if not 1 <= month <= 12:
        fail("generated_at contains an invalid month")
    month_name = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )[month - 1]

    body = canonical_body(data.get("content"))
    return "\n".join(
        (
            f"# {title}",
            f"**Generated:** {generated_at}",
            f"**Date of Issue:** {month_name} {year}",
            f"**Analysis Period:** {analysis_period}",
            f"**Source:** [{source_name}]({source_url})",
            f"**Articles Analyzed:** {article_count}",
            f"**GRC-Relevant Articles:** {grc_article_count}",
            f"**Model:** {model}",
            "**Analysis Mode:** Model-backed",
            "",
            body,
            "",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--feed-url", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"unable to read stored report response: {error}")
    if not isinstance(data, dict):
        fail("stored report response must be an object")

    INDEX_MD.write_text(
        compose_report(data, args.feed_url, args.model), encoding="utf-8"
    )
    print("site report composition completed")


if __name__ == "__main__":
    main()
