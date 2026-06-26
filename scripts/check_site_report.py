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
