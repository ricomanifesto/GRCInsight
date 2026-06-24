#!/usr/bin/env python3
"""Validate the committed GitHub Pages report artifact."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
INDEX_HTML = SITE_DIR / "index.html"
INDEX_MD = SITE_DIR / "index.md"
APP_JS = SITE_DIR / "static" / "app.js"
RENDERER_JS = SITE_DIR / "static" / "renderer.js"
TAGS_JS = SITE_DIR / "static" / "tags.js"
METADATA_JS = SITE_DIR / "static" / "metadata.js"
FILTERS_JS = SITE_DIR / "static" / "filters.js"
ARCHIVE_JS = SITE_DIR / "static" / "archive.js"


def fail(message: str) -> None:
    raise SystemExit(f"site report check failed: {message}")


def read_text(path: Path) -> str:
    if not path.exists():
        fail(f"missing {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    html = read_text(INDEX_HTML)
    style_css = read_text(SITE_DIR / "static" / "style.css")
    markdown = read_text(INDEX_MD)
    app_js = read_text(APP_JS)
    renderer_js = read_text(RENDERER_JS)
    tags_js = read_text(TAGS_JS)
    metadata_js = read_text(METADATA_JS)
    filters_js = read_text(FILTERS_JS)
    archive_js = read_text(ARCHIVE_JS)

    for asset in (
        "static/style.css",
        "static/tags.js",
        "static/metadata.js",
        "static/filters.js",
        "static/archive.js",
        "static/renderer.js",
        "static/app.js",
    ):
        if asset not in html:
            fail(f"index.html does not reference {asset}")

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

    h2_count = sum(1 for line in lines if line.startswith("## "))
    if h2_count < 2:
        fail("index.md must contain at least two report sections")

    if "Temporary placeholder" in markdown or "Temporary Outline" in markdown:
        fail("index.md still contains temporary placeholder content")

    if 'href="$2"' in app_js:
        fail("app.js renders Markdown links without URL sanitization")

    if "window.GRCInsightRenderer" not in app_js:
        fail("app.js does not use exported renderer helpers")

    if "window.GRCInsightTags" not in app_js:
        fail("app.js does not use exported compliance tag helpers")

    if "window.GRCInsightMetadata" not in app_js:
        fail("app.js does not use exported section metadata helpers")

    if "window.GRCInsightFilters" not in app_js:
        fail("app.js does not use exported section filter helpers")

    if "window.GRCInsightArchive" not in app_js:
        fail("app.js does not use exported archive digest data")

    for inline_catalog in ("const frameworks =", "const regulations =", "const risks ="):
        if inline_catalog in app_js:
            fail(f"app.js still defines inline tag catalog: {inline_catalog}")

    required_link_guards = (
        "function sanitizeMarkdownUrl(",
        "function renderMarkdownLink(",
        "sanitizeMarkdownUrl(url)",
    )
    for guard in required_link_guards:
        if guard not in renderer_js:
            fail(f"renderer.js missing link sanitizer guard: {guard}")

    required_tag_guards = (
        "window.GRCInsightTags",
        "frameworks",
        "regulations",
        "risks",
        "controls",
        "agencies",
        "pillClass",
        "control",
        "agency",
    )
    for guard in required_tag_guards:
        if guard not in tags_js:
            fail(f"tags.js missing compliance tag guard: {guard}")

    required_metadata_guards = (
        "window.GRCInsightMetadata",
        "deriveSectionMetadata",
        "renderSectionMetadata",
        "summarizeSections",
        "renderAuditSummary",
        "reviewStatus",
        "Needs source trail",
        "Audit-ready",
        "Evidence trail",
        "data-review-status",
        "data-obligations",
        "data-evidence",
        "data-owners",
        "Owner cues",
    )
    for guard in required_metadata_guards:
        if guard not in metadata_js:
            fail(f"metadata.js missing section metadata guard: {guard}")

    required_filter_guards = (
        "window.GRCInsightFilters",
        "filterSections",
        "parseFilterParams",
        "buildFilterParams",
        "sectionMatches",
        "statusQuickFilterCounts",
        "summarizeFilterResults",
        "activeFilterEntries",
        "activeFilterLabels",
        "reviewStatus",
        "evidenceState",
        "tagCategory",
        "ownerCue",
        "query",
    )
    for guard in required_filter_guards:
        if guard not in filters_js:
            fail(f"filters.js missing section filter guard: {guard}")

    required_filter_ui = (
        "sectionSearch",
        "statusFilter",
        "tagFilter",
        "ownerFilter",
        "evidenceFilter",
        "clearFilters",
        "filterSummary",
        "activeFilterChips",
        "statusQuickFilters",
        "sectionFilters.statusQuickFilterCounts(sections, filters)",
        "statuses.reduce((fallbackCounts, [value])",
        "fallbackCounts[value] = sections.filter(section => section.metadata && section.metadata.reviewStatus === value).length",
        "const disabled = count === 0 && !selected",
        "data-clear-filter",
        "renderActiveFilterChips(filters)",
        "clearSingleFilter(clearButton.dataset.clearFilter)",
        "data-status-filter",
        "updateStatusQuickFilters(sections, filters)",
        "button.dataset.statusFilter",
        "status.value = targetStatus",
        "sectionFilters.summarizeFilterResults(count, total, filters)",
        "empty.textContent = count === 0",
        "emptyResults",
        "sidebarFilterState",
        "topbarFilterState",
        "mobileToc",
        "document.getElementById(v)",
        "updateNavigationContext(count, total)",
        "No sections in filtered view",
    )
    for guard in required_filter_ui:
        if guard not in html + app_js:
            fail(f"site missing section filter UI guard: {guard}")

    required_filter_layout = (
        ".filter-controls",
        "repeat(4, minmax(120px, 0.8fr))",
        "@media (max-width: 900px)",
        ".active-filter-chips[hidden]",
        ".clear-filters",
    )
    for guard in required_filter_layout:
        if guard not in style_css:
            fail(f"style.css missing section filter layout guard: {guard}")

    required_archive_guards = (
        "window.GRCInsightArchive",
        "currentReportId",
        "buildReports",
        "deriveCurrentReportMetadata",
        "id: 'current'",
        "href: 'index.html'",
        "status: 'Current'",
        "Generated:",
        "Report Period",
    )
    for guard in required_archive_guards:
        if guard not in archive_js:
            fail(f"archive.js missing digest metadata guard: {guard}")

    required_archive_ui = (
        "archiveDigest",
        "renderArchiveDigest",
        "renderArchiveDigest(md)",
        "archiveDigest.buildReports(markdown || '')",
        "archive-card",
        "archive-entry${isCurrent ? ' current' : ''}",
        "sanitizeMarkdownUrl(report.href || '#')",
        "escapeAttribute(report.generatedAt || '')",
    )
    for guard in required_archive_ui:
        if guard not in html + app_js:
            fail(f"site missing archive digest UI guard: {guard}")

    if ".archive-entry.current" not in style_css:
        fail("style.css missing archive current-entry styling")

    required_audit_summary_ui = (
        "auditSummary",
        "installAuditSummary",
        "summarizeSections",
        "renderAuditSummary",
        "data-obligations",
        "audit-summary-card",
    )
    for guard in required_audit_summary_ui:
        if guard not in html + app_js + style_css:
            fail(f"site missing audit summary UI guard: {guard}")

    placeholder_cleanup = app_js.find("function handleTempOutline()")
    audit_summary_install = app_js.rfind("installAuditSummary();")
    if placeholder_cleanup == -1:
        fail("app.js missing temporary outline cleanup guard")
    if audit_summary_install == -1:
        fail("app.js missing audit summary install call")
    if audit_summary_install < placeholder_cleanup:
        fail("app.js installs audit summary before temporary outline cleanup")

    if "filterSections(sections, currentFilters()).map(section => section.id)" in app_js:
        fail("app.js collapses filtered section matches by section id")

    if "matches.has(section.id)" in app_js:
        fail("app.js keys filtered section visibility by section id")

    required_filtered_navigation_guards = (
        "function visibleSectionHeadings()",
        "#report .card:not(.filtered-out) h2",
        "function clearFocusMode()",
        "focusedCard.classList.contains('filtered-out')",
    )
    for guard in required_filtered_navigation_guards:
        if guard not in app_js:
            fail(f"app.js missing filtered navigation guard: {guard}")

    print("site report check passed")


if __name__ == "__main__":
    main()
