"""Structured selections cannot introduce model-authored narrative claims."""

from copy import deepcopy
import json
from pathlib import Path
import re
import runpy

import pytest

SOURCES = [
    {
        "title": "Security advisory",
        "url": "https://example.com/advisory",
        "snippet": "A vendor published a security advisory for deployed gateways.",
        "digest_url": "https://digest.example/archive/2026-10-05/#advisory",
        "cves": [],
    }
]
PLAN = {
    "regulatory_changes": [],
    "control_implications": [
        {
            "control_id": "vulnerability_management",
            "priority": "high",
            "source_ids": [1],
            "focus": "security advisory",
            "evidence_excerpt": SOURCES[0]["snippet"],
        }
    ],
    "industry_impacts": [{"sector_id": "technology", "source_ids": [1]}],
}


def test_report_plan_renders_only_owned_text_and_retained_source_identity():
    from core.report_plan import (
        parse_report_plan,
        render_report_plan,
        validate_rendered_report,
    )

    plan = parse_report_plan(json.dumps(PLAN), SOURCES)
    body = render_report_plan(plan, SOURCES)
    assert "## Executive Summary" in body
    assert "## Sourced Regulatory Changes" in body
    assert "Inferred priority: High" in body
    assert "[Security advisory](https://example.com/advisory)" in body
    assert "No sourced regulatory changes identified" in body
    validate_rendered_report(body, plan, SOURCES)
    assert render_report_plan(plan, SOURCES) == body


@pytest.mark.parametrize(
    "claim",
    [
        "The rule takes effect on 2027-01-01.",
        "Effective January 1, 2027, the rule changes reporting.",
        "The entry into force is January 1, 2027.",
        "The rule applies beginning January 1, 2027.",
        "The new duty begins on the first day of next year.",
        "Any arbitrary assertion, without timing vocabulary.",
    ],
)
def test_report_plan_rejects_any_added_narrative_independent_of_phrasing(claim):
    from core.report_plan import render_report_plan, validate_rendered_report

    body = render_report_plan(PLAN, SOURCES)
    for heading in (
        "Executive Summary",
        "Inferred Control and Governance Implications",
        "Source Highlights",
    ):
        bad = body.replace(f"## {heading}\n", f"## {heading}\n{claim}\n")
        with pytest.raises(ValueError, match="retained report plan"):
            validate_rendered_report(bad, PLAN, SOURCES)


@pytest.mark.parametrize(
    "change",
    [
        {"executive_summary": "Effective January 1, 2027, the rule changes reporting."},
        {
            "control_implications": [
                {"control_id": "invented", "priority": "high", "source_ids": [1]}
            ]
        },
        {
            "control_implications": [
                {
                    "control_id": "governance",
                    "priority": "high tomorrow",
                    "source_ids": [1],
                }
            ]
        },
        {
            "control_implications": [
                {"control_id": "governance", "priority": "high", "source_ids": [True]}
            ]
        },
        {
            "control_implications": [
                {"control_id": "governance", "priority": "high", "source_ids": [2]}
            ]
        },
        {
            "regulatory_changes": [
                {
                    "source_id": 1,
                    "change": "A vendor",
                    "jurisdiction": "Unknown",
                    "evidence_excerpt": SOURCES[0]["snippet"],
                    "effective_date": "2027-01-01",
                }
            ]
        },
        {
            "industry_impacts": [
                {
                    "sector_id": "technology",
                    "source_ids": [1],
                    "prose": "The deadline is tomorrow",
                }
            ]
        },
    ],
)
def test_report_plan_rejects_extra_fields_invalid_enums_and_source_ids(change):
    from core.report_plan import parse_report_plan

    plan = {**deepcopy(PLAN), **change}
    with pytest.raises(ValueError):
        parse_report_plan(json.dumps(plan), SOURCES)


def test_report_plan_preserves_source_title_quotations_without_treating_them_as_prose():
    from core.report_plan import render_report_plan, validate_rendered_report

    sources = [{**SOURCES[0], "title": "Rule effective January 1, 2027"}]
    body = render_report_plan(PLAN, sources)
    validate_rendered_report(body, PLAN, sources)
    assert "[Rule effective January 1, 2027]" in body


@pytest.mark.parametrize("title", ["SEC.gov | Final Rule", r"SEC.gov C:\[Docs] \| Final Rule"])
def test_report_plan_escapes_source_title_pipes_in_regulatory_table(title):
    from core.report_plan import render_report_plan, validate_rendered_report
    from test_report_evidence import stored_report

    source = {
        **SOURCES[0],
        "title": title,
        "url": "https://www.sec.gov/rules/final/example",
        "snippet": "The United States final reporting rule changes reporting requirements.",
    }
    plan = {
        **deepcopy(PLAN),
        "regulatory_changes": [
            {
                "source_id": 1,
                "change": "final reporting rule",
                "jurisdiction": "United States",
                "evidence_excerpt": source["snippet"],
            }
        ],
    }

    plan["control_implications"][0].update(
        focus="final reporting rule", evidence_excerpt=source["snippet"]
    )
    body = render_report_plan(plan, [source])

    assert r"\| Final Rule]" in body
    validate_rendered_report(body, plan, [source])
    root = Path(__file__).resolve().parents[2]
    composer = runpy.run_path(str(root / "scripts/compose_site_report.py"))
    checker = runpy.run_path(str(root / "scripts/check_site_report.py"))
    builder = runpy.run_path(str(root / "scripts/build_site.py"))
    data = stored_report(body, plan)
    data["metadata"]["source_articles"] = [
        {key: value for key, value in source.items() if key != "digest_url"}
    ]
    markdown = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    manifest = composer["evidence_manifest"](data, composer["source_articles"](data["metadata"]))
    checker["validate_evidence_manifest"](
        markdown, builder["report_fields"](markdown), json.dumps(manifest)
    )
    rendered = builder["render_report"](markdown)
    table = re.search(r"<tbody>(.*?)</tbody>", rendered, re.S)
    assert table is not None and table[1].count("<td>") == 5
    assert f'aria-label="Source 1: {title}"' in rendered
    assert f">{title}</a>" in rendered


def test_report_metadata_retains_the_selection_plan():
    from models.api import ReportMetadata

    metadata = ReportMetadata(article_count=1, grc_article_count=1, report_plan=PLAN)
    assert metadata.model_dump()["report_plan"] == PLAN


def test_composer_preserves_source_ids_for_duplicate_urls():
    from core.report_plan import render_report_plan
    from test_report_evidence import stored_report

    root = Path(__file__).resolve().parents[2]
    composer = runpy.run_path(str(root / "scripts/compose_site_report.py"))
    shared_url = "https://example.com/shared-advisory"
    sources = [
        {
            **{key: value for key, value in SOURCES[0].items() if key != "digest_url"},
            "title": "First feed entry",
            "url": shared_url,
        },
        {
            **{key: value for key, value in SOURCES[0].items() if key != "digest_url"},
            "title": "Second feed entry",
            "url": shared_url,
        },
    ]
    plan = {
        "regulatory_changes": [],
        "control_implications": [
            {
                "control_id": "governance",
                "priority": "medium",
                "source_ids": [2],
                "focus": "security advisory",
                "evidence_excerpt": SOURCES[0]["snippet"],
            }
        ],
        "industry_impacts": [],
    }
    data = stored_report(render_report_plan(plan, sources), plan)
    data["metadata"]["source_articles"] = sources

    normalized_sources = composer["source_articles"](data["metadata"])
    assert [source["title"] for source in normalized_sources] == [
        "First feed entry",
        "Second feed entry",
    ]
    report = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    assert "Governance and accountability" in report
    assert "[Second feed entry](https://example.com/shared-advisory)" in report


def publish_plan(plan, sources):
    from core.report_plan import render_report_plan
    from test_report_evidence import stored_report

    root = Path(__file__).resolve().parents[2]
    composer = runpy.run_path(str(root / "scripts/compose_site_report.py"))
    checker = runpy.run_path(str(root / "scripts/check_site_report.py"))
    builder = runpy.run_path(str(root / "scripts/build_site.py"))
    data = stored_report(render_report_plan(plan, sources), plan)
    data["metadata"]["source_articles"] = sources
    report = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    manifest = composer["evidence_manifest"](data, composer["source_articles"](data["metadata"]))
    checker["validate_evidence_manifest"](
        report,
        builder["report_fields"](report),
        json.dumps(manifest),
        require_current_schema=True,
    )
    return report, manifest


@pytest.mark.parametrize("same_title", [False, True])
def test_indexed_duplicate_sources_survive_full_publication(same_title):
    sources = [{k: v for k, v in SOURCES[0].items() if k != "digest_url"}]
    sources.append({**sources[0], "title": sources[0]["title"] if same_title else "Second entry"})
    sources.append({**sources[0], "title": "Later source", "url": "https://example.com/later"})
    plan = deepcopy(PLAN)
    plan["control_implications"] = [
        {**PLAN["control_implications"][0], "source_ids": [i]} for i in [2, 3]
    ]
    plan["industry_impacts"][0]["source_ids"] = [2, 3]
    report, manifest = publish_plan(plan, sources)
    assert [s["title"] for s in manifest["sources"]] == [s["title"] for s in sources]
    assert report.count("[View in SentryDigest]") == 3
    assert "[Later source](https://example.com/later)" in report


def test_markdown_url_serialization_preserves_distinct_digest_identities():
    sources = [
        {**{k: v for k, v in SOURCES[0].items() if k != "digest_url"}, "url": url}
        for url in ("https://example.com/a_(b)", "https://example.com/a_%28b%29")
    ]
    plan = deepcopy(PLAN)
    plan["control_implications"] = [
        {**PLAN["control_implications"][0], "source_ids": [i]} for i in [1, 2]
    ]
    report, manifest = publish_plan(plan, sources)
    assert [s["url"] for s in manifest["sources"]] == [s["url"] for s in sources]
    assert len({s["digest_url"] for s in manifest["sources"]}) == 2
    assert report.count("[View in SentryDigest]") == 2


def test_regulatory_rows_resolve_duplicate_url_evidence_by_exact_selected_source():
    from test_report_evidence import SOURCE, selection_plan

    sources = [
        SOURCE,
        {
            **SOURCE,
            "title": "Another retained excerpt",
            "snippet": "A separate notice discusses public consultation.",
        },
    ]
    report, _ = publish_plan(selection_plan(), sources)
    assert SOURCE["snippet"] in report


@pytest.mark.parametrize("field", ["title", "url"])
def test_composition_rejects_missing_source_identity_without_shifting_indices(field):
    from test_report_evidence import stored_report

    root = Path(__file__).resolve().parents[2]
    composer = runpy.run_path(str(root / "scripts/compose_site_report.py"))
    data = stored_report("", PLAN)
    data["metadata"]["source_articles"] = [{**SOURCES[0], field: ""}, SOURCES[0]]
    with pytest.raises(SystemExit, match="must retain its title and URL"):
        composer["source_articles"](data["metadata"])
