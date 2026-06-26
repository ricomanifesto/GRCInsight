#!/usr/bin/env python3
"""Exercise generated-site renderer helpers without a browser."""

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDERER_JS = REPO_ROOT / "site" / "static" / "renderer.js"
TAGS_JS = REPO_ROOT / "site" / "static" / "tags.js"
METADATA_JS = REPO_ROOT / "site" / "static" / "metadata.js"
FILTERS_JS = REPO_ROOT / "site" / "static" / "filters.js"
ARCHIVE_JS = REPO_ROOT / "site" / "static" / "archive.js"


def fail(message: str) -> None:
    raise SystemExit(f"site renderer check failed: {message}")


def main() -> None:
    if not RENDERER_JS.exists():
        fail("missing site/static/renderer.js")
    if not TAGS_JS.exists():
        fail("missing site/static/tags.js")
    if not METADATA_JS.exists():
        fail("missing site/static/metadata.js")
    if not FILTERS_JS.exists():
        fail("missing site/static/filters.js")
    if not ARCHIVE_JS.exists():
        fail("missing site/static/archive.js")

    script = f"""
const fs = require('fs');
const vm = require('vm');
const rendererSource = fs.readFileSync({json.dumps(str(RENDERER_JS))}, 'utf8');
const tagsSource = fs.readFileSync({json.dumps(str(TAGS_JS))}, 'utf8');
const metadataSource = fs.readFileSync({json.dumps(str(METADATA_JS))}, 'utf8');
const filtersSource = fs.readFileSync({json.dumps(str(FILTERS_JS))}, 'utf8');
const archiveSource = fs.readFileSync({json.dumps(str(ARCHIVE_JS))}, 'utf8');
const context = {{ URLSearchParams, window: {{}} }};
vm.createContext(context);
vm.runInContext(rendererSource, context, {{ filename: 'renderer.js' }});
vm.runInContext(tagsSource, context, {{ filename: 'tags.js' }});
vm.runInContext(metadataSource, context, {{ filename: 'metadata.js' }});
vm.runInContext(filtersSource, context, {{ filename: 'filters.js' }});
vm.runInContext(archiveSource, context, {{ filename: 'archive.js' }});
const renderer = context.window.GRCInsightRenderer;
const tags = context.window.GRCInsightTags;
const metadata = context.window.GRCInsightMetadata;
const filters = context.window.GRCInsightFilters;
const archive = context.window.GRCInsightArchive;
function assert(condition, message) {{
  if (!condition) throw new Error(message);
}}
assert(renderer, 'renderer object is not exported');
assert(tags, 'tag catalog is not exported');
assert(metadata, 'section metadata helpers are not exported');
assert(filters, 'section filter helpers are not exported');
assert(archive, 'archive digest data is not exported');
assert(archive.currentReportId === 'current', 'archive should keep the current report as default');
assert(typeof archive.buildReports === 'function', 'archive should build reports from markdown');
assert(typeof archive.deriveCurrentReportMetadata === 'function', 'archive should derive current metadata from markdown');
assert(typeof filters.parseFilterParams === 'function', 'filters should parse URL filter params');
assert(typeof filters.buildFilterParams === 'function', 'filters should build URL filter params');
assert(typeof filters.defaultFilterState === 'function', 'filters should build canonical default filter state');
assert(typeof filters.isDefaultFilterState === 'function', 'filters should detect canonical default filter state');
assert(typeof filters.filterParamEntries === 'function', 'filters should expose canonical URL param entries');
assert(typeof filters.nonDefaultFilterEntries === 'function', 'filters should expose canonical non-default filter entries');
assert(typeof filters.normalizeFilterValue === 'function', 'filters should normalize canonical active filter values');
assert(typeof filters.normalizeFilterState === 'function', 'filters should normalize canonical active filter state');
assert(Array.isArray(filters.filterStateOptions), 'filters should expose canonical filter state options');
assert(filters.filterStateOptionMap && typeof filters.filterStateOptionMap === 'object', 'filters should expose canonical filter state option lookup map');
assert(filters.filterStateOptions.map(option => option.key).join('|') === 'query|reviewStatus|tagCategory|ownerCue|evidenceState', 'filter state options should use stable keys');
assert(filters.filterStateOptions.map(option => option.param).join('|') === 'q|status|tag|owner|evidence', 'filter state options should use stable URL params');
assert(filters.filterStateOptions.map(option => option.defaultValue).join('|') === '|all|all|all|all', 'filter state options should use stable defaults');
assert(filters.filterStateOptions.map(option => option.labelPrefix).join('|') === 'Search|Status|Tag|Owner cues|Evidence', 'filter state options should use stable labels');
assert(filters.filterStateOptionMap.query.param === 'q', 'filter state option lookup should expose query params by key');
assert(filters.filterStateOptionMap.reviewStatus.defaultValue === 'all', 'filter state option lookup should expose defaults by key');
assert(typeof filters.statusQuickFilterCounts === 'function', 'filters should expose context-aware status quick-filter counts');
assert(typeof filters.summarizeFilterResults === 'function', 'filters should summarize active filter results');
assert(typeof filters.activeFilterEntries === 'function', 'filters should expose active filter entries for UI chips');
assert(typeof filters.activeFilterLabels === 'function', 'filters should expose active filter labels for summaries and UI chips');
assert(typeof metadata.buildProvenanceSummary === 'function', 'metadata should expose canonical provenance summaries');
assert(Array.isArray(metadata.reviewStatusOptions), 'metadata should expose canonical review status options');
assert(metadata.reviewStatusOptions.map(option => option.value).join('|') === 'Action required|Review ready|Needs review', 'review status options should use stable values');
assert(metadata.reviewStatusOptions.map(option => option.label).join('|') === 'Action|Ready|Needs review', 'review status options should use stable short labels');
assert(typeof filters.setReviewStatusOptions === 'function', 'filters should accept canonical review status options');
filters.setReviewStatusOptions(metadata.reviewStatusOptions);
assert(filters.allowedReviewStatusValues().join('|') === 'all|Action required|Review ready|Needs review', 'filters should expose canonical review status values');
assert(metadata.metadataStates, 'metadata should expose canonical metadata states');
assert(metadata.metadataStates.detection.detected === 'Detected', 'detection state should expose detected value');
assert(metadata.metadataStates.detection.notDetected === 'Not detected', 'detection state should expose not-detected value');
assert(metadata.metadataStates.evidence.sourceReferenced === 'Source referenced', 'evidence state should expose source-referenced value');
assert(metadata.metadataStates.evidence.needsSourceTrail === 'Needs source trail', 'evidence state should expose needs-source-trail value');
assert(typeof filters.setMetadataStates === 'function', 'filters should accept canonical metadata states');
filters.setMetadataStates(metadata.metadataStates);
assert(filters.evidenceStateValues().join('|') === 'all|referenced|missing', 'filters should expose stable evidence query values');
assert(metadata.reviewSignalStates, 'metadata should expose canonical review signal states');
assert(metadata.reviewSignalStates.ready === 'ready', 'review signal states should expose ready');
assert(metadata.reviewSignalStates.gap === 'gap', 'review signal states should expose gap');
assert(metadata.reviewSignalStates.empty === 'empty', 'review signal states should expose empty');
assert(metadata.reviewSignalStates.attention === 'attention', 'review signal states should expose attention');
assert(typeof metadata.coverageMetricEntries === 'function', 'metadata should expose canonical coverage metric entries');
assert(typeof metadata.renderCoverageTableRows === 'function', 'metadata should expose canonical coverage table row renderer');
assert(typeof metadata.auditSummaryMetricEntries === 'function', 'metadata should expose canonical audit summary metric entries');
assert(typeof metadata.auditSummaryListSections === 'function', 'metadata should expose canonical audit summary list sections');
assert(typeof metadata.auditSummaryReadiness === 'function', 'metadata should expose canonical audit summary readiness projection');
assert(typeof metadata.workspaceActionEntries === 'function', 'metadata should expose canonical workspace action entries');
assert(typeof archive.setReviewSignalStates === 'function', 'archive should accept canonical review signal states');
archive.setReviewSignalStates(metadata.reviewSignalStates);
const archiveMarkdown = `# GRC Intelligence Report - 2026-06-23
**Generated:** 2026-06-23T12:00:00Z

| **Field** | **Detail** |
|---|---|
| **Report Period** | Q3 2026 |
`;
const derivedReport = archive.deriveCurrentReportMetadata(archiveMarkdown);
assert(derivedReport.title === 'GRC Intelligence Report - 2026-06-23', 'archive should derive title from index markdown');
assert(derivedReport.generatedAt === '2026-06-23T12:00:00Z', 'archive should derive generatedAt from index markdown');
assert(derivedReport.period === 'Q3 2026', 'archive should derive report period from index markdown');
const archiveReports = archive.buildReports(archiveMarkdown);
assert(Array.isArray(archiveReports) && archiveReports.length >= 1, 'archive should expose at least one report entry');
const currentReport = archiveReports.find(report => report.id === archive.currentReportId);
assert(currentReport, 'archive should include the current report entry');
assert(currentReport.href === 'index.html', 'current report should keep index.html as the default route');
assert(currentReport.status === 'Current', 'current report should be marked current');
assert(currentReport.generatedAt === '2026-06-23T12:00:00Z', 'current report should use generated markdown timestamp');
assert(currentReport.period === 'Q3 2026', 'current report should use generated markdown period');
assert(Array.isArray(currentReport.highlights) && currentReport.highlights.length >= 2, 'current report should expose digest highlights');
assert(Array.isArray(currentReport.tags) && currentReport.tags.includes('GRC'), 'current report should expose digest tags');
const archiveReviewReports = archive.buildReports(archiveMarkdown, {{
  summary: {{
    totalSections: 4,
    actionRequired: 2,
  }},
  provenanceSummary: {{ value: '3/4', state: 'gap', sourceGaps: 1 }},
  tagCategories: ['framework', 'control', 'risk'],
}});
const archiveReviewMetrics = archiveReviewReports[0].reviewMetrics;
assert(Array.isArray(archiveReviewMetrics) && archiveReviewMetrics.length === 5, 'archive entry should expose review metrics when context is available');
assert(archiveReviewMetrics.map(row => row.label).join('|') === 'Sections|Action required|Evidence ready|Source-trail gaps|Tag categories', 'archive review metrics should use stable labels');
assert(archiveReviewMetrics[0].value === '4', 'archive review metrics should expose section count');
assert(archiveReviewMetrics[2].value === '3/4', 'archive review metrics should expose evidence readiness coverage');
assert(archiveReviewMetrics[3].state === 'gap', 'archive review metrics should flag source-trail gaps');
assert(archiveReviewMetrics[4].value === '3', 'archive review metrics should count unique tag categories');
const summaryOnlyArchiveReports = archive.buildReports(archiveMarkdown, {{
  summary: {{
    totalSections: 4,
    actionRequired: 2,
    evidenceReady: 3,
    evidenceGaps: 1,
  }},
}});
const summaryOnlyArchiveMetrics = summaryOnlyArchiveReports[0].reviewMetrics;
assert(summaryOnlyArchiveMetrics[2].value === '3/4', 'archive metrics should preserve summary-only evidence readiness');
assert(summaryOnlyArchiveMetrics[2].state === 'gap', 'archive metrics should preserve summary-only evidence gap state');
assert(summaryOnlyArchiveMetrics[3].value === '1', 'archive metrics should preserve summary-only source gap count');
assert(summaryOnlyArchiveMetrics[3].state === 'gap', 'archive metrics should preserve summary-only source gap state');
assert(renderer.sanitizeMarkdownUrl('https://example.com/a') === 'https://example.com/a', 'https links should be allowed');
assert(renderer.sanitizeMarkdownUrl('/reports/current') === '/reports/current', 'root-relative links should be allowed');
assert(renderer.sanitizeMarkdownUrl('controls/nist') === 'controls/nist', 'relative links should be allowed');
assert(renderer.sanitizeMarkdownUrl('#summary') === '#summary', 'hash links should be allowed');
assert(renderer.sanitizeMarkdownUrl('javascript:alert(1)') === null, 'javascript links should be blocked');
assert(renderer.sanitizeMarkdownUrl('data:text/html,test') === null, 'data links should be blocked');
assert(renderer.sanitizeMarkdownUrl('https://example.com/"bad') === null, 'quote-bearing links should be blocked');
assert(renderer.renderMarkdownLink('Safe', 'https://example.com') === '<a href="https://example.com" target="_blank" rel="noopener">Safe</a>', 'safe link should render as anchor');
assert(renderer.renderMarkdownLink('Unsafe', 'javascript:alert(1)') === 'Unsafe', 'unsafe link should render as text');
const frameworks = tags.categories.find(category => category.key === 'frameworks');
const regulations = tags.categories.find(category => category.key === 'regulations');
const risks = tags.categories.find(category => category.key === 'risks');
const controls = tags.categories.find(category => category.key === 'controls');
const agencies = tags.categories.find(category => category.key === 'agencies');
assert(frameworks && frameworks.terms.includes('NIST') && frameworks.pillClass === 'framework', 'framework tag category should render framework pills');
assert(regulations && regulations.terms.includes('GDPR') && regulations.pillClass === 'regulation', 'regulation tag category should render regulation pills');
assert(risks && risks.terms.includes('Ransomware') && risks.pillClass === 'risk', 'risk tag category should render risk pills');
assert(controls && controls.terms.includes('Access Control') && controls.pillClass === 'control', 'control tag category should render control pills');
assert(agencies && agencies.terms.includes('SEC') && agencies.pillClass === 'agency', 'agency tag category should render agency pills');
const actionMetadata = metadata.deriveSectionMetadata('Recommendations for Action', 'P0 CRITICAL Conduct gap assessment within 30 days before next QSA assessment Owner CISO Framework PCI-DSS v4.0.1');
assert(actionMetadata.reviewStatus === 'Action required', 'action sections should be marked action required');
assert(actionMetadata.obligations === 'Detected', 'action sections should detect obligations');
assert(actionMetadata.deadlines === 'Detected', 'deadline language should be detected');
assert(actionMetadata.evidence === 'Needs source trail', 'sections without source language should flag source trail gaps');
assert(actionMetadata.owners === 'Detected', 'owner language should be detected');
const sourceMetadata = metadata.deriveSectionMetadata('Executive Summary', 'Source Multi-Source OSINT Articles Analyzed 30 of 30');
assert(sourceMetadata.reviewStatus === 'Review ready', 'source-backed sections should be review ready');
assert(sourceMetadata.evidence === 'Source referenced', 'source-backed sections should detect evidence');
const obligationOnlyMetadata = metadata.deriveSectionMetadata('Control Update', 'Source evidence shows PCI requires implementation of encryption controls.');
assert(obligationOnlyMetadata.reviewStatus === 'Action required', 'obligation-only sections should still need action');
assert(obligationOnlyMetadata.gaps === 'Not detected', 'obligation-only sections should not detect gaps');
assert(obligationOnlyMetadata.deadlines === 'Not detected', 'obligation-only sections should not detect deadlines');
const emptyMetadata = metadata.deriveSectionMetadata('Overview', '');
assert(emptyMetadata.reviewStatus === 'Needs review', 'empty sections should default to needs review');
assert(emptyMetadata.owners === 'Not detected', 'empty sections should not detect owners');
const genericDomainMetadata = metadata.deriveSectionMetadata('Compliance Overview', 'Board and legal teams review general GRC risk themes.');
assert(genericDomainMetadata.owners === 'Not detected', 'generic domain terms should not count as owner cues');
assert(metadata.renderSectionMetadata(emptyMetadata).includes('data-review-status="Needs review"'), 'metadata renderer should expose review status');
assert(metadata.renderSectionMetadata(actionMetadata).includes('data-owners="Detected"'), 'metadata renderer should expose owner cue state');
const auditSummary = metadata.summarizeSections([
  {{ title: 'PCI remediation', metadata: actionMetadata }},
  {{ title: 'Evidence backed overview', metadata: sourceMetadata }},
  {{ title: 'Unmapped overview', metadata: emptyMetadata }},
]);
assert(auditSummary.totalSections === 3, 'audit summary should count sections');
assert(auditSummary.actionRequired === 1, 'audit summary should count action-required sections');
assert(auditSummary.reviewReady === 1, 'audit summary should count review-ready sections');
assert(auditSummary.needsReview === 1, 'audit summary should count needs-review sections');
assert(auditSummary.obligations === 1, 'audit summary should count detected obligations');
assert(auditSummary.deadlines === 1, 'audit summary should count detected deadlines');
assert(auditSummary.owners === 1, 'audit summary should count detected owner cues');
assert(auditSummary.evidenceGaps === 2, 'audit summary should count sections needing source trails');
assert(auditSummary.auditReady === false, 'audit summary should not be audit-ready when gaps remain');
assert(auditSummary.evidenceTitles.includes('Evidence backed overview'), 'audit summary should name source-backed sections');
assert(auditSummary.gapTitles.includes('PCI remediation') && auditSummary.gapTitles.includes('Unmapped overview'), 'audit summary should name source-trail gaps');
assert(auditSummary.ownerTitles.includes('PCI remediation'), 'audit summary should name sections with owner cues');
const auditMetrics = metadata.auditSummaryMetricEntries(auditSummary);
assert(Array.isArray(auditMetrics) && auditMetrics.length === 6, 'audit summary metrics should expose compact audit counts');
assert(auditMetrics.map(row => row.key).join('|') === 'actionRequired|obligations|gaps|deadlines|owners|evidenceGaps', 'audit summary metrics should use stable keys');
assert(auditMetrics.map(row => row.label).join('|') === 'action required|obligations|gaps|deadlines|owner cues|source-trail gaps', 'audit summary metrics should use stable labels');
assert(auditMetrics.map(row => row.value).join('|') === '1|1|1|1|1|2', 'audit summary metrics should project summary counts in order');
const auditListSections = metadata.auditSummaryListSections(auditSummary);
assert(Array.isArray(auditListSections) && auditListSections.length === 4, 'audit summary list sections should expose compact list groups');
assert(auditListSections.map(row => row.key).join('|') === 'actionFocus|evidenceTrail|ownerCues|evidenceGaps', 'audit summary list sections should use stable keys');
assert(auditListSections.map(row => row.heading).join('|') === 'Action focus|Evidence trail|Owner cues|Evidence gaps', 'audit summary list sections should use stable headings');
assert(auditListSections[0].items.join('|') === 'PCI remediation', 'action focus list should project action titles');
assert(auditListSections[1].items.join('|') === 'Evidence backed overview', 'evidence trail list should project evidence-backed titles');
assert(auditListSections[2].items.join('|') === 'PCI remediation', 'owner cues list should project owner titles');
assert(auditListSections[3].items.join('|') === 'PCI remediation|Unmapped overview', 'evidence gaps list should project source gap titles');
const needsReadiness = metadata.auditSummaryReadiness(auditSummary);
assert(needsReadiness.state === 'gap', 'readiness projection should flag source-trail gaps with canonical gap state');
assert(needsReadiness.workspaceHeading === 'Compliance review workspace', 'readiness projection should expose review workspace heading');
assert(needsReadiness.auditHeading === 'Needs source trail', 'readiness projection should expose source-trail audit heading');
const workspaceActions = metadata.workspaceActionEntries();
assert(Array.isArray(workspaceActions) && workspaceActions.length === 3, 'workspace action entries should expose compact action links');
assert(workspaceActions.map(row => row.key).join('|') === 'auditSummary|generatedSections|sectionIndex', 'workspace action entries should use stable keys');
assert(workspaceActions.map(row => row.label).join('|') === 'Audit summary|Generated sections|Section index', 'workspace action entries should use stable labels');
assert(workspaceActions.map(row => row.href).join('|') === '#auditSummary|#report|#toc', 'workspace action entries should use stable anchors');
const coverageMetrics = metadata.coverageMetricEntries(auditSummary);
assert(Array.isArray(coverageMetrics) && coverageMetrics.length === 5, 'coverage metrics should expose generated section coverage');
assert(coverageMetrics.map(row => row.key).join('|') === 'generatedSections|sourceProvenance|obligations|ownershipCues|gapsAndDeadlines', 'coverage metrics should use stable keys');
assert(coverageMetrics.map(row => row.label).join('|') === 'Generated sections|Source provenance|Obligations|Ownership cues|Gaps and deadlines', 'coverage metrics should use stable labels');
assert(coverageMetrics[0].value === '3', 'coverage metrics should expose generated section count');
assert(coverageMetrics[1].value === '1/3', 'source provenance metric should expose source-ready coverage');
assert(coverageMetrics[1].state === 'gap', 'source provenance metric should flag missing source trails');
const coverageRows = metadata.coverageRows(auditSummary);
assert(JSON.stringify(coverageRows) === JSON.stringify(coverageMetrics), 'coverage rows should remain a compatibility alias for coverage metrics');
const coverageTableRows = metadata.renderCoverageTableRows(auditSummary);
assert(coverageTableRows.includes('data-coverage-state="ready"'), 'coverage table rows should render ready state');
assert(coverageTableRows.includes('data-coverage-state="gap"'), 'coverage table rows should render gap state');
assert(coverageTableRows.includes('<th scope="row">Generated sections</th>'), 'coverage table rows should render metric labels');
assert(coverageTableRows.includes('<td><strong>3</strong></td>'), 'coverage table rows should render metric values');
assert(coverageTableRows.includes('Rendered report sections available for review.'), 'coverage table rows should render metric notes');
const provenanceSummary = metadata.buildProvenanceSummary(auditSummary);
assert(provenanceSummary.totalSections === 3, 'provenance summary should expose total section count');
assert(provenanceSummary.sourceReady === 1, 'provenance summary should expose source-ready section count');
assert(provenanceSummary.sourceGaps === 2, 'provenance summary should expose source-gap count');
assert(provenanceSummary.value === '1/3', 'provenance summary should expose coverage value');
assert(provenanceSummary.state === 'gap', 'provenance summary should flag source gaps');
assert(provenanceSummary.note === '2 sections still need source trails.', 'provenance summary should expose gap note');
assert(metadata.renderWorkspaceOverview(auditSummary).includes('workspace-overview-card'), 'workspace overview renderer should produce a workspace card');
assert(metadata.renderWorkspaceOverview(auditSummary).includes('coverage-table'), 'workspace overview should expose the coverage matrix');
assert(metadata.renderWorkspaceOverview(auditSummary).includes('Source provenance'), 'workspace overview should name source provenance coverage');
assert(metadata.renderWorkspaceOverview(auditSummary).includes('aria-label="Workspace actions"'), 'workspace overview should render the action row');
assert(metadata.renderWorkspaceOverview(auditSummary).includes('href="#auditSummary"'), 'workspace overview should render audit summary action link');
assert(metadata.renderWorkspaceOverview(auditSummary).includes('href="#report"'), 'workspace overview should render generated sections action link');
assert(metadata.renderWorkspaceOverview(auditSummary).includes('href="#toc"'), 'workspace overview should render section index action link');
assert(metadata.renderAuditSummary(auditSummary).includes('audit-summary-card'), 'audit summary renderer should produce a summary card');
assert(metadata.renderAuditSummary(auditSummary).includes('Needs source trail'), 'audit summary renderer should expose missing evidence state');
assert(metadata.renderAuditSummary(auditSummary).includes('Evidence trail'), 'audit summary renderer should expose evidence trail list');
assert(metadata.renderAuditSummary(auditSummary).includes('Evidence backed overview'), 'audit summary renderer should list source-backed sections');
assert(metadata.renderAuditSummary(auditSummary).includes('Owner cues'), 'audit summary renderer should expose owner cue list');
assert(metadata.renderAuditSummary(auditSummary).includes('PCI remediation'), 'audit summary renderer should list sections with owner cues');
const filteredAuditSummary = metadata.summarizeSections([
  {{ title: 'Evidence backed overview', metadata: sourceMetadata }},
]);
assert(filteredAuditSummary.totalSections === 1, 'filtered audit summary should count only matched sections');
assert(filteredAuditSummary.actionRequired === 0, 'filtered audit summary should not retain full-report action counts');
assert(filteredAuditSummary.reviewReady === 1, 'filtered audit summary should count matched review-ready sections');
assert(filteredAuditSummary.evidenceGaps === 0, 'filtered audit summary should not retain hidden source-trail gaps');
assert(filteredAuditSummary.auditReady === true, 'filtered audit summary should evaluate readiness from matched sections');
const readyReadiness = metadata.auditSummaryReadiness(filteredAuditSummary);
assert(readyReadiness.state === 'ready', 'readiness projection should flag audit-ready summaries');
assert(readyReadiness.workspaceHeading === 'Audit-ready visible set', 'readiness projection should expose ready workspace heading');
assert(readyReadiness.auditHeading === 'Audit-ready', 'readiness projection should expose ready audit heading');
const completeProvenanceSummary = metadata.buildProvenanceSummary(filteredAuditSummary);
assert(completeProvenanceSummary.value === '1/1', 'complete provenance summary should expose full coverage');
assert(completeProvenanceSummary.state === 'ready', 'complete provenance summary should be ready');
assert(completeProvenanceSummary.note === 'Every visible section includes source evidence language.', 'complete provenance summary should expose complete note');
assert(metadata.renderAuditSummary(filteredAuditSummary).includes('1 sections reviewed'), 'filtered audit summary renderer should expose matched section count');
const emptyFilteredAuditSummary = metadata.summarizeSections([]);
assert(emptyFilteredAuditSummary.totalSections === 0, 'empty filtered audit summary should count zero sections');
assert(emptyFilteredAuditSummary.auditReady === false, 'empty filtered audit summary should not be audit-ready');
const emptyReadiness = metadata.auditSummaryReadiness(emptyFilteredAuditSummary);
assert(emptyReadiness.state === 'empty', 'readiness projection should flag empty summaries');
assert(emptyReadiness.workspaceHeading === 'No generated sections match the active filters', 'readiness projection should expose empty workspace heading');
assert(emptyReadiness.auditHeading === 'Needs source trail', 'readiness projection should keep empty audit heading explicit');
assert(metadata.auditSummaryMetricEntries(emptyFilteredAuditSummary).map(row => row.value).join('|') === '0|0|0|0|0|0', 'empty audit summary metrics should preserve zero counts');
const emptyAuditListSections = metadata.auditSummaryListSections(emptyFilteredAuditSummary);
assert(emptyAuditListSections.every(section => section.items.length === 0), 'empty audit summary list sections should preserve empty item lists');
assert(emptyAuditListSections.map(section => section.emptyText).join('|') === 'No action-required sections detected|No source-backed sections detected|No owner cues detected|No missing source trails detected', 'empty audit summary list sections should expose stable empty text');
assert(metadata.coverageMetricEntries(emptyFilteredAuditSummary)[0].value === '0', 'empty coverage metrics should preserve zero generated sections');
const emptyCoverageMetrics = metadata.coverageMetricEntries(emptyFilteredAuditSummary);
assert(emptyCoverageMetrics.every(row => row.state === 'empty'), 'empty coverage metrics should use empty states');
assert(emptyCoverageMetrics[1].value === 'No data', 'empty source provenance metric should not expose 0/0 coverage');
assert(emptyCoverageMetrics[1].note === 'No generated sections available for provenance review.', 'empty source provenance metric should avoid complete-coverage wording');
const emptyProvenanceSummary = metadata.buildProvenanceSummary(emptyFilteredAuditSummary);
assert(emptyProvenanceSummary.value === 'No data', 'empty provenance summary should not expose 0/0 coverage');
assert(emptyProvenanceSummary.state === 'empty', 'empty provenance summary should use empty state');
assert(emptyProvenanceSummary.note === 'No generated sections available for provenance review.', 'empty provenance summary should avoid complete-coverage wording');
assert(metadata.renderWorkspaceOverview(emptyFilteredAuditSummary).includes('No generated sections match the active filters'), 'empty workspace overview should expose empty filtered state');
assert(!metadata.renderWorkspaceOverview(emptyFilteredAuditSummary).includes('Every visible section includes source evidence language'), 'empty workspace overview should not claim complete provenance coverage');
assert(metadata.renderAuditSummary(emptyFilteredAuditSummary).includes('0 sections reviewed'), 'empty filtered audit summary renderer should expose zero matched sections');
const obligationOnlySummary = metadata.summarizeSections([
  {{ title: 'Obligation only', metadata: obligationOnlyMetadata }},
]);
const obligationOnlyRows = metadata.coverageMetricEntries(obligationOnlySummary);
assert(obligationOnlySummary.actionRequired === 1, 'obligation-only summary should retain action-required count');
assert(obligationOnlyRows[4].value === '0', 'gap/deadline row should not count generic action-required signals');
assert(obligationOnlyRows[4].state === 'ready', 'gap/deadline row should stay ready when only obligation/action wording is present');
assert(obligationOnlyRows[4].note === 'No gap or deadline signals detected in visible sections.', 'gap/deadline row should match its zero value');
const sections = [
  {{
    id: 'gdpr-obligations',
    title: 'GDPR Obligations',
    text: 'GDPR requires evidence collection for privacy controls.',
    tagCategories: ['regulation'],
    metadata: {{ reviewStatus: 'Action required', evidence: 'Source referenced' }},
  }},
  {{
    id: 'nist-summary',
    title: 'NIST Summary',
    text: 'NIST control review is source backed.',
    tagCategories: ['framework'],
    metadata: {{ reviewStatus: 'Review ready', evidence: 'Source referenced' }},
  }},
  {{
    id: 'ransomware-risk',
    title: 'Ransomware Risk',
    text: 'Needs incident tabletop review.',
    tagCategories: ['risk'],
    metadata: {{ reviewStatus: 'Needs review', evidence: 'Needs source trail' }},
  }},
  {{
    id: 'access-control',
    title: 'Access Control',
    text: 'Access Control review maps to IAM evidence.',
    tagCategories: ['control'],
    metadata: {{ reviewStatus: 'Action required', evidence: 'Needs source trail' }},
  }},
  {{
    id: 'sec-review',
    title: 'SEC Review',
    text: 'SEC disclosure review is source backed.',
    tagCategories: ['agency'],
    metadata: {{ reviewStatus: 'Review ready', evidence: 'Source referenced' }},
  }},
  {{
    id: 'explicit-owner',
    title: 'Owner Cue',
    text: 'Recommendations table lists an Owner column.',
    tagCategories: [],
    metadata: {{ reviewStatus: 'Action required', owners: 'Detected', evidence: 'Needs source trail' }},
  }},
  {{
    id: 'metadata-label-only',
    title: 'Metadata Label Only',
    text: 'OwnersNot detected EvidenceNeeds source trail',
    tagCategories: [],
    metadata: {{ reviewStatus: 'Needs review', owners: 'Not detected', evidence: 'Needs source trail' }},
  }},
];
assert(filters.filterSections(sections, {{}}).length === 7, 'empty filters should keep all sections');
assert(filters.filterSections(sections, {{ query: 'privacy controls' }}).map(s => s.id).join(',') === 'gdpr-obligations', 'query should match section text');
assert(filters.filterSections(sections, {{ query: 'owner' }}).map(s => s.id).join(',') === 'explicit-owner', 'owner query should match owner cues, not metadata labels');
assert(filters.filterSections(sections, {{ ownerCue: 'detected' }}).map(s => s.id).join(',') === 'explicit-owner', 'owner cue detected filter should narrow to owner-cue sections');
assert(filters.filterSections(sections, {{ ownerCue: 'missing' }}).map(s => s.id).join(',') === 'gdpr-obligations,nist-summary,ransomware-risk,access-control,sec-review,metadata-label-only', 'owner cue missing filter should narrow to sections without owner cues');
assert(filters.filterSections(sections, {{ reviewStatus: 'Review ready' }}).map(s => s.id).join(',') === 'nist-summary,sec-review', 'review status should filter sections');
assert(filters.filterSections(sections, {{ evidenceState: 'referenced' }}).map(s => s.id).join(',') === 'gdpr-obligations,nist-summary,sec-review', 'evidence referenced filter should narrow to source-backed sections');
assert(filters.filterSections(sections, {{ evidenceState: 'missing' }}).map(s => s.id).join(',') === 'ransomware-risk,access-control,explicit-owner,metadata-label-only', 'evidence missing filter should narrow to source-trail gaps');
assert(filters.filterSections(sections, {{ tagCategory: 'risk' }}).map(s => s.id).join(',') === 'ransomware-risk', 'tag category should filter sections');
assert(filters.filterSections(sections, {{ tagCategory: 'control' }}).map(s => s.id).join(',') === 'access-control', 'control tag category should filter sections');
assert(filters.filterSections(sections, {{ tagCategory: 'agency' }}).map(s => s.id).join(',') === 'sec-review', 'agency tag category should filter sections');
assert(filters.filterSections(sections, {{ query: 'GDPR', reviewStatus: 'Action required', tagCategory: 'regulation' }}).map(s => s.id).join(',') === 'gdpr-obligations', 'combined filters should narrow sections');
assert(filters.filterSections(sections, {{ query: 'not present' }}).length === 0, 'unmatched query should return empty results');
const statusCounts = filters.statusQuickFilterCounts(sections, {{ tagCategory: 'control', reviewStatus: 'Needs review' }});
assert(statusCounts['Action required'] === 1 && statusCounts['Review ready'] === 0 && statusCounts['Needs review'] === 0, 'status quick-filter counts should respect tag context while ignoring selected status');
const evidenceCounts = filters.statusQuickFilterCounts(sections, {{ ownerCue: 'missing', evidenceState: 'referenced', reviewStatus: 'Action required' }});
assert(evidenceCounts['Action required'] === 1 && evidenceCounts['Review ready'] === 2 && evidenceCounts['Needs review'] === 0, 'status quick-filter counts should respect owner and evidence context');
const duplicateSections = [
  {{
    id: 'same-heading',
    title: 'Repeated Heading',
    text: 'Unique GDPR obligation text.',
    tagCategories: ['regulation'],
    metadata: {{ reviewStatus: 'Action required' }},
  }},
  {{
    id: 'same-heading',
    title: 'Repeated Heading',
    text: 'Unrelated framework summary.',
    tagCategories: ['framework'],
    metadata: {{ reviewStatus: 'Review ready' }},
  }},
];
const duplicateMatches = filters.filterSections(duplicateSections, {{ query: 'unique gdpr' }});
assert(duplicateMatches.length === 1 && duplicateMatches[0] === duplicateSections[0], 'duplicate section ids should not merge filter results');
const parsedFilters = filters.parseFilterParams('?q=privacy%20controls&status=Review%20ready&tag=control&owner=detected&evidence=referenced');
assert(parsedFilters.query === 'privacy controls', 'filter params should parse search query');
assert(parsedFilters.reviewStatus === 'Review ready', 'filter params should parse review status');
assert(parsedFilters.tagCategory === 'control', 'filter params should parse tag category');
assert(parsedFilters.ownerCue === 'detected', 'filter params should parse owner cue filter');
assert(parsedFilters.evidenceState === 'referenced', 'filter params should parse evidence filter');
const safeFilters = filters.parseFilterParams('?status=Bad&tag=unknown&owner=unclear&evidence=maybe');
assert(safeFilters.query === '' && safeFilters.reviewStatus === 'all' && safeFilters.tagCategory === 'all' && safeFilters.ownerCue === 'all' && safeFilters.evidenceState === 'all', 'invalid filter params should fall back to defaults');
const defaultFilters = filters.defaultFilterState();
assert(JSON.stringify(defaultFilters) === JSON.stringify({{ query: '', reviewStatus: 'all', tagCategory: 'all', ownerCue: 'all', evidenceState: 'all' }}), 'default filter state should come from canonical option defaults');
assert(filters.normalizeFilterValue('query', ' privacy controls ') === 'privacy controls', 'query active value should trim whitespace');
assert(filters.normalizeFilterValue('reviewStatus', 'Bad') === 'all', 'invalid review status should normalize to default');
assert(filters.normalizeFilterValue('tagCategory', 'control') === 'control', 'valid tag category should be preserved');
assert(filters.normalizeFilterValue('ownerCue', '') === 'all', 'empty owner cue should normalize to default');
assert(filters.normalizeFilterValue('evidenceState', 'maybe') === 'all', 'invalid evidence state should normalize to default');
assert(JSON.stringify(filters.normalizeFilterState({{ query: ' privacy controls ', reviewStatus: 'Review ready', tagCategory: 'control', ownerCue: 'detected', evidenceState: 'referenced' }})) === JSON.stringify({{ query: 'privacy controls', reviewStatus: 'Review ready', tagCategory: 'control', ownerCue: 'detected', evidenceState: 'referenced' }}), 'filter state normalization should preserve valid canonical active values');
assert(filters.isDefaultFilterState(defaultFilters), 'default filter state should be detected as default');
assert(filters.isDefaultFilterState(safeFilters), 'invalid filter params should parse to default filter state');
assert(filters.isDefaultFilterState({{ query: ' ', reviewStatus: 'all', tagCategory: 'all', ownerCue: 'all', evidenceState: 'all' }}), 'whitespace-only query should be detected as default');
assert(!filters.isDefaultFilterState({{ query: 'privacy controls', reviewStatus: 'all', tagCategory: 'all', ownerCue: 'all', evidenceState: 'all' }}), 'active query should not be detected as default');
const activeParamEntries = filters.filterParamEntries({{ query: ' privacy controls ', reviewStatus: 'Review ready', tagCategory: 'control', ownerCue: 'detected', evidenceState: 'referenced' }});
assert(activeParamEntries.map(entry => `${{entry.key}}:${{entry.param}}=${{entry.value}}`).join('|') === 'query:q=privacy controls|reviewStatus:status=Review ready|tagCategory:tag=control|ownerCue:owner=detected|evidenceState:evidence=referenced', 'filter param entries should preserve canonical option order and active values');
const nonDefaultEntries = filters.nonDefaultFilterEntries({{ query: ' privacy controls ', reviewStatus: 'Review ready', tagCategory: 'control', ownerCue: 'detected', evidenceState: 'referenced' }});
assert(nonDefaultEntries.map(entry => `${{entry.key}}:${{entry.param}}:${{entry.labelPrefix}}=${{entry.value}}`).join('|') === 'query:q:Search=privacy controls|reviewStatus:status:Status=Review ready|tagCategory:tag:Tag=control|ownerCue:owner:Owner cues=detected|evidenceState:evidence:Evidence=referenced', 'non-default filter entries should expose option metadata and normalized active values');
assert(filters.nonDefaultFilterEntries({{ query: '', reviewStatus: 'Bad', tagCategory: 'unknown', ownerCue: 'unclear', evidenceState: 'maybe' }}).length === 0, 'non-default filter entries should omit defaults and invalid values');
assert(filters.filterParamEntries({{ query: '', reviewStatus: 'Bad', tagCategory: 'unknown', ownerCue: 'unclear', evidenceState: 'maybe' }}).length === 0, 'filter param entries should omit defaults and invalid values');
assert(filters.buildFilterParams({{ query: 'privacy controls', reviewStatus: 'Review ready', tagCategory: 'control', ownerCue: 'detected', evidenceState: 'referenced' }}) === '?q=privacy+controls&status=Review+ready&tag=control&owner=detected&evidence=referenced', 'filter params should serialize active filters');
assert(filters.buildFilterParams(defaultFilters) === '', 'filter params should omit default filters');
const activeEntries = filters.activeFilterEntries({{ query: 'privacy controls', reviewStatus: 'Review ready', tagCategory: 'control', ownerCue: 'missing', evidenceState: 'referenced' }});
assert(activeEntries.map(entry => `${{entry.key}}=${{entry.label}}`).join('|') === 'query=Search: privacy controls|reviewStatus=Status: Review ready|tagCategory=Tag: control|ownerCue=Owner cues: missing|evidenceState=Evidence: referenced', 'active filter entries should preserve labels and clear keys');
assert(filters.activeFilterLabels({{ query: 'privacy controls', reviewStatus: 'Review ready', tagCategory: 'control', ownerCue: 'missing', evidenceState: 'referenced' }}).join('|') === 'Search: privacy controls|Status: Review ready|Tag: control|Owner cues: missing|Evidence: referenced', 'active filter labels should expose canonical active filter labels');
assert(filters.activeFilterEntries({{ query: ' ', reviewStatus: 'Bad', tagCategory: 'unknown', ownerCue: 'unclear', evidenceState: 'maybe' }}).length === 0, 'active filter entries should omit invalid and default values');
assert(filters.activeFilterEntries({{ query: '', reviewStatus: 'all', tagCategory: 'all', ownerCue: 'all', evidenceState: 'all' }}).length === 0, 'default filters should not create active filter entries');
assert(filters.summarizeFilterResults(7, 7, {{}}) === 'Showing all 7 sections', 'filter summary should describe the default view');
const activeSummary = filters.summarizeFilterResults(2, 7, {{ query: 'privacy controls', reviewStatus: 'Review ready', tagCategory: 'control', ownerCue: 'detected', evidenceState: 'referenced' }});
assert(activeSummary === 'Showing 2 of 7 sections | Search: privacy controls | Status: Review ready | Tag: control | Owner cues: detected | Evidence: referenced', 'filter summary should name active filters');
const emptySummary = filters.summarizeFilterResults(0, 7, {{ query: 'not present', ownerCue: 'missing', evidenceState: 'missing' }});
assert(emptySummary === 'No sections match 3 active filters | Search: not present | Owner cues: missing | Evidence: missing', 'filter summary should describe empty active filters');
"""
    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        fail(
            "node executable not found; install Node.js to run generated-site "
            "renderer validation"
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        fail(detail or "node renderer assertions failed")

    print("site renderer check passed")


if __name__ == "__main__":
    main()
