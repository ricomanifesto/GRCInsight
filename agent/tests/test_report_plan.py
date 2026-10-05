"""Structured selections cannot introduce model-authored narrative claims."""

from copy import deepcopy
import json

import pytest

SOURCES = [
    {
        "title": "Security advisory",
        "url": "https://example.com/advisory",
        "snippet": "A vendor published a security advisory.",
        "digest_url": "https://digest.example/archive/2026-10-05/#advisory",
        "cves": [],
    }
]
PLAN = {
    "regulatory_changes": [],
    "control_implications": [
        {"control_id": "vulnerability_management", "priority": "high", "source_ids": [1]}
    ],
    "industry_impacts": [{"sector_id": "technology", "source_ids": [1]}],
}


def test_report_plan_renders_only_owned_text_and_retained_source_identity():
    from core.report_plan import parse_report_plan, render_report_plan, validate_rendered_report

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
                {"control_id": "governance", "priority": "high tomorrow", "source_ids": [1]}
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
                {"sector_id": "technology", "source_ids": [1], "prose": "The deadline is tomorrow"}
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


def test_report_metadata_retains_the_selection_plan():
    from models.api import ReportMetadata

    metadata = ReportMetadata(article_count=1, grc_article_count=1, report_plan=PLAN)
    assert metadata.model_dump()["report_plan"] == PLAN
