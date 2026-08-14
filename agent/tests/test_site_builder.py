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


def test_archive_detail_page_discloses_pre_pin_context_in_chrome():
    namespace = builder_namespace()
    markdown = """# GRC Intelligence Report
**Generated:** 2026-08-14T03:10:14Z

## Executive Summary
Historical publication content.
"""

    html = namespace["archive_detail_html"](markdown)

    assert "Historical context note" in html
    assert "publication-era rolling SentryDigest links" in html
    assert 'href="../">Read the archive history</a>' in html
    assert html.index("Historical context note") < html.index(
        '<main class="container archive-report">'
    )


def test_archive_detail_page_omits_context_at_the_pin_boundary():
    namespace = builder_namespace()
    boundary = namespace["DATED_DIGEST_HANDOFF_BOUNDARY"]
    html = """<body>
    <main class="container archive-report"><p>Preserved report.</p></main>
    </body>"""

    built = namespace["with_archive_detail_chrome"](html, boundary)

    assert built == html
    assert "Historical context note" not in built


def test_archive_detail_chrome_preserves_report_body_bytes_and_is_idempotent():
    namespace = builder_namespace()
    generated = namespace["DATED_DIGEST_HANDOFF_BOUNDARY"] - timedelta(seconds=1)
    report_body = (
        '<main class="container archive-report">'
        '<section data-era="original">Publication-era body.</section>'
        "</main>"
    )
    html = f"<body>\n    {report_body}\n</body>"

    first = namespace["with_archive_detail_chrome"](html, generated)
    second = namespace["with_archive_detail_chrome"](first, generated)

    assert first == second
    assert report_body in first
    assert first.count(namespace["ARCHIVE_CONTEXT_START"]) == 1
    assert first.count(namespace["ARCHIVE_CONTEXT_END"]) == 1


def test_publication_notice_is_silent_when_report_published():
    namespace = builder_namespace()

    assert namespace["publication_notice_html"](None) == ""
    assert namespace["publication_notice_html"]({"outcome": "published"}) == ""


def test_publication_notice_names_safe_retention_context():
    namespace = builder_namespace()

    html = namespace["publication_notice_html"](
        {
            "outcome": "retained",
            "attempted_at": "2026-08-14T14:07:22Z",
            "refusal_category": "provider_quota",
        }
    )

    assert "Publication update" in html
    assert "August 14, 2026 at 2:07:22 PM UTC" in html
    assert "current model-backed report was retained" in html
    assert "provider quota refusal" in html
    assert 'href="publication-state.json"' in html


def test_archive_entries_stack_at_the_phone_breakpoint():
    style = STYLE_CSS.read_text()
    phone_rules = style.split("@media (max-width: 760px) {", 1)[1].split(
        "/* Print: report only */", 1
    )[0]

    assert ".archive-list a { grid-template-columns: 1fr; gap: 4px; }" in phone_rules
