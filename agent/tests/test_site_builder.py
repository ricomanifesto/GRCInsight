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


def test_archive_detail_chrome_adds_icons_without_changing_report_body():
    namespace = builder_namespace()
    generated = namespace["DATED_DIGEST_HANDOFF_BOUNDARY"]
    report_body = (
        '<main class="container archive-report">'
        '<section data-era="original">Publication-era body.</section>'
        "</main>"
    )
    html = f"<html><head><title>Archive</title></head><body>{report_body}</body></html>"

    first = namespace["with_archive_detail_chrome"](html, generated)
    second = namespace["with_archive_detail_chrome"](first, generated)

    assert first == second
    assert report_body in first
    assert first.count('href="../../static/favicon.ico"') == 1
    assert first.count('href="../../static/icon.svg"') == 1
    assert first.count('href="../../static/apple-touch-icon.png"') == 1


def test_secondary_pages_link_site_icons_explicitly():
    namespace = builder_namespace()
    boundary = namespace["DATED_DIGEST_HANDOFF_BOUNDARY"]
    history = {
        "schema_version": 1,
        "max_entries": 30,
        "history_started_at": "2026-08-14T14:07:22Z",
        "schedule": {"cadence": "daily", "time_utc": "13:00"},
        "events": [],
    }

    archive_html = namespace["archive_index_html"]([report_tuple(namespace, boundary)])
    history_html = namespace["publication_history_html"](history)

    for html in (archive_html, history_html):
        assert 'href="../static/favicon.ico"' in html
        assert 'href="../static/icon.svg"' in html
        assert 'href="../static/apple-touch-icon.png"' in html


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
            "report_generated_at": "2026-08-14T13:00:00Z",
            "refusal_category": "provider_quota",
        },
        {"schedule": {"cadence": "daily", "time_utc": "13:00"}},
    )

    assert "Publication update" in html
    assert "August 14, 2026 at 14:07:22 UTC" in html
    assert "August 14, 2026 at 13:00:00 UTC" in html
    assert "Showing the report generated on" in html
    assert "refresh failed" in html
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


def test_batch_rendering_matches_isolated_rendering():
    namespace = builder_namespace()
    first = "# Report\n\n## Summary\n\nSee [one](https://example.com/a?x=$&y=1).\n"
    second = "# Report\n\n## Summary\n\n- [two](/b) and [three](#c)\n"
    batched = namespace["render_reports"]([(first, None), (second, None)])
    assert batched == [namespace["render_report"](first), namespace["render_report"](second)]
    assert namespace["render_reports"]([]) == []
    # Link destinations are inserted literally, never as replacement patterns.
    assert 'href="https://example.com/a?x=$&amp;y=1"' in batched[0]


# ----- Source history: earlier coverage and sources by control -----

import json  # noqa: E402
import re  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import pytest  # noqa: E402

V5_FIXTURE = REPO_ROOT / "agent" / "tests" / "fixtures" / "report-v5-2026-10-29"
UTC = timezone.utc


def history_module():
    builder_namespace()  # puts scripts/ and agent/ on sys.path
    import source_history

    return source_history


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def report(sh, generated: str, *findings, regulatory_rows=0):
    when = at(generated)
    built = tuple(
        sh.Finding(
            number=n,
            control_id=control,
            label=f"Finding {n}",
            sources=tuple(sh.Source(url=url, title=title) for url, title in sources),
        )
        for n, (control, sources) in enumerate(findings, start=1)
    )
    return sh.Report(
        key=when.strftime("%Y-%m-%dT%H-%M-%SZ"),
        generated=when,
        findings=built,
        anchors=frozenset(f.number for f in built),
        regulatory_rows=regulatory_rows,
    )


A = ("https://news.example.test/a", "Article A")
B = ("https://news.example.test/b", "Article B")
C = ("https://news.example.test/c", "Article C")


def test_one_url_cited_by_three_reports_is_one_source_first_cited_earliest():
    sh = history_module()
    reports = [
        report(sh, "2026-11-01T10:00:00", ("third_party_risk", [A])),
        report(sh, "2026-11-02T10:00:00", ("third_party_risk", [A])),
        report(sh, "2026-11-03T10:00:00", ("third_party_risk", [A])),
    ]
    by_url, by_control = sh.first_citations(reports)
    assert set(by_url) == {A[0]}
    assert by_url[A[0]].report.key == "2026-11-01T10-00-00Z"
    assert by_url[A[0]].finding.number == 1
    view = sh.window_view(reports[-1].generated, reports, [])
    (entry,) = [e for group in view.groups for e in group.entries]
    assert entry.first.report.key == "2026-11-01T10-00-00Z"
    html = sh.sources_by_control_html(view)
    assert 'href="2026-11-01T10-00-00Z/#finding-1"' in html


def test_one_url_under_two_controls_is_listed_under_each_at_its_own_first_citation():
    sh = history_module()
    reports = [
        report(sh, "2026-11-01T10:00:00", ("vulnerability_management", [A])),
        report(sh, "2026-11-02T10:00:00", ("third_party_risk", [A])),
    ]
    view = sh.window_view(reports[-1].generated, reports, [])
    firsts = {g.control_id: [e.first.report.key for e in g.entries] for g in view.groups}
    assert firsts["vulnerability_management"] == ["2026-11-01T10-00-00Z"]
    assert firsts["third_party_risk"] == ["2026-11-02T10-00-00Z"]
    current_html = sh.earlier_coverage_html(reports[-1], reports)
    assert "under Vulnerability management" in current_html
    assert 'href="archive/2026-11-01T10-00-00Z/#finding-1"' in current_html


def test_new_and_previously_cited_sources_in_one_finding_are_attributed_separately():
    sh = history_module()
    earlier = report(sh, "2026-11-01T10:00:00", ("monitoring", [A]))
    current = report(sh, "2026-11-02T10:00:00", ("monitoring", [A, B]), ("governance", [A]))
    coverage = sh.current_coverage(current, [earlier, current])
    assert coverage.new_findings == 1
    first, second = coverage.findings
    assert first.finding.number == 1  # the finding with a new source leads
    assert [(s.source.url, s.earlier is None) for s in first.sources] == [
        (A[0], False),
        (B[0], True),
    ]
    assert all(s.earlier is not None for s in second.sources)
    html = sh.earlier_coverage_html(current, [earlier, current])
    assert "1 of this report's 2 findings" in html


def test_ineligible_reports_count_as_not_included_with_their_reason():
    sh = history_module()
    reasons = {
        sh.exclusion_reason(None),
        sh.exclusion_reason({"schema_version": 3, "sources": []}),
        sh.exclusion_reason({"report_contract_version": 3, "report_plan": {}, "sources": []}),
        sh.exclusion_reason({"report_contract_version": 4, "report_plan": {}, "sources": []}),
        sh.exclusion_reason({"report_contract_version": 5, "report_plan": {}, "sources": []}),
    }
    assert reasons == {"manifest_unavailable", "no_plan", "older_version", "not_reproduced"}
    current = report(sh, "2026-11-02T10:00:00", ("monitoring", [A]))
    excluded = [
        sh.Excluded(
            key="2026-10-01T00-00-00Z", generated=at("2026-10-01T00:00:00"), reason="no_plan"
        ),
        sh.Excluded(
            key="2026-10-02T00-00-00Z", generated=at("2026-10-02T00:00:00"), reason="older_version"
        ),
    ]
    view = sh.window_view(current.generated, [current], excluded)
    assert view.excluded_by_reason == {"no_plan": 1, "older_version": 1}
    html = sh.sources_by_control_html(view)
    assert "1 report predates the structured plan" in html
    assert "1 report uses an older plan version" in html


def test_v5_report_whose_plan_does_not_reproduce_its_body_is_not_eligible():
    namespace = builder_namespace()
    markdown = (V5_FIXTURE / "report.md").read_text(encoding="utf-8")
    manifest = json.loads((V5_FIXTURE / "evidence-manifest.json").read_text(encoding="utf-8"))
    assert namespace["eligible_plan"](markdown, manifest) is not None
    tampered = markdown.replace(
        "## Evidence and Decisions", "## Evidence and Decisions\n\nEdited.", 1
    )
    assert namespace["eligible_plan"](tampered, manifest) is None
    legacy = {key: value for key, value in manifest.items() if key != "report_plan"}
    assert namespace["eligible_plan"](markdown, legacy) is None


def test_window_edges_are_inclusive_at_thirty_days_and_independent_of_local_time(monkeypatch):
    import time

    sh = history_module()
    anchor = at("2026-11-10T15:22:31.954351")
    edge = report(sh, "2026-10-11T15:22:31.954351", ("monitoring", [A]))
    before = report(sh, "2026-10-11T15:22:30.954351", ("monitoring", [B]))
    current = report(sh, "2026-11-10T15:22:31.954351", ("monitoring", [C]))
    reports = [before, edge, current]
    results = []
    for zone in ("UTC", "America/Chicago", "Asia/Kolkata"):
        monkeypatch.setenv("TZ", zone)
        time.tzset()
        view = sh.window_view(anchor, reports, [])
        results.append(
            ([e.url for g in view.groups for e in g.entries], sh.sources_by_control_html(view))
        )
    time.tzset()
    urls, html = results[0]
    assert A[0] in urls and B[0] not in urls and C[0] in urls
    assert all(r == results[0] for r in results)
    assert "2026-10-11T15:22:31.954351Z" in html and "2026-11-10T15:22:31.954351Z" in html


def test_uncovered_dates_are_reported_as_intervals_not_as_no_activity():
    sh = history_module()
    reports = [
        report(sh, "2026-11-06T12:00:00", ("monitoring", [A])),
        report(sh, "2026-11-10T09:00:00", ("monitoring", [B])),
    ]
    view = sh.window_view(at("2026-11-10T09:00:00"), reports, [])
    html = sh.sources_by_control_html(view)
    assert "November 7–9" in html
    assert "October 11 from 09:00 UTC" in html  # partial boundary day, not the whole day
    assert "nothing is known" in html
    for word in ("recurring", "trend", "again", "increase", "escalat"):
        assert word not in html.lower()


def test_single_eligible_report_reads_first_cited_in_this_report_and_nothing_empty():
    sh = history_module()
    current = report(sh, "2026-11-10T09:00:00", ("monitoring", [A]), ("governance", [B]))
    html = sh.earlier_coverage_html(current, [current])
    assert html.count("first cited in this report") == 2
    assert "2 of this report's 2 findings" in html
    assert "<ul></ul>" not in html and "<ol></ol>" not in html
    archive_html = sh.sources_by_control_html(sh.window_view(current.generated, [current], []))
    assert "<ol></ol>" not in archive_html


def test_history_text_is_escaped_and_only_http_urls_become_links():
    sh = history_module()
    hostile = ("javascript:alert(1)", 'Tom & Jerry <script>"quoted"</script>')
    current = report(sh, "2026-11-10T09:00:00", ("monitoring", [hostile, A]))
    html = sh.earlier_coverage_html(current, [current]) + sh.sources_by_control_html(
        sh.window_view(current.generated, [current], [])
    )
    assert "<script>" not in html and "Tom &amp; Jerry &lt;script&gt;&quot;quoted&quot;" in html
    assert 'href="javascript:' not in html
    assert f'href="{A[0]}"' in html


def test_regulatory_sentence_states_only_the_count():
    sh = history_module()
    none = report(sh, "2026-11-10T09:00:00", ("monitoring", [A]))
    html = sh.sources_by_control_html(sh.window_view(none.generated, [none], []))
    assert "contains a sourced regulatory change" in html and "not regulatory activity" in html
    some = report(sh, "2026-11-10T09:00:00", ("monitoring", [A]), regulatory_rows=2)
    html = sh.sources_by_control_html(sh.window_view(some.generated, [some], []))
    assert "2 sourced regulatory changes" in html


def test_retained_publication_shows_the_block_beside_the_notice():
    namespace = builder_namespace()
    sh = history_module()
    template = INDEX_HTML.read_text(encoding="utf-8")
    markdown = (REPO_ROOT / "site" / "index.md").read_text(encoding="utf-8")
    history = json.loads((REPO_ROOT / "site" / "publication-history.json").read_text())
    generated = re.search(r"\*\*Generated:\*\*\s*(\S+)", markdown).group(1)
    state = {
        "outcome": "retained",
        "attempted_at": "2026-11-11T13:00:00Z",
        "report_generated_at": generated,
        "refusal_category": "report_quality",
    }
    current = report(sh, "2026-11-10T09:00:00", ("monitoring", [A]))
    block = sh.earlier_coverage_html(current, [current])
    built = namespace["current_index_html"](
        template, markdown, state, history, report_html="<p>x</p>", history_html=block
    )
    assert "publication-notice-title" in built and 'id="earlier-coverage-title"' in built
    assert built.index("publication-notice-title") < built.index("earlier-coverage-title")


# Real-archive checks share one build of the committed site.


@pytest.fixture(scope="module")
def real_build():
    namespace = builder_namespace()
    markdown = namespace["read_text"](namespace["INDEX_MD"])
    template = namespace["read_text"](namespace["INDEX_HTML"])
    manifest_bytes = namespace["EVIDENCE_MANIFEST"].read_bytes()
    state, history = namespace["load_publication_artifacts"](manifest_bytes)
    outputs = namespace["expected_outputs"](markdown, template, state, history)
    return namespace, outputs, (markdown, template, state, history)


def test_real_build_is_deterministic(real_build):
    namespace, outputs, inputs = real_build
    assert namespace["expected_outputs"](*inputs) == outputs


def test_real_build_leaves_every_archived_page_and_secondary_page_unchanged(real_build):
    namespace, outputs, _ = real_build
    archive_dir = namespace["ARCHIVE_DIR"]
    for path, content in outputs.items():
        if path in (namespace["INDEX_HTML"], archive_dir / "index.html"):
            continue
        assert path.read_text(encoding="utf-8") == content, path


def history_links(html: str, prefix: str) -> list[tuple[str, int]]:
    return [
        (slug, int(n))
        for slug, n in re.findall(
            rf'href="{re.escape(prefix)}(\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}Z)/#finding-(\d+)"',
            html,
        )
    ]


def test_every_real_history_link_targets_an_existing_finding(real_build):
    namespace, outputs, _ = real_build
    archive_dir = namespace["ARCHIVE_DIR"]
    current = outputs[namespace["INDEX_HTML"]]
    archive = outputs[archive_dir / "index.html"]
    links = history_links(current, "archive/") + history_links(archive, "")
    assert links, "expected history links in the real build"
    for slug, n in links:
        page = outputs[archive_dir / slug / "index.html"]
        assert f'id="finding-{n}"' in page, (slug, n)
    for n in re.findall(
        r'<a href="#finding-(\d+)"',
        current.split("EARLIER_COVERAGE_START")[1].split("EARLIER_COVERAGE_END")[0],
    ):
        assert f'id="finding-{n}"' in current


def test_real_sources_by_control_counts_equal_a_recount(real_build):
    namespace, outputs, (markdown, *_rest) = real_build
    archive_dir = namespace["ARCHIVE_DIR"]
    archive = outputs[archive_dir / "index.html"]
    section = archive.split('id="sources-by-control"')[1].split("</section>")[0]
    shown = {
        label: int(count)
        for label, count in re.findall(r"<summary>([^<]+?) · (\d+) sources?</summary>", section)
    }
    anchor = namespace["parse_generated"](namespace["report_fields"](markdown)["generated"])
    start = anchor - timedelta(days=30)
    from core.report_plan import CONTROLS, report_finding_groups

    pairs = set()
    for report_md in sorted(archive_dir.glob("????-??-??T??-??-??Z/report.md")):
        body = report_md.read_text(encoding="utf-8")
        generated = namespace["parse_generated"](namespace["report_fields"](body)["generated"])
        if not start <= generated <= anchor:
            continue
        manifest = json.loads((report_md.parent / "evidence-manifest.json").read_text())
        plan = namespace["eligible_plan"](body, manifest)
        if plan is None:
            continue
        for group in report_finding_groups(plan):
            for source_id in dict.fromkeys(i for row in group for i in row.source_ids):
                pairs.add((group[0].control_id, manifest["sources"][source_id - 1]["url"]))
    recount = {}
    for control_id, _url in pairs:
        label = CONTROLS[control_id][0]
        recount[label] = recount.get(label, 0) + 1
    assert shown and shown == recount


def test_a_projection_error_yields_exactly_the_no_history_pages(real_build, monkeypatch, capsys):
    namespace, outputs, inputs = real_build
    sh = history_module()

    def boom(*_args, **_kwargs):
        raise RuntimeError("forced")

    monkeypatch.setattr(sh, "build_views", boom)
    degraded = namespace["expected_outputs"](*inputs)
    archive_index = namespace["ARCHIVE_DIR"] / "index.html"
    assert 'id="sources-by-control"' not in degraded[archive_index]
    assert 'id="earlier-coverage-title"' not in degraded[namespace["INDEX_HTML"]]
    assert {p for p in degraded} == {p for p in outputs}
    for path in degraded:
        if path not in (namespace["INDEX_HTML"], archive_index):
            assert degraded[path] == outputs[path]
    assert "optional source history omitted" in capsys.readouterr().err


def test_empty_window_and_window_without_finding_sources_are_stated_differently():
    sh = history_module()
    # Nothing comparable inside the window: the only report is older than 30 days.
    old = report(sh, "2026-09-01T10:00:00", ("monitoring", [A]))
    empty = sh.sources_by_control_html(sh.window_view(at("2026-11-10T09:00:00"), [old], []))
    assert "No comparable report falls in this window." in empty
    assert "<details" not in empty
    # A comparable regulatory-only report inside the window has no finding sources.
    regulatory_only = report(sh, "2026-11-10T09:00:00", regulatory_rows=1)
    view = sh.window_view(regulatory_only.generated, [regulatory_only], [])
    html = sh.sources_by_control_html(view)
    assert view.reports_in_window == 1 and view.groups == ()
    assert "Sources cited by the 1 report published" in html
    assert "1 sourced regulatory change" in html
    assert "No comparable report falls in this window" not in html
    assert "The 1 report in this window cites no finding sources to group by control." in html
    assert "<details" not in html
