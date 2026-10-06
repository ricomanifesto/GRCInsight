"""Finding evidence must retain article-field provenance, never infer it from a title."""

from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from core.workflow import _build_source_evidence
from core.report_plan import parse_report_plan
from models.api import ArticleInput

TITLE = "Critical vulnerability: enterprise gateway permits remote code execution"
DETAIL = "The affected gateway requires an authenticated administrator session; no exploitation has been reported."


def source(summary=DETAIL, content="", title=TITLE):
    return _build_source_evidence(
        [
            ArticleInput(
                title=title,
                url="https://example.com/advisory",
                summary=summary,
                content=content,
                published=datetime(2026, 10, 6, tzinfo=timezone.utc),
            )
        ]
    )[0]


def plan(excerpt=DETAIL, origin="summary"):
    return {
        "regulatory_changes": [],
        "industry_impacts": [],
        "control_implications": [
            {
                "control_id": "vulnerability_management",
                "priority": "medium",
                "source_ids": [1],
                "focus": "gateway",
                "evidence_origin": origin,
                "evidence_excerpt": excerpt,
            }
        ],
    }


def test_builder_keeps_article_fields_separate_from_the_headline():
    item = source(content="A separate article passage contains additional remediation details.")
    assert item["article_evidence"] == [
        {"origin": "summary", "text": DETAIL, "extraction_version": 1, "raw_text": DETAIL},
        {
            "origin": "content",
            "text": "A separate article passage contains additional remediation details.",
            "extraction_version": 1,
            "raw_text": "A separate article passage contains additional remediation details.",
        },
    ]
    assert parse_report_plan(json.dumps(plan()), [item]) == plan()


@pytest.mark.parametrize("repeats", [1, 2, 3, 12])
def test_repeated_headlines_from_actual_source_builder_are_not_evidence(repeats):
    item = source(summary=(TITLE + " ") * repeats, content=TITLE)
    candidate = item["article_evidence"][0]["text"]
    with pytest.raises(ValueError, match="non-headline"):
        parse_report_plan(json.dumps(plan(candidate)), [item])


def test_title_and_article_fields_cannot_be_spliced_into_one_quote():
    item = source()
    with pytest.raises(ValueError, match="segment"):
        parse_report_plan(json.dumps(plan(item["snippet"])), [item])


@pytest.mark.parametrize("origin", ["headline", "snippet", "content", "model", None])
def test_finding_cannot_invent_or_relabel_its_evidence_origin(origin):
    with pytest.raises(ValueError, match="origin|segment"):
        parse_report_plan(json.dumps(plan(origin=origin)), [source()])


def test_legacy_flattened_source_cannot_be_promoted_by_guessing_an_origin():
    item = source()
    item.pop("article_evidence")
    with pytest.raises(ValueError, match="article evidence"):
        parse_report_plan(json.dumps(plan()), [item])


def test_excerpt_cannot_select_only_the_headline_inside_a_real_article_segment():
    item = source(summary=TITLE + ". " + DETAIL)
    with pytest.raises(ValueError, match="non-headline"):
        parse_report_plan(json.dumps(plan(TITLE)), [item])
    assert parse_report_plan(json.dumps(plan()), [item]) == plan()


def test_truncation_never_creates_a_new_word_from_a_long_repeated_headline():
    item = source(summary=(TITLE + " ") * 20)
    segment = item["article_evidence"][0]["text"]
    assert len(segment) <= 700
    assert segment[-1].isspace() is False
    with pytest.raises(ValueError, match="non-headline"):
        parse_report_plan(json.dumps(plan(segment)), [item])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x[0].update(origin="headline"),
        lambda x: x[0].update(approved=True),
        lambda x: x.append(deepcopy(x[0])),
        lambda x: x[0].update(text=123),
    ],
)
def test_segment_receipt_rejects_ambiguous_or_unsupported_shape(mutation):
    item = source()
    mutation(item["article_evidence"])
    with pytest.raises(ValueError, match="article evidence"):
        parse_report_plan(json.dumps(plan()), [item])


def test_segment_origin_survives_composition_and_manifest_validation():
    import runpy
    from pathlib import Path
    from core.report_plan import render_report_plan
    from test_report_evidence import stored_report

    root = Path(__file__).resolve().parents[2]
    composer, checker, builder = [
        runpy.run_path(str(root / "scripts" / name))
        for name in ("compose_site_report.py", "check_site_report.py", "build_site.py")
    ]
    item = source(content="A different retained passage records that the patch is available.")
    selection = plan()
    report = stored_report(render_report_plan(selection, [item]), selection)
    report["metadata"]["source_articles"] = [item]
    markdown = composer["compose_report"](
        report, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    manifest = composer["evidence_manifest"](
        report, composer["source_articles"](report["metadata"])
    )
    assert manifest["sources"][0]["article_evidence"] == item["article_evidence"]
    assert manifest["report_plan"]["control_implications"][0]["evidence_origin"] == "summary"
    checker["validate_evidence_manifest"](
        markdown,
        builder["report_fields"](markdown),
        json.dumps(manifest),
        require_current_contract=True,
    )
    for mutation in ("missing", "changed_text", "changed_origin", "changed_plan"):
        broken = deepcopy(manifest)
        if mutation == "missing":
            broken["sources"][0].pop("article_evidence")
        elif mutation == "changed_text":
            broken["sources"][0]["article_evidence"][0]["text"] = TITLE
        elif mutation == "changed_origin":
            broken["sources"][0]["article_evidence"][0]["origin"] = "headline"
        else:
            broken["report_plan"]["control_implications"][0]["evidence_origin"] = "content"
        with pytest.raises(SystemExit):
            checker["validate_evidence_manifest"](
                markdown,
                builder["report_fields"](markdown),
                json.dumps(broken),
                require_current_contract=True,
            )


def test_prompt_offers_only_article_segments_eligible_for_a_finding():
    from services.model_service import GRCModelService

    item = source(summary=TITLE + ". " + TITLE, content=DETAIL)
    service = GRCModelService.__new__(GRCModelService)
    prompt = service._create_report_prompt({"source_evidence": [item]}, {})
    segment_line = next(
        line for line in prompt.splitlines() if "Eligible article evidence segments:" in line
    )
    assert json.loads(segment_line.split("segments: ")[1]) == {"content": DETAIL}
    assert "evidence_origin" in prompt


@pytest.mark.parametrize("cve", ["cve-2026-12345", "Cve-2026-12345"])
def test_prompt_preserves_original_spelling_of_allowed_cves(cve):
    from services.model_service import GRCModelService

    detail = f"The gateway flaw {cve} requires an authenticated administrator session."
    item = source(summary=detail)
    service = GRCModelService.__new__(GRCModelService)
    prompt = service._create_report_prompt({"source_evidence": [item]}, {})
    segment_line = next(
        line for line in prompt.splitlines() if "Eligible article evidence segments:" in line
    )
    assert json.loads(segment_line.split("segments: ")[1]) == {"summary": detail}
    assert parse_report_plan(json.dumps(plan(detail)), [item]) == plan(detail)


def test_prompt_still_omits_segments_with_cves_outside_the_bounded_set():
    from services.model_service import GRCModelService

    item = source(summary="The gateway flaw cve-2026-12345 requires administrator access.")
    item["cves"] = []
    service = GRCModelService.__new__(GRCModelService)
    prompt = service._create_report_prompt({"source_evidence": [item]}, {})
    segment_line = next(
        line for line in prompt.splitlines() if "Eligible article evidence segments:" in line
    )
    assert json.loads(segment_line.split("segments: ")[1]) == {}


@pytest.mark.parametrize("field", ["evidence_excerpt", "focus"])
@pytest.mark.parametrize("separator", ["  ", "\t", "\u00a0"])
def test_finding_rejects_changed_internal_whitespace(field, separator):
    selection = plan()
    selection["control_implications"][0][field] = (
        DETAIL.replace("requires an", "requires" + separator + "an")
        if field == "evidence_excerpt"
        else "authenticated" + separator + "administrator"
    )
    with pytest.raises(ValueError, match="exactly"):
        parse_report_plan(json.dumps(selection), [source()])
