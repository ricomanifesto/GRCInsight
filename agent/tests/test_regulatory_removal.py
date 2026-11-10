"""The site presents no Sourced Regulatory Changes section; the evidence record keeps it."""

from __future__ import annotations

import json
from pathlib import Path
import re
import runpy
from typing import Any

import pytest

from core.report_plan import load_report_plan, render_report_plan
from narrative_fixture import narrated
from test_report_evidence import SOURCE as PRIMARY, v5_selection_plan

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE = REPO_ROOT / "site"
FIXTURES = REPO_ROOT / "agent" / "tests" / "fixtures"
SECTION = "Sourced Regulatory Changes"
POINTER = "See the sourced regulatory evidence above"
FALLBACK = "The sourced regulatory table is the evidence"


@pytest.fixture(scope="module")
def ns() -> dict:
    return runpy.run_path(str(REPO_ROOT / "scripts" / "build_site.py"))


def fixture(name: str) -> tuple[str, Any]:
    folder = FIXTURES / name
    return (
        (folder / "report.md").read_text(encoding="utf-8"),
        json.loads((folder / "evidence-manifest.json").read_text(encoding="utf-8")),
    )


def summary(html: str) -> str:
    match = re.search(r"<h2>Executive Summary</h2>(.*?)(?=<section|$)", html, re.S)
    assert match
    return match.group(1)


def glance(html: str) -> list[str]:
    return re.findall(r'<dt class="glance-label">([^<]+)</dt>', html)


PRIMARY_SOURCE = {**PRIMARY, "digest_url": "https://digest.example/archive/2026-10-05/#rule"}


def populated(contract: int) -> tuple[str, dict]:
    """A valid plan whose one finding quotes the same passage as its regulatory row."""
    plan = v5_selection_plan() if contract == 5 else narrated(v5_selection_plan())
    markdown = render_report_plan(
        load_report_plan(plan, [PRIMARY_SOURCE], contract_version=contract),
        [PRIMARY_SOURCE],
        include_digest=True,
    )
    manifest = {
        "report_contract_version": contract,
        "report_plan": plan,
        "sources": [PRIMARY_SOURCE],
    }
    return markdown, manifest


def regulatory_only() -> tuple[str, dict]:
    plan = narrated(v5_selection_plan())
    plan["control_implications"] = []
    plan["executive_brief"] = {"decision_frame": "regulatory", "source_ids": [1]}
    plan = narrated(plan)
    markdown = render_report_plan(
        load_report_plan(plan, [PRIMARY_SOURCE]), [PRIMARY_SOURCE], include_digest=True
    )
    return markdown, {
        "report_contract_version": 6,
        "report_plan": plan,
        "sources": [PRIMARY_SOURCE],
    }


# ----- The section, in every form -----


def test_the_empty_section_of_the_current_report_is_not_presented(ns):
    markdown = (SITE / "index.md").read_text(encoding="utf-8")
    manifest = json.loads((SITE / "evidence-manifest.json").read_text(encoding="utf-8"))
    assert f"## {SECTION}" in markdown, "the as-generated Markdown keeps the section"
    html = ns["render_report"](markdown, manifest)
    assert SECTION not in html
    assert "No sourced regulatory changes identified" not in html


def test_a_populated_table_is_not_presented(ns):
    markdown, manifest = populated(6)
    assert "| Change | Jurisdiction |" in markdown
    html = ns["render_report"](markdown, manifest)
    assert SECTION not in html and "Jurisdiction" not in html and "<th>Change</th>" not in html


def test_a_numbered_heading_form_is_recognised_and_dropped(ns):
    markdown = (
        "## Executive Summary\nLead.\n\n3. Sourced Regulatory Changes\n\n"
        "No sourced regulatory changes identified in the supplied evidence.\n\n"
        "## Source Highlights\n- [Source](https://example.test/a)\n"
    )
    html = ns["render_report"](markdown)
    assert SECTION not in html and "No sourced regulatory changes" not in html
    assert "<h2>Source Highlights</h2>" in html


def test_the_glance_lists_four_figures_in_order(ns):
    markdown = (SITE / "index.md").read_text(encoding="utf-8")
    manifest = json.loads((SITE / "evidence-manifest.json").read_text(encoding="utf-8"))
    html = ns["render_report"](markdown, manifest)
    assert glance(html) == ["Findings", "High priority", "Control areas", "Sources reviewed"]
    assert "Regulatory changes" not in html


# ----- The four application-written sentences, exact matches only -----


def test_the_v6_scope_count_drops_only_its_regulatory_clause(ns):
    markdown = (SITE / "index.md").read_text(encoding="utf-8")
    manifest = json.loads((SITE / "evidence-manifest.json").read_text(encoding="utf-8"))
    original = re.search(
        r"Scope: (\d+) findings? and \d+ sourced regulatory changes? from (\d+) retained sources?\.",
        markdown,
    )
    assert original
    html = summary(ns["render_report"](markdown, manifest))
    assert (
        f"Scope: {original.group(1)} findings from {original.group(2)} retained sources. Review priorities rank"
        in html
    )
    assert "sourced regulatory" not in html


def test_the_v4_scope_count_drops_only_its_regulatory_clause(ns):
    markdown, manifest = fixture("report-v4-2026-10-06")
    assert "Scope: 6 selected control findings and 0 sourced regulatory changes from 12" in markdown
    html = summary(ns["render_report"](markdown, manifest))
    assert "Scope: 6 selected control findings from 12 retained sources. Review questions" in html
    assert "sourced regulatory" not in html


def test_the_v5_sentence_is_removed_and_its_neighbours_stay(ns):
    markdown, manifest = fixture("report-v5-2026-10-29")
    assert (
        "No primary-source regulatory change is established by this selection. Revise" in markdown
    )
    html = summary(ns["render_report"](markdown, manifest))
    assert "No primary-source regulatory change" not in html
    assert "Revise the agenda if the relevant product" in html


def test_the_v5_populated_sentence_is_removed(ns):
    markdown, manifest = populated(5)
    assert (
        "Regulatory applicability still requires an assessment of the cited primary material. "
        in markdown
    )
    html = summary(ns["render_report"](markdown, manifest))
    assert "Regulatory applicability still requires" not in html
    assert "Revise the agenda if the relevant product" in html


def test_the_v3_sentence_is_removed_and_the_next_stays(ns):
    markdown, manifest = fixture("report-v3-2026-10-06")
    html = summary(ns["render_report"](markdown, manifest))
    assert "This report separates sourced regulatory changes" not in html
    assert "Use the primary evidence to assess applicability to your organization." in html


def test_model_prose_about_regulatory_obligations_is_unchanged(ns):
    prose = (
        "Regulatory obligations under the cited rule may change reporting duties, and "
        "No primary-source regulatory change is established by this selection, a model said."
    )
    markdown = f"## Executive Summary\n{prose}\n\n## Sourced Regulatory Changes\n\nNone.\n"
    html = ns["render_report"](markdown)
    assert prose in html


def test_a_near_miss_scope_sentence_is_left_alone(ns):
    prose = "Scope: 6 findings and 2 sourced regulatory changes from 12 retained sources, roughly."
    html = ns["render_report"](f"## Executive Summary\n{prose}\n")
    assert prose in html


# ----- Evidence that the template deduplicated against the removed table -----


@pytest.mark.parametrize("contract", [5, 6])
def test_a_finding_sharing_its_passage_with_a_row_shows_its_own_evidence(ns, contract):
    markdown, manifest = populated(contract)
    assert POINTER in markdown, "the generator deduplicated this finding's quote"
    html = ns["render_report"](markdown, manifest)
    assert POINTER not in html
    evidence = html.split("<h2>Evidence and Decisions</h2>")[1]
    assert "The United States final reporting rule takes effect on 2027" in evidence
    assert 'href="https://www.sec.gov/rules/final/example"' in evidence
    assert "Source evidence" in evidence


def test_a_regulatory_only_report_has_no_pointer_to_a_removed_table(ns):
    markdown, manifest = regulatory_only()
    assert FALLBACK in markdown
    html = ns["render_report"](markdown, manifest)
    assert FALLBACK not in html and "sourced regulatory table" not in html
    assert "No control findings were selected." in html
    assert 'class="review-map"' not in html


def test_unrelated_text_mentioning_the_pointer_words_is_left_alone(ns):
    prose = "Analysts said to see the sourced regulatory evidence above the fold."
    html = ns["render_report"](f"## Evidence and Decisions\n### A finding\n{prose}\n")
    assert prose in html


def test_the_review_map_carries_each_findings_quoted_excerpt(ns):
    markdown, manifest = populated(6)
    rows = ns["review_map_rows"](markdown, manifest)
    assert [row["evidence"] for row in rows] == [
        "The United States final reporting rule takes effect on 2027-01-01."
    ]


# ----- The populated-plan tripwire -----


def test_a_populated_current_plan_writes_one_diagnostic(ns, capsys):
    markdown, manifest = populated(6)
    plan = ns["eligible_plan"](markdown, manifest)
    ns["note_unpresented_regulatory_rows"](plan)
    err = capsys.readouterr().err.strip().splitlines()
    assert err == [
        "site build: the current report carries 1 regulatory row that the site does not present"
    ]
    ns["note_unpresented_regulatory_rows"](None)
    assert capsys.readouterr().err == ""


# ----- The real tree -----


@pytest.fixture(scope="module")
def real(ns):
    markdown = ns["read_text"](ns["INDEX_MD"])
    template = ns["read_text"](ns["INDEX_HTML"])
    state, history = ns["load_publication_artifacts"](ns["EVIDENCE_MANIFEST"].read_bytes())
    return ns["expected_outputs"](markdown, template, state, history)


def test_no_built_page_presents_the_section_the_metric_or_the_retired_lanes(ns, real):
    for path, page in real.items():
        assert f"<h2>{SECTION}</h2>" not in page, path
        assert "Regulatory changes" not in page, path
        assert "regulatory-window" not in page and "regulatory-lane" not in page, path
        assert "regulatory-register.json" not in page, path
        assert "Past 30 days" not in page, path


def test_the_archive_statement_has_no_regulatory_sentence(ns, real):
    archive = real[ns["ARCHIVE_DIR"] / "index.html"]
    statement = archive.split('id="sources-by-control"')[1].split("</p>")[0]
    assert "regulatory" not in statement
    assert "A control is a topic: sources under one control are not one event." in statement


def test_legacy_pages_keep_their_regulatory_and_control_context(ns, real):
    legacy = [
        path
        for path in real
        if path.name == "index.html"
        and (path.parent / "report.md").exists()
        and "## Key Regulatory Developments" in (path.parent / "report.md").read_text()
    ]
    assert len(legacy) > 200
    for path in legacy:
        assert real[path] == path.read_text(encoding="utf-8"), path


def test_markdown_downloads_and_manifests_still_carry_the_section():
    markdown = (SITE / "index.md").read_text(encoding="utf-8")
    assert f"## {SECTION}" in markdown
    assert "sourced regulatory changes from" in markdown


def test_no_register_runtime_remains():
    for retired in (
        ".github/workflows/regulatory-register.yml",
        "site/regulatory-register.json",
        "scripts/regulatory_register.py",
        "scripts/regulatory_window.py",
        "agent/tests/fixtures/federal-register",
    ):
        assert not (REPO_ROOT / retired).exists(), retired
    style = (SITE / "static" / "style.css").read_text(encoding="utf-8")
    assert ".regulatory-" not in style
    builder = (REPO_ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    assert "regulatory_register" not in builder and "regulatory_window" not in builder


def test_the_page_description_claims_only_what_the_report_shows():
    head = (SITE / "index.html").read_text(encoding="utf-8").split("</head>")[0]
    for claim in ("regulatory and security feeds", "agency signals", "industry relevance"):
        assert claim not in head
    assert head.count("GRCInsight turns security news into audit-ready GRC intelligence") == 4


def test_a_projected_quote_is_rendered_as_text_never_markup():
    import subprocess

    markdown = (
        "## Executive Summary\nLead.\n\n## Evidence and Decisions\n### A finding\n\n"
        "See the sourced regulatory evidence above. [Source](https://example.test/a)\n"
    )
    rows = [
        {
            "focus": "f",
            "control": "Governance and accountability",
            "priority": "High",
            "evidence": "<img src=x onerror=alert(1)> & [x](javascript:alert(1))",
        }
    ]
    script = """
const fs = require('fs'), vm = require('vm');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const {markdown, rows} = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(context.window.GRCInsightRenderer.renderReportDocument(markdown, rows));
"""
    html = subprocess.run(
        ["node", "-e", script, str(SITE / "static" / "renderer.js")],
        input=json.dumps({"markdown": markdown, "rows": rows}),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "<img" not in html and "javascript:" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert POINTER not in html
