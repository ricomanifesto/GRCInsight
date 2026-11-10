"""Source history across archived reports: first citations and sources by control.

Everything here is a mechanical projection of archived report plans. The
comparable history is the set of archived reports whose structured plan
reproduces their published body; nothing else is compared, and nothing is
inferred from a shared control, a shared source or a missing day.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from html import escape
from typing import Any, Iterable, Sequence
from urllib.parse import urlsplit

from core.report_plan import CONTROLS

WINDOW = timedelta(days=30)
UTC = timezone.utc

EXCLUSION_TEXT = {
    "no_plan": ("report predates the structured plan", "reports predate the structured plan"),
    "older_version": ("report uses an older plan version", "reports use an older plan version"),
    "not_reproduced": (
        "report's plan does not reproduce its published text",
        "reports' plans do not reproduce their published text",
    ),
    "manifest_unavailable": (
        "report has no readable evidence manifest",
        "reports have no readable evidence manifest",
    ),
}


@dataclass(frozen=True)
class Source:
    url: str
    title: str


@dataclass(frozen=True)
class Finding:
    number: int  # 1-based, in the report's published finding order
    control_id: str
    label: str
    sources: tuple[Source, ...]


@dataclass(frozen=True)
class Report:
    key: str  # archive slug
    generated: datetime  # UTC
    findings: tuple[Finding, ...]
    anchors: frozenset[int]  # finding numbers that have an anchor in the rendered page
    regulatory_rows: int = 0


@dataclass(frozen=True)
class Excluded:
    key: str
    generated: datetime
    reason: str


@dataclass(frozen=True)
class Citation:
    report: Report
    finding: Finding
    title: str


@dataclass(frozen=True)
class SourceStatus:
    source: Source
    earlier: Citation | None  # None: first cited in this report


@dataclass(frozen=True)
class FindingCoverage:
    finding: Finding
    sources: tuple[SourceStatus, ...]

    @property
    def has_new_source(self) -> bool:
        return any(status.earlier is None for status in self.sources)


@dataclass(frozen=True)
class CurrentCoverage:
    findings: tuple[FindingCoverage, ...]  # new-source findings first, each group in report order
    earlier_reports: int
    first_comparable: datetime | None

    @property
    def new_findings(self) -> int:
        return sum(1 for finding in self.findings if finding.has_new_source)


@dataclass(frozen=True)
class WindowEntry:
    control_id: str
    url: str
    first: Citation  # earliest citation under this control in all comparable history
    predates_window: bool


@dataclass(frozen=True)
class ControlGroup:
    control_id: str
    entries: tuple[WindowEntry, ...]


@dataclass(frozen=True)
class Gap:
    start: datetime
    end: datetime
    whole_days: bool


@dataclass(frozen=True)
class WindowView:
    start: datetime
    end: datetime
    reports_in_window: int
    groups: tuple[ControlGroup, ...]
    gaps: tuple[Gap, ...]
    older_reports: int
    newer_reports: int
    excluded_by_reason: dict[str, int]
    regulatory_rows: int


# ----- Building the corpus -----


def findings_from_plan(
    groups: Sequence[Sequence[Any]], sources: Sequence[Any]
) -> tuple[Finding, ...]:
    """Findings in published order; each keeps every source its rows cite, in order."""
    findings = []
    for number, group in enumerate(groups, start=1):
        first = group[0]
        cited: dict[str, Source] = {}
        for row in group:
            for source_id in row.source_ids:
                entry = sources[source_id - 1]
                url = entry.get("url") if isinstance(entry, dict) else None
                if not isinstance(url, str) or not url:
                    continue
                title = entry.get("title")
                cited.setdefault(
                    url, Source(url=url, title=title if isinstance(title, str) else url)
                )
        findings.append(
            Finding(
                number=number,
                control_id=first.control_id,
                label=first.headline or first.focus,
                sources=tuple(cited.values()),
            )
        )
    return tuple(findings)


def exclusion_reason(manifest: object) -> str:
    """Why an archived report is not in the comparable history."""
    if not isinstance(manifest, dict):
        return "manifest_unavailable"
    if manifest.get("report_plan") is None:
        return "no_plan"
    if manifest.get("report_contract_version") not in {5, 6}:
        return "older_version"
    return "not_reproduced"


def _ordered(reports: Iterable[Report]) -> list[Report]:
    return sorted(reports, key=lambda report: (report.generated, report.key))


def first_citations(
    reports: Iterable[Report],
) -> tuple[dict[str, Citation], dict[tuple[str, str], Citation]]:
    """Earliest citation of each URL, and of each (control, URL), by Generated time."""
    by_url: dict[str, Citation] = {}
    by_control: dict[tuple[str, str], Citation] = {}
    for report in _ordered(reports):
        for finding in report.findings:
            for source in finding.sources:
                citation = Citation(report=report, finding=finding, title=source.title)
                by_url.setdefault(source.url, citation)
                by_control.setdefault((finding.control_id, source.url), citation)
    return by_url, by_control


def current_coverage(current: Report, reports: Iterable[Report]) -> CurrentCoverage:
    """Compare the current report with every strictly earlier comparable report."""
    earlier = [report for report in reports if report.generated < current.generated]
    by_url, _ = first_citations(earlier)
    rows = tuple(
        FindingCoverage(
            finding=finding,
            sources=tuple(
                SourceStatus(source=source, earlier=by_url.get(source.url))
                for source in finding.sources
            ),
        )
        for finding in current.findings
    )
    ordered = tuple(row for row in rows if row.has_new_source) + tuple(
        row for row in rows if not row.has_new_source
    )
    ordered_earlier = _ordered(earlier)
    return CurrentCoverage(
        findings=ordered,
        earlier_reports=len(ordered_earlier),
        first_comparable=ordered_earlier[0].generated if ordered_earlier else None,
    )


def _gaps(start: datetime, end: datetime, reports: Sequence[Report]) -> tuple[Gap, ...]:
    """UTC calendar intervals inside [start, end] with no comparable report."""
    times = sorted(report.generated for report in reports)
    segments: list[Gap] = []
    day = start.date()
    while day <= end.date():
        day_start = datetime.combine(day, time(0), tzinfo=UTC)
        day_end = day_start + timedelta(days=1)
        seg_start, seg_end = max(day_start, start), min(day_end, end)
        covered = any(seg_start <= t < seg_end or (t == end and seg_end == end) for t in times)
        if not covered:
            whole = seg_start == day_start and seg_end == day_end
            if whole and segments and segments[-1].whole_days and segments[-1].end == seg_start:
                segments[-1] = Gap(start=segments[-1].start, end=seg_end, whole_days=True)
            else:
                segments.append(Gap(start=seg_start, end=seg_end, whole_days=whole))
        day += timedelta(days=1)
    return tuple(segments)


def window_view(
    anchor: datetime, reports: Iterable[Report], excluded: Iterable[Excluded]
) -> WindowView:
    """Distinct (control, URL) pairs cited inside the 30 days ending at ``anchor``."""
    all_reports = _ordered(reports)
    start, end = anchor - WINDOW, anchor
    inside = [report for report in all_reports if start <= report.generated <= end]
    _, by_control = first_citations(all_reports)
    members: dict[tuple[str, str], WindowEntry] = {}
    for report in inside:
        for finding in report.findings:
            for source in finding.sources:
                key = (finding.control_id, source.url)
                if key not in members:
                    first = by_control[key]
                    members[key] = WindowEntry(
                        control_id=finding.control_id,
                        url=source.url,
                        first=first,
                        predates_window=first.report.generated < start,
                    )
    groups = []
    for control_id in CONTROLS:
        entries = sorted(
            (entry for entry in members.values() if entry.control_id == control_id),
            key=lambda entry: (
                -entry.first.report.generated.timestamp(),
                entry.first.report.key,
                entry.first.finding.number,
                entry.url,
            ),
        )
        if entries:
            groups.append(ControlGroup(control_id=control_id, entries=tuple(entries)))
    reasons: dict[str, int] = {}
    for item in sorted(excluded, key=lambda item: item.key):
        reasons[item.reason] = reasons.get(item.reason, 0) + 1
    return WindowView(
        start=start,
        end=end,
        reports_in_window=len(inside),
        groups=tuple(groups),
        gaps=_gaps(start, end, inside),
        older_reports=sum(1 for report in all_reports if report.generated < start),
        newer_reports=sum(1 for report in all_reports if report.generated > end),
        excluded_by_reason={key: reasons[key] for key in EXCLUSION_TEXT if key in reasons},
        regulatory_rows=sum(report.regulatory_rows for report in inside),
    )


def build_views(
    current: Report | None,
    anchor: datetime,
    reports: Sequence[Report],
    excluded: Sequence[Excluded],
) -> tuple[str, str]:
    """Both history surfaces as HTML: (current-report block, archive section)."""
    current_html = earlier_coverage_html(current, reports) if current is not None else ""
    return current_html, sources_by_control_html(window_view(anchor, reports, excluded))


# ----- Rendering -----


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _date(value: datetime) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def _minute(value: datetime) -> str:
    return f"{_date(value)} at {value.strftime('%H:%M')} UTC"


def _second(value: datetime) -> str:
    return f"{_date(value)}, {value.strftime('%H:%M:%S')} UTC"


def _time(value: datetime, text: str) -> str:
    return f'<time datetime="{escape(_iso(value), quote=True)}">{escape(text)}</time>'


def _http_url(url: str) -> bool:
    try:
        return urlsplit(url.strip()).scheme.lower() in {"http", "https"}
    except ValueError:
        return False


def _source_link(source_url: str, title: str) -> str:
    if _http_url(source_url):
        return f'<a href="{escape(source_url, quote=True)}">{escape(title)}</a>'
    return escape(title)


def _finding_href(citation: Citation, prefix: str) -> str | None:
    if citation.finding.number not in citation.report.anchors:
        return None
    return f"{prefix}{citation.report.key}/#finding-{citation.finding.number}"


def _control(control_id: str) -> str:
    entry = CONTROLS.get(control_id)
    return entry[0] if entry else control_id


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def earlier_coverage_html(current: Report, reports: Iterable[Report]) -> str:
    coverage = current_coverage(current, reports)
    total = len(current.findings)
    if total == 0:
        return ""
    if coverage.first_comparable is None:
        scope = (
            "No earlier report in this archive is comparable, so the comparable retained "
            "history starts with this report."
        )
    else:
        scope = (
            f"Compared with the {_plural(coverage.earlier_reports, 'earlier report', 'earlier reports')} "
            f"that carry a structured plan reproducing their text, published since "
            f"{_time(coverage.first_comparable, _minute(coverage.first_comparable))}. "
            "Older reports are not compared, so “first cited” means first in that comparable retained history."
        )
    items = []
    for row in coverage.findings:
        number = row.finding.number
        label = escape(row.finding.label)
        heading = f'<a href="#finding-{number}">{label}</a>' if number in current.anchors else label
        lines = []
        for status in row.sources:
            source = _source_link(status.source.url, status.source.title)
            if status.earlier is None:
                lines.append(f"<li>{source}: first cited in this report.</li>")
                continue
            citation = status.earlier
            href = _finding_href(citation, "archive/")
            where = (
                f'<a href="{escape(href, quote=True)}">in that report</a>'
                if href
                else f"in the report generated {_time(citation.report.generated, _minute(citation.report.generated))}"
            )
            lines.append(
                f"<li>{source}: first cited "
                f"{_time(citation.report.generated, _minute(citation.report.generated))}, "
                f"{where}, under {escape(_control(citation.finding.control_id))}.</li>"
            )
        items.append(f'<li>{heading}<ul class="history-sources">{"".join(lines)}</ul></li>')
    summary = (
        f"{coverage.new_findings} of this report's {_plural(total, 'finding', 'findings')} "
        f"{'cites' if coverage.new_findings == 1 else 'cite'} at least one source that no earlier report "
        "in the comparable retained history cited."
    )
    # A briefing card: result first, method last, listed by the contents index.
    return (
        '<section class="card history-section" aria-labelledby="earlier-coverage-title">'
        '<h2 id="earlier-coverage-title">Earlier coverage</h2>'
        f"<p>{summary}</p>"
        f'<ol class="history-findings">{"".join(items)}</ol>'
        f"<p>{scope}</p>"
        '<p><a href="archive/#sources-by-control">Sources by control, last 30 days</a></p>'
        "</section>"
    )


def _gap_text(gap: Gap) -> str:
    if gap.whole_days:
        last = gap.end - timedelta(days=1)
        if last.date() == gap.start.date():
            return f"{gap.start.strftime('%B')} {gap.start.day}"
        if last.month == gap.start.month:
            return f"{gap.start.strftime('%B')} {gap.start.day}–{last.day}"
        return f"{gap.start.strftime('%B')} {gap.start.day}–{last.strftime('%B')} {last.day}"
    day = f"{gap.start.strftime('%B')} {gap.start.day}"
    if gap.start.time() != time(0):
        return f"{day} from {gap.start.strftime('%H:%M')} UTC"
    return f"{day} until {gap.end.strftime('%H:%M')} UTC"


def sources_by_control_html(view: WindowView) -> str:
    window = f"{_time(view.start, _second(view.start))} to {_time(view.end, _second(view.end))}"
    sentences = [
        f"Sources cited by the {_plural(view.reports_in_window, 'report', 'reports')} published from "
        f"{window} whose structured plan reproduces their published text.",
    ]
    if view.gaps:
        sentences.append(
            "No such report falls in these UTC intervals: "
            + ", ".join(escape(_gap_text(gap)) for gap in view.gaps)
            + "; nothing is known about those intervals from here."
        )
    if view.older_reports:
        sentences.append(
            f"{_plural(view.older_reports, 'comparable report is', 'comparable reports are')} older than this window; "
            "a source they first cited is shown with that earlier time."
        )
    if view.newer_reports:
        sentences.append(
            f"{_plural(view.newer_reports, 'comparable report is', 'comparable reports are')} newer than the current report and not included."
        )
    for reason, count in view.excluded_by_reason.items():
        one, many = EXCLUSION_TEXT[reason]
        sentences.append(
            f"{count} {one if count == 1 else many} and {'is' if count == 1 else 'are'} listed below but not included."
        )
    sentences.append("A control is a topic: sources under one control are not one event.")
    if view.regulatory_rows:
        sentences.append(
            f"These reports contain {_plural(view.regulatory_rows, 'sourced regulatory change', 'sourced regulatory changes')}."
        )
    else:
        sentences.append(
            "None of these reports contains a sourced regulatory change; that describes these reports, not regulatory activity."
        )
    groups = []
    for group in view.groups:
        entries = []
        for entry in group.entries:
            first = entry.first
            href = _finding_href(first, "")
            when = _time(first.report.generated, _minute(first.report.generated))
            where = (
                f'<a href="{escape(href, quote=True)}">first cited {when}</a>'
                if href
                else f"first cited {when}"
            )
            note = " (before this window)" if entry.predates_window else ""
            entries.append(
                f'<li>{_source_link(entry.url, first.title)} <span class="history-meta">{where}{note}</span></li>'
            )
        count = len(group.entries)
        groups.append(
            f'<details class="history-control"><summary>{escape(_control(group.control_id))} · '
            f'{count} {"source" if count == 1 else "sources"}</summary><ol>{"".join(entries)}</ol></details>'
        )
    if groups:
        body = "".join(groups)
    elif view.reports_in_window:
        # A comparable plan may carry regulatory changes and no control findings.
        body = (
            f"<p>The {_plural(view.reports_in_window, 'report in this window cites', 'reports in this window cite')} "
            "no finding sources to group by control.</p>"
        )
    else:
        body = "<p>No comparable report falls in this window.</p>"
    return f"""      <section class="history-shell" id="sources-by-control" aria-labelledby="sources-by-control-title">
        <h2 id="sources-by-control-title">Sources by control, last 30 days</h2>
        <p class="history-scope">{" ".join(sentences)}</p>
        {body}
      </section>
"""
