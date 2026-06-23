#!/usr/bin/env python3
"""Exercise pure generated-site renderer helpers without a browser."""

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDERER_JS = REPO_ROOT / "site" / "static" / "renderer.js"


def fail(message: str) -> None:
    raise SystemExit(f"site renderer check failed: {message}")


def main() -> None:
    if not RENDERER_JS.exists():
        fail("missing site/static/renderer.js")

    script = f"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync({json.dumps(str(RENDERER_JS))}, 'utf8');
const context = {{ window: {{}} }};
vm.createContext(context);
vm.runInContext(source, context, {{ filename: 'renderer.js' }});
const renderer = context.window.GRCInsightRenderer;
function assert(condition, message) {{
  if (!condition) throw new Error(message);
}}
assert(renderer, 'renderer object is not exported');
assert(renderer.sanitizeMarkdownUrl('https://example.com/a') === 'https://example.com/a', 'https links should be allowed');
assert(renderer.sanitizeMarkdownUrl('/reports/current') === '/reports/current', 'root-relative links should be allowed');
assert(renderer.sanitizeMarkdownUrl('controls/nist') === 'controls/nist', 'relative links should be allowed');
assert(renderer.sanitizeMarkdownUrl('#summary') === '#summary', 'hash links should be allowed');
assert(renderer.sanitizeMarkdownUrl('javascript:alert(1)') === null, 'javascript links should be blocked');
assert(renderer.sanitizeMarkdownUrl('data:text/html,test') === null, 'data links should be blocked');
assert(renderer.sanitizeMarkdownUrl('https://example.com/\"bad') === null, 'quote-bearing links should be blocked');
assert(renderer.renderMarkdownLink('Safe', 'https://example.com') === '<a href=\"https://example.com\" target=\"_blank\" rel=\"noopener\">Safe</a>', 'safe link should render as anchor');
assert(renderer.renderMarkdownLink('Unsafe', 'javascript:alert(1)') === 'Unsafe', 'unsafe link should render as text');
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        fail(detail or "node renderer assertions failed")

    print("site renderer check passed")


if __name__ == "__main__":
    main()
