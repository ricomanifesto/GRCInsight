#!/usr/bin/env python3
"""Exercise the canonical site renderer and tag catalog without a browser."""

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RENDERER_JS = REPO_ROOT / "site" / "static" / "renderer.js"
TAGS_JS = REPO_ROOT / "site" / "static" / "tags.js"


def fail(message: str) -> None:
    raise SystemExit(f"site renderer check failed: {message}")


def main() -> None:
    if not RENDERER_JS.exists():
        fail("missing site/static/renderer.js")
    if not TAGS_JS.exists():
        fail("missing site/static/tags.js")

    script = f"""
const fs = require('fs');
const vm = require('vm');
const rendererSource = fs.readFileSync({json.dumps(str(RENDERER_JS))}, 'utf8');
const tagsSource = fs.readFileSync({json.dumps(str(TAGS_JS))}, 'utf8');
const context = {{ window: {{}} }};
vm.createContext(context);
vm.runInContext(rendererSource, context, {{ filename: 'renderer.js' }});
vm.runInContext(tagsSource, context, {{ filename: 'tags.js' }});
const renderer = context.window.GRCInsightRenderer;
const tags = context.window.GRCInsightTags;
function assert(condition, message) {{
  if (!condition) throw new Error(message);
}}

assert(renderer, 'renderer object is not exported');
assert(tags, 'tag catalog is not exported');
assert(typeof renderer.renderMarkdown === 'function', 'renderer should expose renderMarkdown');
assert(typeof renderer.renderReportDocument === 'function', 'renderer should expose renderReportDocument');
assert(typeof renderer.parseReportDocument === 'function', 'renderer should expose parseReportDocument');
assert(typeof renderer.sanitizeMarkdownUrl === 'function', 'renderer should expose sanitizeMarkdownUrl');
assert(typeof renderer.normalizeReportMarkdown === 'function', 'renderer should expose normalizeReportMarkdown');

// URL sanitization (security oracle): allow safe schemes, block the rest.
assert(renderer.sanitizeMarkdownUrl('https://example.com/a') === 'https://example.com/a', 'https links should be allowed');
assert(renderer.sanitizeMarkdownUrl('/reports/current') === '/reports/current', 'root-relative links should be allowed');
assert(renderer.sanitizeMarkdownUrl('controls/nist') === 'controls/nist', 'relative links should be allowed');
assert(renderer.sanitizeMarkdownUrl('#summary') === '#summary', 'hash links should be allowed');
assert(renderer.sanitizeMarkdownUrl('javascript:alert(1)') === null, 'javascript links should be blocked');
assert(renderer.sanitizeMarkdownUrl('data:text/html,test') === null, 'data links should be blocked');
assert(renderer.sanitizeMarkdownUrl('https://example.com/"bad') === null, 'quote-bearing links should be blocked');
assert(renderer.renderMarkdownLink('Safe', 'https://example.com') === '<a href="https://example.com" target="_blank" rel="noopener">Safe</a>', 'safe link should render as anchor');
assert(renderer.renderMarkdownLink('Unsafe', 'javascript:alert(1)') === 'Unsafe', 'unsafe link should render as text');

// Numbered known section labels normalize to h2; numbered prose does not.
const normalized = renderer.normalizeReportMarkdown('1. Executive Summary\\n1. Review vendor contracts.');
assert(normalized.includes('## Executive Summary'), 'numbered known section labels should normalize to h2 headings');
assert(normalized.includes('1. Review vendor contracts.'), 'numbered prose must not be promoted to a heading');
assert(renderer.normalizeReportMarkdown('## Executive Summary').includes('## Executive Summary'), 'existing h2 headings should be preserved');
const reportSections = renderer.normalizeReportMarkdown('4. Risk Assessment\\n5. Recommendations for Action');
assert(reportSections.includes('## Risk Assessment'), 'risk section should normalize to h2');
assert(reportSections.includes('## Recommendations for Action'), 'recommendations section should normalize to h2');

// Markdown rendering: headings, tables, lists, code.
assert(renderer.renderMarkdown('## Risk Assessment').includes('<h2>Risk Assessment</h2>'), 'h2 markdown should render as an h2 element');
const tableHtml = renderer.renderMarkdown('| Field | Detail |\\n|-------|--------|\\n| Date | June 2026 |');
assert(tableHtml.includes('<table>') && tableHtml.includes('<th>Field</th>') && tableHtml.includes('<td>June 2026</td>'), 'pipe tables should render as HTML tables');
assert(renderer.renderMarkdown('- one\\n- two').includes('<ul><li>one</li><li>two</li></ul>'), 'dash lists should render as unordered lists');
assert(renderer.renderMarkdown('```\\ncode\\n```').includes('<pre><code>code</code></pre>'), 'fenced code should render as a pre block');
assert(renderer.renderMarkdown('---   ').trim() === '<hr>', 'rules with trailing whitespace should not leak as literal text');
const queryLinkHtml = renderer.renderMarkdown('[Evidence](https://example.com/feed?a=1&b=2)');
assert(queryLinkHtml.includes('href="https://example.com/feed?a=1&amp;b=2"'), 'query separators should be escaped exactly once in rendered links');
assert(!queryLinkHtml.includes('&amp;amp;'), 'rendered links must not double-escape query separators');
const apostropheLinkHtml = renderer.renderMarkdown("[Evidence](HTTPS://example.com/O'Reilly)");
assert(apostropheLinkHtml.includes('href="HTTPS://example.com/O\\'Reilly"'), 'RFC-valid apostrophes and case-insensitive HTTP schemes should remain clickable');
const parenthesizedLinkHtml = renderer.renderMarkdown('[Evidence](https://example.com/a_(b).html)');
assert(parenthesizedLinkHtml.includes('href="https://example.com/a_(b).html"'), 'balanced parentheses should remain part of a link destination');
assert(!parenthesizedLinkHtml.includes('.html)</p>'), 'balanced link destinations must not leak a trailing fragment into prose');
const escapedDestinationHtml = renderer.renderMarkdown('[Evidence](https://example.com/a\\\\)b)');
assert(escapedDestinationHtml.includes('href="https://example.com/a)b"'), 'escaped destination delimiters should be decoded before rendering');
assert(!escapedDestinationHtml.includes('a/)b') && !escapedDestinationHtml.includes('%5C'), 'Markdown URL escapes must not alter browser navigation');
const bareThenLinkedHtml = renderer.renderMarkdown('[Unresolved reference] then [Evidence](https://example.com/evidence)');
assert(bareThenLinkedHtml.includes('[Unresolved reference] then <a href="https://example.com/evidence"'), 'a bare bracketed reference must not consume the next Markdown link');
const nestedLabelHtml = renderer.renderMarkdown('[Microsoft [Update] advisory](https://example.com/advisory)');
assert(nestedLabelHtml.includes('<a href="https://example.com/advisory"'), 'balanced brackets should remain part of a link label');
assert(nestedLabelHtml.includes('Microsoft [Update] advisory</a>'), 'nested label text should render intact');
const escapedLabelHtml = renderer.renderMarkdown('[Example Feed\\\\\\\\](https://example.com/feed) and [Microsoft \\\\[Update\\\\]](https://example.com/update)');
assert(escapedLabelHtml.includes('Example Feed\\\\</a>'), 'escaped link-label backslashes should render once');
assert(escapedLabelHtml.includes('Microsoft [Update]</a>'), 'escaped link-label brackets should render without escape characters');
const literalLabelHtml = renderer.renderMarkdown('[Critical *BSD* advisory](https://example.com/bsd)');
assert(literalLabelHtml.includes('Critical *BSD* advisory</a>'), 'exact source-title asterisks should render literally');
assert(!literalLabelHtml.includes('<em>BSD</em>'), 'source-title identity must not be rewritten as emphasis');

// A complete report keeps provenance and section cards in the canonical
// renderer so build-time HTML and browser rendering are identical.
const reportDocument = '# GRC Intelligence Report - 2026-08-13\\n**Generated:** 2026-08-13T13:00:00Z\\n**Date of Issue:** August 2026\\n**Source:** [SentryDigest](https://example.com/feed.xml)\\n**Articles Analyzed:** 30\\n**Analysis Mode:** Model-backed\\n\\n---   \\n\\n## Executive Summary\\nCareful analysis.\\n\\n---\\n\\n## Source Highlights\\n- [Evidence](https://example.com/evidence)';
const parsedReport = renderer.parseReportDocument(reportDocument);
assert(parsedReport.title === 'GRC Intelligence Report - 2026-08-13', 'report title should be parsed from h1');
assert(parsedReport.metadata.generated === '2026-08-13T13:00:00Z', 'Generated metadata should be preserved');
assert(parsedReport.metadata['articles analyzed'] === '30', 'article-count provenance should be preserved');
const reportHtml = renderer.renderReportDocument(reportDocument);
assert(reportHtml.includes('<section class="card report-provenance"><h2>About this report</h2>'), 'report provenance should render as a card');
assert(reportHtml.includes('<dt>Source</dt><dd><a href="https://example.com/feed.xml"'), 'source provenance should keep its safe link');
assert((reportHtml.match(/<section class="card">/g) || []).length === 2, 'each report section should render as a card');
assert(!reportHtml.includes('<hr>') && !reportHtml.includes('---'), 'section separators should not survive in report cards');
const querySourceReport = reportDocument.replace('https://example.com/feed.xml', 'https://example.com/feed?a=1&b=2');
const querySourceHtml = renderer.renderReportDocument(querySourceReport);
assert(querySourceHtml.includes('href="https://example.com/feed?a=1&amp;b=2"'), 'provenance links should preserve query parameter separators');
assert(!querySourceHtml.includes('&amp;amp;'), 'provenance links must not double-escape query separators');
const parenthesizedSourceReport = reportDocument.replace('https://example.com/feed.xml', 'https://example.com/feed(1).xml');
const parenthesizedSourceHtml = renderer.renderReportDocument(parenthesizedSourceReport);
assert(parenthesizedSourceHtml.includes('href="https://example.com/feed(1).xml"'), 'provenance links should preserve balanced parentheses');

// Regression: a paragraph that contains bold text must render as a single
// wrapped <p>, not as loose inline fragments. Loose fragments became separate
// grid rows in the card and broke paragraphs across lines.
const boldParagraph = renderer.renderMarkdown('Intro around **PCI-DSS enforcement**, **NIST adoption**, and **SOX modernization**—done.');
assert(boldParagraph.trim().startsWith('<p>') && boldParagraph.trim().endsWith('</p>'), 'a bold-bearing paragraph should be wrapped in a single <p>');
assert((boldParagraph.match(/<p>/g) || []).length === 1, 'a single source paragraph should produce exactly one <p>');
assert(!/^\\s*<strong>/.test(boldParagraph), 'bold paragraphs must not leak <strong> as a top-level node');

// Regression: paragraphs adjacent to lists keep their own <p>. Block constructs
// consume the newline that ended their last line, collapsing the blank-line
// separator and merging an adjacent paragraph into the block; that leaked the
// paragraph out unwrapped (lone-comma fragments in the card grid).
const paraThenList = renderer.renderMarkdown('Intro with commas, A, B, and C.\\n\\n- first item\\n- second item');
assert(paraThenList.includes('<p>Intro with commas, A, B, and C.</p>'), 'a paragraph before a list must stay wrapped in its own <p>');
assert(paraThenList.includes('<ul><li>first item</li><li>second item</li></ul>'), 'the following list must still render as a <ul>');
assert(!/,\\s*<\\/p>\\s*$/.test(paraThenList), 'the paragraph must not be truncated at a trailing comma');

const listThenPara = renderer.renderMarkdown('- first item\\n- second item\\n\\n**Takeaway:** a closing, comma-bearing paragraph.');
assert(listThenPara.includes('<ul><li>first item</li><li>second item</li></ul>'), 'the list before a paragraph must render as a <ul>');
assert(listThenPara.includes('<p><strong>Takeaway:</strong> a closing, comma-bearing paragraph.</p>'), 'a paragraph after a list must stay wrapped in its own <p>');

const orderedThenPara = renderer.renderMarkdown('1. step one\\n2. step two\\n\\nClosing paragraph with a, comma.');
assert(orderedThenPara.includes('<ol><li>step one</li><li>step two</li></ol>'), 'the ordered list before a paragraph must render as an <ol>');
assert(orderedThenPara.includes('<p>Closing paragraph with a, comma.</p>'), 'a paragraph after an ordered list must stay wrapped in its own <p>');

// A multi-line fenced code block survives paragraph assembly intact.
const withCode = renderer.renderMarkdown('Intro line.\\n\\n```\\nrow one\\nrow two\\n```\\n\\nAfter the block.');
assert(withCode.includes('<pre><code>row one\\nrow two</code></pre>'), 'multi-line code blocks must render as a single pre/code with their newlines intact');
assert(withCode.includes('<p>Intro line.</p>') && withCode.includes('<p>After the block.</p>'), 'paragraphs around a code block must each stay wrapped');

// Tag catalog shape and authoritative reference metadata.
const byKey = Object.fromEntries(tags.categories.map(c => [c.key, c]));
const term = (category, label) => category.terms.find(item => item.label === label);
assert(typeof tags.tokenizeComplianceTerms === 'function', 'tag catalog should expose pure term tokenization');
assert(byKey.frameworks && byKey.frameworks.pillClass === 'framework', 'framework category should expose framework pills');
assert(term(byKey.frameworks, 'NIST CSF 2.0').url === 'https://www.nist.gov/cyberframework', 'NIST CSF should link to the official NIST resource');
assert(term(byKey.frameworks, 'NIST CSF 2.0').aliases.includes('NIST'), 'bare NIST mentions should use the official NIST CSF reference');
assert(term(byKey.frameworks, 'PCI DSS').url === 'https://www.pcisecuritystandards.org/standards/pci-dss/', 'PCI DSS should link to the official PCI SSC resource');
assert(byKey.regulations && byKey.regulations.pillClass === 'regulation', 'regulation category should expose regulation pills');
assert(term(byKey.regulations, 'GDPR').url === 'https://eur-lex.europa.eu/eli/reg/2016/679/oj', 'GDPR should link to the official regulation text');
assert(!byKey.risks, 'risk terms should remain prose rather than inert pills');
assert(!byKey.controls, 'control terms should remain prose rather than inert pills');
assert(byKey.agencies && byKey.agencies.pillClass === 'agency', 'agency category should expose agency pills');
assert(term(byKey.agencies, 'SEC').url === 'https://www.sec.gov/about', 'SEC should link to the official agency resource');
assert(tags.categories.every(category => category.terms.every(item => item.url)), 'every pill catalog term must have a destination');

// Tokenization preserves the report's visible typography while normalizing
// Unicode hyphens/spaces for matching and attaching only curated URLs.
const tagged = tags.tokenizeComplianceTerms('PCI‑DSS, ISO\u202f27001, NIST CSF 2.0, GDPR, ransomware, and controls.');
const taggedText = label => tagged.find(item => item.text === label);
assert(taggedText('PCI‑DSS').url === 'https://www.pcisecuritystandards.org/standards/pci-dss/', 'Unicode PCI DSS spelling should receive its official link');
assert(taggedText('ISO\u202f27001').url === 'https://www.iso.org/standard/27001', 'narrow-space ISO spelling should receive its official link');
assert(taggedText('NIST CSF 2.0').url === 'https://www.nist.gov/cyberframework', 'precise NIST CSF spelling should receive its official link');
assert(taggedText('GDPR').url === 'https://eur-lex.europa.eu/eli/reg/2016/679/oj', 'GDPR should receive its official link');
assert(!taggedText('ransomware'), 'risk terms should remain plain prose');
assert(!taggedText('controls'), 'control terms should remain plain prose');
const bareNist = tags.tokenizeComplianceTerms('NIST guidance').find(item => item.text === 'NIST');
assert(bareNist.url === 'https://www.nist.gov/cyberframework', 'bare NIST text should receive the official NIST CSF link');

console.log('node renderer assertions passed');
"""

    result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        fail(detail or "node renderer assertions failed")

    print("site renderer check passed")


if __name__ == "__main__":
    main()
