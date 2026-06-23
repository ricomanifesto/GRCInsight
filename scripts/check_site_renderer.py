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
const sourceMetadata = metadata.deriveSectionMetadata('Executive Summary', 'Source Multi-Source OSINT Articles Analyzed 30 of 30');
assert(sourceMetadata.reviewStatus === 'Review ready', 'source-backed sections should be review ready');
assert(sourceMetadata.evidence === 'Source referenced', 'source-backed sections should detect evidence');
const emptyMetadata = metadata.deriveSectionMetadata('Overview', '');
assert(emptyMetadata.reviewStatus === 'Needs review', 'empty sections should default to needs review');
assert(metadata.renderSectionMetadata(emptyMetadata).includes('data-review-status="Needs review"'), 'metadata renderer should expose review status');
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
assert(auditSummary.evidenceGaps === 2, 'audit summary should count sections needing source trails');
assert(auditSummary.auditReady === false, 'audit summary should not be audit-ready when gaps remain');
assert(auditSummary.evidenceTitles.includes('Evidence backed overview'), 'audit summary should name source-backed sections');
assert(auditSummary.gapTitles.includes('PCI remediation') && auditSummary.gapTitles.includes('Unmapped overview'), 'audit summary should name source-trail gaps');
assert(metadata.renderAuditSummary(auditSummary).includes('audit-summary-card'), 'audit summary renderer should produce a summary card');
assert(metadata.renderAuditSummary(auditSummary).includes('Needs source trail'), 'audit summary renderer should expose missing evidence state');
assert(metadata.renderAuditSummary(auditSummary).includes('Evidence trail'), 'audit summary renderer should expose evidence trail list');
assert(metadata.renderAuditSummary(auditSummary).includes('Evidence backed overview'), 'audit summary renderer should list source-backed sections');
const sections = [
  {{
    id: 'gdpr-obligations',
    title: 'GDPR Obligations',
    text: 'GDPR requires evidence collection for privacy controls.',
    tagCategories: ['regulation'],
    metadata: {{ reviewStatus: 'Action required' }},
  }},
  {{
    id: 'nist-summary',
    title: 'NIST Summary',
    text: 'NIST control review is source backed.',
    tagCategories: ['framework'],
    metadata: {{ reviewStatus: 'Review ready' }},
  }},
  {{
    id: 'ransomware-risk',
    title: 'Ransomware Risk',
    text: 'Needs incident tabletop review.',
    tagCategories: ['risk'],
    metadata: {{ reviewStatus: 'Needs review' }},
  }},
  {{
    id: 'access-control',
    title: 'Access Control',
    text: 'Access Control review maps to IAM evidence.',
    tagCategories: ['control'],
    metadata: {{ reviewStatus: 'Action required' }},
  }},
  {{
    id: 'sec-review',
    title: 'SEC Review',
    text: 'SEC disclosure review is source backed.',
    tagCategories: ['agency'],
    metadata: {{ reviewStatus: 'Review ready' }},
  }},
];
assert(filters.filterSections(sections, {{}}).length === 5, 'empty filters should keep all sections');
assert(filters.filterSections(sections, {{ query: 'privacy controls' }}).map(s => s.id).join(',') === 'gdpr-obligations', 'query should match section text');
assert(filters.filterSections(sections, {{ reviewStatus: 'Review ready' }}).map(s => s.id).join(',') === 'nist-summary,sec-review', 'review status should filter sections');
assert(filters.filterSections(sections, {{ tagCategory: 'risk' }}).map(s => s.id).join(',') === 'ransomware-risk', 'tag category should filter sections');
assert(filters.filterSections(sections, {{ tagCategory: 'control' }}).map(s => s.id).join(',') === 'access-control', 'control tag category should filter sections');
assert(filters.filterSections(sections, {{ tagCategory: 'agency' }}).map(s => s.id).join(',') === 'sec-review', 'agency tag category should filter sections');
assert(filters.filterSections(sections, {{ query: 'GDPR', reviewStatus: 'Action required', tagCategory: 'regulation' }}).map(s => s.id).join(',') === 'gdpr-obligations', 'combined filters should narrow sections');
assert(filters.filterSections(sections, {{ query: 'not present' }}).length === 0, 'unmatched query should return empty results');
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
const parsedFilters = filters.parseFilterParams('?q=privacy%20controls&status=Review%20ready&tag=control');
assert(parsedFilters.query === 'privacy controls', 'filter params should parse search query');
assert(parsedFilters.reviewStatus === 'Review ready', 'filter params should parse review status');
assert(parsedFilters.tagCategory === 'control', 'filter params should parse tag category');
const safeFilters = filters.parseFilterParams('?status=Bad&tag=unknown');
assert(safeFilters.query === '' && safeFilters.reviewStatus === 'all' && safeFilters.tagCategory === 'all', 'invalid filter params should fall back to defaults');
assert(filters.buildFilterParams({{ query: 'privacy controls', reviewStatus: 'Review ready', tagCategory: 'control' }}) === '?q=privacy+controls&status=Review+ready&tag=control', 'filter params should serialize active filters');
assert(filters.buildFilterParams({{ query: '', reviewStatus: 'all', tagCategory: 'all' }}) === '', 'filter params should omit default filters');
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
