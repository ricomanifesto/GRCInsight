from datetime import timedelta
from pathlib import Path
import runpy

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_BUILDER = REPO_ROOT / "scripts" / "build_site.py"
STYLE_CSS = REPO_ROOT / "site" / "static" / "style.css"
APP_JS = REPO_ROOT / "site" / "static" / "app.js"
INDEX_HTML = REPO_ROOT / "site" / "index.html"


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
        },
        {"schedule": {"cadence": "daily", "time_utc": "13:00"}},
    )

    assert "Publication update" in html
    assert "August 14, 2026 at 2:07:22 PM UTC" in html
    assert "current model-backed report was retained" in html
    assert "provider quota refusal" in html
    assert "next regular attempt runs daily at 13:00 UTC" in html
    assert 'href="publication-history/"' in html
    assert 'href="publication-state.json"' in html


def test_publication_history_page_is_bounded_honest_and_newest_first():
    namespace = builder_namespace()
    history = {
        "schema_version": 1,
        "max_entries": 30,
        "history_started_at": "2026-08-14T14:07:22Z",
        "schedule": {"cadence": "daily", "time_utc": "13:00"},
        "events": [
            {
                "event_at": "2026-08-14T16:00:00Z",
                "outcome": "published",
                "report_generated_at": "2026-08-14T15:00:00Z",
                "evidence_manifest_sha256": "a" * 64,
            },
            {
                "event_at": "2026-08-14T14:07:22Z",
                "outcome": "retained",
                "report_generated_at": "2026-08-14T10:12:05Z",
                "evidence_manifest_sha256": "b" * 64,
                "refusal_category": "provider_quota",
            },
        ],
    }

    html = namespace["publication_history_html"](history)

    assert "Earlier outcomes were not reconstructed" in html
    assert "newest 30 terminal outcomes" in html
    assert "next regular attempt runs daily at 13:00 UTC" in html
    list_start = html.index('class="publication-history-list"')
    assert html.index("2026-08-14T16:00:00Z", list_start) < html.index(
        "2026-08-14T14:07:22Z", list_start
    )
    assert html.count('class="publication-history-entry"') == 2
    assert 'href="../publication-history.json"' in html


def test_archive_entries_stack_at_the_phone_breakpoint():
    style = STYLE_CSS.read_text()
    phone_rules = style.split("@media (max-width: 760px) {", 1)[1].split(
        "/* Print: report only */", 1
    )[0]

    assert ".archive-list a { grid-template-columns: 1fr; gap: 4px; }" in phone_rules


def test_reader_shell_uses_an_editorial_briefing_visual_language():
    style = STYLE_CSS.read_text()
    html = INDEX_HTML.read_text()

    assert 'class="brand-kicker">GRCInsight</span>' in html
    assert "font-family: Georgia" in style
    assert "linear-gradient(" not in style
    assert "box-shadow:" not in style
    assert "font-size: 11px" not in style
    assert "font-size: 12px" not in style

    card_rule = style.split(".card {", 1)[1].split("}", 1)[0]
    assert "border: 1px" not in card_rule
    assert "border-radius" not in card_rule


def test_reader_shell_removes_dashboard_gadgets_and_keeps_one_mobile_index():
    app = APP_JS.read_text()
    html = INDEX_HTML.read_text()

    for retired_markup in (
        'id="progress"',
        'id="topbarLinks"',
        'class="reference-legend"',
        'class="shortcuts"',
        'id="copyStatus"',
        'id="backToTop"',
        "static/tags.js",
    ):
        assert retired_markup not in html

    assert html.count('id="mobileToc"') == 1
    assert "window.GRCInsightTags" not in app
    assert "highlightPills" not in app
    assert "buildTopbar" not in app
    assert "collapse-toggle" not in app
    assert "copy-link" not in app
    assert "cardCollapsed" not in app


def test_reader_shell_is_light_and_fully_expanded_without_javascript():
    style = STYLE_CSS.read_text()
    app = APP_JS.read_text()

    root_tokens = style.split(":root {", 1)[1].split("}", 1)[0]
    assert "--paper: #f7f3ea" in root_tokens
    assert "body.dark" in style
    assert "body.light" not in style
    assert ".card.collapsed" not in style
    assert "prefers-color-scheme" not in app
