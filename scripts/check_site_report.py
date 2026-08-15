#!/usr/bin/env python3
"""Validate the committed GitHub Pages report artifact."""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import sys
from urllib.parse import quote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "agent"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from core.reporting_identity import (  # noqa: E402
    ReportingIdentityError,
    legacy_sentrydigest_item_url as build_legacy_sentrydigest_item_url,
    normalize_reporting_url,
    reporting_fragment as build_reporting_fragment,
    sentrydigest_issue_url as build_sentrydigest_issue_url,
    sentrydigest_item_url as build_sentrydigest_item_url,
)
from build_site import (  # noqa: E402
    ARCHIVE_CONTEXT_END,
    ARCHIVE_CONTEXT_START,
    DATED_DIGEST_HANDOFF_BOUNDARY,
)
from publication_state import (  # noqa: E402
    PublicationStateError,
    category_label,
    validate_publication_history,
    validate_publication_state,
)

SITE_DIR = REPO_ROOT / "site"
INDEX_HTML = SITE_DIR / "index.html"
INDEX_MD = SITE_DIR / "index.md"
EVIDENCE_MANIFEST = SITE_DIR / "evidence-manifest.json"
PUBLICATION_STATE = SITE_DIR / "publication-state.json"
PUBLICATION_HISTORY = SITE_DIR / "publication-history.json"
PUBLICATION_HISTORY_INDEX = SITE_DIR / "publication-history" / "index.html"
SITEMAP_XML = SITE_DIR / "sitemap.xml"
APP_JS = SITE_DIR / "static" / "app.js"
RENDERER_JS = SITE_DIR / "static" / "renderer.js"
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
    r"\bSources?\s+#?\s*\d+(?:\s*(?:,|and|-)\s*#?\s*\d+)*\b",
    re.IGNORECASE,
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
    "authoring model",
    "date of issue",
    "generated",
    "requested route",
    "source",
}
LEGACY_REQUIRED_PUBLIC_METADATA = (
    REQUIRED_PUBLIC_METADATA - {"authoring model", "requested route"}
) | {"model"}


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
                has_http_scheme(destination)
                for _, _, _, destination in markdown_links(normalized)
            ):
                return "CVE claim without an inline source link"

    source_section = re.search(
        r"(?ms)^##\s+Source Highlights\s*$([\s\S]*?)(?=^##\s+|\Z)", markdown
    )
    if source_section is None:
        return "missing Source Highlights section"
    if not any(
        has_http_scheme(destination)
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


def canonical_public_url(value: str, field: str) -> str:
    try:
        return normalize_reporting_url(value)
    except ReportingIdentityError as error:
        fail(f"{field}: {error}")


def sentrydigest_issue_url(feed_home_url: str, issue_date: str) -> str:
    try:
        return build_sentrydigest_issue_url(feed_home_url, issue_date)
    except ReportingIdentityError as error:
        fail(f"evidence manifest digest issue date: {error}")


def reporting_fragment(article_url: str) -> str:
    try:
        return build_reporting_fragment(article_url)
    except ReportingIdentityError as error:
        fail(f"evidence manifest source URL: {error}")


def sentrydigest_item_url(feed_home_url: str, issue_date: str, article_url: str) -> str:
    try:
        return build_sentrydigest_item_url(feed_home_url, issue_date, article_url)
    except ReportingIdentityError as error:
        fail(f"evidence manifest source URL: {error}")


def legacy_sentrydigest_item_url(feed_home_url: str, article_url: str) -> str:
    try:
        return build_legacy_sentrydigest_item_url(feed_home_url, article_url)
    except ReportingIdentityError as error:
        fail(f"evidence manifest source URL: {error}")


def usable_model_identity(value: object, field: str) -> str:
    identity = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{1,255}", identity):
        fail(f"{field} is not a usable provider model identity")
    return identity


def has_http_scheme(value: str) -> bool:
    return urlparse(value).scheme.lower() in {"http", "https"}


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
    if locations != [PUBLIC_SITE_URL, f"{PUBLIC_SITE_URL}publication-history/"]:
        fail("sitemap.xml does not match the canonical GRCInsight public routes")


def validate_evidence_manifest(
    markdown: str,
    metadata: dict[str, str],
    manifest_text: str,
    *,
    require_current_schema: bool = False,
) -> dict:
    try:
        manifest = json.loads(manifest_text)
    except json.JSONDecodeError as error:
        fail(f"evidence-manifest.json is invalid JSON: {error}")
    if not isinstance(manifest, dict):
        fail("evidence-manifest.json must be an object")
    schema_version = manifest.get("schema_version", 1)
    if schema_version not in {1, 2, 3}:
        fail("evidence-manifest.json has an unsupported schema version")
    if require_current_schema and schema_version != 3:
        fail("current evidence manifest must include dated digest issue provenance")
    if manifest.get("generated_at") != metadata["generated"]:
        fail("evidence manifest timestamp does not match report provenance")

    source_links = markdown_links(metadata["source"])
    if len(source_links) != 1 or canonical_http_url(
        str(manifest.get("feed_url", ""))
    ) != canonical_http_url(markdown_inline_text(source_links[0][3])):
        fail("evidence manifest feed URL does not match report provenance")

    feed_home_url = ""
    digest_issue_date = ""
    digest_issue_url = ""
    if schema_version >= 2:
        feed_home_url = canonical_public_url(
            str(manifest.get("feed_home_url", "")),
            "evidence manifest feed home URL",
        )
        requested_model = usable_model_identity(
            manifest.get("requested_model"), "evidence manifest requested model"
        )
        resolved_model = usable_model_identity(
            manifest.get("resolved_model"), "evidence manifest resolved model"
        )
        if requested_model != metadata.get("requested route"):
            fail("evidence manifest requested model does not match report provenance")
        if resolved_model != metadata.get("authoring model"):
            fail("evidence manifest resolved model does not match report provenance")
        if resolved_model in {"openrouter/free", "openrouter/auto"}:
            fail("evidence manifest resolved model is still a routing alias")
    if schema_version == 3:
        digest_issue_date = str(manifest.get("digest_issue_date") or "").strip()
        digest_issue_url = canonical_http_url(
            str(manifest.get("digest_issue_url") or "")
        )
        expected_issue_url = sentrydigest_issue_url(feed_home_url, digest_issue_date)
        if digest_issue_url != expected_issue_url:
            fail("evidence manifest digest issue URL does not match its issue date")
        source_issue_links = markdown_links(metadata.get("source issue", ""))
        if len(source_issue_links) != 1 or canonical_http_url(
            markdown_inline_text(source_issue_links[0][3])
        ) != canonical_http_url(digest_issue_url):
            fail("report source issue does not match the evidence manifest")

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
        if not isinstance(url, str) or not has_http_scheme(url):
            fail(f"evidence manifest source {index} has no HTTP URL")
        url = canonical_http_url(url)
        if schema_version >= 2:
            digest_url = source.get("digest_url")
            if not isinstance(digest_url, str) or not has_http_scheme(digest_url):
                fail(f"evidence manifest source {index} has no SentryDigest item URL")
            expected_digest_url = canonical_http_url(
                sentrydigest_item_url(feed_home_url, digest_issue_date, url)
                if schema_version == 3
                else legacy_sentrydigest_item_url(feed_home_url, url)
            )
            if canonical_http_url(digest_url) != expected_digest_url:
                fail(
                    f"evidence manifest source {index} has an invalid "
                    "SentryDigest item URL"
                )
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
        if has_http_scheme(destination)
        and markdown_inline_text(label) != "View in SentryDigest"
    ]
    if not body_links:
        fail("report body has no evidence links")
    unknown_pairs = sorted(set(body_links) - source_pairs)
    if unknown_pairs:
        label, url = unknown_pairs[0]
        fail("report links evidence absent from source manifest: " f"{label} ({url})")

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
            if has_http_scheme(destination)
        }
        supported_cves = set().union(
            *(source_cves.get(url, set()) for url in linked_urls)
        )
        unsupported = sorted(cited_cves - supported_cves)
        if unsupported:
            fail(f"report cites {unsupported[0]} without a linked source containing it")

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
        if markdown_inline_text(label) != "View in SentryDigest"
    }
    if not highlighted_pairs or not highlighted_pairs.issubset(source_pairs):
        fail("Source Highlights must use exact source title and URL pairs")
    if schema_version >= 2:
        expected_digest_urls = {
            canonical_http_url(str(source["digest_url"]))
            for source in raw_sources
            if (str(source["title"]), canonical_http_url(str(source["url"])))
            in highlighted_pairs
        }
        digest_urls = {
            canonical_http_url(markdown_inline_text(destination))
            for _, _, label, destination in markdown_links(source_section.group(1))
            if markdown_inline_text(label) == "View in SentryDigest"
        }
        if not digest_urls or digest_urls != expected_digest_urls:
            fail("Source Highlights must link each highlighted SentryDigest item")
    return manifest


def validate_required_report_sections(markdown: str, artifact: str) -> None:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    section_counts = {
        label: sum(1 for line in lines if report_section_label(line) == label)
        for label in REPORT_SECTION_LABELS
    }
    missing = [label for label, count in section_counts.items() if count == 0]
    repeated = [label for label, count in section_counts.items() if count > 1]
    if missing:
        fail(f"{artifact} missing required report section: " + sorted(missing)[0])
    if repeated:
        fail(f"{artifact} repeats report section: " + sorted(repeated)[0])


def validate_archive_history(archive_dir: Path, archive_html: str) -> None:
    snapshots = sorted(path for path in archive_dir.iterdir() if path.is_dir())
    if not snapshots:
        fail("archive contains no timestamped report snapshots")
    for snapshot in snapshots:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z", snapshot.name):
            fail(f"archive contains invalid snapshot directory: {snapshot.name}")
        required = {
            "report": snapshot / "report.md",
            "manifest": snapshot / "evidence-manifest.json",
            "page": snapshot / "index.html",
        }
        missing_files = [name for name, path in required.items() if not path.is_file()]
        if missing_files:
            fail(f"archive {snapshot.name} missing {sorted(missing_files)[0]} file")

        archived_markdown = required["report"].read_text(encoding="utf-8")
        archived_manifest = required["manifest"].read_text(encoding="utf-8")
        archived_page = required["page"].read_text(encoding="utf-8")
        metadata = report_metadata(archived_markdown)
        try:
            archived_manifest_data = json.loads(archived_manifest)
        except json.JSONDecodeError as error:
            fail(f"evidence-manifest.json is invalid JSON: {error}")
        manifest_schema = (
            archived_manifest_data.get("schema_version", 1)
            if isinstance(archived_manifest_data, dict)
            else None
        )
        required_metadata = (
            REQUIRED_PUBLIC_METADATA
            if manifest_schema in {2, 3}
            else LEGACY_REQUIRED_PUBLIC_METADATA
        )
        missing_metadata = required_metadata - metadata.keys()
        if missing_metadata:
            fail(
                f"archive {snapshot.name} missing provenance metadata: "
                + ", ".join(sorted(missing_metadata))
            )
        if metadata["analysis mode"].lower() != "model-backed":
            fail(f"archive {snapshot.name} is not model-backed")
        try:
            generated = datetime.fromisoformat(
                metadata["generated"].replace("Z", "+00:00")
            )
            if generated.tzinfo is None:
                generated = generated.replace(tzinfo=timezone.utc)
        except ValueError:
            fail(f"archive {snapshot.name} has an invalid Generated timestamp")
        expected_name = generated.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H-%M-%SZ"
        )
        if snapshot.name != expected_name:
            fail(f"archive {snapshot.name} does not match its Generated timestamp")
        validate_required_report_sections(
            archived_markdown, f"archive {snapshot.name}/report.md"
        )
        validate_evidence_manifest(archived_markdown, metadata, archived_manifest)
        if defect := find_reader_surface_defect(archived_markdown):
            fail(f"archive {snapshot.name} contains reader-surface defect: {defect}")
        if integrity := find_public_report_integrity_failure(archived_markdown):
            fail(
                f"archive {snapshot.name} contains report-integrity failure: {integrity}"
            )
        if '<main class="container archive-report">' not in archived_page:
            fail(f"archive {snapshot.name} page is not pre-rendered")
        if generated < DATED_DIGEST_HANDOFF_BOUNDARY:
            if (
                archived_page.count(ARCHIVE_CONTEXT_START) != 1
                or archived_page.count(ARCHIVE_CONTEXT_END) != 1
                or "publication-era rolling SentryDigest links" not in archived_page
                or 'href="../">Read the archive history</a>' not in archived_page
            ):
                fail(f"archive {snapshot.name} page is missing historical-link chrome")
            if archived_page.index(ARCHIVE_CONTEXT_START) > archived_page.index(
                '<main class="container archive-report">'
            ):
                fail(
                    f"archive {snapshot.name} historical-link note is inside its report body"
                )
        elif (
            ARCHIVE_CONTEXT_START in archived_page
            or ARCHIVE_CONTEXT_END in archived_page
        ):
            fail(
                f"archive {snapshot.name} page has inapplicable historical-link chrome"
            )
        if 'class="card report-provenance"' not in archived_page:
            fail(f"archive {snapshot.name} page is missing provenance")
        if 'href="evidence-manifest.json"' not in archived_page:
            fail(f"archive {snapshot.name} page does not link its evidence manifest")
        if f'href="{snapshot.name}/"' not in archive_html:
            fail(f"archive index does not link snapshot {snapshot.name}")


def validate_publication_surface(
    html: str,
    manifest_bytes: bytes,
    publication_state_text: str,
    publication_history_text: str,
    publication_history_html: str,
) -> None:
    try:
        state = json.loads(publication_state_text)
        history = json.loads(publication_history_text)
        validated_state = validate_publication_state(state, manifest_bytes)
        validate_publication_history(history, validated_state, manifest_bytes)
    except (json.JSONDecodeError, PublicationStateError) as error:
        fail(f"publication artifacts are invalid: {error}")

    events = history["events"]
    if publication_history_html.count('class="publication-history-entry"') != len(
        events
    ):
        fail("publication history page does not render every journal event")
    if 'href="../publication-history.json"' not in publication_history_html:
        fail("publication history page does not link its machine-readable journal")
    if "Earlier outcomes were not reconstructed" not in publication_history_html:
        fail("publication history page does not disclose its honest start")
    if "The next regular attempt runs daily at 13:00 UTC." not in publication_history_html:
        fail("publication history page does not name the enforced cadence")

    previous_position = publication_history_html.find(
        'class="publication-history-list"'
    )
    if previous_position < 0:
        fail("publication history page is missing its event list")
    for event in events:
        event_at = str(event["event_at"])
        position = publication_history_html.find(
            f'datetime="{event_at}"', previous_position + 1
        )
        if position <= previous_position:
            fail("publication history page is not newest first")
        previous_position = position
        generated = datetime.fromisoformat(
            str(event["report_generated_at"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        archive_key = generated.strftime("%Y-%m-%dT%H-%M-%SZ")
        archived_manifest_path = ARCHIVE_DIR / archive_key / "evidence-manifest.json"
        if not archived_manifest_path.is_file():
            fail("publication history event does not resolve to an archived report")
        archived_manifest = archived_manifest_path.read_bytes()
        if hashlib.sha256(archived_manifest).hexdigest() != event[
            "evidence_manifest_sha256"
        ]:
            fail("publication history event does not match its archived manifest")
        try:
            archived_manifest_data = json.loads(archived_manifest)
        except json.JSONDecodeError:
            fail("publication history archived manifest is invalid JSON")
        if archived_manifest_data.get("generated_at") != event["report_generated_at"]:
            fail("publication history event names the wrong archived report")

    notice_count = html.count('class="publication-notice"')
    if state["outcome"] == "retained":
        if notice_count != 1:
            fail("current page must render one retained-publication notice")
        if 'href="publication-state.json"' not in html:
            fail("retained-publication notice does not link its machine-readable state")
        if 'href="publication-history/"' not in html:
            fail("retained-publication notice does not link recent outcome history")
        if "The next regular attempt runs daily at 13:00 UTC." not in html:
            fail("retained-publication notice does not name the recovery horizon")
        if category_label(state["refusal_category"]) not in html:
            fail("retained-publication notice does not name its safe refusal category")
        if str(state["attempted_at"]) not in html:
            fail("retained-publication notice does not expose its attempt timestamp")
    elif notice_count:
        fail("published report must not render a retained-publication notice")
    if html.count('href="publication-history/"') < 2:
        fail("current page does not make publication history discoverable")


def main() -> None:
    html = read_text(INDEX_HTML)
    markdown = read_text(INDEX_MD)
    sitemap_xml = read_text(SITEMAP_XML)
    app_js = read_text(APP_JS)
    renderer_js = read_text(RENDERER_JS)
    style_css = read_text(STYLE_CSS)
    archive_html = read_text(ARCHIVE_INDEX)
    evidence_manifest_text = read_text(EVIDENCE_MANIFEST)
    publication_state_text = read_text(PUBLICATION_STATE)
    publication_history_text = read_text(PUBLICATION_HISTORY)
    publication_history_html = read_text(PUBLICATION_HISTORY_INDEX)

    validate_site_identity(html, sitemap_xml)

    # The page loads the shared style, canonical renderer, and small controller.
    for asset in (
        "static/style.css",
        "static/renderer.js",
        "static/app.js",
    ):
        if asset not in html:
            fail(f"index.html does not reference {asset}")

    # The operator workspace modules were removed; keep them gone.
    for removed in ("static/metadata.js", "static/filters.js", "static/archive.js"):
        if removed in html:
            fail(f"index.html still references removed module {removed}")
    for removed_module in ("metadata.js", "filters.js", "archive.js", "tags.js"):
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
    validate_required_report_sections(markdown, "index.md")
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
        has_http_scheme(destination)
        for _, _, _, destination in markdown_links(metadata["source"])
    ):
        fail("index.md Source metadata must be a linked feed")
    validate_evidence_manifest(
        markdown,
        metadata,
        evidence_manifest_text,
        require_current_schema=True,
    )
    validate_publication_surface(
        html,
        EVIDENCE_MANIFEST.read_bytes(),
        publication_state_text,
        publication_history_text,
        publication_history_html,
    )
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
    archived_manifest = read_text(ARCHIVE_DIR / archive_key / "evidence-manifest.json")
    if archived_markdown.rstrip() != markdown.rstrip():
        fail("current report does not match its timestamped archive snapshot")
    if archived_manifest != evidence_manifest_text:
        fail("current evidence manifest does not match its archived snapshot")
    validate_archive_history(ARCHIVE_DIR, archive_html)
    if 'href="archive/"' not in html or 'href="index.md"' not in html:
        fail("index.html is missing report archive or Markdown navigation")
    if 'data-prerendered="true"' not in html:
        fail("index.html does not contain pre-rendered report content")
    if 'class="card report-provenance"' not in html:
        fail("index.html does not render the report provenance card")
    if 'href="evidence-manifest.json"' not in html:
        fail("index.html does not link the machine-readable evidence manifest")
    if 'class="provenance-explanation"' not in html:
        fail(
            "index.html does not explain requested-route and authoring-model provenance"
        )

    # The page controller routes rendering through the canonical renderer.
    if 'href="$2"' in app_js:
        fail("app.js renders Markdown links without URL sanitization")
    if "window.GRCInsightRenderer" not in app_js:
        fail("app.js does not use the canonical renderer")
    if "renderer.renderReportDocument" not in app_js:
        fail("app.js does not render through renderer.renderReportDocument")
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
    for renderer_contract in (
        "renderEvidenceAffordances",
        "evidence-manifest.json",
        "View in SentryDigest",
        "Authoring model",
        "Requested route",
        "Source issue",
        "The requested route is the OpenRouter",
        "the authoring model is the upstream model attested",
    ):
        if renderer_contract not in renderer_js:
            fail(f"renderer.js missing provenance contract: {renderer_contract}")

    if "toLocaleDateString('en-US'" not in app_js or "timeZone: 'UTC'" not in app_js:
        fail("app.js does not format report dates in canonical English UTC")
    if 'class="brand-kicker">GRCInsight</span>' not in html:
        fail("index.html is missing the GRCInsight editorial masthead")
    if html.count('id="mobileToc"') != 1:
        fail("index.html must expose exactly one mobile section index")
    for retired_markup in (
        'id="progress"',
        'id="topbarLinks"',
        'class="reference-legend"',
        'class="shortcuts"',
        'id="copyStatus"',
        'id="backToTop"',
        'static/tags.js',
    ):
        if retired_markup in html:
            fail(f"index.html still exposes retired dashboard markup: {retired_markup}")
    for retired_behavior in (
        "window.GRCInsightTags",
        "highlightPills",
        "buildTopbar",
        "collapse-toggle",
        "copy-link",
        "cardCollapsed",
        "prefers-color-scheme",
    ):
        if retired_behavior in app_js:
            fail(f"app.js still exposes retired dashboard behavior: {retired_behavior}")
    for generic_finish in (
        "linear-gradient(",
        "box-shadow:",
        "font-size: 11px",
        "font-size: 12px",
        ".card.collapsed",
        "body.light",
    ):
        if generic_finish in style_css:
            fail(f"style.css still contains retired dashboard styling: {generic_finish}")
    if "--paper: #f7f3ea" not in style_css or "body.dark" not in style_css:
        fail("style.css does not provide a light editorial default with dark opt-in")
    if 'font-family: Georgia, "Times New Roman", serif' not in style_css:
        fail("style.css is missing the editorial heading type family")
    for style_contract in (
        ".evidence-note",
        ".evidence-inline",
        ".evidence-label",
        ".digest-handoff",
        ".manifest-link",
        ".provenance-explanation",
        ".publication-notice",
        ".publication-history-shell",
        ".publication-history-entry",
        ".archive-context",
    ):
        if style_contract not in style_css:
            fail(f"style.css is missing provenance style: {style_contract}")

    print("site report check passed")


if __name__ == "__main__":
    main()
