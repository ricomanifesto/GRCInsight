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
        "metadataStates",
        "reviewSignalStates",
        "reviewStatusOptions",
        "buildProvenanceSummary",
        "renderSectionMetadata",
        "summarizeSections",
        "coverageMetricEntries",
        "renderCoverageTableRows",
        "auditSummaryMetricEntries",
        "auditSummaryListSections",
        "data-audit-list-state",
        "auditSummaryReadiness",
        "auditSummaryCopy",
        "renderSummaryHeader",
        "workspaceActionEntries",
        "coverageRows",
        "renderWorkspaceOverview",
        "renderAuditSummary",
        "reviewStatus",
        "Needs source trail",
        "Audit-ready",
        "Evidence trail",
        "Coverage matrix",
        "Source provenance",
        "Generated sections",
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
        "filterStateOptions",
        "filterStateOptionMap",
        "function filterStateOption(key)",
        "filterSections",
        "parseFilterParams",
        "buildFilterParams",
        "filterParamEntries",
        "nonDefaultFilterEntries",
        "defaultFilterState",
        "isDefaultFilterState",
        "normalizeFilterValue",
        "normalizeFilterState",
        "sectionMatches",
        "statusQuickFilterCounts",
        "setMetadataStates",
        "evidenceStateValues",
        "setReviewStatusOptions",
        "allowedReviewStatusValues",
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
        "sectionFilters.setReviewStatusOptions(sectionMetadata.reviewStatusOptions)",
        "sectionFilters.setMetadataStates(sectionMetadata.metadataStates)",
        "const metadataStates = sectionMetadata && sectionMetadata.metadataStates",
        "const statusOptions = sectionMetadata && Array.isArray(sectionMetadata.reviewStatusOptions)",
        "sectionFilters.statusQuickFilterCounts(sections, filters)",
        "statusOptions.reduce((fallbackCounts, option)",
        "const value = option.value",
        "fallbackCounts[value] = sections.filter(section => section.metadata && section.metadata.reviewStatus === value).length",
        "const disabled = count === 0 && !selected",
        "data-clear-filter",
        "renderActiveFilterChips(filters)",
        "const filterControlBindings = filterStateOptions.map(option =>",
        "const filterStateOptionMap = sectionFilters.filterStateOptionMap ||",
        "function setFilterControlValue(binding, value)",
        "function setFilterControlDefaults()",
        "function currentFilters()",
        "return filterControlBindings.reduce((filters, binding)",
        "filterControlBindings.forEach(binding =>",
        "filterStateOptions.find(option => option.key === filterKey)",
        "filterControlBindings.find(binding => binding.key === filterKey)",
        "setFilterControlValue(binding, option.defaultValue)",
        "data-status-filter",
        "updateStatusQuickFilters(sections, filters)",
        "button.dataset.statusFilter",
        "status.value = targetStatus",
        "sectionFilters.isDefaultFilterState ? sectionFilters.isDefaultFilterState(filters)",
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

    duplicate_filter_lookup_guards = (
        "const queryOption = filterStateOption('query')",
        "const statusOption = filterStateOption('reviewStatus')",
        "const tagOption = filterStateOption('tagCategory')",
        "const ownerOption = filterStateOption('ownerCue')",
        "const evidenceOption = filterStateOption('evidenceState')",
    )
    for guard in duplicate_filter_lookup_guards:
        if guard in filters_js:
            fail(f"filters.js still duplicates filter option lookup: {guard}")

    duplicate_filter_default_guards = (
        "count === total && !search.value && status.value === 'all' && tag.value === 'all' && owner.value === 'all' && evidence.value === 'all'",
        "query: '', reviewStatus: 'all', tagCategory: 'all', ownerCue: 'all', evidenceState: 'all'",
    )
    for guard in duplicate_filter_default_guards:
        if guard in filters_js + app_js:
            fail(f"site still duplicates filter default state: {guard}")

    duplicate_filter_active_value_guards = (
        "const query = String(active.query || options.query.defaultValue).trim();",
        "const reviewStatus = safeValue(active.reviewStatus || options.reviewStatus.defaultValue, allowedReviewStatusValues(), options.reviewStatus.defaultValue);",
        "const tagCategory = safeValue(active.tagCategory || options.tagCategory.defaultValue, allowedTagCategories, options.tagCategory.defaultValue);",
        "const ownerCue = safeValue(active.ownerCue || options.ownerCue.defaultValue, allowedOwnerCues, options.ownerCue.defaultValue);",
        "const evidenceState = safeValue(active.evidenceState || options.evidenceState.defaultValue, allowedEvidenceStates, options.evidenceState.defaultValue);",
    )
    for guard in duplicate_filter_active_value_guards:
        if guard in filters_js:
            fail(f"filters.js still duplicates active filter value normalization: {guard}")

    duplicate_filter_url_param_guards = (
        "params.set(options.query.param, active.query)",
        "params.set(options.reviewStatus.param, active.reviewStatus)",
        "params.set(options.tagCategory.param, active.tagCategory)",
        "params.set(options.ownerCue.param, active.ownerCue)",
        "params.set(options.evidenceState.param, active.evidenceState)",
    )
    for guard in duplicate_filter_url_param_guards:
        if guard in filters_js:
            fail(f"filters.js still duplicates filter URL param serialization: {guard}")

    duplicate_active_filter_entry_guards = (
        "if (active.query) entries.push({ key: options.query.key, label: `${options.query.labelPrefix}: ${active.query}` });",
        "if (active.reviewStatus !== options.reviewStatus.defaultValue) entries.push({ key: options.reviewStatus.key, label: `${options.reviewStatus.labelPrefix}: ${active.reviewStatus}` });",
        "if (active.tagCategory !== options.tagCategory.defaultValue) entries.push({ key: options.tagCategory.key, label: `${options.tagCategory.labelPrefix}: ${active.tagCategory}` });",
        "if (active.ownerCue !== options.ownerCue.defaultValue) entries.push({ key: options.ownerCue.key, label: `${options.ownerCue.labelPrefix}: ${active.ownerCue}` });",
        "if (active.evidenceState !== options.evidenceState.defaultValue) entries.push({ key: options.evidenceState.key, label: `${options.evidenceState.labelPrefix}: ${active.evidenceState}` });",
    )
    for guard in duplicate_active_filter_entry_guards:
        if guard in filters_js:
            fail(f"filters.js still duplicates active filter entry projection: {guard}")

    duplicate_non_default_filter_projection_guards = (
        "function filterParamEntries(filters) {\n    const active = normalizeFilterState(filters);",
        "function activeFilterEntries(filters) {\n    const active = normalizeFilterState(filters);",
    )
    for guard in duplicate_non_default_filter_projection_guards:
        if guard in filters_js:
            fail(f"filters.js still duplicates non-default filter projection: {guard}")

    duplicate_coverage_metric_guards = (
        "function renderCoverageTable(summary) {\n    const rows = coverageRows(summary).map(row =>",
        "function coverageRows(summary) {\n    const total = summary.totalSections || 0;",
    )
    for guard in duplicate_coverage_metric_guards:
        if guard in metadata_js:
            fail(f"metadata.js still duplicates coverage metric projection: {guard}")

    duplicate_coverage_row_renderer_guards = (
        "function renderCoverageTable(summary) {\n    const rows = coverageMetricEntries(summary).map(row =>",
    )
    for guard in duplicate_coverage_row_renderer_guards:
        if guard in metadata_js:
            fail(f"metadata.js still duplicates coverage table row rendering: {guard}")

    duplicate_audit_summary_metric_guards = (
        "<span><strong>${summary.actionRequired}</strong> action required</span>",
        "<span><strong>${summary.evidenceGaps}</strong> source-trail gaps</span>",
    )
    for guard in duplicate_audit_summary_metric_guards:
        if guard in metadata_js:
            fail(f"metadata.js still duplicates audit summary metric projection: {guard}")

    duplicate_audit_summary_list_guards = (
        "<h3>Action focus</h3>\n            <ul>${renderList(summary.actionTitles, 'No action-required sections detected')}</ul>",
        "<h3>Evidence gaps</h3>\n            <ul>${renderList(summary.gapTitles, 'No missing source trails detected')}</ul>",
    )
    for guard in duplicate_audit_summary_list_guards:
        if guard in metadata_js:
            fail(f"metadata.js still duplicates audit summary list projection: {guard}")

    duplicate_audit_summary_readiness_guards = (
        "const readiness = summary.totalSections === 0\n      ? 'No generated sections match the active filters'\n      : (summary.auditReady ? 'Audit-ready visible set' : 'Compliance review workspace');",
        "const readiness = summary.auditReady ? 'Audit-ready' : 'Needs source trail';",
    )
    for guard in duplicate_audit_summary_readiness_guards:
        if guard in metadata_js:
            fail(f"metadata.js still duplicates audit summary readiness projection: {guard}")

    duplicate_audit_summary_copy_guards = (
        '<p class="workspace-copy">${summary.totalSections} visible sections mapped across obligations, controls, gaps, owner cues, and source provenance.</p>',
        '<p class="audit-summary-copy">${summary.totalSections} sections reviewed for obligations, gaps, deadlines, and evidence trails.</p>',
    )
    for guard in duplicate_audit_summary_copy_guards:
        if guard in metadata_js:
            fail(f"metadata.js still duplicates audit summary body copy: {guard}")

    duplicate_summary_header_guards = (
        "<div class=\"workspace-heading-block\">\n          <p class=\"workspace-kicker\">Generated compliance archive</p>\n          <h2>${escapeHtml(readiness.workspaceHeading)}</h2>\n          <p class=\"workspace-copy\">${escapeHtml(summaryCopy.workspaceCopy)}</p>\n        </div>",
        "<div>\n          <p class=\"audit-kicker\">Audit-ready summary</p>\n          <h2>${escapeHtml(readiness.auditHeading)}</h2>\n          <p class=\"audit-summary-copy\">${escapeHtml(summaryCopy.auditCopy)}</p>\n        </div>",
    )
    for guard in duplicate_summary_header_guards:
        if guard in metadata_js:
            fail(f"metadata.js still duplicates summary header rendering: {guard}")

    duplicate_workspace_action_guards = (
        "<a href=\"#auditSummary\">Audit summary</a>",
        "<a href=\"#report\">Generated sections</a>",
        "<a href=\"#toc\">Section index</a>",
    )
    for guard in duplicate_workspace_action_guards:
        if guard in metadata_js:
            fail(f"metadata.js still duplicates workspace action projection: {guard}")

    required_filter_layout = (
        ".filter-controls",
        "repeat(4, minmax(120px, 0.8fr))",
        "@media (max-width: 900px)",
        ".nav-fab { display: none; }",
        ".active-filter-chips[hidden]",
        ".clear-filters",
    )
    for guard in required_filter_layout:
        if guard not in style_css:
            fail(f"style.css missing section filter layout guard: {guard}")

    required_workspace_visual_contract = (
        "--workspace-accent",
        "--workspace-rail",
        ".app-header .container { position: relative; display: grid;",
        ".theme-toggle { grid-column: 2; grid-row: 1;",
        ".controls { display: grid; grid-template-columns: minmax(0, 1fr) auto;",
        "@media (max-width: 1080px)",
        ".control-buttons { justify-content: flex-start; }",
        ".sidebar { position: static; max-height: none; }",
        ".workspace-overview-card { position: relative;",
        ".workspace-overview-card::before",
        ".audit-metrics { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr));",
        ".sidebar { position: sticky; top: 76px;",
        ".card { position: relative;",
        "@media (max-width: 760px)",
    )
    for guard in required_workspace_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance workspace visual contract guard: {guard}")
    sidebar_base = ".sidebar { position: sticky; top: 76px;"
    sidebar_tablet_override = ".sidebar { position: static; max-height: none; }"
    if style_css.index(sidebar_base) > style_css.index(sidebar_tablet_override):
        fail("style.css applies tablet sidebar flow override before the base sticky sidebar rule")

    required_resource_reference_visual_contract = (
        "--workspace-hairline",
        "--workspace-focus",
        ".workspace-overview-card, .archive-card, .audit-summary-card, .card {",
        ".workspace-heading-block {",
        ".workspace-actions a {",
        ".section-meta-item {",
        ".coverage-table table {",
        ".table-wrap table {",
        ".sidebar nav a.active, .topbar .chip.active {",
        "body.light .sidebar nav a.active, body.light .topbar .chip.active { color: #31513e; }",
        ".archive-entry.current {",
        "@media (max-width: 760px)",
        ".workspace-actions {",
    )
    for guard in required_resource_reference_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing resource-reference visual aesthetic guard: {guard}")

    required_evidence_surface_visual_contract = (
        "--evidence-ready",
        "--evidence-gap",
        ".coverage-row {",
        ".coverage-row[data-coverage-state=\"ready\"] {",
        ".coverage-row[data-coverage-state=\"gap\"] {",
        ".section-meta[data-evidence=\"Source referenced\"] .section-meta-item:nth-child(6)",
        ".section-meta[data-evidence=\"Needs source trail\"] .section-meta-item:nth-child(6)",
        ".table-wrap { overflow-x: auto; margin: 16px 0; border-radius: 8px; border: 1px solid var(--workspace-hairline);",
        ".card, .content, .report { min-width: 0; }",
        ".table-wrap, .coverage-table { max-width: 100%; min-width: 0; }",
        ".table-wrap table { min-width: 680px;",
        ".table-wrap tbody tr:nth-child(even), .coverage-table tbody tr:nth-child(even)",
        "body.light .app-header { background: linear-gradient(180deg, #fbfaf7 0%, #eef3ed 100%);",
        "body.light .section-meta[data-evidence=\"Needs source trail\"] .section-meta-item:nth-child(6)",
        "@media (max-width: 760px)",
    )
    for guard in required_evidence_surface_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing evidence-surface visual QA guard: {guard}")

    required_scan_density_visual_contract = (
        "--workspace-density-gap",
        ".app-header { background: linear-gradient(180deg, #131a17 0%, #0f1412 100%); color: white; padding: 24px 0 14px;",
        ".controls { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--workspace-density-gap);",
        ".filter-field input, .filter-field select { width: 100%; min-height: 34px;",
        ".action-btn { border: 1px solid rgba(255,255,255,0.25); background: transparent; color: #fff; border-radius: 6px; padding: 6px 9px;",
        ".report { display: grid; gap: 12px;",
        ".workspace-overview-card, .archive-card { display: grid; gap: 12px;",
        ".archive-entry { display: grid; grid-template-columns: minmax(0, 1fr) minmax(140px, auto); gap: 10px; padding: 12px;",
        ".layout { display: grid; grid-template-columns: 240px 1fr; gap: 14px;",
        ".sidebar { position: sticky; top: 76px;",
        ".sidebar nav a { display: block; padding: 5px 7px;",
        ".topbar .topbar-scroll { display: flex; gap: 6px; overflow-x: auto; padding: 8px 0;",
        ".topbar .chip { white-space: nowrap; padding: 5px 9px;",
        "@media (max-width: 760px)",
        ".app-header { padding: 20px 0 12px; }",
    )
    for guard in required_scan_density_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance workspace scan-density guard: {guard}")

    required_archive_card_hierarchy_visual_contract = (
        ".archive-card { position: relative; overflow: hidden; padding-left: 24px;",
        ".archive-card::before { content: \"\"; position: absolute; inset: 0 auto 0 0; width: 4px; background: var(--workspace-rail); }",
        ".archive-entry-main { display: grid; gap: 6px; min-width: 0; }",
        ".archive-entry.current .archive-entry-kicker { color: #f5e8c8; }",
        ".archive-entry.current h3 { color: #fde68a; }",
        ".archive-entry h3 a { color: inherit; }",
        ".archive-review-metrics div { display: grid; align-content: center; min-height: 48px;",
        ".archive-tags span { display: inline-flex; min-height: 24px; align-items: center; padding: 3px 7px; font-weight: 700;",
        ".card h2 { display: flex; align-items: center; gap: 8px; scroll-margin-top: 90px; flex-wrap: wrap; }",
        ".card h2::before { content: \"\"; flex: 0 0 auto;",
        "body.light .card h2::before { background: #31513e;",
        "body.light .archive-entry.current .archive-entry-kicker { color: #31513e; }",
        ".card h2 { align-items: flex-start; }",
    )
    for guard in required_archive_card_hierarchy_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing archive card hierarchy visual contract guard: {guard}")

    required_editorial_workspace_aesthetic_visual_contract = (
        "--workspace-card-shadow",
        "--workspace-control-surface",
        ".app-header .title { max-width: 900px; margin: 0; font-size: 46px; line-height: 0.96; letter-spacing: 0; text-wrap: balance; }",
        ".app-header .subtitle { max-width: 760px; margin: 8px 0 0; opacity: 0.86; grid-column: 1 / -1; font-size: 15px; line-height: 1.55; }",
        ".controls { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--workspace-density-gap); margin-top: 14px; align-items: end; grid-column: 1 / -1; padding: 10px; border: 1px solid rgba(255,255,255,0.10); border-radius: 8px; background: var(--workspace-control-surface); }",
        "body.light .controls { border-color: rgba(49,81,62,0.14); }",
        ".workspace-overview-card, .archive-card, .audit-summary-card, .card { border-color: var(--workspace-hairline); box-shadow: var(--workspace-card-shadow); }",
        "body.light .workspace-overview-card, body.light .archive-card { border-color: rgba(0,0,0,0.08); box-shadow: var(--workspace-card-shadow); }",
        ".audit-summary-card { position: relative; display: grid; gap: 14px; background: linear-gradient(180deg, var(--panel), var(--panel-2)); border: 1px solid var(--line); border-radius: 8px; padding: 18px 20px 18px 24px; box-shadow: var(--workspace-card-shadow); overflow: hidden; }",
        "body.light .audit-summary-card { border-color: rgba(0,0,0,0.08); box-shadow: var(--workspace-card-shadow); }",
        ".card { border-color: var(--workspace-hairline); box-shadow: var(--workspace-card-shadow); }",
        "body.light .card { border-color: var(--workspace-hairline); box-shadow: var(--workspace-card-shadow); }",
        ".coverage-table caption { text-align: left; padding: 10px 12px; color: #f5e8c8; font-size: 12px; font-weight: 800; text-transform: uppercase;",
        ".table-wrap, .coverage-table { box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 8px 18px rgba(0,0,0,0.12); }",
        ".app-header .title { font-size: 32px; line-height: 1; }",
    )
    for guard in required_editorial_workspace_aesthetic_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing editorial workspace aesthetic visual contract guard: {guard}")

    required_mobile_workspace_polish_visual_contract = (
        "--mobile-workspace-gap",
        "@media (max-width: 760px)",
        ".app-header { padding: 20px 0 12px; }",
        ".app-header .container { grid-template-columns: 1fr; gap: 8px; }",
        ".controls { padding: 8px; gap: var(--mobile-workspace-gap); }",
        ".filter-controls { gap: var(--mobile-workspace-gap); }",
        ".control-buttons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--mobile-workspace-gap); }",
        ".control-buttons .action-btn, .clear-filters { width: 100%; min-height: 38px; }",
        ".mobile-toc { min-height: 38px; border-radius: 8px; padding: 8px 10px; }",
        ".topbar { box-shadow: 0 8px 18px rgba(0,0,0,0.18); }",
        ".topbar .topbar-scroll { padding: 7px 0; scroll-padding-inline: 12px; }",
        ".workspace-overview-card, .archive-card, .audit-summary-card, .card { border-radius: 8px; }",
        ".coverage-table table { min-width: 560px; }",
        ".table-wrap table { min-width: 560px; }",
    )
    for guard in required_mobile_workspace_polish_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing mobile workspace polish visual contract guard: {guard}")
    base_markdown_table_index = style_css.find(".table-wrap table { min-width: 680px;")
    mobile_markdown_table_index = style_css.rfind(".table-wrap table { min-width: 560px; }")
    if base_markdown_table_index == -1 or mobile_markdown_table_index == -1:
        fail("style.css missing mobile markdown table cascade guard")
    if mobile_markdown_table_index < base_markdown_table_index:
        fail("style.css mobile markdown table override must follow the base markdown table rule")

    required_section_detail_aesthetic_visual_contract = (
        "--section-detail-gap",
        ".card { display: grid; gap: var(--section-detail-gap); }",
        ".card > p { margin: 0 0 8px; }",
        ".card > ul, .card > ol { margin-top: 0; }",
        ".section-meta { padding: 8px; border: 1px solid var(--workspace-hairline); border-radius: 8px; background: rgba(255,255,255,0.028); }",
        ".section-meta-item { min-height: 28px; padding: 5px 8px; }",
        ".card h2 .heading-actions { margin-left: auto; }",
        ".heading-actions { display: inline-grid; grid-auto-flow: column; align-items: center; gap: 4px; flex: 0 0 auto; }",
        ".card > .table-wrap { margin: 10px 0 12px; }",
        "blockquote { margin: 10px 0 12px; }",
        ".card h2 .heading-actions { margin-left: 0; }",
    )
    for guard in required_section_detail_aesthetic_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing section detail aesthetic visual contract guard: {guard}")

    required_compliance_workspace_aesthetic_alignment_visual_contract = (
        "--workspace-action-gap",
        "--workspace-index-width",
        "--workspace-table-density",
        ".app-header .title { max-width: 960px; font-size: 52px; line-height: 0.94; }",
        ".control-buttons { gap: var(--workspace-action-gap); align-content: end; }",
        ".action-btn { min-height: 32px; padding: 5px 8px; }",
        ".layout { grid-template-columns: var(--workspace-index-width) minmax(0, 1fr); }",
        ".sidebar { border-left: 3px solid var(--workspace-rail); padding: 10px; }",
        "body.light .sidebar { border-left-color: var(--workspace-rail); }",
        ".workspace-overview-card { padding: 18px 20px 18px 26px; }",
        ".audit-metrics span { min-height: 52px; padding: 8px; }",
        ".coverage-table th, .coverage-table td { padding: var(--workspace-table-density) 10px; }",
        ".coverage-row strong { display: inline-flex; min-height: 22px; align-items: center; }",
        ".topbar .chip { min-height: 30px; display: inline-flex; align-items: center; }",
        ".app-header .title { font-size: 34px; line-height: 0.98; }",
    )
    for guard in required_compliance_workspace_aesthetic_alignment_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance workspace aesthetic alignment guard: {guard}")

    required_evidence_source_coverage_aesthetic_visual_contract = (
        "--evidence-table-gap",
        ".coverage-table { border-left: 3px solid var(--workspace-rail); }",
        ".coverage-table caption { display: flex; align-items: center; gap: var(--evidence-table-gap); }",
        ".coverage-table caption::before { content: \"\"; width: 8px; height: 8px; border-radius: 999px; background: var(--workspace-rail); }",
        ".coverage-row strong { border-radius: 999px; padding: 2px 7px; background: rgba(255,255,255,0.055); }",
        ".coverage-row[data-coverage-state=\"gap\"] strong { background: rgba(239,68,68,0.16); }",
        ".coverage-row[data-coverage-state=\"ready\"] strong { background: rgba(22,163,74,0.16); }",
        ".table-wrap { border-left: 3px solid rgba(214,160,77,0.46); }",
        "body.light .table-wrap { border-left-color: var(--workspace-rail); }",
        ".table-wrap th:first-child, .table-wrap td:first-child { width: 24%; }",
        ".coverage-table caption { align-items: flex-start; }",
        ".coverage-row strong { white-space: normal; }",
    )
    for guard in required_evidence_source_coverage_aesthetic_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing evidence source coverage aesthetic guard: {guard}")

    required_compliance_archive_surface_aesthetic_continuity_contract = (
        "--surface-continuity-gap",
        "--surface-rail-width",
        ".workspace-overview-card, .archive-card, .audit-summary-card { gap: var(--surface-continuity-gap); }",
        ".workspace-overview-card::before, .archive-card::before, .audit-summary-card::before { width: var(--surface-rail-width); background: var(--workspace-rail); }",
        ".archive-entry, .audit-lists > div, .section-meta { border-color: var(--workspace-hairline); }",
        ".archive-review-metrics, .audit-metrics { gap: var(--workspace-action-gap); }",
        ".workspace-actions a, .status-quick-filter, .active-filter-chip { border-radius: 6px; }",
        ".status-quick-filter { border-radius: 6px; }",
        ".card::before { width: 3px; background: var(--workspace-rail); }",
        "body.light .card::before { background: var(--workspace-rail); }",
        ".archive-entry-meta { gap: var(--surface-continuity-gap); }",
        ".audit-lists { gap: var(--surface-continuity-gap); }",
        ".audit-lists > div { border-color: var(--workspace-hairline); }",
        ".audit-summary-card { gap: var(--surface-continuity-gap); }",
        ".audit-summary-card::before { width: var(--surface-rail-width); background: var(--workspace-rail); }",
    )
    for guard in required_compliance_archive_surface_aesthetic_continuity_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance archive surface continuity guard: {guard}")

    required_compliance_review_action_affordance_visual_contract = (
        "--review-action-min-target",
        "--review-action-focus-ring",
        ".workspace-actions a, .status-quick-filter, .active-filter-chip { min-height: var(--review-action-min-target); }",
        ".workspace-actions a:hover, .workspace-actions a:focus-visible { box-shadow: var(--review-action-focus-ring); }",
        ".status-quick-filter.active, .active-filter-chip:focus-visible { box-shadow: var(--review-action-focus-ring); }",
        ".archive-entry.current { box-shadow: inset 3px 0 0 var(--workspace-rail), 0 10px 20px rgba(0,0,0,0.14); }",
        ".copy-link, .collapse-toggle, .focus-toggle { min-width: var(--review-action-min-target); min-height: var(--review-action-min-target); }",
        ".copy-link:focus-visible, .collapse-toggle:focus-visible, .focus-toggle:focus-visible { box-shadow: var(--review-action-focus-ring); color: #f5e8c8; }",
        "body.light .copy-link:focus-visible, body.light .collapse-toggle:focus-visible, body.light .focus-toggle:focus-visible { color: #31513e; }",
        ".archive-entry.current h3 a:focus-visible { outline: 2px solid var(--workspace-rail); outline-offset: 3px; border-radius: 4px; }",
        ".active-filter-chip-clear { width: 18px; height: 18px; }",
        ".workspace-actions a { justify-content: center; }",
    )
    for guard in required_compliance_review_action_affordance_visual_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance review action affordance guard: {guard}")

    required_compliance_workspace_reference_aesthetic_alignment_contract = (
        "--reference-editorial-heading-size",
        "--reference-context-line-height",
        "--reference-action-row-gap",
        "--reference-card-density",
        ".workspace-overview-card h2 { font-size: var(--reference-editorial-heading-size); line-height: 1.02; }",
        ".workspace-heading-block { gap: 6px; padding-bottom: 10px; }",
        ".workspace-copy, .archive-summary, .audit-summary-copy { line-height: var(--reference-context-line-height); }",
        ".workspace-actions { gap: var(--reference-action-row-gap); padding-top: 2px; }",
        ".sidebar nav a.active { box-shadow: inset 3px 0 0 var(--workspace-rail); }",
        ".audit-lists > div, .archive-entry { padding: var(--reference-card-density); }",
        ".card { padding: 15px 18px 15px 20px; }",
        ".coverage-row[data-coverage-state=\"gap\"] td:last-child { box-shadow: inset 3px 0 0 rgba(239,68,68,0.34); font-weight: 600; }",
        ".coverage-row[data-coverage-state=\"ready\"] td:last-child { box-shadow: inset 3px 0 0 rgba(22,163,74,0.30); }",
        ".workspace-overview-card h2 { font-size: 26px; line-height: 1.04; }",
    )
    for guard in required_compliance_workspace_reference_aesthetic_alignment_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance workspace reference aesthetic guard: {guard}")

    required_compliance_filtered_workspace_state_aesthetic_contract = (
        "--filtered-state-rail",
        "--filtered-state-gap",
        "--filtered-state-note-bg",
        "--empty-state-rail",
        ".filter-state { display: inline-flex; align-items: center; min-height: 30px; padding: 5px 9px 5px 12px; border-left: 3px solid var(--filtered-state-rail); border-radius: 6px; background: var(--filtered-state-note-bg); font-weight: 700; }",
        ".active-filter-chips, .status-quick-filters { gap: var(--filtered-state-gap); align-items: center; }",
        ".status-quick-filter strong { min-width: 18px; text-align: center; }",
        ".empty-results { border-left: 4px solid var(--empty-state-rail); font-weight: 700; }",
        ".nav-empty { display: inline-flex; min-height: 30px; align-items: center; padding: 5px 8px; border-left: 3px solid var(--empty-state-rail); border-radius: 6px; background: rgba(245,158,11,0.10); }",
        ".topbar .nav-filter-state { display: inline-flex; min-height: 30px; align-items: center; border-left: 3px solid var(--filtered-state-rail); border-radius: 6px; background: var(--filtered-state-note-bg); padding: 5px 8px 5px 10px; }",
        ".topbar .nav-empty { margin: 0 12px; }",
        "body.light .nav-empty { background: rgba(245,158,11,0.12); color: #92400e; }",
    )
    for guard in required_compliance_filtered_workspace_state_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance filtered workspace state aesthetic guard: {guard}")

    required_compliance_visual_reference_continuity_aesthetic_contract = (
        "--visual-continuity-gap",
        "--visual-continuity-panel-inset",
        "--visual-continuity-chip-gap",
        "--visual-continuity-row-line-height",
        ".workspace-overview-card, .archive-card, .audit-summary-card, .card { gap: var(--visual-continuity-gap); }",
        ".layout { gap: var(--visual-continuity-gap); }",
        ".sidebar { padding: var(--visual-continuity-panel-inset); }",
        ".sidebar details > summary, .sidebar nav > a { min-height: 30px; display: flex; align-items: center; }",
        ".sidebar details ul a { min-height: auto; display: block; align-items: initial; }",
        ".section-meta { margin: -2px 0 10px; gap: var(--visual-continuity-chip-gap); }",
        ".section-meta-item { min-height: 26px; padding: 4px 7px; }",
        ".card > .table-wrap { margin: 8px 0 10px; }",
        ".coverage-table caption { padding: 8px 10px; }",
        ".coverage-row td:last-child { line-height: var(--visual-continuity-row-line-height); }",
        ".workspace-overview-card, .archive-card, .audit-summary-card { padding-top: var(--visual-continuity-panel-inset); padding-bottom: var(--visual-continuity-panel-inset); }",
        ".audit-summary-card { gap: var(--visual-continuity-gap); }",
        ".audit-summary-card { padding-top: var(--visual-continuity-panel-inset); padding-bottom: var(--visual-continuity-panel-inset); }",
        ".filter-field:first-child { grid-column: 1 / -1; }",
        ".filter-controls { grid-template-columns: repeat(2, minmax(0, 1fr)); }",
    )
    for guard in required_compliance_visual_reference_continuity_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance visual reference continuity aesthetic guard: {guard}")

    audit_surface_gap = ".audit-summary-card { gap: var(--surface-continuity-gap); }"
    audit_visual_gap = ".audit-summary-card { gap: var(--visual-continuity-gap); }"
    audit_visual_padding = ".audit-summary-card { padding-top: var(--visual-continuity-panel-inset); padding-bottom: var(--visual-continuity-panel-inset); }"
    css_lines = style_css.splitlines()
    try:
        audit_surface_gap_line = css_lines.index(audit_surface_gap)
    except ValueError:
        fail(f"style.css missing audit summary surface continuity guard: {audit_surface_gap}")
    for guard in (audit_visual_gap, audit_visual_padding):
        try:
            guard_line = css_lines.index(guard, audit_surface_gap_line + 1)
        except ValueError:
            fail(f"style.css missing later audit summary visual continuity guard: {guard}")
        if guard_line <= audit_surface_gap_line:
            fail(f"style.css audit summary visual continuity guard appears before audit surface rule: {guard}")

    section_card_gap = ".card { display: grid; gap: var(--section-detail-gap); }"
    section_card_visual_gap = ".card { gap: var(--visual-continuity-gap); }"
    try:
        section_card_gap_line = css_lines.index(section_card_gap)
    except ValueError:
        fail(f"style.css missing section card detail gap guard: {section_card_gap}")
    try:
        section_card_visual_gap_line = css_lines.index(section_card_visual_gap, section_card_gap_line + 1)
    except ValueError:
        fail(f"style.css missing later section card visual continuity gap guard: {section_card_visual_gap}")
    if section_card_visual_gap_line <= section_card_gap_line:
        fail(f"style.css section card visual continuity guard appears before section detail rule: {section_card_visual_gap}")

    required_compliance_evidence_review_surface_aesthetic_contract = (
        "--evidence-review-caption-bg",
        "--evidence-review-cell-padding-block",
        "--evidence-review-row-line-height",
        "--evidence-review-table-min-width",
        "--evidence-review-mobile-table-min-width",
        ".coverage-table caption { line-height: 1.35; background: var(--evidence-review-caption-bg); border-bottom: 1px solid var(--workspace-hairline); }",
        ".coverage-table th, .coverage-table td { padding-top: var(--evidence-review-cell-padding-block); padding-bottom: var(--evidence-review-cell-padding-block); line-height: var(--evidence-review-row-line-height); }",
        ".coverage-row[data-coverage-state=\"ready\"] th:first-child { box-shadow: inset 3px 0 0 rgba(22,163,74,0.34); }",
        ".coverage-row[data-coverage-state=\"gap\"] th:first-child { box-shadow: inset 3px 0 0 rgba(239,68,68,0.38); }",
        ".table-wrap table { min-width: var(--evidence-review-table-min-width); }",
        ".table-wrap th, .table-wrap td { padding-top: var(--evidence-review-cell-padding-block); padding-bottom: var(--evidence-review-cell-padding-block); line-height: var(--evidence-review-row-line-height); }",
        ".table-wrap th:first-child, .table-wrap td:first-child { width: 22%; font-weight: 700; }",
        ".table-wrap, .coverage-table { background: var(--evidence-review-caption-bg); }",
        ".table-wrap table { min-width: var(--evidence-review-mobile-table-min-width); }",
    )
    for guard in required_compliance_evidence_review_surface_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance evidence review surface aesthetic guard: {guard}")

    required_compliance_audit_summary_gap_hierarchy_contract = (
        "--audit-summary-list-gap",
        "--audit-summary-note-line-height",
        "--audit-summary-gap-rail",
        ".audit-lists { gap: var(--audit-summary-list-gap); }",
        ".audit-lists > div { display: grid; gap: 7px; align-content: start; }",
        ".audit-lists > div[data-audit-list=\"evidenceGaps\"][data-audit-list-state=\"gap\"] { border-left: 3px solid var(--audit-summary-gap-rail); background: var(--evidence-gap); }",
        ".audit-lists h3 { display: flex; align-items: center; gap: 6px; }",
        ".audit-lists h3::before { content: \"\"; width: 7px; height: 7px; border-radius: 999px; background: var(--workspace-rail); }",
        ".audit-lists li { margin: 3px 0; line-height: var(--audit-summary-note-line-height); }",
        "body.light .audit-lists > div[data-audit-list=\"evidenceGaps\"][data-audit-list-state=\"gap\"] { background: var(--evidence-gap); border-left-color: var(--audit-summary-gap-rail); }",
    )
    for guard in required_compliance_audit_summary_gap_hierarchy_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance audit summary gap hierarchy guard: {guard}")

    required_audit_summary_gap_state_guards = (
        "state: (normalized.gapTitles || []).length ? reviewSignalStates.gap : reviewSignalStates.ready",
        "data-audit-list=\"${escapeAttribute(section.key)}\"",
        "data-audit-list-state=\"${escapeAttribute(section.state || reviewSignalStates.ready)}\"",
    )
    for guard in required_audit_summary_gap_state_guards:
        if guard not in metadata_js:
            fail(f"metadata.js missing audit summary gap state guard: {guard}")

    required_compliance_resource_reference_aesthetic_refinement_contract = (
        "--reference-nav-gap",
        "--reference-nav-chip-padding",
        "--reference-nav-scroll-padding",
        ".sidebar-title { display: flex; align-items: center; gap: var(--reference-nav-gap); text-transform: uppercase; letter-spacing: 0; }",
        ".sidebar-title::before { content: \"\"; width: 7px; height: 7px; border-radius: 999px; background: var(--workspace-rail); }",
        ".sidebar nav a { padding: var(--reference-nav-chip-padding); }",
        ".sidebar details > summary { padding: var(--reference-nav-chip-padding); }",
        ".mobile-toc { min-height: var(--review-action-min-target); border-radius: 6px; padding: var(--reference-nav-chip-padding); }",
        ".mobile-toc { border-radius: 6px; padding: var(--reference-nav-chip-padding); }",
        ".topbar .topbar-scroll { gap: var(--reference-nav-gap); padding: var(--reference-nav-scroll-padding); }",
        ".topbar .chip { padding: var(--reference-nav-chip-padding); border-radius: 6px; }",
        "body.light .topbar { background: linear-gradient(90deg, var(--panel), var(--panel-2)); border-bottom-color: var(--workspace-hairline); }",
    )
    for guard in required_compliance_resource_reference_aesthetic_refinement_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance resource reference aesthetic refinement guard: {guard}")

    required_compliance_workspace_card_rhythm_aesthetic_contract = (
        "--card-rhythm-heading-gap",
        "--card-rhythm-meta-margin",
        "--card-rhythm-table-margin",
        "--card-rhythm-subheading-margin",
        ".card h2 { gap: var(--card-rhythm-heading-gap); line-height: 1.08; }",
        ".section-meta { margin: var(--card-rhythm-meta-margin); }",
        ".card > .table-wrap { margin: var(--card-rhythm-table-margin); }",
        ".card h4 { margin: var(--card-rhythm-subheading-margin); color: #f5e8c8; }",
        "body.light .card h4 { color: #31513e; }",
        ".card > p + .table-wrap, .card > ul + .table-wrap, .card > ol + .table-wrap { margin-top: 6px; }",
    )
    for guard in required_compliance_workspace_card_rhythm_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance workspace card rhythm aesthetic guard: {guard}")

    required_compliance_source_table_rhythm_aesthetic_contract = (
        "--source-table-rail",
        "--source-table-header-bg",
        "--source-table-first-col-width",
        "--source-table-first-col-min-width",
        "--source-table-row-gap-border",
        ".table-wrap { border-left-color: var(--source-table-rail); }",
        ".table-wrap thead { background: var(--source-table-header-bg); }",
        ".table-wrap th:first-child, .table-wrap td:first-child { width: var(--source-table-first-col-width); min-width: var(--source-table-first-col-min-width); }",
        ".table-wrap tbody tr + tr td, .table-wrap tbody tr + tr th { border-top: 1px solid var(--source-table-row-gap-border); }",
        ".table-wrap td:first-child { color: #f5e8c8; }",
        "body.light .table-wrap { border-left-color: var(--source-table-rail); }",
        "body.light .table-wrap thead { background: var(--source-table-header-bg); }",
        "body.light .table-wrap td:first-child { color: #31513e; }",
    )
    for guard in required_compliance_source_table_rhythm_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance source table rhythm aesthetic guard: {guard}")

    required_compliance_coverage_matrix_detail_aesthetic_contract = (
        "--coverage-matrix-caption-padding",
        "--coverage-matrix-caption-bg",
        "--coverage-matrix-label-width",
        "--coverage-matrix-value-width",
        "--coverage-matrix-note-line-height",
        "--coverage-matrix-row-border",
        ".coverage-table caption { padding: var(--coverage-matrix-caption-padding); background: var(--coverage-matrix-caption-bg); }",
        ".coverage-table tbody th { width: var(--coverage-matrix-label-width); }",
        ".coverage-table tbody td:nth-child(2) { width: var(--coverage-matrix-value-width); }",
        ".coverage-row td:last-child { line-height: var(--coverage-matrix-note-line-height); }",
        ".coverage-table tbody tr + tr th, .coverage-table tbody tr + tr td { border-top: 1px solid var(--coverage-matrix-row-border); }",
        ".coverage-row[data-coverage-state=\"gap\"] td:last-child { background: rgba(239,68,68,0.08); }",
        "body.light .coverage-row[data-coverage-state=\"gap\"] td:last-child { background: rgba(185,28,28,0.065); }",
    )
    for guard in required_compliance_coverage_matrix_detail_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance coverage matrix detail aesthetic guard: {guard}")

    required_compliance_audit_summary_metric_density_aesthetic_contract = (
        "--audit-metric-min-height",
        "--audit-metric-padding",
        "--audit-metric-value-size",
        "--audit-metric-label-size",
        "--audit-metric-value-line-height",
        "--status-quick-filter-padding",
        "--status-quick-filter-count-size",
        ".audit-metrics span { min-height: var(--audit-metric-min-height); padding: var(--audit-metric-padding); }",
        ".audit-metrics strong { font-size: var(--audit-metric-value-size); line-height: var(--audit-metric-value-line-height); }",
        ".audit-metrics span { font-size: var(--audit-metric-label-size); }",
        ".status-quick-filter { padding: var(--status-quick-filter-padding); }",
        ".status-quick-filter strong { font-size: var(--status-quick-filter-count-size); }",
        "body.light .audit-metrics span { background: rgba(49,81,62,0.035); }",
    )
    for guard in required_compliance_audit_summary_metric_density_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance audit summary metric density aesthetic guard: {guard}")

    required_compliance_review_state_control_aesthetic_contract = (
        "--review-state-control-gap",
        "--review-state-chip-min-height",
        "--review-state-chip-padding",
        "--review-state-note-padding",
        "--review-state-active-bg",
        "--review-state-note-line-height",
        ".active-filter-chips, .status-quick-filters { gap: var(--review-state-control-gap); }",
        ".active-filter-chip, .status-quick-filter { min-height: var(--review-state-chip-min-height); padding: var(--review-state-chip-padding); }",
        ".filter-state, .topbar .nav-filter-state { padding: var(--review-state-note-padding); line-height: var(--review-state-note-line-height); }",
        ".status-quick-filter.active, .active-filter-chip:hover, .active-filter-chip:focus-visible { background: var(--review-state-active-bg); }",
        "body.light .status-quick-filter.active, body.light .active-filter-chip:hover, body.light .active-filter-chip:focus-visible { background: var(--review-state-active-bg); }",
        ".empty-results, .nav-empty { line-height: var(--review-state-note-line-height); }",
    )
    for guard in required_compliance_review_state_control_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance review state control aesthetic guard: {guard}")

    required_compliance_empty_results_guidance_aesthetic_contract = (
        "--empty-guidance-padding",
        "--empty-guidance-radius",
        "--empty-guidance-line-height",
        "--empty-guidance-marker-size",
        "--empty-guidance-nav-padding",
        "--empty-guidance-clear-bg",
        ".empty-results { display: flex; align-items: flex-start; gap: 9px; padding: var(--empty-guidance-padding); border-radius: var(--empty-guidance-radius); line-height: var(--empty-guidance-line-height); }",
        ".empty-results[hidden] { display: none; }",
        ".empty-results::before { content: \"\"; flex: 0 0 auto; width: var(--empty-guidance-marker-size); height: var(--empty-guidance-marker-size); margin-top: 0.42em; border-radius: 999px; background: var(--empty-state-rail); }",
        ".nav-empty { padding: var(--empty-guidance-nav-padding); line-height: var(--empty-guidance-line-height); }",
        ".topbar .nav-empty { padding: var(--empty-guidance-nav-padding); }",
        ".clear-filters:not(:disabled) { background: var(--empty-guidance-clear-bg); }",
        "body.light .clear-filters:not(:disabled) { background: var(--empty-guidance-clear-bg); }",
    )
    for guard in required_compliance_empty_results_guidance_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance empty results guidance aesthetic guard: {guard}")

    required_compliance_filter_control_form_rhythm_aesthetic_contract = (
        "--filter-control-form-gap",
        "--filter-control-field-gap",
        "--filter-control-input-min-height",
        "--filter-control-input-padding",
        "--filter-control-search-min-width",
        "--filter-control-clear-padding",
        ".filter-controls { gap: var(--filter-control-form-gap); }",
        ".filter-field { gap: var(--filter-control-field-gap); }",
        ".filter-field:first-child { min-width: var(--filter-control-search-min-width); }",
        ".filter-field input, .filter-field select { min-height: var(--filter-control-input-min-height); padding: var(--filter-control-input-padding); }",
        ".clear-filters { min-height: var(--filter-control-input-min-height); padding: var(--filter-control-clear-padding); }",
        "@media (max-width: 760px) {\n  .filter-controls { gap: var(--filter-control-form-gap); }\n  .filter-field:first-child { min-width: 0; }\n  .clear-filters { min-height: 38px; }\n}",
    )
    for guard in required_compliance_filter_control_form_rhythm_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance filter control form rhythm aesthetic guard: {guard}")

    required_compliance_active_filter_chip_density_aesthetic_contract = (
        "--active-chip-density-gap",
        "--active-chip-row-margin",
        "--active-chip-padding",
        "--active-chip-clear-size",
        "--active-chip-max-width",
        "--active-chip-mobile-max-width",
        ".active-filter-chips { gap: var(--active-chip-density-gap); margin-top: var(--active-chip-row-margin); }",
        ".active-filter-chip { max-width: var(--active-chip-max-width); padding: var(--active-chip-padding); }",
        ".active-filter-chip-clear { width: var(--active-chip-clear-size); height: var(--active-chip-clear-size); }",
        ".status-quick-filters { gap: var(--active-chip-density-gap); margin-top: var(--active-chip-row-margin); }",
        "@media (max-width: 760px) {\n  .active-filter-chips, .status-quick-filters { gap: var(--active-chip-density-gap); }\n  .active-filter-chip { max-width: var(--active-chip-mobile-max-width); }\n}",
    )
    for guard in required_compliance_active_filter_chip_density_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance active filter chip density aesthetic guard: {guard}")

    required_compliance_review_summary_stack_rhythm_aesthetic_contract = (
        "--review-summary-stack-gap",
        "--review-summary-stack-margin",
        "--review-summary-stack-empty-margin",
        "--review-summary-stack-empty-gap",
        ".filter-state { margin-top: var(--review-summary-stack-margin); }",
        ".active-filter-chips, .status-quick-filters { margin-top: var(--review-summary-stack-gap); }",
        ".empty-results { margin-top: var(--review-summary-stack-empty-margin); }",
        ".empty-results { gap: var(--review-summary-stack-empty-gap); }",
        "@media (max-width: 760px) {\n  .filter-state, .empty-results { width: 100%; }\n}",
    )
    for guard in required_compliance_review_summary_stack_rhythm_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance review summary stack rhythm aesthetic guard: {guard}")

    required_compliance_sidebar_filter_context_rhythm_aesthetic_contract = (
        "--nav-context-link-gap",
        "--nav-context-state-margin",
        "--nav-context-empty-margin",
        "--nav-context-inline-margin",
        "--nav-context-mobile-margin",
        ".sidebar .nav-filter-state { display: inline-flex; align-items: center; min-height: 30px; padding: var(--review-state-note-padding); border-left: 3px solid var(--filtered-state-rail); border-radius: 6px; background: var(--filtered-state-note-bg); line-height: var(--review-state-note-line-height); }",
        ".nav-filter-state { margin: 0 0 var(--nav-context-state-margin); }",
        ".sidebar nav { display: grid; gap: var(--nav-context-link-gap); }",
        ".nav-empty { margin: var(--nav-context-empty-margin); }",
        ".topbar .nav-filter-state, .topbar .nav-empty { margin: 0 var(--nav-context-inline-margin); flex: 0 0 auto; }",
        ".mobile-toc { margin-top: var(--nav-context-mobile-margin); }",
    )
    for guard in required_compliance_sidebar_filter_context_rhythm_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance sidebar filter context rhythm aesthetic guard: {guard}")

    required_compliance_archive_review_continuity_aesthetic_contract = (
        "--archive-review-entry-gap",
        "--archive-review-meta-gap",
        "--archive-review-metric-min-height",
        "--archive-review-metric-padding",
        "--archive-review-tag-gap",
        "--archive-review-current-rail-width",
        ".archive-list { gap: var(--archive-review-entry-gap); }",
        ".archive-entry { gap: var(--archive-review-entry-gap); }",
        ".archive-entry-meta { gap: var(--archive-review-meta-gap); }",
        ".archive-entry.current { box-shadow: inset var(--archive-review-current-rail-width) 0 0 var(--workspace-rail), 0 10px 20px rgba(0,0,0,0.14); }",
        ".archive-review-metrics div { min-height: var(--archive-review-metric-min-height); padding: var(--archive-review-metric-padding); }",
        ".archive-tags { gap: var(--archive-review-tag-gap); }",
        "@media (max-width: 760px) {\n  .archive-entry-meta { gap: var(--archive-review-meta-gap); }\n  .archive-tags { gap: var(--archive-review-tag-gap); }\n}",
    )
    for guard in required_compliance_archive_review_continuity_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance archive review continuity aesthetic guard: {guard}")

    required_compliance_evidence_handoff_rhythm_aesthetic_contract = (
        "--evidence-handoff-table-margin",
        "--evidence-handoff-caption-gap",
        "--evidence-handoff-row-gap",
        "--evidence-handoff-gap-note-padding",
        "--evidence-handoff-gap-note-rail",
        ".card > .table-wrap { margin: var(--evidence-handoff-table-margin); }",
        ".coverage-table caption { gap: var(--evidence-handoff-caption-gap); }",
        ".coverage-table tbody tr + tr th, .coverage-table tbody tr + tr td { border-top: 1px solid var(--evidence-handoff-row-gap); }",
        ".coverage-row[data-coverage-state=\"gap\"] td:last-child { box-shadow: inset var(--evidence-handoff-gap-note-rail) 0 0 rgba(239,68,68,0.38); padding-inline-start: var(--evidence-handoff-gap-note-padding); }",
        "body.light .coverage-row[data-coverage-state=\"gap\"] td:last-child { box-shadow: inset var(--evidence-handoff-gap-note-rail) 0 0 rgba(185,28,28,0.28); }",
        "@media (max-width: 760px) {\n  .card > .table-wrap { margin: var(--evidence-handoff-table-margin); }\n  .coverage-row[data-coverage-state=\"gap\"] td:last-child { padding-inline-start: var(--evidence-handoff-gap-note-padding); }\n}",
    )
    for guard in required_compliance_evidence_handoff_rhythm_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance evidence handoff rhythm aesthetic guard: {guard}")

    required_compliance_review_filter_recovery_aesthetic_contract = (
        "--filter-recovery-state-margin",
        "--filter-recovery-control-gap",
        "--filter-recovery-empty-padding",
        "--filter-recovery-reset-min-width",
        "--filter-recovery-reset-border",
        "--filter-recovery-mobile-stack-gap",
        ".filter-state { margin-top: var(--filter-recovery-state-margin); }",
        ".active-filter-chips, .status-quick-filters { gap: var(--filter-recovery-control-gap); }",
        ".empty-results { padding: var(--filter-recovery-empty-padding); gap: var(--filter-recovery-control-gap); }",
        ".clear-filters:not(:disabled) { min-width: var(--filter-recovery-reset-min-width); border-color: var(--filter-recovery-reset-border); }",
        "body.light .clear-filters:not(:disabled) { border-color: var(--filter-recovery-reset-border); }",
        "@media (max-width: 760px) {\n  .active-filter-chips, .status-quick-filters, .empty-results { gap: var(--filter-recovery-mobile-stack-gap); }\n  .clear-filters:not(:disabled) { min-width: 0; }\n}",
    )
    for guard in required_compliance_review_filter_recovery_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance review filter recovery aesthetic guard: {guard}")

    required_compliance_workspace_section_trail_aesthetic_contract = (
        "--section-trail-active-rail-width",
        "--section-trail-active-bg",
        "--section-trail-action-gap",
        "--section-trail-heading-action-bg",
        "--section-trail-fab-size",
        "--section-trail-fab-rail",
        ".sidebar nav a.active, .topbar .chip.active { box-shadow: inset var(--section-trail-active-rail-width) 0 0 var(--workspace-rail); background: var(--section-trail-active-bg); }",
        ".heading-actions { gap: var(--section-trail-action-gap); }",
        ".copy-link, .collapse-toggle, .focus-toggle { background: var(--section-trail-heading-action-bg); }",
        ".nav-fab { width: var(--section-trail-fab-size); height: var(--section-trail-fab-size); border-color: var(--section-trail-fab-rail); }",
        "body.light .nav-fab { border-color: var(--section-trail-fab-rail); }",
        ".topbar .chip.active { background: var(--section-trail-active-bg); border-color: rgba(197, 138, 53, 0.3); }",
        "@media (max-width: 900px) { .topbar .chip.active { box-shadow: inset 0 calc(-1 * var(--section-trail-active-rail-width)) 0 var(--workspace-rail); } }",
    )
    for guard in required_compliance_workspace_section_trail_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance workspace section trail aesthetic guard: {guard}")

    required_compliance_workspace_masthead_density_aesthetic_contract = (
        "--masthead-title-size",
        "--masthead-title-line-height",
        "--masthead-mobile-title-size",
        "--masthead-meta-margin",
        "--masthead-controls-margin",
        "--masthead-theme-min-height",
        ".app-header { padding: var(--masthead-header-padding); }",
        ".app-header .container { gap: var(--masthead-grid-gap); }",
        ".app-header .title { max-width: var(--masthead-title-width); font-size: var(--masthead-title-size); line-height: var(--masthead-title-line-height); }",
        ".app-header .subtitle { margin: var(--masthead-meta-margin); line-height: var(--masthead-meta-line-height); }",
        ".theme-toggle { min-height: var(--masthead-theme-min-height); padding: var(--masthead-theme-padding); }",
        ".controls { margin-top: var(--masthead-controls-margin); }",
        ".app-header .title { font-size: var(--masthead-mobile-title-size); line-height: var(--masthead-mobile-title-line-height); }",
        ".theme-toggle { min-height: var(--masthead-theme-min-height); }",
    )
    for guard in required_compliance_workspace_masthead_density_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance workspace masthead density aesthetic guard: {guard}")

    required_compliance_workspace_overview_cadence_aesthetic_contract = (
        "--overview-cadence-section-gap",
        "--overview-cadence-panel-gap",
        "--overview-cadence-heading-gap",
        "--overview-cadence-copy-line-height",
        "--overview-cadence-action-gap",
        "--overview-cadence-mobile-section-gap",
        ".workspace-overview { margin-top: var(--overview-cadence-section-gap); }",
        ".archive-digest, .audit-summary { margin-top: var(--overview-cadence-section-gap); }",
        ".workspace-overview-card, .archive-card, .audit-summary-card { gap: var(--overview-cadence-panel-gap); }",
        ".workspace-heading-block { gap: var(--overview-cadence-heading-gap); }",
        ".workspace-copy, .archive-summary, .audit-summary-copy { line-height: var(--overview-cadence-copy-line-height); }",
        ".workspace-actions { gap: var(--overview-cadence-action-gap); }",
        "@media (max-width: 760px) {\n  .workspace-overview, .archive-digest, .audit-summary { margin-top: var(--overview-cadence-mobile-section-gap); }\n}",
    )
    for guard in required_compliance_workspace_overview_cadence_aesthetic_contract:
        if guard not in style_css:
            fail(f"style.css missing compliance workspace overview cadence aesthetic guard: {guard}")

    required_archive_guards = (
        "window.GRCInsightArchive",
        "currentReportId",
        "buildReports",
        "buildReviewMetrics",
        "setReviewSignalStates",
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
        "renderArchiveDigest(md, fullSections)",
        "archiveDigest.setReviewSignalStates(sectionMetadata.reviewSignalStates)",
        "const reviewSignalStates = sectionMetadata && sectionMetadata.reviewSignalStates",
        "row.state || reviewSignalStates.ready || 'ready'",
        "archiveDigest.buildReports(markdown || '',",
        "const provenanceSummary = sectionMetadata && sectionMetadata.buildProvenanceSummary",
        "provenanceSummary,",
        "tagCategories: Array.from(tagCategorySet)",
        "archive-card",
        "archive-entry${isCurrent ? ' current' : ''}",
        "archive-review-metrics",
        "report.reviewMetrics",
        "sanitizeMarkdownUrl(report.href || '#')",
        "escapeAttribute(report.generatedAt || '')",
    )
    for guard in required_archive_ui:
        if guard not in html + app_js:
            fail(f"site missing archive digest UI guard: {guard}")

    if ".archive-entry.current" not in style_css:
        fail("style.css missing archive current-entry styling")

    required_archive_metric_styles = (
        'body.light .archive-review-metrics [data-review-metric-state="attention"] dd',
        'body.light .archive-review-metrics [data-review-metric-state="gap"] dd',
    )
    for guard in required_archive_metric_styles:
        if guard not in style_css:
            fail(f"style.css missing archive metric state styling: {guard}")

    required_audit_summary_ui = (
        "workspaceOverview",
        "updateWorkspaceOverview",
        "auditSummary",
        "installAuditSummary",
        "updateAuditSummary",
        "updateWorkspaceOverview(Array.from(matches))",
        "updateAuditSummary(Array.from(matches))",
        "function sectionHeadingTitle(heading)",
        "clone.querySelectorAll('.anchor-link, .heading-actions').forEach(node => node.remove())",
        "escapeHtml(sectionHeadingTitle(h))",
        "escapeHtml(b.title)",
        "summarizeSections",
        "renderWorkspaceOverview",
        "renderAuditSummary",
        "data-obligations",
        "workspace-overview-card",
        "coverage-table",
        "coverage-row",
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

    if "childNodes[0]" in app_js:
        fail("app.js reads partial heading text instead of the section heading title helper")

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
