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
ARCHIVE_CONTEXT_START = "<!-- ARCHIVE_CONTEXT_START -->"
ARCHIVE_CONTEXT_END = "<!-- ARCHIVE_CONTEXT_END -->"
PUBLIC_SITE_URL = "https://ricomanifesto.github.io/GRCInsight/"
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
    label = category_label(state["refusal_category"])
    reason = (
        "an unclassified provider failure"
        if label == "unclassified provider failure"
        else f"a {label} refusal"
    )
    attempted_raw = str(state["attempted_at"])
    return f"""          <aside class="publication-notice" aria-labelledby="publication-notice-title">
            <h2 id="publication-notice-title">Publication update</h2>
            <p>A newer report was attempted on <time datetime="{escape(attempted_raw, quote=True)}">{escape(display_timestamp(attempted))}</time>. The current model-backed report was retained because of {escape(reason)}. {escape(schedule_clause(history))} <a href="publication-history/">Recent publication history</a> · <a href="publication-state.json">Machine-readable status</a>.</p>
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


def render_report(markdown: str) -> str:
    node_script = r"""
const fs = require('fs');
const vm = require('vm');
const rendererSource = fs.readFileSync(process.argv[1], 'utf8');
const markdown = fs.readFileSync(0, 'utf8');
const context = { window: {} };
vm.createContext(context);
vm.runInContext(rendererSource, context, { filename: 'renderer.js' });
process.stdout.write(context.window.GRCInsightRenderer.renderReportDocument(markdown));
"""
    result = subprocess.run(
        ["node", "-e", node_script, str(RENDERER_JS)],
        input=markdown,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail((result.stderr or result.stdout).strip() or "renderer failed")
    return result.stdout


def current_index_html(
    template: str,
    markdown: str,
    publication_state: dict[str, object] | None = None,
    publication_history: dict[str, object] | None = None,
) -> str:
    fields = report_fields(markdown)
    generated_raw = fields.get("generated", "")
    generated = parse_generated(generated_raw)
    report_html = render_report(markdown)
    report_node = (
        f"{REPORT_START}\n"
        f'          <div id="report" class="report" data-prerendered="true" '
        f'data-generated-at="{escape(generated_raw, quote=True)}">{report_html}</div>\n'
        f"          {REPORT_END}"
    )
    region = re.compile(
        rf"{re.escape(REPORT_START)}.*?{re.escape(REPORT_END)}", re.DOTALL
    )
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
        rf"{re.escape(PUBLICATION_NOTICE_START)}.*?"
        rf"{re.escape(PUBLICATION_NOTICE_END)}",
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


def with_archive_detail_chrome(html: str, generated: datetime) -> str:
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


def archive_detail_html(markdown: str) -> str:
    fields = report_fields(markdown)
    title = fields.get("title", "GRC Intelligence Report")
    generated_raw = fields.get("generated", "")
    generated = parse_generated(generated_raw)
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
    <main class="container archive-report">{render_report(markdown)}</main>
    <footer class="app-footer"><div class="container"><span>GRCInsight report archive</span></div></footer>
  </body>
</html>
"""
    return with_archive_detail_chrome(html, generated)


def archive_index_html(reports: list[tuple[str, str, str, str]]) -> str:
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
    <link rel="stylesheet" href="../static/style.css">
  </head>
  <body>
    <header class="app-header"><div class="container"><h1 class="title">Report Archive</h1><p class="subtitle">Dated model-backed reports preserved at publication.</p><nav class="header-links" aria-label="Report resources"><a href="../">Latest report</a></nav></div></header>
    <main class="container archive-shell">
      <p>History begins August 13, 2026. A report is added only after the model-backed publication gate succeeds.</p>
{historical_note}      <ol class="archive-list">{items}</ol>
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


def expected_outputs(
    markdown: str,
    template: str,
    publication_state: dict[str, object] | None = None,
    publication_history: dict[str, object] | None = None,
) -> dict[Path, str]:
    if publication_history is None:
        fail("publication history is required")
    outputs = {
        INDEX_HTML: current_index_html(
            template, markdown, publication_state, publication_history
        ),
        PUBLICATION_HISTORY_INDEX: publication_history_html(publication_history),
    }
    reports: list[tuple[str, str, str, str]] = []
    if ARCHIVE_DIR.exists():
        for report_md in sorted(
            ARCHIVE_DIR.glob("????-??-??T??-??-??Z/report.md"), reverse=True
        ):
            archived_markdown = read_text(report_md)
            fields = report_fields(archived_markdown)
            generated = parse_generated(fields.get("generated", ""))
            report_key = report_md.parent.name
            if archive_slug(generated) != report_key:
                fail(
                    "archive timestamp does not match Generated metadata: "
                    f"{report_md.relative_to(REPO_ROOT)}"
                )
            archive_page = report_md.parent / "index.html"
            # The publication-era report body remains byte-for-byte intact.
            # Existing pages receive only boundary-aware page chrome.
            if archive_page.exists():
                outputs[archive_page] = with_archive_detail_chrome(
                    read_text(archive_page), generated
                )
            else:
                outputs[archive_page] = archive_detail_html(archived_markdown)
            reports.append(
                (
                    report_key,
                    fields.get("title", "GRC Intelligence Report"),
                    generated.isoformat().replace("+00:00", "Z"),
                    display_timestamp(generated),
                )
            )
    outputs[ARCHIVE_DIR / "index.html"] = archive_index_html(reports)
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
