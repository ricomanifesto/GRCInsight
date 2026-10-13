from copy import deepcopy
import json
from pathlib import Path
import runpy
import subprocess

from core.report_plan import render_report_plan
from test_report_substance import PLAN, SOURCE

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    plan = deepcopy(PLAN)
    plan["executive_brief"] = {"decision_frame": "separate", "source_ids": [1, 3, 5]}
    plan["control_implications"] = []
    sources = []
    for index, control in enumerate(
        ["vulnerability_management"] * 3 + ["access_management"] + ["incident_response"] * 2,
        1,
    ):
        source = deepcopy(SOURCE)
        focus = f"Java support {index}"
        source["title"] = f"Advisory {index}"
        source["url"] += f"/{index}"
        source["snippet"] = source["snippet"].replace("Java support", focus)
        source["article_evidence"][0]["text"] = source["snippet"]
        source["article_evidence"][0]["raw_text"] = source["snippet"]
        sources.append(source)
        plan["control_implications"].append(
            {
                **PLAN["control_implications"][0],
                "focus": focus,
                "control_id": control,
                "source_ids": [index],
                "evidence_excerpt": source["snippet"],
            }
        )
    manifest = {"report_contract_version": 5, "report_plan": plan, "sources": sources}
    markdown = render_report_plan(plan, sources, include_digest=True)
    return markdown, manifest


def builder():
    return runpy.run_path(str(ROOT / "scripts/build_site.py"))


def test_review_map_groups_findings_and_links_to_static_evidence():
    markdown, manifest = fixture()
    html = builder()["render_report"](markdown, manifest)
    assert html.index("Executive Summary") < html.index("Review map")
    assert html.index("Review map") < html.index("Sourced Regulatory Changes")
    assert 'aria-label="Review map"' in html
    assert "Inferred review priorities" in html
    assert "not measured risk" in html
    rows = builder()["review_map_rows"](markdown, manifest)
    assert len(rows) == 6
    for index, row in enumerate(rows, 1):
        assert row["focus"] in html
        assert f'href="#finding-{index}"' in html
        assert f'id="finding-{index}" tabindex="-1"' in html
    assert html.count('class="review-map-group"') == 3


def test_review_map_omits_missing_legacy_and_mismatched_evidence():
    markdown, manifest = fixture()
    ns = builder()
    for evidence in (
        None,
        {},
        {"report_contract_version": 4},
        {**manifest, "report_plan": {}},
    ):
        html = ns["render_report"](markdown, evidence)
        assert 'class="review-map"' not in html
        assert "Executive Summary" in html
    changed = deepcopy(manifest)
    changed["report_plan"]["control_implications"][0]["priority"] = "low"
    assert ns["review_map_rows"](markdown, changed) == []
    assert (
        ns["review_map_rows"](markdown.replace("## Executive Summary", "## Changed"), manifest)
        == []
    )


def test_identical_findings_share_one_map_target_with_all_citations():
    _, manifest = fixture()
    plan = manifest["report_plan"]
    original = deepcopy(plan["control_implications"][0])
    duplicate = deepcopy(original)
    duplicate["source_ids"] = [2]
    plan["control_implications"][1] = duplicate
    manifest["sources"][1] = deepcopy(manifest["sources"][0])
    manifest["sources"][1]["title"] = "Second account of the same finding"
    markdown = render_report_plan(plan, manifest["sources"], include_digest=True)
    ns = builder()
    rows = ns["review_map_rows"](markdown, manifest)
    assert len(rows) == 5
    assert sum(row["focus"] == original["focus"] for row in rows) == 1
    html = ns["render_report"](markdown, manifest)
    assert html.count('href="#finding-1"') == 1
    assert 'aria-label="Source 2: Second account of the same finding"' in html


def test_regulatory_only_report_has_no_empty_map():
    from test_report_evidence import SOURCE as primary, selection_plan

    primary = {**primary, "digest_url": "https://digest.example/archive/2026-10-05/#rule"}
    plan = selection_plan()
    plan["control_implications"] = []
    plan["industry_impacts"] = []
    plan["executive_brief"] = {"decision_frame": "regulatory", "source_ids": [1]}
    markdown = render_report_plan(plan, [primary], include_digest=True)
    manifest = {"report_contract_version": 5, "report_plan": plan, "sources": [primary]}
    html = builder()["render_report"](markdown, manifest)
    assert 'class="review-map"' not in html
    assert "Sourced Regulatory Changes" in html


def test_renderer_escapes_map_labels_and_rejects_incomplete_navigation():
    markdown = "## Executive Summary\nSummary.\n\n## Evidence and Decisions\n### Finding\nEvidence."
    rows = [{"focus": '<img src=x onerror="alert(1)">', "control": "A & B", "priority": "High"}]
    script = """
const fs = require('fs'), vm = require('vm');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const {markdown, rows} = JSON.parse(fs.readFileSync(0, 'utf8'));
const render = context.window.GRCInsightRenderer.renderReportDocument;
process.stdout.write(JSON.stringify([render(markdown, rows), render(markdown, [...rows, ...rows])]));
"""
    result = subprocess.run(
        ["node", "-e", script, str(ROOT / "site/static/renderer.js")],
        input=json.dumps({"markdown": markdown, "rows": rows}),
        capture_output=True,
        text=True,
        check=True,
    )
    valid, invalid = json.loads(result.stdout)
    assert "<img" not in valid
    assert "&lt;img" in valid and "A &amp; B" in valid
    assert 'href="#finding-1"' in valid
    assert 'class="review-map"' not in invalid
    assert "Evidence." in invalid


def test_prerendered_browser_report_does_not_fetch_a_different_revision():
    script = """
const fs = require('fs'), vm = require('vm');
const report = {dataset: {prerendered: 'true'}, querySelector: () => ({}), querySelectorAll: () => []};
const context = {
  window: {GRCInsightRenderer: {}},
  document: {getElementById: id => id === 'report' ? report : null, body: {classList: {toggle() {}}}},
  localStorage: {getItem: () => null},
  fetch: () => {throw Error('pre-rendered report must stay on its validated revision')},
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
"""
    result = subprocess.run(
        ["node", "-e", script, str(ROOT / "site/static/app.js")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
