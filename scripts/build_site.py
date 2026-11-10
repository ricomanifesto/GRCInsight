#!/usr/bin/env python3
"""Build deterministic, pre-rendered current and archived report pages."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "agent"))

from core.report_plan import (  # noqa: E402
    CONTROL_REVIEWS,
    CONTROLS,
    PRIORITIES,
    load_report_plan,
    report_finding_groups,
    validate_rendered_report,
)

from public_site import emitted_origin, presentation_origins  # noqa: E402
import source_history  # noqa: E402
from publication_state import (  # noqa: E402
    PublicationStateError,
    category_label,
    validate_publication_history,
    validate_publication_state,
)

SITE_DIR = REPO_ROOT / "site"
INDEX_MD = SITE_DIR / "index.md"
INDEX_HTML = SITE_DIR / "index.html"
EVIDENCE_MANIFEST = SITE_DIR / "evidence-manifest.json"
PUBLICATION_STATE = SITE_DIR / "publication-state.json"
PUBLICATION_HISTORY = SITE_DIR / "publication-history.json"
PUBLICATION_HISTORY_INDEX = SITE_DIR / "publication-history" / "index.html"
ARCHIVE_DIR = SITE_DIR / "archive"
RENDERER_JS = SITE_DIR / "static" / "renderer.js"
REPORT_START = "<!-- REPORT_CONTENT_START -->"
REPORT_END = "<!-- REPORT_CONTENT_END -->"
PUBLICATION_NOTICE_START = "<!-- PUBLICATION_NOTICE_START -->"
PUBLICATION_NOTICE_END = "<!-- PUBLICATION_NOTICE_END -->"
PROVENANCE_BOUNDARY = '<section class="card report-provenance"><h2>About this report</h2>'
ARCHIVE_CONTEXT_START = "<!-- ARCHIVE_CONTEXT_START -->"
ARCHIVE_CONTEXT_END = "<!-- ARCHIVE_CONTEXT_END -->"
PUBLIC_SITE_URL = emitted_origin("GRCInsight")
DATED_DIGEST_HANDOFF_BOUNDARY = datetime(
    2026, 8, 14, 4, 49, 12, 35_399, tzinfo=timezone.utc
)


def fail(message: str) -> None:
    raise SystemExit(f"site build failed: {message}")


def read_text(path: Path) -> str:
    if not path.exists():
        fail(f"missing {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def report_fields(markdown: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in markdown.splitlines():
        if line.startswith("## "):
            break
        if line.startswith("# ") and "title" not in fields:
            fields["title"] = line[2:].strip()
            continue
        match = re.match(r"^\*\*([^*]+?):\*\*\s*(.+?)\s*$", line)
        if match is None:
            match = re.match(r"^\*\*([^*]+?):\s*(.+?)\*\*\s*$", line)
        if match:
            fields[match.group(1).strip().lower()] = match.group(2).strip()
    return fields


def parse_generated(value: str) -> datetime:
    if not value:
        fail("report is missing Generated metadata")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"invalid Generated timestamp: {error}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def display_date(value: datetime) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def display_timestamp(value: datetime) -> str:
    hour = value.strftime("%I").lstrip("0") or "0"
    return f"{display_date(value)} at {hour}{value.strftime(':%M:%S %p')} UTC"


def schedule_clause(history: dict[str, object]) -> str:
    schedule = history["schedule"]
    assert isinstance(schedule, dict)
    return (
        f"The next regular attempt runs {schedule['cadence']} at "
        f"{schedule['time_utc']} UTC."
    )


def publication_notice_html(
    state: dict[str, object] | None,
    history: dict[str, object] | None = None,
) -> str:
    if state is None or state["outcome"] != "retained":
        return ""
    if history is None:
        fail("retained publication notice requires publication history")
    attempted = parse_generated(str(state["attempted_at"]))
    generated_raw = str(state["report_generated_at"])
    generated = parse_generated(generated_raw)
    label = category_label(state["refusal_category"])
    reason = (
        "an unclassified provider failure"
        if label == "unclassified provider failure"
        else f"a {label} refusal"
    )
    attempted_raw = str(state["attempted_at"])
    return f"""          <aside class="publication-notice" aria-labelledby="publication-notice-title">
            <h2 id="publication-notice-title">Publication update</h2>
            <p>Showing the report generated on <time datetime="{escape(generated_raw, quote=True)}">{escape(display_date(generated))} at {generated.strftime('%H:%M:%S')} UTC</time>. The <time datetime="{escape(attempted_raw, quote=True)}">{escape(display_date(attempted))} at {attempted.strftime('%H:%M:%S')} UTC</time> refresh failed.</p>
            <details><summary>Refresh details and publication history</summary>
              <p>The previous report remains available because of {escape(reason)}. {escape(schedule_clause(history))} <a href="publication-history/">Recent publication history</a> · <a href="publication-state.json">Machine-readable status</a>.</p>
            </details>
          </aside>
"""


def load_publication_artifacts(
    manifest_bytes: bytes,
) -> tuple[dict[str, object], dict[str, object]]:
    try:
        state = json.loads(PUBLICATION_STATE.read_text(encoding="utf-8"))
        history = json.loads(PUBLICATION_HISTORY.read_text(encoding="utf-8"))
        validated_state = validate_publication_state(state, manifest_bytes)
        validated_history = validate_publication_history(
            history, validated_state, manifest_bytes
        )
        return validated_state, validated_history
    except FileNotFoundError as error:
        fail(f"missing {Path(error.filename).relative_to(REPO_ROOT)}")
    except (json.JSONDecodeError, PublicationStateError) as error:
        fail(f"invalid publication artifacts: {error}")


def archive_slug(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H-%M-%SZ")


def eligible_plan(markdown: str, manifest: object):
    """The review-map gate: a v5 or v6 plan that exactly reproduces this report's body."""
    if not isinstance(manifest, dict) or manifest.get("report_contract_version") not in {5, 6}:
        return None
    body_start = re.search(r"^## ", markdown, re.MULTILINE)
    if body_start is None:
        return None
    try:
        plan = load_report_plan(
            manifest["report_plan"],
            manifest["sources"],
            contract_version=manifest["report_contract_version"],
        )
        validate_rendered_report(
            markdown[body_start.start() :], plan, manifest["sources"], include_digest=True
        )
        return plan
    except (ValueError, KeyError, TypeError, IndexError):
        # This optional projection never repairs or substitutes report evidence.
        return None


def plan_review_rows(plan) -> list[dict[str, str]]:
    if plan is None:
        return []
    return [
        {
            "focus": group[0].focus,
            "headline": group[0].headline or group[0].focus,
            "control": CONTROLS[group[0].control_id][0],
            "owner": CONTROL_REVIEWS[group[0].control_id][0],
            "priority": PRIORITIES[group[0].priority],
        }
        for group in report_finding_groups(plan)
    ]


def review_map_rows(markdown: str, manifest: object) -> list[dict[str, str]]:
    """Project only a v5 or v6 plan that exactly reproduces this report's body."""
    return plan_review_rows(eligible_plan(markdown, manifest))


def read_manifest(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


RENDER_BATCH_SCRIPT = r"""
const fs = require('fs');
const vm = require('vm');
const rendererPath = process.argv[1];
const renderer = new vm.Script(fs.readFileSync(rendererPath, 'utf8'), { filename: 'renderer.js' });
const {origins, reports} = JSON.parse(fs.readFileSync(0, 'utf8'));
const rendered = reports.map(({markdown, reviewMap}, index) => {
  // A fresh context per report keeps each rendering isolated, exactly as if
  // it ran in its own process; only the compiled script is shared.
  const context = { window: {} };
  vm.createContext(context);
  try {
    renderer.runInContext(context);
    return context.window.GRCInsightRenderer.renderReportDocument(markdown, reviewMap, origins);
  } catch (error) {
    error.message = `report ${index}: ${error.message}`;
    throw error;
  }
});
process.stdout.write(JSON.stringify(rendered));
"""


def render_reports(
    reports: list[tuple[str, object]],
    review_maps: list[list[dict[str, str]]] | None = None,
) -> list[str]:
    """Render (markdown, manifest) pairs with one Node process for the batch.

    ``review_maps`` lets a caller that already gated each plan pass the rows
    instead of loading and validating every plan a second time.
    """
    if not reports:
        return []
    if review_maps is None:
        review_maps = [review_map_rows(markdown, manifest) for markdown, manifest in reports]
    result = subprocess.run(
        ["node", "-e", RENDER_BATCH_SCRIPT, str(RENDERER_JS)],
        input=json.dumps({
            "origins": presentation_origins(),
            "reports": [
                {"markdown": markdown, "reviewMap": review_map}
                for (markdown, _manifest), review_map in zip(reports, review_maps)
            ],
        }),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail((result.stderr or result.stdout).strip() or "renderer failed")
    rendered = json.loads(result.stdout)
    if not isinstance(rendered, list) or len(rendered) != len(reports):
        fail("renderer returned an unexpected number of reports")
    return rendered


def render_report(markdown: str, manifest: object = None) -> str:
    return render_reports([(markdown, manifest)])[0]


def current_index_html(
    template: str,
    markdown: str,
    publication_state: dict[str, object] | None = None,
    publication_history: dict[str, object] | None = None,
    manifest: object = None,
    report_html: str | None = None,
    history_html: str = "",
) -> str:
    fields = report_fields(markdown)
    generated_raw = fields.get("generated", "")
    generated = parse_generated(generated_raw)
    if report_html is None:
        report_html = render_report(markdown, manifest)
    report_html, after_report = with_earlier_coverage(report_html, history_html)
    report_node = (
        f"{REPORT_START}\n"
        f'          <div id="report" class="report" data-prerendered="true" '
        f'data-public-origins="{escape(json.dumps(presentation_origins()), quote=True)}" '
        f'data-generated-at="{escape(generated_raw, quote=True)}">{report_html}</div>\n'
        f"{after_report}"
        f"          {REPORT_END}"
    )
    region = re.compile(rf"{re.escape(REPORT_START)}.*?{re.escape(REPORT_END)}", re.DOTALL)
    if len(region.findall(template)) != 1:
        fail("index.html must contain one report content marker pair")
    # A generated report may legitimately contain backslashes (for example,
    # Windows paths). A callable replacement keeps re.sub from interpreting
    # them as replacement-string escapes or group references.
    built = region.sub(lambda _match: report_node, template)
    generated_node = (
        f'<time class="subtitle" id="generated" '
        f'datetime="{escape(generated_raw, quote=True)}">'
        f"Generated {display_date(generated)}</time>"
    )
    built, count = re.subn(
        r'<time class="subtitle" id="generated"(?: datetime="[^"]*")?>.*?</time>',
        generated_node,
        built,
        count=1,
    )
    if count != 1:
        fail("index.html is missing the generated time element")
    notice_region = re.compile(
        rf"{re.escape(PUBLICATION_NOTICE_START)}.*?" rf"{re.escape(PUBLICATION_NOTICE_END)}",
        re.DOTALL,
    )
    if len(notice_region.findall(built)) != 1:
        fail("index.html must contain one publication notice marker pair")
    notice_node = (
        f"{PUBLICATION_NOTICE_START}\n"
        f"{publication_notice_html(publication_state, publication_history)}"
        f"          {PUBLICATION_NOTICE_END}"
    )
    built = notice_region.sub(lambda _match: notice_node, built)
    return built


def with_earlier_coverage(report_html: str, history_html: str) -> tuple[str, str]:
    """Place the optional history card immediately before About this report.

    Returns the report HTML and anything to place directly after the report
    container. History never precedes the report: without exactly one
    provenance boundary the card follows the container, with a diagnostic.
    """
    if not history_html:
        return report_html, ""
    if report_html.count(PROVENANCE_BOUNDARY) == 1:
        return report_html.replace(PROVENANCE_BOUNDARY, history_html + PROVENANCE_BOUNDARY, 1), ""
    print(
        "site build: earlier coverage placed after the report "
        "(provenance boundary not found exactly once)",
        file=sys.stderr,
    )
    return report_html, f"          {history_html}\n"


def historical_context_note(archive_href: str | None = None) -> str:
    boundary_iso = DATED_DIGEST_HANDOFF_BOUNDARY.isoformat().replace("+00:00", "Z")
    archive_link = (
        f' <a href="{escape(archive_href, quote=True)}">Read the archive history</a>.'
        if archive_href is not None
        else ""
    )
    return f"""<aside class="archive-note" aria-label="Historical context links">
        <strong>Historical context note:</strong> Reports published before <time datetime="{boundary_iso}">{escape(display_timestamp(DATED_DIGEST_HANDOFF_BOUNDARY))}</time> retain their publication-era rolling SentryDigest links. Those links may no longer land on the original card; the archived reports remain unchanged.{archive_link}
      </aside>"""


def with_site_icons(html: str, static_prefix: str) -> str:
    favicon_href = f'{static_prefix}/favicon.ico'
    if html.count("</head>") != 1:
        return html

    icon_hrefs = (
        favicon_href,
        f"{static_prefix}/icon.svg",
        f"{static_prefix}/apple-touch-icon.png",
    )
    for href in icon_hrefs:
        # The pattern needs this literal attribute; skip the whole-page scan
        # when it is absent (archive pages never carry these links).
        if f'href="{href}"' not in html:
            continue
        html = re.sub(
            rf'[ \t]*<link\b[^>]*\bhref="{re.escape(href)}"[^>]*>[ \t]*\n?',
            "",
            html,
        )
    icon_links = (
        f'    <link rel="icon" href="{favicon_href}" sizes="48x48">\n'
        f'    <link rel="icon" type="image/svg+xml" href="{static_prefix}/icon.svg">\n'
        f'    <link rel="apple-touch-icon" href="{static_prefix}/apple-touch-icon.png">\n'
    )
    return re.sub(r"[ \t]*</head>", f"{icon_links}  </head>", html, count=1)


def with_archive_detail_chrome(html: str, generated: datetime) -> str:
    html = with_site_icons(html, "../../static")
    region = re.compile(
        rf"{re.escape(ARCHIVE_CONTEXT_START)}.*?{re.escape(ARCHIVE_CONTEXT_END)}",
        re.DOTALL,
    )
    matches = region.findall(html)
    if len(matches) > 1 or (
        (ARCHIVE_CONTEXT_START in html) != (ARCHIVE_CONTEXT_END in html)
    ):
        fail("archive detail page has invalid historical-context markers")
    if generated >= DATED_DIGEST_HANDOFF_BOUNDARY:
        return region.sub("", html) if matches else html

    context_node = (
        f"{ARCHIVE_CONTEXT_START}\n"
        f'    <div class="container archive-context">\n'
        f"      {historical_context_note('../')}\n"
        f"    </div>\n"
        f"    {ARCHIVE_CONTEXT_END}"
    )
    if matches:
        return region.sub(lambda _match: context_node, html)
    main_node = '<main class="container archive-report">'
    if html.count(main_node) != 1:
        fail("archive detail page must contain one report body")
    return html.replace(main_node, f"{context_node}\n    {main_node}", 1)


def archive_detail_html(
    markdown: str, manifest: object = None, report_html: str | None = None
) -> str:
    fields = report_fields(markdown)
    title = fields.get("title", "GRC Intelligence Report")
    generated_raw = fields.get("generated", "")
    generated = parse_generated(generated_raw)
    if report_html is None:
        report_html = render_report(markdown, manifest)
    html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} | GRCInsight Archive</title>
    <meta name="description" content="Archived GRCInsight intelligence report generated {escape(display_date(generated))}.">
    <link rel="stylesheet" href="../../static/style.css">
  </head>
  <body>
    <header class="app-header">
      <div class="container">
        <h1 class="title">{escape(title)}</h1>
        <time class="subtitle" datetime="{escape(generated_raw, quote=True)}">Generated {escape(display_date(generated))}</time>
        <nav class="header-links" aria-label="Report resources"><a href="../../">Latest report</a><a href="../">Archive</a><a href="report.md">Markdown</a></nav>
      </div>
    </header>
    <main class="container archive-report">{report_html}</main>
    <footer class="app-footer"><div class="container"><span>GRCInsight report archive</span></div></footer>
  </body>
</html>
"""
    return with_archive_detail_chrome(html, generated)


def archive_index_html(
    reports: list[tuple[str, str, str, str]], history_html: str = ""
) -> str:
    items = "\n".join(
        f'<li><a href="{escape(report_key, quote=True)}/"><span>{escape(title)}</span><time datetime="{escape(generated_at, quote=True)}">{escape(label)}</time></a></li>'
        for report_key, title, generated_at, label in reports
    )
    if not items:
        items = "<li>No archived reports are available yet.</li>"
    historical_note = ""
    if any(
        parse_generated(generated_at) < DATED_DIGEST_HANDOFF_BOUNDARY
        for _, _, generated_at, _ in reports
    ):
        historical_note = f"      {historical_context_note()}\n"
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Report Archive | GRCInsight</title>
    <meta name="description" content="Dated, model-backed GRCInsight intelligence reports.">
    <link rel="canonical" href="{PUBLIC_SITE_URL}archive/">
    <link rel="icon" href="../static/favicon.ico" sizes="48x48">
    <link rel="icon" type="image/svg+xml" href="../static/icon.svg">
    <link rel="apple-touch-icon" href="../static/apple-touch-icon.png">
    <link rel="stylesheet" href="../static/style.css">
  </head>
  <body>
    <header class="app-header"><div class="container"><h1 class="title">Report Archive</h1><p class="subtitle">Dated model-backed reports preserved at publication.</p><nav class="header-links" aria-label="Report resources"><a href="../">Latest report</a></nav></div></header>
    <main class="container archive-shell">
      <p>History begins August 13, 2026. A report is added only after the model-backed publication gate succeeds.</p>
{historical_note}{history_html}      <ol class="archive-list">{items}</ol>
    </main>
    <footer class="app-footer"><div class="container"><span>GRCInsight report archive</span></div></footer>
  </body>
</html>
"""


def publication_history_html(history: dict[str, object]) -> str:
    events = history["events"]
    assert isinstance(events, list)
    items: list[str] = []
    for event in events:
        assert isinstance(event, dict)
        event_at_raw = str(event["event_at"])
        event_at = parse_generated(event_at_raw)
        report_generated = parse_generated(str(event["report_generated_at"]))
        report_href = f"../archive/{archive_slug(report_generated)}/"
        if event["outcome"] == "retained":
            label = category_label(event["refusal_category"])
            outcome_text = (
                "Current model-backed report retained because of "
                f"a {label} refusal."
            )
        else:
            outcome_text = "Model-backed report published."
        items.append(
            f'<li class="publication-history-entry" data-outcome="{escape(str(event["outcome"]), quote=True)}">'
            f'<div><strong>{escape(outcome_text)}</strong>'
            f'<time datetime="{escape(event_at_raw, quote=True)}">{escape(display_timestamp(event_at))}</time></div>'
            f'<a href="{escape(report_href, quote=True)}">Report generated {escape(display_timestamp(report_generated))}</a>'
            "</li>"
        )
    history_started_raw = str(history["history_started_at"])
    history_started = parse_generated(history_started_raw)
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Publication History | GRCInsight</title>
    <meta name="description" content="Recent GRCInsight report publication and retention outcomes.">
    <link rel="canonical" href="{PUBLIC_SITE_URL}publication-history/">
    <link rel="icon" href="../static/favicon.ico" sizes="48x48">
    <link rel="icon" type="image/svg+xml" href="../static/icon.svg">
    <link rel="apple-touch-icon" href="../static/apple-touch-icon.png">
    <link rel="stylesheet" href="../static/style.css">
  </head>
  <body>
    <header class="app-header"><div class="container"><h1 class="title">Publication History</h1><p class="subtitle">Recent report publication and retention outcomes.</p><nav class="header-links" aria-label="Report resources"><a href="../">Latest report</a><a href="../archive/">Report archive</a><a href="../publication-history.json">Machine-readable history</a></nav></div></header>
    <main class="container publication-history-shell">
      <p>This bounded journal begins <time datetime="{escape(history_started_raw, quote=True)}">{escape(display_timestamp(history_started))}</time> and retains the newest {history['max_entries']} terminal outcomes. Earlier outcomes were not reconstructed. {escape(schedule_clause(history))}</p>
      <ol class="publication-history-list">{"".join(items)}</ol>
    </main>
    <footer class="app-footer"><div class="container"><span>GRCInsight publication history</span></div></footer>
  </body>
</html>
"""


def _history_report(key: str, generated: datetime, plan, sources: list, html: str):
    findings = source_history.findings_from_plan(report_finding_groups(plan), sources)
    return source_history.Report(
        key=key,
        generated=generated,
        findings=findings,
        anchors=frozenset(f.number for f in findings if f'id="finding-{f.number}"' in html),
        regulatory_rows=len(plan.regulatory_changes),
    )


def source_history_html(
    markdown: str,
    current_manifest: object,
    current_plan,
    current_html: str,
    archived: list,
    archived_plans: list,
    archived_html: list[str],
) -> tuple[str, str]:
    """Optional history surfaces; on any error both are omitted and the build continues."""
    try:
        anchor = parse_generated(report_fields(markdown).get("generated", ""))
        reports, excluded = [], []
        for (report_md, _markdown, manifest, _fields, generated), plan, html in zip(
            archived, archived_plans, archived_html
        ):
            key = report_md.parent.name
            if plan is None:
                excluded.append(
                    source_history.Excluded(
                        key=key,
                        generated=generated,
                        reason=source_history.exclusion_reason(manifest),
                    )
                )
            else:
                reports.append(_history_report(key, generated, plan, manifest["sources"], html))
        current = None
        if current_plan is not None:
            current = _history_report(
                archive_slug(anchor), anchor, current_plan, current_manifest["sources"], current_html
            )
        return source_history.build_views(current, anchor, reports, excluded)
    except Exception as error:  # noqa: BLE001 - optional projection, never a publication gate
        print(
            f"site build: optional source history omitted ({type(error).__name__})",
            file=sys.stderr,
        )
        return "", ""


def expected_outputs(
    markdown: str,
    template: str,
    publication_state: dict[str, object] | None = None,
    publication_history: dict[str, object] | None = None,
) -> dict[Path, str]:
    if publication_history is None:
        fail("publication history is required")
    current_manifest = read_manifest(EVIDENCE_MANIFEST)
    archived: list[tuple[Path, str, object, dict[str, str], datetime]] = []
    if ARCHIVE_DIR.exists():
        for report_md in sorted(ARCHIVE_DIR.glob("????-??-??T??-??-??Z/report.md"), reverse=True):
            archived_markdown = read_text(report_md)
            fields = report_fields(archived_markdown)
            generated = parse_generated(fields.get("generated", ""))
            if archive_slug(generated) != report_md.parent.name:
                fail(
                    "archive timestamp does not match Generated metadata: "
                    f"{report_md.relative_to(REPO_ROOT)}"
                )
            archived.append(
                (
                    report_md,
                    archived_markdown,
                    read_manifest(report_md.parent / "evidence-manifest.json"),
                    fields,
                    generated,
                )
            )

    # Gate every plan once; the review map and the source history share it.
    current_plan = eligible_plan(markdown, current_manifest)
    archived_plans = [
        eligible_plan(archived_markdown, manifest)
        for _, archived_markdown, manifest, _, _ in archived
    ]
    # Starting Node once per report dominated build time; render the current
    # report and every archive in a single batch instead.
    current_html, *archived_html = render_reports(
        [(markdown, current_manifest)]
        + [(archived_markdown, manifest) for _, archived_markdown, manifest, _, _ in archived],
        [plan_review_rows(current_plan)] + [plan_review_rows(plan) for plan in archived_plans],
    )
    current_history, archive_history = source_history_html(
        markdown,
        current_manifest,
        current_plan,
        current_html,
        archived,
        archived_plans,
        archived_html,
    )
    outputs = {
        INDEX_HTML: current_index_html(
            template,
            markdown,
            publication_state,
            publication_history,
            current_manifest,
            report_html=current_html,
            history_html=current_history,
        ),
        PUBLICATION_HISTORY_INDEX: publication_history_html(publication_history),
    }
    reports: list[tuple[str, str, str, str]] = []
    for (report_md, archived_markdown, manifest, fields, generated), report_html in zip(
        archived, archived_html
    ):
        # Markdown and manifests retain publication-era evidence; HTML is a
        # deterministic reader projection shared with the current report.
        outputs[report_md.parent / "index.html"] = archive_detail_html(
            archived_markdown, manifest, report_html=report_html
        )
        reports.append(
            (
                report_md.parent.name,
                fields.get("title", "GRC Intelligence Report"),
                generated.isoformat().replace("+00:00", "Z"),
                display_timestamp(generated),
            )
        )
    outputs[ARCHIVE_DIR / "index.html"] = archive_index_html(reports, archive_history)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive-current",
        action="store_true",
        help="Store the current report under its generated UTC timestamp before building.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of writing when generated site artifacts are stale.",
    )
    args = parser.parse_args()

    markdown = read_text(INDEX_MD)
    fields = report_fields(markdown)
    generated = parse_generated(fields.get("generated", ""))
    if args.archive_current:
        report_md = ARCHIVE_DIR / archive_slug(generated) / "report.md"
        archive_manifest = report_md.parent / "evidence-manifest.json"
        if args.check:
            fail("--archive-current and --check cannot be combined")
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text(markdown.rstrip() + "\n", encoding="utf-8")
        archive_manifest.write_text(read_text(EVIDENCE_MANIFEST), encoding="utf-8")

    template = read_text(INDEX_HTML)
    manifest_bytes = EVIDENCE_MANIFEST.read_bytes()
    publication_state, publication_history = load_publication_artifacts(manifest_bytes)
    outputs = expected_outputs(
        markdown, template, publication_state, publication_history
    )
    stale = []
    for path, content in outputs.items():
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        if args.check:
            stale.append(str(path.relative_to(REPO_ROOT)))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    if stale:
        fail("stale generated artifact(s): " + ", ".join(stale))
    print("site build passed" if args.check else "site build completed")


if __name__ == "__main__":
    main()
