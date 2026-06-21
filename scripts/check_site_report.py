#!/usr/bin/env python3
"""Validate the committed GitHub Pages report artifact."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
INDEX_HTML = SITE_DIR / "index.html"
INDEX_MD = SITE_DIR / "index.md"


def fail(message: str) -> None:
    raise SystemExit(f"site report check failed: {message}")


def read_text(path: Path) -> str:
    if not path.exists():
        fail(f"missing {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    html = read_text(INDEX_HTML)
    markdown = read_text(INDEX_MD)

    for asset in ("static/style.css", "static/app.js"):
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

    print("site report check passed")


if __name__ == "__main__":
    main()
