"""An executive decision agenda must add structure above the source evidence."""

from copy import deepcopy
import json
from pathlib import Path
import re
import runpy

import pytest

from core.report_plan import parse_report_plan, render_report_plan, validate_rendered_report
from test_report_substance import PLAN as FINDING_PLAN, SOURCE


def narrative_plan():
    plan = deepcopy(FINDING_PLAN)
    plan["industry_impacts"] = []
    plan["executive_brief"] = {"decision_frame": "exposure", "source_ids": [1]}
    return plan


def summary_of(body):
    return body.split("## Executive Summary\n\n", 1)[1].split("\n\n## ", 1)[0]


def test_executive_brief_is_a_conditional_decision_narrative_not_an_excerpt_list():
    plan = parse_report_plan(json.dumps(narrative_plan()), [SOURCE])
    body = render_report_plan(plan, [SOURCE])
    summary = summary_of(body)
    assert not re.search(r"(?m)^\s*(?:[-*]|\d+[.)])\s", summary)
    assert 2 <= len(summary.split("\n\n")) <= 3
    assert "Java support" in summary and SOURCE["url"] in summary
    assert "decid" in summary.lower()
    assert "if " in summary.lower() or "whether " in summary.lower()
    assert "Source excerpt:" not in summary
    assert SOURCE["snippet"] not in summary
    assert "proof of concept" in body and "no exploitation" in body
    assert body.count(SOURCE["snippet"]) == 1
    assert body.index(SOURCE["snippet"]) > body.index("## Evidence and Decisions")
    assert "Owner:" in body and "Evidence to request:" in body
    assert "Decision trigger:" in body
    assert re.findall(r"(?m)^## (.+)$", body) == [
        "Executive Summary",
        "Sourced Regulatory Changes",
        "Evidence and Decisions",
        "Source Highlights",
    ]
    validate_rendered_report(body, plan, [SOURCE])


@pytest.mark.parametrize(
    "brief",
    [
        None,
        "A changing threat landscape requires a proactive approach.",
        {"decision_frame": "exposure", "source_ids": []},
        {"decision_frame": "exposure", "source_ids": [1, 1]},
        {"decision_frame": "exposure", "source_ids": [2]},
        {"decision_frame": "supplier", "source_ids": [1]},
        {"decision_frame": "invented_trend", "source_ids": [1]},
        {
            "decision_frame": "exposure",
            "source_ids": [1],
            "narrative": "Every business is now exposed.",
        },
    ],
)
def test_generic_missing_or_unsupported_executive_selections_fail_closed(brief):
    plan = narrative_plan()
    if brief is None:
        del plan["executive_brief"]
    else:
        plan["executive_brief"] = brief
    with pytest.raises(ValueError, match="executive|editorial"):
        parse_report_plan(json.dumps(plan), [SOURCE])


def test_sector_labels_do_not_justify_a_sector_consequence():
    plan = narrative_plan()
    plan["industry_impacts"] = [{"sector_id": "healthcare", "source_ids": [1]}]
    with pytest.raises(ValueError, match="sector|editorial"):
        parse_report_plan(json.dumps(plan), [SOURCE])


@pytest.mark.parametrize(
    "replacement",
    [
        "- Java support. Source excerpt: “" + SOURCE["snippet"] + "”",
        "This report highlights emerging risks. Leaders should stay informed and review controls.",
        "Review Java support. Assess Java support. Consider Java support and review controls.",
    ],
)
def test_publication_rejects_bullet_only_generic_and_paraphrased_repetition(replacement):
    plan = narrative_plan()
    body = render_report_plan(plan, [SOURCE])
    bad = body.replace(summary_of(body), replacement)
    with pytest.raises(ValueError, match="retained report plan|editorial"):
        validate_rendered_report(bad, plan, [SOURCE])


@pytest.mark.parametrize(
    "extra",
    [
        "## Risk Assessment\n\nReview Java support against your control environment.",
        "## Recommendations for Action\n\nAssess Java support in the context of deployed controls.",
        "## Industry Impact Analysis\n\nThis has significant implications for every sector.",
    ],
)
def test_rephrased_duplicate_sections_are_not_additional_insight(extra):
    plan = narrative_plan()
    body = render_report_plan(plan, [SOURCE])
    with pytest.raises(ValueError, match="retained report plan|editorial"):
        validate_rendered_report(body + "\n\n" + extra, plan, [SOURCE])


def test_legitimate_overview_to_detail_reuses_identity_and_citations():
    plan = narrative_plan()
    body = render_report_plan(plan, [SOURCE], include_digest=True)
    assert body.count("Java support") >= 2
    assert body.count(SOURCE["url"]) >= 3
    assert body.count(SOURCE["snippet"]) == 1
    validate_rendered_report(body, plan, [SOURCE], include_digest=True)


def test_identical_control_findings_combine_evidence_without_losing_sources():
    plan = narrative_plan()
    plan["control_implications"].append({**plan["control_implications"][0], "source_ids": [2]})
    sources = [SOURCE, {**SOURCE, "title": "Second source", "url": "https://example.com/second"}]
    body = render_report_plan(plan, sources)
    assert body.count("### Java support") == 1
    assert body.count(SOURCE["snippet"]) == 1
    assert "[Second source](https://example.com/second)" in body
    validate_rendered_report(body, plan, sources)


def test_source_identity_text_is_not_misclassified_as_repeated_analysis():
    plan = narrative_plan()
    sources = [SOURCE, {**SOURCE, "title": SOURCE["snippet"], "url": "https://example.com/related"}]
    body = render_report_plan(plan, sources)
    assert body.count("**Source evidence:**") == 1
    assert "https://example.com/related" in body
    validate_rendered_report(body, plan, sources)


def test_generic_three_paragraph_substitution_is_rejected_even_with_valid_citations():
    from core.report_plan import validate_editorial_quality

    plan = narrative_plan()
    body = render_report_plan(plan, [SOURCE])
    link = f"[{SOURCE['title']}]({SOURCE['url']})"
    generic = (
        f"Java support deserves attention. Leaders should consider whether controls remain appropriate and assess the available evidence before deciding how to respond. {link}\n\n"
        "Management should review the current position, consider the relevant controls and determine appropriate next steps. Accountable teams should assess available information and confirm whether any changes are warranted.\n\n"
        "Local applicability remains uncertain. Review priorities when further information becomes available, confirm the facts with the relevant owners and consider what actions might be appropriate in the circumstances."
    )
    bad = body.replace(summary_of(body), generic)
    # Shape/citation checks alone are deliberately not presented as a semantic oracle.
    validate_editorial_quality(bad, plan, [SOURCE])
    with pytest.raises(ValueError, match="retained report plan"):
        validate_rendered_report(bad, plan, [SOURCE])


def test_regulatory_evidence_is_not_repeated_in_the_control_decision():
    from test_report_evidence import SOURCE as primary, selection_plan

    plan = selection_plan()
    body = render_report_plan(plan, [primary])
    assert body.count(primary["snippet"]) == 1
    assert "Control decision (inference):" in body
    assert "See the sourced regulatory evidence above" in body


def test_shared_regulatory_quote_keeps_literal_ampersands_without_a_false_duplicate():
    from test_report_evidence import SOURCE as primary, selection_plan

    excerpt = "The United States final reporting rule covers risk & compliance disclosures."
    source = {
        **primary,
        "snippet": excerpt,
        "article_evidence": [
            {
                "origin": "summary",
                "raw_text": excerpt,
                "text": excerpt,
                "extraction_version": 1,
            }
        ],
    }
    plan = selection_plan()
    plan["regulatory_changes"][0]["evidence_excerpt"] = excerpt
    plan["control_implications"][0]["evidence_excerpt"] = excerpt
    body = render_report_plan(plan, [source])
    assert body.count(excerpt) == 1
    validate_rendered_report(body, plan, [source])


def test_mixed_topics_require_separate_decisions_instead_of_an_invented_shared_frame():
    plan = narrative_plan()
    plan["control_implications"].append(
        {**plan["control_implications"][0], "source_ids": [2], "control_id": "third_party_risk"}
    )
    plan["executive_brief"]["source_ids"] = [1, 2]
    sources = [
        SOURCE,
        {**SOURCE, "title": "Supplier assessment", "url": "https://example.com/supplier"},
    ]
    with pytest.raises(ValueError, match="frame is not supported"):
        parse_report_plan(json.dumps(plan), sources)
    plan["executive_brief"]["decision_frame"] = "separate"
    body = render_report_plan(plan, sources)
    assert "separate decisions" in summary_of(body)
    assert "Supplier risk owner" in body
    validate_rendered_report(body, plan, sources)


def test_regulatory_frame_uses_applicability_agenda_even_with_a_control_mapping():
    from test_report_evidence import SOURCE as primary, selection_plan

    plan = selection_plan()
    plan["executive_brief"]["decision_frame"] = "regulatory"
    summary = summary_of(render_report_plan(plan, [primary]))
    assert "verify jurisdiction and organizational applicability" in summary
    assert "check whether the development changes a control assumption" not in summary


def test_historical_v4_publication_still_validates_exactly():
    fixture = Path(__file__).parent / "fixtures/report-v4-2026-10-06"
    markdown = (fixture / "report.md").read_text()
    manifest = json.loads((fixture / "evidence-manifest.json").read_text())
    body = markdown[markdown.index("## Executive Summary") :].strip()
    assert (
        render_report_plan(
            manifest["report_plan"], manifest["sources"], include_digest=True, contract_version=4
        )
        == body
    )
    checker = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "scripts/check_site_report.py")
    )
    builder = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/build_site.py"))
    checker["validate_evidence_manifest"](
        markdown, builder["report_fields"](markdown), json.dumps(manifest)
    )
    with pytest.raises(SystemExit, match="current report contract"):
        checker["validate_evidence_manifest"](
            markdown,
            builder["report_fields"](markdown),
            json.dumps(manifest),
            require_current_contract=True,
        )


def test_report_quality_failure_has_its_own_retention_category():
    script = Path(__file__).resolve().parents[2] / "scripts/publication_state.py"
    classify = runpy.run_path(str(script))["classify_fallback_reason"]
    assert (
        classify("Report quality validation failed: executive brief is missing") == "report_quality"
    )


def test_generator_requires_supported_brief_and_distinct_section_roles():
    from services.model_service import GRCModelService

    service = GRCModelService.__new__(GRCModelService)
    prompt = service._create_report_prompt({"source_evidence": [SOURCE]}, {})
    for requirement in (
        "executive_brief",
        "decision_frame",
        "one to three",
        "separate decisions",
        "industry_impacts must be empty",
        "Do not default every finding to high",
        "Evidence and Decisions",
    ):
        assert requirement in prompt


def test_quality_retry_uses_actionable_diagnostic_and_does_not_attest_failure():
    import asyncio
    from services.model_service import GRCModelService
    from services.openrouter_client import OpenRouterGeneration

    service = GRCModelService.__new__(GRCModelService)
    calls = []
    invalid = narrative_plan()
    del invalid["executive_brief"]

    async def invoke(**kwargs):
        calls.append(kwargs)
        return OpenRouterGeneration(text=json.dumps(invalid), resolved_model="example/model")

    service._invoke = invoke
    result = asyncio.run(service.generate_grc_report({"source_evidence": [SOURCE]}, {}))
    assert len(calls) == 2
    assert "executive brief is required" in calls[1]["user_prompt"]
    assert result.failure_reason.startswith("Report quality validation failed:")
    assert "executive brief is required" in result.failure_reason
    assert result.resolved_model == "" and result.report_plan is None


def test_quality_failure_survives_workflow_and_selects_retention(monkeypatch):
    import asyncio
    from core import workflow
    from models.api import GRCAnalysisConfig
    from services.model_service import GRCReportGeneration

    reason = "Report quality validation failed: executive brief is required"

    async def feed(_url):
        return {
            "title": "Digest",
            "link": "https://digest.example/",
            "last_updated": "Tue, 06 Oct 2026 00:00:00 GMT",
            "entries": [
                {
                    "title": SOURCE["title"],
                    "link": SOURCE["url"],
                    "description": SOURCE["snippet"],
                    "content": SOURCE["snippet"],
                    "published": "Tue, 06 Oct 2026 00:00:00 GMT",
                }
            ],
        }

    async def enrich(articles):
        return articles

    class Model:
        def __init__(self, **kwargs):
            pass

        async def analyze_articles_for_grc(self, articles):
            return {
                "summary": {"total_articles": 1, "grc_relevant_count": 1},
                "analysis": {},
                "grc_articles": [{"title": articles[0].title, "url": articles[0].url}],
            }

        async def generate_grc_report(self, *_args):
            return GRCReportGeneration(content="", resolved_model="", failure_reason=reason)

    monkeypatch.setattr(workflow.rss_service, "fetch_feed", feed)
    monkeypatch.setattr(workflow.rss_service, "enrich_articles", enrich)
    monkeypatch.setattr(workflow, "GRCModelService", Model)
    result = asyncio.run(
        workflow.run_grc_analysis_endpoint("https://digest.example/feed.xml", GRCAnalysisConfig())
    )
    assert result.metadata is not None
    assert result.metadata.analysis_mode == "fallback"
    assert result.metadata.fallback_reason == reason
    classify = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "scripts/publication_state.py")
    )["classify_fallback_reason"]
    assert classify(result.metadata.fallback_reason) == "report_quality"
