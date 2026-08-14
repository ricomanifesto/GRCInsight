from datetime import timedelta
from pathlib import Path
import runpy

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_BUILDER = REPO_ROOT / "scripts" / "build_site.py"
STYLE_CSS = REPO_ROOT / "site" / "static" / "style.css"


def builder_namespace() -> dict:
    return runpy.run_path(str(SITE_BUILDER))


def report_tuple(namespace: dict, generated) -> tuple[str, str, str, str]:
    return (
        namespace["archive_slug"](generated),
        "GRC Intelligence Report",
        generated.isoformat().replace("+00:00", "Z"),
        namespace["display_timestamp"](generated),
    )


def test_archive_index_discloses_pre_pin_context_links():
    namespace = builder_namespace()
    boundary = namespace["DATED_DIGEST_HANDOFF_BOUNDARY"]

    html = namespace["archive_index_html"](
        [
            report_tuple(namespace, boundary),
            report_tuple(namespace, boundary - timedelta(seconds=1)),
        ]
    )

    assert 'aria-label="Historical context links"' in html
    assert "Reports published before" in html
    assert 'datetime="2026-08-14T04:49:12.035399Z"' in html
    assert "publication-era rolling SentryDigest links" in html
    assert "archived reports remain unchanged" in html


def test_archive_index_omits_note_when_all_reports_use_dated_handoffs():
    namespace = builder_namespace()
    boundary = namespace["DATED_DIGEST_HANDOFF_BOUNDARY"]

    html = namespace["archive_index_html"]([report_tuple(namespace, boundary)])

    assert "Historical context note" not in html
    assert "publication-era rolling SentryDigest links" not in html


def test_archive_detail_page_never_receives_the_index_disclosure():
    namespace = builder_namespace()
    markdown = """# GRC Intelligence Report
**Generated:** 2026-08-14T03:10:14Z

## Executive Summary
Historical publication content.
"""

    html = namespace["archive_detail_html"](markdown)

    assert "Historical context note" not in html
    assert "publication-era rolling SentryDigest links" not in html


def test_archive_entries_stack_at_the_phone_breakpoint():
    style = STYLE_CSS.read_text()
    phone_rules = style.split("@media (max-width: 760px) {", 1)[1].split(
        "/* Print: report only */", 1
    )[0]

    assert ".archive-list a { grid-template-columns: 1fr; gap: 4px; }" in phone_rules
