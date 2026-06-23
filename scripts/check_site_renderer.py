#!/usr/bin/env python3
"""Exercise generated-site renderer helpers without a browser."""

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDERER_JS = REPO_ROOT / "site" / "static" / "renderer.js"
TAGS_JS = REPO_ROOT / "site" / "static" / "tags.js"
METADATA_JS = REPO_ROOT / "site" / "static" / "metadata.js"


def fail(message: str) -> None:
    raise SystemExit(f"site renderer check failed: {message}")


def main() -> None:
    if not RENDERER_JS.exists():
        fail("missing site/static/renderer.js")
    if not TAGS_JS.exists():
        fail("missing site/static/tags.js")
    if not METADATA_JS.exists():
        fail("missing site/static/metadata.js")

    script = f"""
const fs = require('fs');
const vm = require('vm');
const rendererSource = fs.readFileSync({json.dumps(str(RENDERER_JS))}, 'utf8');
const tagsSource = fs.readFileSync({json.dumps(str(TAGS_JS))}, 'utf8');
const metadataSource = fs.readFileSync({json.dumps(str(METADATA_JS))}, 'utf8');
const context = {{ window: {{}} }};
vm.createContext(context);
vm.runInContext(rendererSource, context, {{ filename: 'renderer.js' }});
vm.runInContext(tagsSource, context, {{ filename: 'tags.js' }});
vm.runInContext(metadataSource, context, {{ filename: 'metadata.js' }});
const renderer = context.window.GRCInsightRenderer;
const tags = context.window.GRCInsightTags;
const metadata = context.window.GRCInsightMetadata;
function assert(condition, message) {{
  if (!condition) throw new Error(message);
}}
assert(renderer, 'renderer object is not exported');
assert(tags, 'tag catalog is not exported');
assert(metadata, 'section metadata helpers are not exported');
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
assert(frameworks && frameworks.terms.includes('NIST') && frameworks.pillClass === 'framework', 'framework tag category should render framework pills');
assert(regulations && regulations.terms.includes('GDPR') && regulations.pillClass === 'regulation', 'regulation tag category should render regulation pills');
assert(risks && risks.terms.includes('Ransomware') && risks.pillClass === 'risk', 'risk tag category should render risk pills');
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
