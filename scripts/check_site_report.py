#!/usr/bin/env python3
"""Validate the committed GitHub Pages report artifact."""

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
INDEX_HTML = SITE_DIR / "index.html"
INDEX_MD = SITE_DIR / "index.md"
EVIDENCE_MANIFEST = SITE_DIR / "evidence-manifest.json"
SITEMAP_XML = SITE_DIR / "sitemap.xml"
APP_JS = SITE_DIR / "static" / "app.js"
RENDERER_JS = SITE_DIR / "static" / "renderer.js"
TAGS_JS = SITE_DIR / "static" / "tags.js"
STYLE_CSS = SITE_DIR / "static" / "style.css"
ARCHIVE_DIR = SITE_DIR / "archive"
ARCHIVE_INDEX = ARCHIVE_DIR / "index.html"
PUBLIC_SITE_URL = "https://ricomanifesto.github.io/GRCInsight/"
PUBLIC_DESCRIPTION = (
    "GRCInsight turns regulatory and security feeds into audit-ready GRC "
    "intelligence, with framework mapping, agency signals, industry relevance, "
    "and concise action-oriented reports."
)
REPORT_SECTION_LABELS = {
    "Executive Summary",
    "Key Regulatory Developments",
    "Industry Impact Analysis",
    "Risk Assessment",
    "Recommendations for Action",
    "Source Highlights",
}
FORBIDDEN_REPORT_SECTION_LABELS = {
    "cve and vulnerability highlights",
    "threat actor activities",
}
NUMBERED_SECTION_PATTERN = re.compile(r"^\d+[\).]\s+(.+)$")
FORBIDDEN_METADATA_FIELDS = {"distribution approval", "prepared by"}
PRIVATE_VALUE_FIELDS = {"audience", "classification", "confidentiality", "distribution"}
REPORT_METADATA_TABLE_FIELDS = {
    "analysis period",
    "date",
    "date of issue",
    "detail",
    "field",
    "grc relevant articles",
    "grc-relevant articles",
    "report date",
    "source",
    "total articles analyzed",
}
PRIVATE_VALUE_TERMS = {
    "confidential",
    "internal",
    "non-public",
    "nonpublic",
    "private",
    "proprietary",
    "restricted",
}
AFFIRMATIVE_LABEL_VALUES = {"true", "yes"}
MARKDOWN_LABEL_PREFIX = re.compile(r"^\s*(?:>\s*|(?:\d+[\).]|[-*])\s*|#{1,6}\s*)")
SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
# Generated identifier leaks have long lowercase prefixes joined to a title-case
# noun (for example, customerCredential or criticalCommerce). Requiring five
# lowercase characters avoids flagging established mixed-case brands such as
# ownCloud, openSUSE, and macOS. Exact evidence titles are excluded below.
SUSPICIOUS_CAMEL_CASE = re.compile(r"\b[a-z]{5,}[A-Z][a-z]{2,}\b")
DANGLING_SOURCE_REFERENCE_PATTERN = re.compile(
    r"\bSources?\s+\d+(?:\s*(?:,|and|-)\s*\d+)*\b", re.IGNORECASE
)
LEAKED_DELIBERATION_PATTERN = re.compile(
    r"^(?:let me\b|actually\b|hmm\b|i need\b|i should\b|now i need\b|wait\b)",
    re.IGNORECASE,
)
UNRESOLVED_REPORT_PLACEHOLDER_PATTERN = re.compile(
    r"^\[(?:table|analysis(?:\s+with.*)?|actionable items)\]$", re.IGNORECASE
)
MAX_REPORT_PREAMBLE_LINES = 30
REQUIRED_PUBLIC_METADATA = {
    "analysis mode",
    "analysis period",
    "articles analyzed",
    "date of issue",
    "generated",
    "model",
    "source",
}


def normalize_label_text(text: str) -> str:
    normalized = text.replace("–", "-").replace("—", "-")
    while True:
        stripped = MARKDOWN_LABEL_PREFIX.sub("", normalized)
        if stripped == normalized:
            break
        normalized = stripped
    normalized = normalized.strip().strip("|").strip()
    normalized = re.sub(r"[*_`]+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip(" .;:").lower()


def table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if "|" not in stripped:
        return []

    return [normalize_label_text(cell) for cell in stripped.strip("|").split("|")]


def table_row_is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(
        cell == "" or re.fullmatch(r":?-{3,}:?", cell) for cell in cells
    )


def field_matches_any(
    field: str, candidates: set[str], *, allow_prefixed_field: bool = False
) -> bool:
    field = field.replace("-", " ")
    return any(
        field == candidate
        or field.startswith(f"{candidate} ")
        or (allow_prefixed_field and field.endswith(f" {candidate}"))
        for candidate in candidates
    )


def table_row_has_metadata_header(cells: list[str]) -> bool:
    return any(
        field_matches_any(cell, PRIVATE_VALUE_FIELDS, allow_prefixed_field=True)
        or field_matches_any(cell, FORBIDDEN_METADATA_FIELDS, allow_prefixed_field=True)
        for cell in cells
    )


def table_row_has_report_metadata_context(cells: list[str]) -> bool:
    normalized = {cell.replace("-", " ") for cell in cells}
    if "field" in normalized and "detail" in normalized:
        return True

    if normalized & REPORT_METADATA_TABLE_FIELDS:
        return True

    return {"date", "classification"} <= normalized or {
        "classification",
        "distribution",
    } <= normalized


def table_field_and_value(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if "|" not in stripped:
        return None

    cells = [
        normalize_label_text(cell) for cell in stripped.strip("|").split("|") if cell
    ]
    if len(cells) < 2:
        return None

    return cells[0], cells[1]


def line_field_and_value(line: str) -> tuple[str, str] | None:
    normalized = normalize_label_text(line)
    match = re.match(r"^([a-z][a-z -]{1,40}?):\s*(.+)$", normalized)
    if not match:
        match = re.match(r"^([a-z][a-z -]{1,40}?)\s+-\s+(.+)$", normalized)
    if not match:
        return None

    return match.group(1).strip(), match.group(2).strip()


def is_private_footer_label(line: str) -> bool:
    normalized = normalize_label_text(line)
    exact_labels = {
        "internal use only",
        "internal-only",
        "for internal use only",
        "for internal-only use",
        "for internal distribution only",
        "internal distribution only",
        "this report is intended for internal use only",
        "this report is intended for internal distribution only",
    }
    footer_prefixes = (
        "internal use only",
        "internal-only",
        "for internal use only",
        "for internal-only use",
        "for internal distribution only",
        "internal distribution only",
        "this report is intended for internal use only",
        "this report is intended for internal distribution only",
    )
    return normalized in exact_labels or any(
        re.match(rf"^{re.escape(prefix)}(?:[.;:-]|\s)", normalized)
        for prefix in footer_prefixes
    )


def is_private_standalone_banner(line: str) -> bool:
    normalized = normalize_label_text(line)
    return (
        normalized == "confidential"
        or normalized
        in {"non-public", "nonpublic", "private", "proprietary", "restricted"}
        or normalized.startswith("confidential:")
        or normalized.startswith("confidential - ")
        or re.match(
            r"^(company|highly|internal|private|proprietary|sensitive|strictly)(?:\s*&\s*|\s+and\s+|\s+)confidential$",
            normalized,
        )
        is not None
        or re.match(
            r"^confidential(?:\s*&\s*|\s+and\s+)proprietary$",
            normalized,
        )
        is not None
        or re.match(
            r"^internal(?:\s*-\s*|\s+)(?:executive\s+)?distribution$", normalized
        )
        is not None
    )


def is_private_prose_footer(line: str) -> bool:
    normalized = normalize_label_text(line)
    return bool(
        re.match(r"^this report contains\b.*\b(confidential|proprietary)\b", normalized)
        or re.match(
            r"^unauthorized distribution\b.*\b(prohibited|forbidden)\b", normalized
        )
    )


def field_value_is_forbidden(field: str, value: str) -> bool:
    field = field.replace("-", " ")
    if field_matches_any(field, FORBIDDEN_METADATA_FIELDS, allow_prefixed_field=True):
        return True

    if not field_matches_any(field, PRIVATE_VALUE_FIELDS, allow_prefixed_field=True):
        return False

    value_text = value.replace("-", " ")
    value_words = set(re.findall(r"[a-z]+", value_text))
    if (
        field_matches_any(field, {"confidentiality"}, allow_prefixed_field=True)
        and value_words & AFFIRMATIVE_LABEL_VALUES
    ):
        return True

    if "non public" in value_text:
        return True

    if value_words & (PRIVATE_VALUE_TERMS - {"internal", "non-public"}):
        return True

    return "internal" in value_words and "internal control" not in value_text


def is_distribution_approval_label(line: str) -> bool:
    normalized = normalize_label_text(line)
    if not (
        normalized.startswith("distribution outside")
        or normalized.startswith("for distribution outside")
        or normalized.startswith("external distribution")
        or normalized.startswith("for external distribution")
    ):
        return False

    return bool(re.search(r"\b(requires?|required|approval|approved)\b", normalized))


def horizontal_table_forbidden_label(lines: list[str], index: int) -> str | None:
    headers = table_cells(lines[index])
    if (
        not table_row_has_metadata_header(headers)
        or not table_row_has_report_metadata_context(headers)
        or table_row_is_separator(headers)
    ):
        return None

    value_index = index + 1
    while value_index < len(lines):
        values = table_cells(lines[value_index])
        if not values:
            return None
        if table_row_is_separator(values):
            value_index += 1
            continue
        for field, value in zip(headers, values):
            if field_value_is_forbidden(field, value):
                return f"{field} metadata label"
        value_index += 1

    return None


def find_public_report_forbidden_label(markdown: str) -> str | None:
    lowered = markdown.lower()
    if "intended for internal executive use" in lowered:
        return "internal executive use note"

    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        if label := horizontal_table_forbidden_label(lines, index):
            return label
        if is_private_footer_label(line):
            return "internal footer label"
        if is_private_standalone_banner(line):
            return "confidential banner"
        if is_private_prose_footer(line):
            return "confidential footer"
        if is_distribution_approval_label(line):
            return "distribution approval note"

        for parsed in (table_field_and_value(line), line_field_and_value(line)):
            if parsed is None:
                continue
            field, value = parsed
            if field_value_is_forbidden(field, value):
                return f"{field} metadata label"

    return None


def report_metadata(markdown: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in markdown.splitlines():
        if line.startswith("## "):
            break
        match = re.match(r"^\*\*([^*]+?):\*\*\s*(.+?)\s*$", line)
        if match is None:
            match = re.match(r"^\*\*([^*]+?):\s*(.+?)\*\*\s*$", line)
        if match:
            metadata[match.group(1).strip().lower()] = match.group(2).strip()
    if "total articles analyzed" in metadata and "articles analyzed" not in metadata:
        metadata["articles analyzed"] = metadata["total articles analyzed"]
    return metadata


def markdown_links(markdown: str) -> list[tuple[int, int, str, str]]:
    links: list[tuple[int, int, str, str]] = []
    cursor = 0
    while cursor < len(markdown):
        label_start = markdown.find("[", cursor)
        if label_start < 0:
            break
        label_depth = 1
        label_escaped = False
        label_end = -1
        for index in range(label_start + 1, len(markdown)):
            character = markdown[index]
            if label_escaped:
                label_escaped = False
                continue
            if character == "\\":
                label_escaped = True
                continue
            if character == "[":
                label_depth += 1
            elif character == "]":
                label_depth -= 1
                if label_depth == 0:
                    label_end = index
                    break
        if label_end < 0:
            break
        if label_end + 1 >= len(markdown) or markdown[label_end + 1] != "(":
            cursor = label_start + 1
            continue
        destination_marker = label_end
        depth = 1
        escaped = False
        destination_end = -1
        for index in range(destination_marker + 2, len(markdown)):
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
            cursor = destination_marker + 2
            continue
        links.append(
            (
                label_start,
                destination_end + 1,
                markdown[label_start + 1 : destination_marker],
                markdown[destination_marker + 2 : destination_end],
            )
        )
        cursor = destination_end + 1
    return links


def prose_without_destinations(markdown: str) -> str:
    prose = re.sub(r"^```[\s\S]*?^```", "", markdown, flags=re.MULTILINE)
    prose = re.sub(r"`[^`]*`", "", prose)
    links = markdown_links(prose)
    for start, end, _label, _destination in reversed(links):
        prose = prose[:start] + " " + prose[end:]
    prose = re.sub(r"https?://\S+", "", prose)
    return prose


def find_reader_surface_defect(markdown: str) -> str | None:
    prose = prose_without_destinations(markdown)
    if re.search(rf"[{SUPERSCRIPT_DIGITS}]", prose):
        return "unresolved superscript citation marker"

    bare_reference = re.search(r"(?<!!)\[([^\]]+)\](?!\()", prose)
    if bare_reference:
        return f"unresolved bracketed reference [{bare_reference.group(1)}]"

    camel_case = SUSPICIOUS_CAMEL_CASE.search(prose)
    if camel_case:
        return f"suspicious camelCase token {camel_case.group(0)}"

    dangling_source = DANGLING_SOURCE_REFERENCE_PATTERN.search(prose)
    if dangling_source:
        return f"unresolved source reference {dangling_source.group(0)}"

    if re.search(r"(?m)^\s*(?:-{3,}|_{3,}|\*{3,})\s*$", markdown):
        return "standalone section separator"

    for line in markdown.splitlines():
        normalized = line.replace("‑", "-").replace("–", "-").replace("—", "-")
        if re.search(r"\bCVE-\d{4}-\d{4,}\b", normalized, re.IGNORECASE):
            if not any(
                destination.startswith(("http://", "https://"))
                for _, _, _, destination in markdown_links(normalized)
            ):
                return "CVE claim without an inline source link"

    source_section = re.search(
        r"(?ms)^##\s+Source Highlights\s*$([\s\S]*?)(?=^##\s+|\Z)", markdown
    )
    if source_section is None:
        return "missing Source Highlights section"
    if not any(
        destination.startswith(("http://", "https://"))
        for _, _, _, destination in markdown_links(source_section.group(1))
    ):
        return "Source Highlights section has no linked evidence"
    return None


def find_public_report_integrity_failure(markdown: str) -> str | None:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    for line in lines:
        if LEAKED_DELIBERATION_PATTERN.match(line):
            return f"leaked model deliberation: {line[:80]}"
        if UNRESOLVED_REPORT_PLACEHOLDER_PATTERN.match(line):
            return f"unresolved report placeholder: {line}"

    first_section_index = next(
        (index for index, line in enumerate(lines) if is_report_section(line)), None
    )
    if (
        first_section_index is not None
        and first_section_index > MAX_REPORT_PREAMBLE_LINES
    ):
        return "first report section appears after an excessive preamble"
    return None


def fail(message: str) -> None:
    raise SystemExit(f"site report check failed: {message}")


def read_text(path: Path) -> str:
    if not path.exists():
        fail(f"missing {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def canonical_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        fail(f"invalid evidence URL: {url}")
    return quote(url, safe=":/?#[]@!$&*+,;=%")


def markdown_inline_text(value: str) -> str:
    """Decode the escapes used to serialize a Markdown link label."""
    return re.sub(r"\\([\\[\]()])", r"\1", value)


def report_section_label(line: str) -> str | None:
    if line.startswith("## "):
        label = line[3:].strip()
        return label if label in REPORT_SECTION_LABELS else None

    match = NUMBERED_SECTION_PATTERN.match(line)
    if not match:
        return None

    label = match.group(1).strip()
    return label if label in REPORT_SECTION_LABELS else None


def is_report_section(line: str) -> bool:
    return report_section_label(line) is not None


def validate_site_identity(html: str, sitemap_xml: str) -> None:
    expected_html = (
        f'<meta name="description" content="{PUBLIC_DESCRIPTION}">',
        f'<link rel="canonical" href="{PUBLIC_SITE_URL}">',
        f'<meta property="og:url" content="{PUBLIC_SITE_URL}">',
        '<meta name="twitter:card" content="summary_large_image">',
        'href="https://ricomanifesto.com/">Michael Rico</a>',
        "<noscript>",
    )
    for expected in expected_html:
        if expected not in html:
            fail(f"index.html missing public identity contract: {expected}")

    match = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    if match is None:
        fail("index.html missing JSON-LD project identity")
    try:
        identity = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        fail(f"index.html JSON-LD is invalid: {error}")

    expected_author = {
        "@type": "Person",
        "name": "Michael Rico",
        "url": "https://ricomanifesto.com/",
    }
    if (
        identity.get("@context") != "https://schema.org"
        or identity.get("@type") != "WebSite"
        or identity.get("name") != "GRCInsight"
        or identity.get("url") != PUBLIC_SITE_URL
        or identity.get("description") != PUBLIC_DESCRIPTION
        or identity.get("author") != expected_author
        or identity.get("sameAs") != "https://github.com/ricomanifesto/GRCInsight"
    ):
        fail(
            "index.html JSON-LD does not match the public GRCInsight identity contract"
        )

    try:
        sitemap = ET.fromstring(sitemap_xml)
    except ET.ParseError as error:
        fail(f"sitemap.xml is invalid XML: {error}")
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [element.text for element in sitemap.findall("s:url/s:loc", namespace)]
    if locations != [PUBLIC_SITE_URL]:
        fail("sitemap.xml must contain only the canonical GRCInsight project URL")


def validate_evidence_manifest(
    markdown: str, metadata: dict[str, str], manifest_text: str
) -> dict:
    try:
        manifest = json.loads(manifest_text)
    except json.JSONDecodeError as error:
        fail(f"evidence-manifest.json is invalid JSON: {error}")
    if not isinstance(manifest, dict):
        fail("evidence-manifest.json must be an object")
    if manifest.get("generated_at") != metadata["generated"]:
        fail("evidence manifest timestamp does not match report provenance")

    source_links = markdown_links(metadata["source"])
    if len(source_links) != 1 or canonical_http_url(
        str(manifest.get("feed_url", ""))
    ) != canonical_http_url(markdown_inline_text(source_links[0][3])):
        fail("evidence manifest feed URL does not match report provenance")

    raw_sources = manifest.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        fail("evidence manifest must contain source articles")
    source_pairs: set[tuple[str, str]] = set()
    source_urls: set[str] = set()
    source_cves: dict[str, set[str]] = {}
    for index, source in enumerate(raw_sources):
        if not isinstance(source, dict):
            fail(f"evidence manifest source {index} must be an object")
        title = source.get("title")
        url = source.get("url")
        if not isinstance(title, str) or not title.strip():
            fail(f"evidence manifest source {index} has no title")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            fail(f"evidence manifest source {index} has no HTTP URL")
        url = canonical_http_url(url)
        raw_cves = source.get("cves", [])
        if not isinstance(raw_cves, list):
            fail(f"evidence manifest source {index} CVEs must be a list")
        cves: set[str] = set()
        for cve in raw_cves:
            if not isinstance(cve, str) or not re.fullmatch(
                r"CVE-\d{4}-\d{4,}", cve, re.IGNORECASE
            ):
                fail(f"evidence manifest source {index} has an invalid CVE")
            cves.add(cve.upper())
        if url in source_urls:
            fail(f"evidence manifest repeats source URL: {url}")
        source_urls.add(url)
        source_cves[url] = cves
        source_pairs.add((title, url))

    body_start = markdown.find("\n## ")
    body = markdown[body_start + 1 :] if body_start >= 0 else ""
    body_links = [
        (
            markdown_inline_text(label),
            canonical_http_url(markdown_inline_text(destination)),
        )
        for _, _, label, destination in markdown_links(body)
        if destination.startswith(("http://", "https://"))
    ]
    if not body_links:
        fail("report body has no evidence links")
    unknown_pairs = sorted(set(body_links) - source_pairs)
    if unknown_pairs:
        label, url = unknown_pairs[0]
        fail(
            "report links evidence absent from source manifest: "
            f"{label} ({url})"
        )

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
            canonical_http_url(markdown_inline_text(destination))
            for _, _, _, destination in markdown_links(line)
            if destination.startswith(("http://", "https://"))
        }
        supported_cves = set().union(
            *(source_cves.get(url, set()) for url in linked_urls)
        )
        unsupported = sorted(cited_cves - supported_cves)
        if unsupported:
            fail(
                f"report cites {unsupported[0]} without a linked source containing it"
            )

    source_section = re.search(
        r"(?ms)^##\s+Source Highlights\s*$([\s\S]*?)(?=^##\s+|\Z)", body
    )
    if source_section is None:
        fail("report has no Source Highlights section")
    highlighted_pairs = {
        (
            markdown_inline_text(label),
            canonical_http_url(markdown_inline_text(destination)),
        )
        for _, _, label, destination in markdown_links(source_section.group(1))
    }
    if not highlighted_pairs or not highlighted_pairs.issubset(source_pairs):
        fail("Source Highlights must use exact source title and URL pairs")
    return manifest


def main() -> None:
    html = read_text(INDEX_HTML)
    markdown = read_text(INDEX_MD)
    sitemap_xml = read_text(SITEMAP_XML)
    app_js = read_text(APP_JS)
    renderer_js = read_text(RENDERER_JS)
    tags_js = read_text(TAGS_JS)
    style_css = read_text(STYLE_CSS)
    archive_html = read_text(ARCHIVE_INDEX)
    evidence_manifest_text = read_text(EVIDENCE_MANIFEST)

    validate_site_identity(html, sitemap_xml)

    # The page loads exactly one script per concern: the tag catalog, the
    # canonical renderer, and the page controller.
    for asset in (
        "static/style.css",
        "static/tags.js",
        "static/renderer.js",
        "static/app.js",
    ):
        if asset not in html:
            fail(f"index.html does not reference {asset}")

    # The operator workspace modules were removed; keep them gone.
    for removed in ("static/metadata.js", "static/filters.js", "static/archive.js"):
        if removed in html:
            fail(f"index.html still references removed module {removed}")
    for removed_module in ("metadata.js", "filters.js", "archive.js"):
        if (SITE_DIR / "static" / removed_module).exists():
            fail(f"removed module still present: static/{removed_module}")

    # index.md must be a valid, public-safe report.
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    if not lines:
        fail("index.md is empty")
    if not lines[0].startswith("# "):
        fail("index.md must start with a top-level report title")
    generated_lines = [line for line in lines[:5] if line.startswith("**Generated:**")]
    if len(generated_lines) != 1:
        fail("index.md must include exactly one Generated line near the top")
    h1_count = sum(
        1 for line in lines if line.startswith("# ") and not line.startswith("## ")
    )
    if h1_count != 1:
        fail("index.md must contain exactly one top-level report title")
    section_counts = {
        label: sum(1 for line in lines if report_section_label(line) == label)
        for label in REPORT_SECTION_LABELS
    }
    missing_sections = [label for label, count in section_counts.items() if count == 0]
    repeated_sections = [label for label, count in section_counts.items() if count > 1]
    if missing_sections:
        fail("index.md missing required report section: " + sorted(missing_sections)[0])
    if repeated_sections:
        fail("index.md repeats report section: " + sorted(repeated_sections)[0])
    forbidden_sections = {
        normalize_label_text(line)
        for line in lines
        if normalize_label_text(line) in FORBIDDEN_REPORT_SECTION_LABELS
    }
    if forbidden_sections:
        fail(
            "index.md contains unsupported report section: "
            + ", ".join(sorted(forbidden_sections))
        )
    if "Temporary placeholder" in markdown or "Temporary Outline" in markdown:
        fail("index.md still contains temporary placeholder content")
    metadata = report_metadata(markdown)
    missing_metadata = REQUIRED_PUBLIC_METADATA - metadata.keys()
    if missing_metadata:
        fail(
            "index.md missing public provenance metadata: "
            + ", ".join(sorted(missing_metadata))
        )
    if metadata["analysis mode"].lower() != "model-backed":
        fail("index.md analysis mode must be Model-backed")
    if not re.fullmatch(r"\d+", metadata["articles analyzed"]):
        fail("index.md Articles Analyzed must be an integer")
    if not any(
        destination.startswith(("http://", "https://"))
        for _, _, _, destination in markdown_links(metadata["source"])
    ):
        fail("index.md Source metadata must be a linked feed")
    validate_evidence_manifest(markdown, metadata, evidence_manifest_text)
    forbidden_label = find_public_report_forbidden_label(markdown)
    if forbidden_label:
        fail(f"index.md contains public report forbidden label: {forbidden_label}")
    reader_defect = find_reader_surface_defect(markdown)
    if reader_defect:
        fail(f"index.md contains reader-surface defect: {reader_defect}")
    integrity_failure = find_public_report_integrity_failure(markdown)
    if integrity_failure:
        fail(f"index.md contains report-integrity failure: {integrity_failure}")

    generated_at = metadata["generated"]
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=timezone.utc)
        generated = generated.astimezone(timezone.utc)
    except ValueError:
        fail("index.md Generated metadata must be an ISO timestamp")
    archive_key = generated.strftime("%Y-%m-%dT%H-%M-%SZ")
    archived_markdown = read_text(ARCHIVE_DIR / archive_key / "report.md")
    archived_page = read_text(ARCHIVE_DIR / archive_key / "index.html")
    archived_manifest = read_text(ARCHIVE_DIR / archive_key / "evidence-manifest.json")
    if archived_markdown.rstrip() != markdown.rstrip():
        fail("current report does not match its timestamped archive snapshot")
    if archived_manifest != evidence_manifest_text:
        fail("current evidence manifest does not match its archived snapshot")
    if f'href="{archive_key}/"' not in archive_html:
        fail("archive index does not link the current timestamped report")
    if 'class="card report-provenance"' not in archived_page:
        fail("archived report page is not pre-rendered with provenance")
    if 'href="archive/"' not in html or 'href="index.md"' not in html:
        fail("index.html is missing report archive or Markdown navigation")
    if 'data-prerendered="true"' not in html:
        fail("index.html does not contain pre-rendered report content")
    if 'class="card report-provenance"' not in html:
        fail("index.html does not render the report provenance card")

    # The page controller routes rendering through the canonical renderer and
    # the shared tag catalog, and never emits an unsanitized Markdown link.
    if 'href="$2"' in app_js:
        fail("app.js renders Markdown links without URL sanitization")
    if "window.GRCInsightRenderer" not in app_js:
        fail("app.js does not use the canonical renderer")
    if "renderer.renderReportDocument" not in app_js:
        fail("app.js does not render through renderer.renderReportDocument")
    if "window.GRCInsightTags" not in app_js:
        fail("app.js does not use the shared compliance tag catalog")
    if "tokenizeComplianceTerms" not in app_js:
        fail("app.js does not use the tag catalog tokenizer")
    if "parent.closest('a, .pill, code, pre, button')" not in app_js:
        fail("app.js does not preserve existing links and code while adding pills")
    if "renderer.sanitizeMarkdownUrl(segment.url)" not in app_js:
        fail("app.js does not sanitize catalog links before rendering")
    if "pill.target = '_blank'" not in app_js or "pill.rel = 'noopener'" not in app_js:
        fail("app.js reference pills are missing safe external-link behavior")
    for inline_catalog in (
        "const frameworks =",
        "const regulations =",
        "const risks =",
    ):
        if inline_catalog in app_js:
            fail(f"app.js still defines an inline tag catalog: {inline_catalog}")
    for removed_global in (
        "GRCInsightMetadata",
        "GRCInsightFilters",
        "GRCInsightArchive",
    ):
        if removed_global in app_js:
            fail(f"app.js still references removed module global: {removed_global}")

    # The renderer owns Markdown rendering and URL sanitization.
    for export in (
        "window.GRCInsightRenderer",
        "function renderMarkdown",
        "function renderReportDocument",
        "function sanitizeMarkdownUrl",
        "function normalizeReportMarkdown",
    ):
        if export not in renderer_js:
            fail(f"renderer.js missing canonical export: {export}")
    if 'rel="noopener"' not in renderer_js:
        fail("renderer.js missing safe-link rel=noopener guard")

    if "window.GRCInsightTags" not in tags_js:
        fail("tags.js does not export the compliance tag catalog")
    if "function tokenizeComplianceTerms" not in tags_js:
        fail("tags.js does not own compliance-term tokenization")
    for inert_category in ("key: 'risks'", "key: 'controls'"):
        if inert_category in tags_js:
            fail(f"tags.js still presents inert pills: {inert_category}")

    if "ArrowDown" in app_js or "ArrowUp" in app_js:
        fail("app.js overrides native arrow-key scrolling")
    if 'aria-live="polite"' not in html or "copyStatus" not in app_js:
        fail("copy-link confirmation is missing an aria-live status")
    if "toLocaleDateString('en-US'" not in app_js or "timeZone: 'UTC'" not in app_js:
        fail("app.js does not format report dates in canonical English UTC")
    if (
        "const collapsibleCards" not in app_js
        or ".filter(card => !card.classList.contains('report-provenance'))"
        not in app_js
        or "collapsibleCards.forEach((card, idx)" not in app_js
    ):
        fail("app.js does not keep the first report section expanded on mobile")
    if "prefers-color-scheme: light" not in app_js:
        fail("app.js does not honor the reader's preferred theme")
    for token in (
        "--pill-framework-bg",
        "--pill-framework-text",
        "--pill-regulation-bg",
        "--pill-regulation-text",
        "--pill-agency-bg",
        "--pill-agency-text",
    ):
        if style_css.count(token) < 3:
            fail(f"style.css does not define and consume both-theme pill token {token}")
    heading_actions = re.search(r"(?m)^\.heading-actions\s*\{([^}]+)\}", style_css)
    if heading_actions is None or re.search(
        r"opacity:\s*0\s*;", heading_actions.group(1)
    ):
        fail("style.css hides heading actions until hover")

    print("site report check passed")


if __name__ == "__main__":
    main()
