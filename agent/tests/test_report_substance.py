"""A citation and a category are insufficient to publish a useful finding."""

from copy import deepcopy
import json
from pathlib import Path
import runpy

import pytest

from core.report_plan import (
    parse_report_plan,
    render_report_plan,
    validate_rendered_report,
)

SOURCE = {
    "title": "Spreadsheet code execution advisory",
    "url": "https://example.com/spreadsheet",
    "snippet": "The spreadsheet attack requires Java support. It has only been demonstrated as a proof of concept; no exploitation has been reported.",
    "cves": [],
    "digest_url": "https://digest.example/archive/2026-10-05/#spreadsheet",
}
PLAN = {
    "regulatory_changes": [],
    "control_implications": [
        {
            "control_id": "vulnerability_management",
            "priority": "medium",
            "source_ids": [1],
            "focus": "Java support",
            "evidence_excerpt": SOURCE["snippet"],
        }
    ],
    "industry_impacts": [{"sector_id": "technology", "source_ids": [1]}],
}


def test_reader_sees_event_limit_and_decision_without_opening_a_citation():
    plan = parse_report_plan(json.dumps(PLAN), [SOURCE])
    body = render_report_plan(plan, [SOURCE])
    summary = body.split("## Sourced Regulatory Changes")[0]
    assert "Java support" in summary
    assert "proof of concept" in summary
    assert body.count(str(SOURCE["snippet"])) == 1
    assert "proof of concept" in body and "no exploitation" in body
    assert "Evidence to request" in body
    assert "Owner" in body
    assert "If applicable" in body
    assert "This report separates" not in summary
    assert "No sourced regulatory changes" in body
    validate_rendered_report(body, plan, [SOURCE])
    renderer = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/build_site.py"))
    html = renderer["render_report"](body)
    assert "Java support" in html.split("<h2>Sourced Regulatory Changes")[0]
    assert "proof of concept" in html


@pytest.mark.parametrize(
    "change",
    [
        {"control_implications": []},
        {
            "control_implications": [
                {"control_id": "governance", "priority": "high", "source_ids": [1]}
            ]
        },
    ],
)
def test_category_only_or_empty_reports_cannot_pass_generation(change):
    with pytest.raises(ValueError):
        parse_report_plan(json.dumps({**PLAN, **change}), [SOURCE])


@pytest.mark.parametrize(
    "field,value",
    [
        ("focus", "unsupported product"),
        ("focus", "support requires"),
        ("evidence_excerpt", "An unrelated vendor is actively exploited."),
        ("evidence_excerpt", "Java support"),
        ("source_ids", [1, 2]),
        ("source_ids", [2]),
    ],
)
def test_finding_must_be_bound_to_one_source_and_its_exact_evidence(field, value):
    plan = deepcopy(PLAN)
    plan["control_implications"][0][field] = value
    with pytest.raises(ValueError):
        parse_report_plan(json.dumps(plan), [SOURCE, {**SOURCE, "snippet": "Different evidence."}])


def test_title_only_evidence_cannot_be_promoted_to_a_finding():
    source = {**SOURCE, "snippet": SOURCE["title"]}
    plan = deepcopy(PLAN)
    plan["control_implications"][0].update(focus="Spreadsheet", evidence_excerpt=source["snippet"])
    with pytest.raises(ValueError):
        parse_report_plan(json.dumps(plan), [source])


def test_distinct_events_in_the_same_control_are_not_collapsed():
    sources = [
        SOURCE,
        {**SOURCE, "title": "Other event", "url": "https://example.com/other"},
    ]
    plan = deepcopy(PLAN)
    plan["control_implications"].append({**plan["control_implications"][0], "source_ids": [2]})
    body = render_report_plan(plan, sources)
    assert "[Other event](https://example.com/other)" in body


def test_model_prose_and_render_mutations_still_fail_closed():
    plan = deepcopy(PLAN)
    plan["control_implications"][0]["rationale"] = "A new legal deadline begins tomorrow."
    with pytest.raises(ValueError):
        parse_report_plan(json.dumps(plan), [SOURCE])
    body = render_report_plan(PLAN, [SOURCE])
    with pytest.raises(ValueError):
        validate_rendered_report(body + "\nAn unsupported assertion.", PLAN, [SOURCE])


def publication_tools():
    root = Path(__file__).resolve().parents[2]
    return [
        runpy.run_path(str(root / "scripts" / name))
        for name in ("compose_site_report.py", "check_site_report.py", "build_site.py")
    ]


def test_actual_hollow_publication_is_readable_history_but_cannot_be_republished():
    composer, checker, builder = publication_tools()
    fixture = Path(__file__).parent / "fixtures/report-v3-2026-10-06"
    markdown = (fixture / "report.md").read_text()
    manifest_text = (fixture / "evidence-manifest.json").read_text()
    manifest = json.loads(manifest_text)
    before = (markdown, manifest_text)
    # Immutable v3 output still has to match its exact plan and sources.
    checker["validate_evidence_manifest"](
        markdown, builder["report_fields"](markdown), manifest_text
    )
    with pytest.raises(SystemExit, match="current report contract"):
        checker["validate_evidence_manifest"](
            markdown,
            builder["report_fields"](markdown),
            manifest_text,
            require_current_contract=True,
        )
    with pytest.raises(ValueError):
        parse_report_plan(json.dumps(manifest["report_plan"]), manifest["sources"])
    # Merely relabeling a historical manifest cannot upgrade its content.
    manifest["report_contract_version"] = 4
    with pytest.raises(SystemExit):
        checker["validate_evidence_manifest"](
            markdown,
            builder["report_fields"](markdown),
            json.dumps(manifest),
            require_current_contract=True,
        )
    assert before == (
        (fixture / "report.md").read_text(),
        (fixture / "evidence-manifest.json").read_text(),
    )


def test_finding_reaches_composition_manifest_and_compact_html():
    from test_report_evidence import stored_report

    composer, checker, builder = publication_tools()
    data = stored_report(render_report_plan(PLAN, [SOURCE]), deepcopy(PLAN))
    data["metadata"]["source_articles"] = [{k: v for k, v in SOURCE.items() if k != "digest_url"}]
    markdown = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    manifest = composer["evidence_manifest"](data, composer["source_articles"](data["metadata"]))
    assert manifest["report_contract_version"] == 4
    checker["validate_evidence_manifest"](
        markdown,
        builder["report_fields"](markdown),
        json.dumps(manifest),
        require_current_schema=True,
        require_current_contract=True,
    )
    html = builder["render_report"](markdown)
    assert "Java support" in html and "proof of concept" in html
    assert 'class="report-citation"' in html
    assert "View in SentryDigest" in html
    for version in (1, 3, 5, True):
        with pytest.raises(SystemExit):
            checker["validate_evidence_manifest"](
                markdown,
                builder["report_fields"](markdown),
                json.dumps({**manifest, "report_contract_version": version}),
                require_current_contract=True,
            )
    manifest["report_plan"]["control_implications"][0][
        "evidence_excerpt"
    ] = "A fabricated event without any supporting source text."
    with pytest.raises(SystemExit):
        checker["validate_evidence_manifest"](
            markdown, builder["report_fields"](markdown), json.dumps(manifest)
        )


def test_invalid_model_finding_retries_then_cannot_attest_publication():
    import asyncio
    from services.model_service import GRCModelService
    from services.openrouter_client import OpenRouterGeneration

    service = GRCModelService.__new__(GRCModelService)
    calls = []

    async def invoke(**kwargs):
        calls.append(kwargs)
        return OpenRouterGeneration(
            text=json.dumps({**PLAN, "control_implications": []}),
            resolved_model="example/model",
        )

    service._invoke = invoke
    result = asyncio.run(service.generate_grc_report({"source_evidence": [SOURCE]}, {}))
    assert len(calls) == 2
    assert result.resolved_model == "" and result.report_plan is None
    assert "Unable to generate report" in result.content


def test_invalid_finding_does_not_overwrite_last_published_files(tmp_path, monkeypatch):
    import sys
    from test_report_evidence import stored_report

    composer, _, _ = publication_tools()
    plan = {**PLAN, "control_implications": []}
    old_body = render_report_plan(
        {"regulatory_changes": [], "control_implications": [], "industry_impacts": []},
        [SOURCE],
        contract_version=3,
    )
    data = stored_report(old_body, plan)
    data["metadata"]["source_articles"] = [{k: v for k, v in SOURCE.items() if k != "digest_url"}]
    report_input = tmp_path / "report.json"
    report_input.write_text(json.dumps(data))
    report, manifest = tmp_path / "index.md", tmp_path / "evidence-manifest.json"
    report.write_text("last verified report")
    manifest.write_text("last verified manifest")
    main = composer["main"]
    main.__globals__["INDEX_MD"] = report
    main.__globals__["EVIDENCE_MANIFEST"] = manifest
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compose_site_report.py",
            "--input",
            str(report_input),
            "--feed-url",
            "https://digest.example/feed.xml",
            "--model",
            "openrouter/example/model",
        ],
    )
    with pytest.raises(SystemExit):
        main()
    assert report.read_text() == "last verified report"
    assert manifest.read_text() == "last verified manifest"


def test_new_publication_gate_runs_before_both_push_paths():
    root = Path(__file__).resolve().parents[2]
    workflow = (root / ".github/workflows/lambda-report-generation.yml").read_text()
    validation = workflow.index("Validate generated site report")
    publish = workflow.index("Commit and push report")
    rebase = workflow.index("git rebase -X theirs")
    command = "python3 scripts/check_site_report.py --require-current-contract"
    assert validation < workflow.index(command) < publish
    assert rebase < workflow.index(command, rebase) < workflow.index("git push origin HEAD", rebase)


def test_quoted_evidence_is_literal_text_in_the_reader():
    from html.parser import HTMLParser

    class Reader(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text = []
            self.links = []

        def handle_data(self, data):
            self.text.append(data)

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self.links.append(dict(attrs).get("href"))

    excerpt = "Java [support](https://untrusted.example) **requires** <img src=x> & &#42; @@GRCINSIGHT_LINK_0@@ %%CODEBLOCK_0%% for this demonstration."
    source = {**SOURCE, "snippet": excerpt, "url": "https://example.com/evidence?literal=&#38;"}
    plan = deepcopy(PLAN)
    plan["control_implications"][0].update(focus="Java [support]", evidence_excerpt=excerpt)
    body = render_report_plan(plan, [source])
    _, _, builder = publication_tools()
    html = builder["render_report"](body)
    reader = Reader()
    reader.feed(html)
    assert excerpt in "".join(reader.text)
    assert reader.links and all(link == source["url"] for link in reader.links)
    assert "<img" not in html


def test_primary_regulatory_only_report_remains_publishable():
    from test_report_evidence import SOURCE as PRIMARY_SOURCE, selection_plan

    plan = selection_plan()
    plan["control_implications"] = []
    body = render_report_plan(plan, [PRIMARY_SOURCE])
    assert "final reporting rule" in body.split("## Sourced Regulatory Changes")[0]
    assert "| Unknown |" in body
    validate_rendered_report(body, plan, [PRIMARY_SOURCE])
