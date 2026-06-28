#!/usr/bin/env python3
"""Validate the committed GitHub Pages report artifact."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
INDEX_HTML = SITE_DIR / "index.html"
INDEX_MD = SITE_DIR / "index.md"
APP_JS = SITE_DIR / "static" / "app.js"
RENDERER_JS = SITE_DIR / "static" / "renderer.js"
TAGS_JS = SITE_DIR / "static" / "tags.js"
REPORT_SECTION_LABELS = {
    "Executive Summary",
    "Key Regulatory Developments",
    "Industry Impact Analysis",
    "Threat Actor Activities",
    "CVE and Vulnerability Highlights",
    "Risk Assessment",
    "Recommendations for Action",
    "Source Highlights",
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
MARKDOWN_LABEL_PREFIX = re.compile(
    r"^\s*(?:>\s*|(?:\d+[\).]|[-*])\s*|#{1,6}\s*)"
)


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
        or field_matches_any(
            cell, FORBIDDEN_METADATA_FIELDS, allow_prefixed_field=True
        )
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

    cells = [normalize_label_text(cell) for cell in stripped.strip("|").split("|") if cell]
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
        or normalized in {"non-public", "nonpublic", "private", "proprietary", "restricted"}
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
        or re.match(r"^internal(?:\s*-\s*|\s+)(?:executive\s+)?distribution$", normalized)
        is not None
    )


def is_private_prose_footer(line: str) -> bool:
    normalized = normalize_label_text(line)
    return bool(
        re.match(r"^this report contains\b.*\b(confidential|proprietary)\b", normalized)
        or re.match(r"^unauthorized distribution\b.*\b(prohibited|forbidden)\b", normalized)
    )


def field_value_is_forbidden(field: str, value: str) -> bool:
    field = field.replace("-", " ")
    if field_matches_any(
        field, FORBIDDEN_METADATA_FIELDS, allow_prefixed_field=True
    ):
        return True

    if not field_matches_any(
        field, PRIVATE_VALUE_FIELDS, allow_prefixed_field=True
    ):
        return False

    value_text = value.replace("-", " ")
    value_words = set(re.findall(r"[a-z]+", value_text))
    if field_matches_any(
        field, {"confidentiality"}, allow_prefixed_field=True
    ) and value_words & AFFIRMATIVE_LABEL_VALUES:
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


def fail(message: str) -> None:
    raise SystemExit(f"site report check failed: {message}")


def read_text(path: Path) -> str:
    if not path.exists():
        fail(f"missing {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def is_report_section(line: str) -> bool:
    if line.startswith("## "):
        return True

    match = NUMBERED_SECTION_PATTERN.match(line)
    if not match:
        return False

    return match.group(1).strip() in REPORT_SECTION_LABELS


def main() -> None:
    html = read_text(INDEX_HTML)
    markdown = read_text(INDEX_MD)
    app_js = read_text(APP_JS)
    renderer_js = read_text(RENDERER_JS)
    tags_js = read_text(TAGS_JS)

    # The page loads exactly one script per concern: the tag catalog, the
    # canonical renderer, and the page controller.
    for asset in ("static/style.css", "static/tags.js", "static/renderer.js", "static/app.js"):
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
    h1_count = sum(1 for line in lines if line.startswith("# ") and not line.startswith("## "))
    if h1_count != 1:
        fail("index.md must contain exactly one top-level report title")
    section_count = sum(1 for line in lines if is_report_section(line))
    if section_count < 2:
        fail("index.md must contain at least two report sections")
    if "Temporary placeholder" in markdown or "Temporary Outline" in markdown:
        fail("index.md still contains temporary placeholder content")
    forbidden_label = find_public_report_forbidden_label(markdown)
    if forbidden_label:
        fail(f"index.md contains public report forbidden label: {forbidden_label}")

    # The page controller routes rendering through the canonical renderer and
    # the shared tag catalog, and never emits an unsanitized Markdown link.
    if 'href="$2"' in app_js:
        fail("app.js renders Markdown links without URL sanitization")
    if "window.GRCInsightRenderer" not in app_js:
        fail("app.js does not use the canonical renderer")
    if "renderer.renderMarkdown" not in app_js and "renderMarkdown(" not in app_js:
        fail("app.js does not render through renderer.renderMarkdown")
    if "window.GRCInsightTags" not in app_js:
        fail("app.js does not use the shared compliance tag catalog")
    for inline_catalog in ("const frameworks =", "const regulations =", "const risks ="):
        if inline_catalog in app_js:
            fail(f"app.js still defines an inline tag catalog: {inline_catalog}")
    for removed_global in ("GRCInsightMetadata", "GRCInsightFilters", "GRCInsightArchive"):
        if removed_global in app_js:
            fail(f"app.js still references removed module global: {removed_global}")

    # The renderer owns Markdown rendering and URL sanitization.
    for export in (
        "window.GRCInsightRenderer",
        "function renderMarkdown",
        "function sanitizeMarkdownUrl",
        "function normalizeReportMarkdown",
    ):
        if export not in renderer_js:
            fail(f"renderer.js missing canonical export: {export}")
    if "rel=\"noopener\"" not in renderer_js:
        fail("renderer.js missing safe-link rel=noopener guard")

    if "window.GRCInsightTags" not in tags_js:
        fail("tags.js does not export the compliance tag catalog")

    print("site report check passed")


if __name__ == "__main__":
    main()
