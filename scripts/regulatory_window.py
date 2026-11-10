"""The "Past 30 days" sub-section of the Sourced Regulatory Changes card.

Two lanes, each with its own clock:

- This site's reports: regulatory sources that the comparable reports first
  cited in the 30 days ending at the current report, dated by that first
  citation. A later citation never refreshes an item's age.
- U.S. Federal Register: final and proposed federal rules with a security term
  in the title, dated by official publication, as the register listed them at
  one stated read time. Only a read that covers every date of the window, with
  no page limit hit and no unreadable match, may say the register lists none.

Nothing here changes a report count or sentence, reproduces generated text, or
states what a document requires.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html import escape
import re
import sys
from typing import Any, Sequence

from core.regulatory_dates import federal_register_api_url
from source_history import (
    WINDOW,
    Report,
    Source,
    _http_url,
    _minute,
    _plural,
    _source_link,
    _time,
)
import regulatory_register

UTC = timezone.utc
VISIBLE = 5
DISCLOSED = 25
RENDERED = VISIBLE + DISCLOSED
NAMED_PEERS = 3
REGISTER_DAYS = 30
REGULATORY_CARD = re.compile(r'<section class="card"><h2>Sourced Regulatory Changes</h2>')
NEXT_CARD = '<section class="card'
CARD_END = "</section>"
ARCHIVE_METHOD = '<p><a href="archive/#sources-by-control">How these reports are compared</a></p>'
REGISTER_SCOPE = (
    "Official register, narrow filter: final and proposed U.S. federal rules with a security "
    "term in the title."
)


# ----- Lane 1: this site's reports -----


@dataclass(frozen=True)
class FirstCitation:
    item: str  # "document:<number>" or "url:<stored URL>"
    document: str | None  # Federal Register document number, when the URL resolves to one
    source: Source  # as stored by the first report to cite it
    report: Report


@dataclass(frozen=True)
class ArchiveLane:
    start: datetime
    end: datetime
    reports: int  # comparable reports inside the window
    rows: int  # regulatory rows in those reports
    cited: int  # distinct items those rows cite
    listed: tuple[FirstCitation, ...]  # items first cited inside the window, newest first


def document_number(url: str) -> str | None:
    api_url = federal_register_api_url(url)
    return api_url.rsplit("/", 1)[1].removesuffix(".json") if api_url else None


def _item(source: Source) -> tuple[str, str | None]:
    document = document_number(source.url)
    return (f"document:{document}", document) if document else (f"url:{source.url}", None)


def archive_lane(anchor: datetime, reports: Sequence[Report]) -> ArchiveLane:
    """First citations over comparable history up to the anchor; never a later report."""
    corpus = sorted(
        {report.key: report for report in reports if report.generated <= anchor}.values(),
        key=lambda report: (report.generated, report.key),
    )
    first: dict[str, FirstCitation] = {}
    for report in corpus:
        for source in report.regulatory_sources:
            item, document = _item(source)
            first.setdefault(item, FirstCitation(item, document, source, report))
    start = anchor - WINDOW
    inside = [report for report in corpus if start <= report.generated]
    cited = {_item(source)[0] for report in inside for source in report.regulatory_sources}
    listed = sorted(
        (first[item] for item in cited if first[item].report.generated >= start),
        key=lambda citation: (-citation.report.generated.timestamp(), citation.item),
    )
    return ArchiveLane(
        start=start,
        end=anchor,
        reports=len(inside),
        rows=sum(len(report.regulatory_sources) for report in inside),
        cited=len(cited),
        listed=tuple(listed),
    )


# ----- Lane 2: U.S. Federal Register -----


@dataclass(frozen=True)
class RegisterLane:
    state: str  # "not-read", "limited" or "complete"; an absent file has no lane at all
    checked_at: datetime
    window: tuple[date, date]  # the 30 issue dates ending on the report's UTC date
    covered: tuple[date, date] | None  # the part of the window the read can know
    entries: tuple[dict[str, Any], ...]  # documents published in the window, newest first
    truncated: bool
    invalid_matches: int


def register_lane(anchor: datetime, register: dict[str, Any]) -> RegisterLane:
    read = register["read"]
    checked = datetime.strptime(read["checked_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    end = anchor.astimezone(UTC).date()
    start = end - timedelta(days=REGISTER_DAYS - 1)
    # A read cannot know documents published after the day it was made.
    low = max(start, date.fromisoformat(read["query_from"]))
    high = min(end, date.fromisoformat(read["query_to"]), checked.date())
    covered = (low, high) if low <= high else None
    entries = tuple(
        document
        for document in register["documents"]
        if start <= date.fromisoformat(document["publication_date"]) <= end
    )
    if covered is None and not entries:
        state = "not-read"
    elif covered != (start, end) or read["truncated"] or read["invalid_matches"] > 0:
        state = "limited"
    else:
        state = "complete"
    return RegisterLane(
        state=state,
        checked_at=checked,
        window=(start, end),
        covered=covered,
        entries=entries,
        truncated=read["truncated"],
        invalid_matches=read["invalid_matches"],
    )


# ----- Rendering -----


def _date_text(value: date) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def _date_range(start: date, end: date) -> str:
    if start == end:
        return _date_text(start)
    if start.year == end.year:
        return f"{start.strftime('%B')} {start.day} to {_date_text(end)}"
    return f"{_date_text(start)} to {_date_text(end)}"


def _entries(items: list[str]) -> tuple[str, int]:
    """At most five visible, 25 more behind one disclosure; returns the number not shown."""
    html = ""
    if items[:VISIBLE]:
        html += f'<ol class="regulatory-entries">{"".join(items[:VISIBLE])}</ol>'
    disclosed = items[VISIBLE:RENDERED]
    if disclosed:
        html += (
            f'<details class="regulatory-more"><summary>Show {len(disclosed)} more</summary>'
            f'<ol class="regulatory-entries" start="{VISIBLE + 1}">{"".join(disclosed)}</ol>'
            "</details>"
        )
    return html, max(0, len(items) - RENDERED)


def _report_link(report: Report, current_key: str) -> str:
    if report.key == current_key:
        return "in this report"
    return f'<a href="archive/{escape(report.key, quote=True)}/">in that report</a>'


def _first_cited(citation: FirstCitation) -> str:
    return _time(citation.report.generated, _minute(citation.report.generated))


def _archive_html(lane: ArchiveLane, current_key: str, merged: dict[str, FirstCitation]) -> str:
    window = f"{_time(lane.start, _minute(lane.start))} to {_time(lane.end, _minute(lane.end))}"
    reports = lane.reports
    lead, trailing, body = "", [], ""
    if reports == 0:
        state = "no-corpus"
        lead = (
            f"No comparable report was published from {window}; nothing is known from this "
            "site's reports."
        )
    elif lane.rows == 0:
        state = "no-rows"
        lead = (
            f"The 1 comparable report published from {window} does not contain a sourced "
            "regulatory change."
            if reports == 1
            else f"None of the {reports} comparable reports published from {window} contains "
            "a sourced regulatory change."
        )
    elif not lane.listed:
        state = "repeats-only"
        subject = (
            f"The 1 comparable report published from {window} cites"
            if reports == 1
            else f"The {reports} comparable reports published from {window} cite"
        )
        cited = (
            "1 regulatory source, first cited before this window; it is not listed."
            if lane.cited == 1
            else f"{lane.cited} regulatory sources, each first cited before this window; "
            "they are not listed."
        )
        lead = f"{subject} {cited}"
    else:
        state = "entries"
        lead = f"Regulatory sources first cited by this site's comparable reports from {window}."
        shown = [c for c in lane.listed if c.document is None or c.document not in merged]
        items = [
            f'<li class="regulatory-entry">{_source_link(c.source.url, c.source.title)}: '
            f"first cited {_first_cited(c)}, {_report_link(c.report, current_key)}.</li>"
            for c in shown
        ]
        body, hidden = _entries(items)
        if hidden:
            trailing.append(
                f"{hidden} more first cited in this period "
                f"{'is' if hidden == 1 else 'are'} not shown here; the "
                '<a href="archive/">archive index</a> lists every report.'
            )
        earlier = lane.cited - len(lane.listed)
        if earlier:
            trailing.append(
                f"{earlier} more cited in this period "
                f"{'was' if earlier == 1 else 'were'} first cited earlier and "
                f"{'is' if earlier == 1 else 'are'} not listed."
            )
        if merged:
            trailing.append(
                f"{len(merged)} also {'appears' if len(merged) == 1 else 'appear'} under the "
                "Federal Register below."
            )
    tail = f"<p>{' '.join(trailing)}</p>" if trailing else ""
    return (
        f'<div class="regulatory-lane" data-lane="archive" data-state="{state}">'
        f"<h4>This site's reports</h4><p>{lead}</p>{body}{tail}{ARCHIVE_METHOD}</div>"
    )


def _peers(entries: Sequence[dict[str, Any]]) -> dict[str, list[str]]:
    """Other listed documents sharing a regulation identifier number, exact equality only."""
    result: dict[str, list[str]] = {}
    for document in entries:
        own = set(document["regulation_id_numbers"])
        result[document["document_number"]] = [
            other["document_number"]
            for other in entries
            if other is not document and own & set(other["regulation_id_numbers"])
        ]
    return result


def _peer_text(peers: list[str]) -> str:
    named = peers[:NAMED_PEERS]
    rest = len(peers) - len(named)
    if rest:
        listed = f"{', '.join(named)} and {rest} more"
    elif len(named) > 1:
        listed = f"{', '.join(named[:-1])} and {named[-1]}"
    else:
        listed = named[0]
    return f"Same regulation identifier number as {escape(listed)}."


def _register_entry(
    document: dict[str, Any], peers: list[str], citation: FirstCitation | None, current_key: str
) -> str:
    title = escape(document["title"])
    url = document["html_url"]
    heading = f'<a href="{escape(url, quote=True)}">{title}</a>' if _http_url(url) else title
    meta = []
    if document["agencies"]:
        meta.append("; ".join(escape(name) for name in document["agencies"]))
    meta.append(escape(document["action"] or document["type"]))
    meta.append(
        f"Published {escape(document['publication_date'])} (Federal Register publication date)"
    )
    if document["effective_on"]:
        meta.append(f"Effective {escape(document['effective_on'])} (register metadata)")
    if document["comments_close_on"]:
        meta.append(f"Comments close {escape(document['comments_close_on'])} (register metadata)")
    meta.append(f"Document {escape(document['document_number'])}")
    lines = [heading, f'<span class="regulatory-meta">{" · ".join(meta)}</span>']
    if peers:
        lines.append(f'<span class="regulatory-related">{_peer_text(peers)}</span>')
    if citation is not None:
        lines.append(
            f'<span class="regulatory-related">First cited by this site\'s reports '
            f"{_first_cited(citation)}, {_report_link(citation.report, current_key)}.</span>"
        )
    return f'<li class="regulatory-entry">{" ".join(lines)}</li>'


def _register_html(lane: RegisterLane, current_key: str, merged: dict[str, FirstCitation]) -> str:
    read_at = _time(lane.checked_at, _minute(lane.checked_at))
    window = _date_range(*lane.window)
    limits = []
    if lane.covered != lane.window:
        if lane.covered is None:
            limits.append(
                f"The read of {read_at} covers none of the window {window}; documents published "
                "on its dates are not known."
            )
        else:
            limits.append(
                f"The read of {read_at} covers {_date_range(*lane.covered)} of the window "
                f"{window}; documents published on its other dates are not known."
            )
    if lane.truncated:
        limits.append(
            "The read stopped at its two-page limit, so further candidates were not examined."
        )
    if lane.invalid_matches:
        count = lane.invalid_matches
        limits.append(
            f"{_plural(count, 'matching record', 'matching records')} had unreadable metadata "
            f"and {'is' if count == 1 else 'are'} not listed."
        )
    opening = [REGISTER_SCOPE]
    after: list[str] = []
    body = ""
    if lane.state == "not-read":
        opening.append(
            f"The Federal Register has not been read for this window. Last read: {read_at}."
        )
    elif not lane.entries:
        if lane.state == "limited":
            opening += [f"As read {read_at}, no match in the records available.", *limits]
        else:
            opening.append(f"As read {read_at}, it lists none published from {window}.")
    else:
        peers = _peers(lane.entries)
        items = [
            _register_entry(
                d, peers[d["document_number"]], merged.get(d["document_number"]), current_key
            )
            for d in lane.entries
        ]
        body, hidden = _entries(items)
        if hidden:
            after.append(
                f"{hidden} more {'is' if hidden == 1 else 'are'} not shown here; the "
                f'<a href="regulatory-register.json">data file</a> lists '
                f"{'it' if hidden == 1 else 'them'}."
            )
        if lane.state == "limited":
            after += [f"As read {read_at}, this list may be incomplete.", *limits]
        else:
            after.append(f"As read {read_at}; issue dates {window}.")
    terms = ", ".join(escape(term) for term in regulatory_register.TERMS)
    scope = (
        '<details class="regulatory-scope"><summary>What this covers</summary>'
        f"<p>Listed: documents of type Rule or Proposed Rule whose title contains one of these "
        f"terms: {terms}. Notices, guidance, enforcement actions, state rules and other "
        "countries are not covered. Register metadata is informational; the document itself "
        "governs its legal effect.</p></details>"
    )
    tail = f"<p>{' '.join(after)}</p>" if after else ""
    return (
        f'<div class="regulatory-lane" data-lane="register" data-state="{lane.state}">'
        f"<h4>U.S. Federal Register</h4><p>{' '.join(opening)}</p>{body}{tail}{scope}</div>"
    )


def window_html(
    anchor: datetime,
    current_key: str,
    reports: Sequence[Report],
    register: dict[str, Any] | None,
) -> str:
    """The sub-section; the register lane appears only with a valid register file."""
    archive = archive_lane(anchor, reports)
    register_view = register_lane(anchor, register) if register is not None else None
    # One document, one entry: an item moves to the register lane only when that lane
    # actually renders the document, so its first-citation line stays visible.
    rendered = (
        {d["document_number"] for d in register_view.entries[:RENDERED]}
        if register_view is not None
        else set()
    )
    merged = {c.document: c for c in archive.listed if c.document in rendered}
    lanes = _archive_html(archive, current_key, merged)
    if register_view is not None:
        lanes += _register_html(register_view, current_key, merged)
    return (
        '<div class="regulatory-window" aria-labelledby="regulatory-window-title">'
        f'<h3 id="regulatory-window-title">Past 30 days</h3>{lanes}</div>'
    )


def with_regulatory_window(report_html: str, window: str) -> str:
    """Close the Sourced Regulatory Changes card with the sub-section, or omit it."""
    if not window:
        return report_html
    cards = list(REGULATORY_CARD.finditer(report_html))
    if len(cards) == 1:
        following = report_html.find(NEXT_CARD, cards[0].end())
        end = following if following != -1 else len(report_html)
        close = report_html.rfind(CARD_END, cards[0].end(), end)
        if close != -1 and not report_html[close + len(CARD_END) : end].strip():
            return report_html[:close] + window + report_html[close:]
    print(
        "site build: regulatory window omitted "
        "(Sourced Regulatory Changes card not found exactly once)",
        file=sys.stderr,
    )
    return report_html
