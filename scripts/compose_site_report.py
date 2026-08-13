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
EVIDENCE_MANIFEST = REPO_ROOT / "site" / "evidence-manifest.json"
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
    return (
        single_line(value, field)
        .replace("\\", "\\\\")
        .replace("[", "(")
        .replace("]", ")")
    )


def http_url(value: object, field: str) -> str:
    url = single_line(value, field)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        fail(f"{field} must be an http(s) URL")
    if re.search(r"[\s<>\"]", url):
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


def markdown_links(markdown: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    cursor = 0
    while cursor < len(markdown):
        label_start = markdown.find("[", cursor)
        if label_start < 0:
            break
        label_depth = 1
        escaped = False
        label_end = -1
        for index in range(label_start + 1, len(markdown)):
            character = markdown[index]
            if escaped:
                escaped = False
                continue
            if character == "\\":
                escaped = True
                continue
            if character == "[":
                label_depth += 1
            elif character == "]":
                label_depth -= 1
                if label_depth == 0:
                    label_end = index
                    break
        if (
            label_end < 0
            or label_end + 1 >= len(markdown)
            or markdown[label_end + 1] != "("
        ):
            cursor = label_start + 1
            continue
        depth = 1
        escaped = False
        destination_end = -1
        for index in range(label_end + 2, len(markdown)):
            character = markdown[index]
            if escaped:
                escaped = False
                continue
            if character == "\\":
                escaped = True
                continue
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    destination_end = index
                    break
        if destination_end < 0:
            cursor = label_end + 2
            continue
        links.append(
            (
                markdown[label_start + 1 : label_end],
                markdown[label_end + 2 : destination_end],
            )
        )
        cursor = destination_end + 1
    return links


def markdown_inline_text(value: str) -> str:
    """Decode the escapes used to serialize a Markdown link label."""
    return re.sub(r"\\([\\[\]()])", r"\1", value)


def source_articles(metadata: dict) -> list[dict[str, object]]:
    raw_sources = metadata.get("source_articles")
    if not isinstance(raw_sources, list) or not raw_sources:
        fail("metadata.source_articles must contain the analyzed source evidence")
    sources: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for index, raw_source in enumerate(raw_sources):
        if not isinstance(raw_source, dict):
            fail(f"metadata.source_articles[{index}] must be an object")
        if not str(raw_source.get("title") or "").strip() or not str(
            raw_source.get("url") or ""
        ).strip():
            continue
        title = single_line(
            raw_source.get("title"), f"metadata.source_articles[{index}].title"
        )
        url = http_url(raw_source.get("url"), f"metadata.source_articles[{index}].url")
        raw_cves = raw_source.get("cves", [])
        if not isinstance(raw_cves, list):
            fail(f"metadata.source_articles[{index}].cves must be a list")
        cves: list[str] = []
        for cve_index, raw_cve in enumerate(raw_cves):
            cve = single_line(
                raw_cve, f"metadata.source_articles[{index}].cves[{cve_index}]"
            ).upper()
            if not re.fullmatch(r"CVE-\d{4}-\d{4,}", cve):
                fail(f"metadata.source_articles[{index}] contains an invalid CVE")
            if cve not in cves:
                cves.append(cve)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        sources.append({"title": title, "url": url, "cves": cves})
    if not sources:
        fail("metadata.source_articles contains no usable linked evidence")
    return sources


def validate_evidence_links(body: str, sources: list[dict[str, object]]) -> None:
    allowed_pairs = {
        (str(source["title"]), str(source["url"])) for source in sources
    }
    evidence_links = [
        (
            markdown_inline_text(label),
            http_url(markdown_inline_text(url), "report evidence URL"),
        )
        for label, url in markdown_links(body)
        if url.startswith(("http://", "https://"))
    ]
    if not evidence_links:
        fail("report body contains no linked source evidence")
    unknown_pairs = sorted(set(evidence_links) - allowed_pairs)
    if unknown_pairs:
        label, url = unknown_pairs[0]
        fail(
            "report contains evidence title/URL pair absent from source articles: "
            f"{label} ({url})"
        )

    cves_by_url = {
        str(source["url"]): set(source["cves"])
        for source in sources
    }
    for line in body.splitlines():
        normalized_line = line.replace("‑", "-").replace("–", "-").replace("—", "-")
        cited_cves = {
            match.group(0).upper()
            for match in re.finditer(
                r"\bCVE-\d{4}-\d{4,}\b", normalized_line, re.IGNORECASE
            )
        }
        if not cited_cves:
            continue
        linked_urls = {
            http_url(markdown_inline_text(url), "report evidence URL")
            for _label, url in markdown_links(line)
            if url.startswith(("http://", "https://"))
        }
        supported_cves = set().union(
            *(cves_by_url.get(url, set()) for url in linked_urls)
        )
        unsupported = sorted(cited_cves - supported_cves)
        if unsupported:
            fail(
                f"report cites {unsupported[0]} without a linked source containing it"
            )


def evidence_manifest(data: dict, sources: list[dict[str, object]]) -> dict:
    metadata = data.get("metadata") or {}
    return {
        "generated_at": single_line(data.get("generated_at"), "generated_at"),
        "feed_url": http_url(metadata.get("source_url"), "metadata.source_url"),
        "sources": sources,
    }


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
    sources = source_articles(metadata)
    validate_evidence_links(body, sources)
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

    report = compose_report(data, args.feed_url, args.model)
    sources = source_articles(data.get("metadata") or {})
    INDEX_MD.write_text(report, encoding="utf-8")
    EVIDENCE_MANIFEST.write_text(
        json.dumps(evidence_manifest(data, sources), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    print("site report composition completed")


if __name__ == "__main__":
    main()
