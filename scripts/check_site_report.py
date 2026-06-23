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


def fail(message: str) -> None:
    raise SystemExit(f"site report check failed: {message}")


def read_text(path: Path) -> str:
    if not path.exists():
        fail(f"missing {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    html = read_text(INDEX_HTML)
    markdown = read_text(INDEX_MD)
    app_js = read_text(APP_JS)
    renderer_js = read_text(RENDERER_JS)
    tags_js = read_text(TAGS_JS)
    metadata_js = read_text(METADATA_JS)

    for asset in (
        "static/style.css",
        "static/tags.js",
        "static/metadata.js",
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
        "pillClass",
    )
    for guard in required_tag_guards:
        if guard not in tags_js:
            fail(f"tags.js missing compliance tag guard: {guard}")

    required_metadata_guards = (
        "window.GRCInsightMetadata",
        "deriveSectionMetadata",
        "renderSectionMetadata",
        "reviewStatus",
        "Needs source trail",
        "data-review-status",
    )
    for guard in required_metadata_guards:
        if guard not in metadata_js:
            fail(f"metadata.js missing section metadata guard: {guard}")

    print("site report check passed")


if __name__ == "__main__":
    main()
