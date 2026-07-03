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
const entitySections = renderer.normalizeReportMarkdown('4. Threat Actor Activities\\n5. CVE and Vulnerability Highlights');
assert(entitySections.includes('## Threat Actor Activities'), 'threat actor section should normalize to h2');
assert(entitySections.includes('## CVE and Vulnerability Highlights'), 'CVE section should normalize to h2');

// Markdown rendering: headings, tables, lists, code.
assert(renderer.renderMarkdown('## Risk Assessment').includes('<h2>Risk Assessment</h2>'), 'h2 markdown should render as an h2 element');
const tableHtml = renderer.renderMarkdown('| Field | Detail |\\n|-------|--------|\\n| Date | June 2026 |');
assert(tableHtml.includes('<table>') && tableHtml.includes('<th>Field</th>') && tableHtml.includes('<td>June 2026</td>'), 'pipe tables should render as HTML tables');
assert(renderer.renderMarkdown('- one\\n- two').includes('<ul><li>one</li><li>two</li></ul>'), 'dash lists should render as unordered lists');
assert(renderer.renderMarkdown('```\\ncode\\n```').includes('<pre><code>code</code></pre>'), 'fenced code should render as a pre block');

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

// Tag catalog shape.
const byKey = Object.fromEntries(tags.categories.map(c => [c.key, c]));
assert(byKey.frameworks && byKey.frameworks.pillClass === 'framework' && byKey.frameworks.terms.includes('NIST'), 'framework category should expose framework pills');
assert(byKey.regulations && byKey.regulations.pillClass === 'regulation' && byKey.regulations.terms.includes('GDPR'), 'regulation category should expose regulation pills');
assert(byKey.risks && byKey.risks.pillClass === 'risk', 'risk category should expose risk pills');
assert(byKey.controls && byKey.controls.pillClass === 'control', 'control category should expose control pills');
assert(byKey.agencies && byKey.agencies.pillClass === 'agency' && byKey.agencies.terms.includes('SEC'), 'agency category should expose agency pills');

console.log('node renderer assertions passed');
"""

    result = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        fail(detail or "node renderer assertions failed")

    print("site renderer check passed")


if __name__ == "__main__":
    main()
