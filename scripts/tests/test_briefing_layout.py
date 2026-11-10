"""The reader presents a validated report as an executive briefing for control owners."""

import json
from pathlib import Path
import re
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
# The builder puts the agent package on the import path for the report contract.
BUILDER = runpy.run_path(str(ROOT / "scripts/build_site.py"))
sys.path.insert(0, str(ROOT / "agent" / "tests"))
NARRATIVE = runpy.run_path(str(ROOT / "agent/tests/test_grc_narrative.py"))
PLAN, SOURCES = NARRATIVE["PLAN"], NARRATIVE["SOURCES"]

from core.report_plan import (  # noqa: E402
    CONTROL_REVIEWS,
    CONTROLS,
    parse_report_plan,
    render_report_plan,
)
from core.report_plan import load_report_plan  # noqa: E402


def briefing():
    plan = parse_report_plan(json.dumps(PLAN), SOURCES)
    body = render_report_plan(plan, SOURCES, include_digest=True)
    markdown = (
        "# GRC Intelligence Report - 2026-10-29\n**Generated:** 2026-10-29T15:22:02Z\n\n" + body
    )
    manifest = {"report_contract_version": 6, "report_plan": plan, "sources": SOURCES}
    return BUILDER["render_report"](markdown, manifest), BUILDER["review_map_rows"](
        markdown, manifest
    )


def section(html, heading):
    match = re.search(
        rf"<h2[^>]*>{re.escape(heading)}</h2>([\s\S]*?)(?=<section class=\"card|$)", html
    )
    assert match, heading
    return match.group(1)


def test_rows_carry_headline_and_accountable_owner():
    _html, rows = briefing()
    assert [row["headline"] for row in rows] == [
        row["headline"] for row in PLAN["control_implications"]
    ]
    assert rows[0]["owner"] == CONTROL_REVIEWS["monitoring"][0]
    assert rows[0]["control"] == CONTROLS["monitoring"][0]


def test_summary_leads_with_figures_then_numbered_key_messages():
    html, _rows = briefing()
    summary = section(html, "Executive Summary")
    figures = re.findall(
        r'<div class="glance-item"><dt class="glance-label">([^<]+)</dt><dd class="glance-value">(\d+)</dd></div>',
        summary,
    )
    assert figures == [
        ("Findings", "4"),
        ("High priority", "2"),
        ("Control areas", "4"),
        ("Sources reviewed", "12"),
    ]
    messages = re.findall(
        r'<li class="key-message"><p><strong class="key-lead">(.*?)</strong>', summary
    )
    assert messages == [
        "Two intrusions this period aimed at the records and keys that assurance depends on.",
        "Exposed administrative surfaces are the second theme.",
    ]
    assert summary.index('class="glance"') < summary.index('class="key-messages"')
    assert '<p class="summary-scope">Scope: 4 findings' in summary


def test_overview_exhibits_rank_findings_and_show_control_coverage():
    html, rows = briefing()
    overview = section(html, "Findings at a glance")
    assert 'aria-label="Review map"' in overview and 'class="review-map"' in overview
    assert '<p class="exhibit-label">Exhibit 1</p>' in overview
    assert "2 of 4 findings carry high review priority" in overview
    assert "not measured risk" in overview
    for index, row in enumerate(rows, 1):
        assert f'href="#finding-{index}"' in overview
        assert f'<span class="finding-index">{index:02d}</span>' in overview
    assert '<p class="exhibit-label">Exhibit 2</p>' in overview
    assert "Findings span 4 of 8 control areas" in overview
    for label, *_rest in CONTROLS.values():
        assert f'<th scope="row">{label}</th>' in overview
    assert overview.count('class="coverage-cell is-empty"') == 8 * 3 - 4


def test_each_finding_becomes_a_numbered_briefing_block():
    html, rows = briefing()
    evidence = section(html, "Evidence and Decisions")
    articles = re.findall(r'<article class="finding priority-(high|medium|low)">', evidence)
    assert articles == ["high", "high", "medium", "medium"]
    for index, row in enumerate(rows, 1):
        assert f'<span class="finding-number">{index:02d}</span>' in evidence
        assert f'id="finding-{index}" tabindex="-1"' in evidence
    first = evidence.split('<article class="finding')[1]
    assert '<span class="priority-pill">High priority</span>' in first
    assert '<p class="finding-lead">' in first and '<figure class="finding-evidence">' in first
    for label in (
        "Accountable owner",
        "Evidence to request",
        "Decision trigger",
        "Reference controls",
    ):
        assert f"<dt>{label}</dt>" in first
    assert "Detection and monitoring owner" in first
    assert "Review priority:" not in evidence


def test_renderer_control_catalog_matches_the_application_catalog():
    source = (ROOT / "site/static/renderer.js").read_text()
    match = re.search(r"const CONTROL_AREAS = \[([\s\S]*?)\];", source)
    assert match
    assert re.findall(r"'([^']+)'", match.group(1)) == [label for label, *_ in CONTROLS.values()]
