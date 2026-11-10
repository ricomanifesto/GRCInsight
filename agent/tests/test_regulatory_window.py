"""The "Past 30 days" sub-section: this site's first citations and the Federal Register lane."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import runpy
import time
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_BUILDER = REPO_ROOT / "scripts" / "build_site.py"
FIXTURES = REPO_ROOT / "agent" / "tests" / "fixtures" / "federal-register"
UTC = timezone.utc
STATE_FOUR = "it lists none published"
REGULATORY_CARD = '<section class="card"><h2>Sourced Regulatory Changes</h2>'


@pytest.fixture(scope="module")
def ns() -> dict:
    return runpy.run_path(str(SITE_BUILDER))


@pytest.fixture(scope="module")
def sh(ns) -> Any:
    return ns["source_history"]


@pytest.fixture(scope="module")
def rw(ns) -> Any:
    return ns["regulatory_window"]


@pytest.fixture(scope="module")
def rr(ns) -> Any:
    return ns["regulatory_register"]


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def key(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H-%M-%SZ")


def report(sh, generated: str, *regulatory, findings=()):
    when = at(generated)
    return sh.Report(
        key=key(when),
        generated=when,
        findings=tuple(findings),
        anchors=frozenset(),
        regulatory_rows=len(regulatory),
        regulatory_sources=tuple(sh.Source(url=url, title=title) for url, title in regulatory),
    )


def lane(html: str, name: str) -> str:
    # A lane holds no nested <div>, so its first closing tag ends it.
    match = re.search(
        rf'<div class="regulatory-lane" data-lane="{name}"[^>]*>(.*?)</div>', html, re.S
    )
    return match.group(1) if match else ""


def state(html: str, name: str) -> str | None:
    match = re.search(rf'data-lane="{name}" data-state="([a-z0-9-]+)"', html)
    return match.group(1) if match else None


BLOCK = re.compile(r"</?(?:h3|h4|p|li|ol|ul|div|details|summary)\b[^>]*>")


def text(html: str) -> str:
    spaced = BLOCK.sub(" ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", spaced)).strip()


FR_A = "https://www.federalregister.gov/documents/2026/07/31/2026-15601/modernization-of-alerting"
FR_A_OTHER = "https://federalregister.gov/documents/2026/07/31/2026-15601"
AGENCY = ("https://agency.example.gov/notice/1", "Agency notice on data breach rules")


# ----- Lane 1: this site's reports -----


def test_one_register_document_under_two_url_spellings_is_one_item_at_the_earlier_report(sh, rw):
    anchor = "2026-11-10T09:00:00"
    first = report(sh, "2026-11-01T08:00:00", (FR_A, "FCC alerting rule"))
    later = report(sh, "2026-11-05T08:00:00", (FR_A_OTHER, "FCC alerting rule (again)"))
    current = report(sh, anchor)
    html = rw.window_html(at(anchor), current.key, [first, later, current], None)
    archive = lane(html, "archive")
    assert state(html, "archive") == "entries"
    assert archive.count("<li") == 1
    assert f'href="{FR_A}"' in archive and "FCC alerting rule</a>" in archive
    assert f'href="archive/{first.key}/">in that report</a>' in archive
    assert later.key not in archive


def test_an_item_first_cited_before_the_window_is_not_listed_and_is_counted(sh, rw):
    anchor = "2026-11-10T09:00:00"
    old = report(sh, "2026-10-01T09:00:00", AGENCY)
    repeat = report(sh, "2026-11-05T09:00:00", AGENCY, (FR_A, "FCC alerting rule"))
    html = rw.window_html(at(anchor), "x", [old, repeat], None)
    archive = lane(html, "archive")
    assert "Agency notice" not in archive and archive.count("<li") == 1
    assert "1 more cited in this period was first cited earlier and is not listed." in text(archive)


def test_the_thirty_day_edge_is_exact_and_independent_of_local_time(sh, rw, monkeypatch):
    monkeypatch.setenv("TZ", "Pacific/Kiritimati")
    time.tzset()
    try:
        anchor = at("2026-11-10T09:00:00")
        edge = report(sh, "2026-10-11T09:00:00", (FR_A, "Edge rule"))
        inside = rw.window_html(anchor, "x", [edge], None)
        assert state(inside, "archive") == "entries" and "Edge rule" in inside
        before = report(sh, "2026-10-11T08:59:59", (FR_A, "Edge rule"))
        outside = rw.window_html(anchor, "x", [before], None)
        assert "Edge rule" not in lane(outside, "archive")
        assert state(outside, "archive") == "no-corpus"
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()


def test_the_current_report_first_citing_an_item_reads_in_this_report(sh, rw):
    current = report(sh, "2026-11-10T09:00:00", AGENCY)
    html = rw.window_html(current.generated, current.key, [current], None)
    archive = lane(html, "archive")
    assert "in this report." in text(archive)
    assert f"archive/{current.key}/" not in archive


def test_a_non_register_source_is_keyed_by_url_and_a_non_http_url_is_text(sh, rw):
    current = report(
        sh,
        "2026-11-10T09:00:00",
        AGENCY,
        ("https://agency.example.gov/notice/1?utm=x", "Same page, different URL"),
        ("javascript:alert(1)", "Unsafe <scheme>"),
    )
    html = rw.window_html(current.generated, current.key, [current], None)
    archive = lane(html, "archive")
    assert archive.count("<li") == 3
    assert "javascript:" not in archive and "Unsafe &lt;scheme&gt;" in archive


def test_each_archive_state_has_its_exact_wording(sh, rw):
    anchor = at("2026-11-10T15:22:00")
    window = "October 11, 2026 at 15:22 UTC to November 10, 2026 at 15:22 UTC"
    none = rw.window_html(anchor, "x", [], None)
    assert state(none, "archive") == "no-corpus"
    assert (
        f"No comparable report was published from {window}; nothing is known from this "
        "site's reports." in text(lane(none, "archive"))
    )
    plain = [report(sh, "2026-11-01T10:00:00"), report(sh, "2026-11-02T10:00:00")]
    rows = rw.window_html(anchor, "x", plain, None)
    assert state(rows, "archive") == "no-rows"
    assert (
        f"None of the 2 comparable reports published from {window} contains a sourced "
        "regulatory change." in text(lane(rows, "archive"))
    )
    old = report(sh, "2026-09-01T10:00:00", AGENCY)
    repeats = rw.window_html(anchor, "x", [old, report(sh, "2026-11-01T10:00:00", AGENCY)], None)
    assert state(repeats, "archive") == "repeats-only"
    assert (
        f"The 1 comparable report published from {window} cites 1 regulatory source, first "
        "cited before this window; it is not listed." in text(lane(repeats, "archive"))
    )
    entries = rw.window_html(anchor, "x", [report(sh, "2026-11-01T10:00:00", AGENCY)], None)
    assert state(entries, "archive") == "entries"
    for html in (none, rows, repeats, entries):
        assert (
            lane(html, "archive")
            .rstrip()
            .endswith(
                '<a href="archive/#sources-by-control">How these reports are compared</a></p>'
            )
        )


def test_reports_after_the_anchor_never_affect_an_older_view(sh, rw):
    anchor = at("2026-11-01T10:00:00")
    future = report(sh, "2026-11-05T10:00:00", AGENCY)
    current = report(sh, "2026-11-01T10:00:00")
    html = rw.window_html(anchor, current.key, [current, future], None)
    assert state(html, "archive") == "no-rows"
    assert "None of the 1 comparable" not in html
    assert "The 1 comparable report published" in text(lane(html, "archive"))


def test_a_non_comparable_report_contributes_nothing_and_still_anchors_the_window(ns, rw):
    generated = at("2026-11-10T09:00:00")
    archived_md = REPO_ROOT / "site" / "archive" / key(generated) / "report.md"
    markdown = "# GRC Intelligence Report\n**Generated:** 2026-11-10T09:00:00Z\n\n## Risk\nText."
    corpus = ns["history_corpus"](
        markdown,
        None,
        None,
        "",
        [(archived_md, markdown, None, {}, generated)],
        [None],
        [""],
    )
    assert corpus.current is None and corpus.reports == [] and len(corpus.excluded) == 1
    html = ns["regulatory_window_section"](corpus, None)
    assert state(html, "archive") == "no-corpus"
    assert "November 10, 2026 at 09:00 UTC" in html


# ----- Lane 2: what the register lane may claim -----


def fr_doc(number: str, day: str, *, title="Cybersecurity Rule", type_="Rule", **extra) -> dict:
    y, m, d = day.split("-")
    doc = {
        "action": "Final rule." if type_ == "Rule" else "Proposed rule.",
        "agencies": ["Federal Communications Commission"],
        "comments_close_on": None,
        "docket_ids": [],
        "document_number": number,
        "effective_on": None,
        "html_url": f"https://www.federalregister.gov/documents/{y}/{m}/{d}/{number}/a-title",
        "matched_terms": ["cybersecurity"],
        "publication_date": day,
        "regulation_id_numbers": [],
        "title": title,
        "type": type_,
    }
    doc.update(extra)
    return doc


def register(rr, checked_at, query_from, query_to, docs=(), *, truncated=False, invalid=0):
    docs = sorted(docs, key=lambda d: (d["publication_date"], d["document_number"]), reverse=True)
    value = {
        "documents": docs,
        "read": {
            "candidates": 200 if truncated else max(1, len(docs) + invalid),
            "checked_at": checked_at,
            "invalid_matches": invalid,
            "pages_read": 2 if truncated else 1,
            "query_from": query_from,
            "query_to": query_to,
            "truncated": truncated,
        },
        "schema": rr.SCHEMA,
        "source": rr.source_record(),
    }
    return rr.validate_register_bytes(rr.serialize_register(value))


def saved(rr, name: str) -> dict:
    fixture = FIXTURES / f"fixture-window-{name}.json"
    query_from, query_to = name.split("_")
    return rr.assemble(
        [json.loads(fixture.read_text())], "2026-11-10T18:28:59Z", query_from, query_to
    )


def test_combined_empty_and_incomplete_read_is_limited_and_never_says_none(rr, rw):
    anchor = at("2026-11-10T15:22:31")
    file = register(rr, "2026-11-10T12:20:00Z", "2026-10-20", "2026-11-11", truncated=True)
    html = rw.window_html(anchor, "x", [], file)
    reg = text(lane(html, "register"))
    assert state(html, "register") == "limited"
    assert "As read November 10, 2026 at 12:20 UTC, no match in the records available." in reg
    assert (
        "The read of November 10, 2026 at 12:20 UTC covers October 20 to November 10, 2026 of "
        "the window October 12 to November 10, 2026; documents published on its other dates are "
        "not known." in reg
    )
    assert "The read stopped at its two-page limit, so further candidates were not examined." in reg
    assert STATE_FOUR not in html


def test_entries_with_unreadable_records_say_the_list_may_be_incomplete(rr, rw):
    file = register(
        rr,
        "2026-11-10T12:20:00Z",
        "2026-09-26",
        "2026-11-11",
        [fr_doc("2026-21001", "2026-11-02")],
        invalid=2,
    )
    html = rw.window_html(at("2026-11-10T15:00:00"), "x", [], file)
    reg = text(lane(html, "register"))
    assert state(html, "register") == "limited"
    assert "Cybersecurity Rule" in reg
    assert "As read November 10, 2026 at 12:20 UTC, this list may be incomplete." in reg
    assert "2 matching records had unreadable metadata and are not listed." in reg
    assert STATE_FOUR not in html


def test_a_report_before_the_days_read_is_limited_until_the_read_lands(rr, rw):
    anchor = at("2026-11-10T09:00:00")
    yesterday = register(rr, "2026-11-09T12:20:00Z", "2026-09-25", "2026-11-10")
    before = rw.window_html(anchor, "x", [], yesterday)
    assert state(before, "register") == "limited"
    assert "covers October 12 to November 9, 2026 of the window" in text(before)
    today = register(rr, "2026-11-10T12:20:00Z", "2026-09-26", "2026-11-11")
    after = rw.window_html(anchor, "x", [], today)
    assert state(after, "register") == "complete"
    assert (
        "As read November 10, 2026 at 12:20 UTC, it lists none published from October 12 to "
        "November 10, 2026." in text(after)
    )


def test_a_read_older_than_the_window_has_not_read_it(rr, rw):
    old = register(rr, "2026-09-01T12:20:00Z", "2026-07-18", "2026-09-02")
    html = rw.window_html(at("2026-11-10T09:00:00"), "x", [], old)
    assert state(html, "register") == "not-read"
    assert (
        "The Federal Register has not been read for this window. Last read: September 1, 2026 "
        "at 12:20 UTC." in text(html)
    )
    assert STATE_FOUR not in html and "no match" not in html


def test_august_fixture_lists_the_fcc_rule_only_inside_its_window(rr, rw):
    file = saved(rr, "2026-07-01_2026-08-15")
    inside = rw.window_html(at("2026-08-29T13:00:00"), "x", [], file)
    assert "2026-15601" in lane(inside, "register")
    assert "Final rule." in lane(inside, "register")
    for day in ("2026-08-30T13:00:00", "2026-07-30T13:00:00"):
        assert "2026-15601" not in rw.window_html(at(day), "x", [], file)


def test_november_fixture_is_complete_with_no_entry(rr, rw):
    file = saved(rr, "2026-09-27_2026-11-10")
    html = rw.window_html(at("2026-11-10T15:22:31"), "x", [], file)
    assert state(html, "register") == "complete"
    assert (
        "As read November 10, 2026 at 18:28 UTC, it lists none published from October 12 to "
        "November 10, 2026." in text(html)
    )
    assert "<li" not in lane(html, "register").split("<details")[0]


def test_register_dates_print_as_given_with_their_basis(rr, rw):
    docs = [
        fr_doc("2026-22750", "2026-11-09", effective_on="2026-01-04"),
        fr_doc(
            "2026-22751", "2026-11-08", effective_on="2031-06-01", comments_close_on="2027-01-11"
        ),
    ]
    file = register(rr, "2026-11-10T12:20:00Z", "2026-09-26", "2026-11-11", docs)
    reg = text(lane(rw.window_html(at("2026-11-10T15:00:00"), "x", [], file), "register"))
    assert "Effective 2026-01-04 (register metadata)" in reg
    assert "Effective 2031-06-01 (register metadata)" in reg
    assert "Comments close 2027-01-11 (register metadata)" in reg
    assert "Published 2026-11-09 (Federal Register publication date)" in reg


def test_without_a_valid_file_the_register_lane_is_absent(rw):
    html = rw.window_html(at("2026-11-10T15:00:00"), "x", [], None)
    assert 'data-lane="register"' not in html and "Federal Register" not in html


def test_the_lane_opens_with_its_scope_and_discloses_what_it_covers(rr, rw):
    file = register(rr, "2026-11-10T12:20:00Z", "2026-09-26", "2026-11-11")
    reg = lane(rw.window_html(at("2026-11-10T15:00:00"), "x", [], file), "register")
    assert text(reg).startswith(
        "U.S. Federal Register Official register, narrow filter: final and proposed U.S. federal "
        "rules with a security term in the title."
    )
    details = reg.split('<details class="regulatory-scope">')[1]
    assert "<summary>What this covers</summary>" in details
    for term in rr.TERMS:
        assert term in details
    assert "the document itself governs its legal effect" in details


# ----- Bounds, merging and escaping -----


def docs_in_window(n: int) -> list[dict]:
    return [fr_doc(f"2026-{21000 + i}", f"2026-11-{1 + i % 9:02d}") for i in range(n)]


def test_six_register_entries_show_five_and_one_behind_show_more(rr, rw):
    file = register(rr, "2026-11-10T12:20:00Z", "2026-09-26", "2026-11-11", docs_in_window(6))
    reg = lane(rw.window_html(at("2026-11-10T15:00:00"), "x", [], file), "register")
    visible, hidden = reg.split('<details class="regulatory-more">')
    assert visible.count('<li class="regulatory-entry"') == 5
    assert '<summary>Show 1 more</summary><ol class="regulatory-entries" start="6">' in hidden
    assert hidden.split("</details>")[0].count('<li class="regulatory-entry"') == 1


def test_thirty_one_register_entries_render_thirty_and_a_route(rr, rw):
    file = register(rr, "2026-11-10T12:20:00Z", "2026-09-26", "2026-11-11", docs_in_window(31))
    reg = lane(rw.window_html(at("2026-11-10T15:00:00"), "x", [], file), "register")
    assert reg.count('<li class="regulatory-entry"') == 30
    assert "<summary>Show 25 more</summary>" in reg
    assert "1 more is not shown here;" in text(reg)
    assert 'href="regulatory-register.json"' in reg


def test_thirty_one_archive_items_render_thirty_and_route_to_the_archive(sh, rw):
    sources = [(f"https://agency.example.gov/rule/{i}", f"Rule {i}") for i in range(31)]
    current = report(sh, "2026-11-10T09:00:00", *sources)
    archive = lane(rw.window_html(current.generated, current.key, [current], None), "archive")
    assert archive.count('<li class="regulatory-entry"') == 30
    assert "<summary>Show 25 more</summary>" in archive
    assert "1 more first cited in this period is not shown here;" in text(archive)
    assert '<a href="archive/">' in archive


def test_shared_identifiers_name_three_others_and_a_correction_stays_its_own_entry(rr, rw):
    rin = ["3060-AK57"]
    docs = [
        fr_doc(f"2026-2100{i}", f"2026-11-0{i + 1}", regulation_id_numbers=rin) for i in range(5)
    ]
    docs.append(
        fr_doc(
            "2026-21009", "2026-11-09", action="Final rule; correction.", regulation_id_numbers=rin
        )
    )
    file = register(rr, "2026-11-10T12:20:00Z", "2026-09-26", "2026-11-11", docs)
    reg = lane(rw.window_html(at("2026-11-10T15:00:00"), "x", [], file), "register")
    entries = re.findall(r'<li class="regulatory-entry".*?</li>', reg, re.S)
    assert len(entries) == 6
    first = text(entries[0])
    assert first.startswith("Cybersecurity Rule") and "Final rule; correction." in first
    assert (
        "Same regulation identifier number as 2026-21004, 2026-21003, 2026-21002 and 2 more."
        in first
    )
    assert (
        "Same regulation identifier number as 2026-21009, 2026-21003, 2026-21002 and 2 more."
        in text(entries[1])
    )


def test_a_document_both_lanes_would_list_appears_once_in_the_register_lane(sh, rr, rw):
    first = report(sh, "2026-11-03T09:00:00", (FR_A_OTHER, "FCC alerting rule"))
    current = report(sh, "2026-11-10T09:00:00")
    doc = fr_doc(
        "2026-15601", "2026-11-02", title="Protecting Communications From Cybersecurity Threats"
    )
    file = register(rr, "2026-11-10T12:20:00Z", "2026-09-26", "2026-11-11", [doc])
    html = rw.window_html(current.generated, current.key, [first, current], file)
    archive, reg = lane(html, "archive"), lane(html, "register")
    assert "<li" not in archive
    assert "1 also appears under the Federal Register below." in text(archive)
    assert (
        "First cited by this site's reports November 3, 2026 at 09:00 UTC, in that report."
        in text(reg)
    )
    assert f'href="archive/{first.key}/">in that report</a>' in reg
    assert html.count("2026-15601") == 2  # the register link and its document number


def test_a_document_only_reachable_in_the_data_file_stays_in_the_archive_lane(sh, rr, rw):
    docs = docs_in_window(30) + [fr_doc("2026-15601", "2026-10-13")]
    file = register(rr, "2026-11-10T12:20:00Z", "2026-09-26", "2026-11-11", docs)
    first = report(sh, "2026-11-03T09:00:00", (FR_A, "FCC alerting rule"))
    html = rw.window_html(at("2026-11-10T15:00:00"), "x", [first], file)
    assert "FCC alerting rule" in lane(html, "archive")
    assert "also appear" not in html


def test_titles_and_names_are_escaped(sh, rr, rw):
    doc = fr_doc(
        "2026-21001",
        "2026-11-02",
        title='Cybersecurity <b>"Rule"</b> & more',
        agencies=['Agency <script>&"'],
    )
    file = register(rr, "2026-11-10T12:20:00Z", "2026-09-26", "2026-11-11", [doc])
    current = report(sh, "2026-11-10T09:00:00", ("https://a.example.gov/x?a=1&b=2", 'Title "<i>"'))
    html = rw.window_html(current.generated, current.key, [current], file)
    assert "<b>" not in html and "<script>" not in html and "<i>" not in html
    assert "Cybersecurity &lt;b&gt;&quot;Rule&quot;&lt;/b&gt; &amp; more" in html
    assert 'href="https://a.example.gov/x?a=1&amp;b=2"' in html


def test_an_empty_lane_stays_within_five_sentences(rr, rw):
    file = register(
        rr, "2026-11-10T12:20:00Z", "2026-10-20", "2026-11-11", truncated=True, invalid=3
    )
    reg = lane(rw.window_html(at("2026-11-10T15:00:00"), "x", [], file), "register")
    body = text(reg.split("<details")[0]).replace("U.S.", "US").removeprefix("US Federal Register ")
    sentences = [part for part in re.split(r"(?<=\.)\s+", body) if part]
    assert len(sentences) == 5, sentences  # scope, state, and the three limits


# ----- Placement and preservation -----


REPORT = (
    '<section class="card executive-summary"><h2>Executive Summary</h2><p>Lead.</p></section>'
    f"{REGULATORY_CARD}\n<p>No sourced regulatory changes identified in the supplied evidence.</p></section>"
    '<section class="card evidence-section"><h2>Evidence and Decisions</h2></section>'
)


def test_the_sub_section_closes_the_regulatory_card_and_adds_no_contents_entry(rw):
    block = rw.window_html(at("2026-11-10T15:00:00"), "x", [], None)
    placed = rw.with_regulatory_window(REPORT, block)
    card = placed.split(REGULATORY_CARD)[1].split('<section class="card evidence-section">')[0]
    assert card.endswith(block + "</section>")
    assert '<h3 id="regulatory-window-title">Past 30 days</h3>' in block
    assert "<h2" not in block
    assert placed.index("Executive Summary") < placed.index("Past 30 days")
    assert placed.replace(block, "") == REPORT


@pytest.mark.parametrize("copies", [0, 2])
def test_a_missing_or_duplicated_regulatory_card_omits_the_sub_section(rw, copies, capsys):
    body = REPORT.replace(REGULATORY_CARD, '<section class="card"><h2>Other</h2>')
    body += f"{REGULATORY_CARD}</section>" * copies if copies else ""
    block = rw.window_html(at("2026-11-10T15:00:00"), "x", [], None)
    assert rw.with_regulatory_window(body, block) == body
    assert "regulatory window omitted" in capsys.readouterr().err


def test_the_report_container_is_otherwise_identical(ns, rw):
    template = (
        '<time class="subtitle" id="generated">Loading</time>'
        "<!-- PUBLICATION_NOTICE_START --><!-- PUBLICATION_NOTICE_END -->"
        "<!-- REPORT_CONTENT_START --><!-- REPORT_CONTENT_END -->"
    )
    markdown = "# GRC Intelligence Report\n**Generated:** 2026-11-10T15:00:00Z\n\n## Risk\nText."
    block = rw.window_html(at("2026-11-10T15:00:00"), "x", [], None)
    with_block = ns["current_index_html"](
        template, markdown, report_html=REPORT, regulatory_html=block
    )
    without = ns["current_index_html"](template, markdown, report_html=REPORT)
    assert block in with_block and with_block.replace(block, "") == without


# ----- The real tree and the builder -----


@pytest.fixture(scope="module")
def real(ns):
    markdown = ns["read_text"](ns["INDEX_MD"])
    template = ns["read_text"](ns["INDEX_HTML"])
    state_, history = ns["load_publication_artifacts"](ns["EVIDENCE_MANIFEST"].read_bytes())
    return markdown, template, state_, history


def without_register(ns, monkeypatch, tmp_path) -> Path:
    """Point the builder at an explicit absent register, whatever the tree holds."""
    path = tmp_path / "absent" / "regulatory-register.json"
    monkeypatch.setitem(ns["expected_outputs"].__globals__, "REGULATORY_REGISTER", path)
    return path


def recount_archive_lane(ns, markdown: str) -> tuple[str, int, int, int]:
    """An independent recount of lane 1 from the archive: (state, reports, cited, listed)."""
    from core.regulatory_dates import federal_register_api_url

    def item(url: str) -> str:
        api_url = federal_register_api_url(url)
        return f"document:{api_url}" if api_url else f"url:{url}"

    anchor = ns["parse_generated"](ns["report_fields"](markdown)["generated"])
    start = anchor - timedelta(days=30)
    corpus: dict[str, tuple] = {}
    candidates = [
        (report_md.parent.name, report_md.read_text(encoding="utf-8"), report_md.parent)
        for report_md in ns["ARCHIVE_DIR"].glob("????-??-??T??-??-??Z/report.md")
    ]
    candidates.append((ns["archive_slug"](anchor), markdown, ns["SITE_DIR"]))
    for key_, body, folder in candidates:
        generated = ns["parse_generated"](ns["report_fields"](body)["generated"])
        if generated > anchor or key_ in corpus:
            continue
        manifest = json.loads((folder / "evidence-manifest.json").read_text())
        plan = ns["eligible_plan"](body, manifest)
        if plan is not None:
            urls = [
                manifest["sources"][row.source_id - 1]["url"] for row in plan.regulatory_changes
            ]
            corpus[key_] = (generated, key_, urls)
    first: dict[str, datetime] = {}
    for generated, _key, urls in sorted(corpus.values()):
        for url in urls:
            first.setdefault(item(url), generated)
    inside = [entry for entry in corpus.values() if entry[0] >= start]
    rows = sum(len(urls) for _g, _k, urls in inside)
    cited = {item(url) for _g, _k, urls in inside for url in urls}
    listed = {i for i in cited if first[i] >= start}
    if not inside:
        state_ = "no-corpus"
    elif rows == 0:
        state_ = "no-rows"
    else:
        state_ = "entries" if listed else "repeats-only"
    return state_, len(inside), len(cited), len(listed)


def test_the_real_page_states_what_a_recount_of_its_corpus_shows(ns, real, monkeypatch, tmp_path):
    # Production content may gain regulatory rows; the page must match a recount either way.
    without_register(ns, monkeypatch, tmp_path)
    markdown, template, state_, history = real
    page = ns["expected_outputs"](markdown, template, state_, history)[ns["INDEX_HTML"]]
    expected, reports, cited, listed = recount_archive_lane(ns, markdown)
    archive = text(lane(page, "archive"))
    assert state(page, "archive") == expected
    assert reports > 0
    if expected == "no-rows":
        assert (
            f"None of the {reports} comparable reports published" in archive
            if reports != 1
            else "The 1 comparable report published" in archive
        )
    elif expected == "repeats-only":
        assert f" {cited} regulatory source" in archive
    elif expected == "entries":
        assert lane(page, "archive").count('<li class="regulatory-entry"') == min(listed, 30)
    assert 'data-lane="register"' not in page
    card = page.split(REGULATORY_CARD)[1].split('<section class="card')[0]
    assert "Past 30 days" in card


def test_builds_are_deterministic_and_an_invalid_file_equals_no_file(
    ns, real, rr, tmp_path, monkeypatch, capsys
):
    path = without_register(ns, monkeypatch, tmp_path)
    absent = ns["expected_outputs"](*real)
    path.parent.mkdir()
    path.write_text('{"schema": "wrong"}\n')
    invalid = ns["expected_outputs"](*real)
    assert invalid == absent
    assert "register lane omitted (rule 1" in capsys.readouterr().err
    path.write_bytes(rr.serialize_register(saved(rr, "2026-09-27_2026-11-10")))
    present = ns["expected_outputs"](*real)
    assert present == ns["expected_outputs"](*real)
    index = ns["INDEX_HTML"]
    assert 'data-lane="register"' in present[index]
    assert {p for p in present} == {p for p in absent}
    for p in present:
        if p != index:
            assert present[p] == absent[p], p


def test_a_lane_error_omits_only_the_sub_section(ns, real, rw, monkeypatch, capsys):
    absent = ns["expected_outputs"](*real)

    def boom(*_args, **_kwargs):
        raise RuntimeError("forced")

    monkeypatch.setattr(rw, "window_html", boom)
    degraded = ns["expected_outputs"](*real)
    index = ns["INDEX_HTML"]
    assert "Past 30 days" not in degraded[index]
    assert 'id="earlier-coverage-title"' in degraded[index]
    assert "optional regulatory window omitted" in capsys.readouterr().err
    for p in degraded:
        if p != index:
            assert degraded[p] == absent[p]


def test_process_time_zone_does_not_change_the_page(ns, real, monkeypatch):
    baseline = ns["expected_outputs"](*real)[ns["INDEX_HTML"]]
    monkeypatch.setenv("TZ", "Asia/Kolkata")
    time.tzset()
    try:
        assert ns["expected_outputs"](*real)[ns["INDEX_HTML"]] == baseline
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()
    assert os.environ.get("TZ") is None


def test_a_nested_object_in_matched_terms_omits_only_the_register_lane(ns, rr, tmp_path, capsys):
    # Reported in review: an unhashable term once escaped the validator as TypeError.
    register_ = saved(rr, "2026-07-01_2026-08-15")
    register_["documents"][0]["matched_terms"] = [{}]
    path = tmp_path / "regulatory-register.json"
    path.write_bytes(rr.serialize_register(register_))
    assert ns["register_for_build"](path) is None
    assert "site build: register lane omitted (rule 8:" in capsys.readouterr().err


MALFORMED = ({}, [{}], [[]], [None], None, 1.5, True, "x", -1)


def _paths(register_: dict) -> list[tuple]:
    paths: list[tuple] = [(name,) for name in register_]
    paths += [("source", name) for name in register_["source"]]
    paths += [("read", name) for name in register_["read"]]
    paths += [("documents", 0, name) for name in register_["documents"][0]]
    return paths


def test_malformed_nested_json_anywhere_is_refused_by_a_numbered_rule(ns, rr, tmp_path, capsys):
    base = saved(rr, "2026-07-01_2026-08-15")
    path = tmp_path / "regulatory-register.json"
    checked = 0
    for where in _paths(base):
        for value in MALFORMED:
            register_ = json.loads(json.dumps(base))
            target = register_
            for step in where[:-1]:
                target = target[step]
            target[where[-1]] = value
            path.write_bytes(rr.serialize_register(register_))
            result = ns["register_for_build"](path)
            err = capsys.readouterr().err
            assert "unexpected" not in err, (where, value, err)
            assert result is not None or "register lane omitted (rule " in err, (where, value)
            checked += 1
    assert checked == len(_paths(base)) * len(MALFORMED)
