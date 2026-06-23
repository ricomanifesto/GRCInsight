#!/usr/bin/env python3
"""Exercise generated-site renderer helper behavior without Node or a browser."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDERER_JS = REPO_ROOT / "site" / "static" / "renderer.js"


def fail(message: str) -> None:
    raise SystemExit(f"site renderer check failed: {message}")


def escape_html(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_attribute(value: str) -> str:
    return escape_html(value).replace('"', "&quot;")


def sanitize_markdown_url(url: str) -> str | None:
    value = url.strip()
    if not value or re.search(r"""[\s"'<>]""", value):
        return None
    if re.match(r"^(https?://|/(?!/)|\.{0,2}/|#)", value, flags=re.IGNORECASE):
        return value
    if not re.match(r"^[a-z][a-z0-9+.-]*:", value, flags=re.IGNORECASE):
        return value
    return None


def render_markdown_link(text: str, url: str) -> str:
    safe_url = sanitize_markdown_url(url)
    if not safe_url:
        return text
    return (
        f'<a href="{escape_attribute(safe_url)}" target="_blank" '
        f'rel="noopener">{text}</a>'
    )


def assert_equal(actual: str | None, expected: str | None, message: str) -> None:
    if actual != expected:
        fail(f"{message}: expected {expected!r}, got {actual!r}")


def main() -> None:
    if not RENDERER_JS.exists():
        fail("missing site/static/renderer.js")

    source = RENDERER_JS.read_text()
    required_snippets = [
        "window.GRCInsightRenderer",
        "escapeHtml",
        "escapeAttribute",
        "sanitizeMarkdownUrl",
        "renderMarkdownLink",
        'rel="noopener"',
    ]
    for snippet in required_snippets:
        if snippet not in source:
            fail(f"missing renderer snippet: {snippet}")

    assert_equal(
        sanitize_markdown_url("https://example.com/a"),
        "https://example.com/a",
        "https links should be allowed",
    )
    assert_equal(
        sanitize_markdown_url("/reports/current"),
        "/reports/current",
        "root-relative links should be allowed",
    )
    assert_equal(
        sanitize_markdown_url("controls/nist"),
        "controls/nist",
        "relative links should be allowed",
    )
    assert_equal(sanitize_markdown_url("#summary"), "#summary", "hash links should be allowed")
    assert_equal(
        sanitize_markdown_url("javascript:alert(1)"),
        None,
        "javascript links should be blocked",
    )
    assert_equal(
        sanitize_markdown_url("data:text/html,test"),
        None,
        "data links should be blocked",
    )
    assert_equal(
        sanitize_markdown_url('https://example.com/"bad'),
        None,
        "quote-bearing links should be blocked",
    )
    assert_equal(
        render_markdown_link("Safe", "https://example.com"),
        '<a href="https://example.com" target="_blank" rel="noopener">Safe</a>',
        "safe link should render as anchor",
    )
    assert_equal(
        render_markdown_link("Unsafe", "javascript:alert(1)"),
        "Unsafe",
        "unsafe link should render as text",
    )

    print("site renderer check passed")


if __name__ == "__main__":
    main()
