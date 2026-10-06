"""Reader and publication contracts exercised without provider calls."""

import json
from pathlib import Path
from typing import Any
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE: dict[str, Any] = {
    "title": "Final reporting rule",
    "url": "https://www.sec.gov/rules/final/example",
    "snippet": "The United States final reporting rule takes effect on 2027-01-01.",
    "article_evidence": [
        {
            "origin": "summary",
            "text": "The United States final reporting rule takes effect on 2027-01-01.",
            "extraction_version": 1,
            "raw_text": "The United States final reporting rule takes effect on 2027-01-01.",
        }
    ],
}


def validate(body, sources):
    from core.report_evidence import validate_regulatory_evidence

    return validate_regulatory_evidence(body, sources)


def body(row=None):
    changes = "No sourced regulatory changes identified in the supplied evidence."
    if row:
        changes = (
            "| Change | Jurisdiction | Document effective date | Source | Evidence excerpt |\n"
            "|---|---|---|---|---|\n" + row
        )
    return (
        "## Sourced Regulatory Changes\n\n"
        + changes
        + "\n\n## Inferred Control and Governance Implications\n\n"
        "Inference: review reporting controls.\n"
    )


def row(
    jurisdiction="United States",
    date="2027-01-01",
    quote=SOURCE["snippet"],
    url=SOURCE["url"],
):
    return f"| final reporting rule | {jurisdiction} | {date} | [Final reporting rule]({url}) | {quote} |"


def test_regulatory_change_requires_grounded_primary_evidence():
    changes = validate(body(row(date="Unknown")), [SOURCE])
    assert changes[0].jurisdiction == "United States"
    assert changes[0].document_effective_date is None
    assert changes[0].source_url == SOURCE["url"]


def test_regulatory_change_retains_date_first_excerpt_without_inferring_a_date():
    excerpt = "On 2027-01-01, the United States final reporting rule takes effect."
    source = {
        **SOURCE,
        "snippet": excerpt,
        "article_evidence": [
            {"origin": "summary", "text": excerpt, "extraction_version": 1, "raw_text": excerpt}
        ],
    }
    with pytest.raises(ValueError, match="effective date"):
        validate(body(row(quote=excerpt)), [source])
    changes = validate(body(row(date="Unknown", quote=excerpt)), [source])
    assert changes[0].document_effective_date is None
    assert changes[0].evidence_excerpt == excerpt


def test_regulatory_change_rejects_publication_date_before_relative_effective_date():
    excerpt = (
        "On 2027-01-01, the United States final reporting rule was published; "
        "it takes effect 30 days later."
    )
    with pytest.raises(ValueError, match="effective date"):
        validate(
            body(row(quote=excerpt)),
            [
                {
                    **SOURCE,
                    "snippet": excerpt,
                    "article_evidence": [
                        {
                            "origin": "summary",
                            "text": excerpt,
                            "extraction_version": 1,
                            "raw_text": excerpt,
                        }
                    ],
                }
            ],
        )


@pytest.mark.parametrize(
    "excerpt",
    [
        "On 2027-01-01, the United States agency announced the final reporting rule, and on 2028-01-01 it takes effect.",
        "The United States final reporting rule does not take effect on 2027-01-01.",
        "On 2027-01-01, the United States final reporting rule does not take effect.",
    ],
)
def test_date_claim_cannot_be_inferred_from_mixed_or_negated_prose(excerpt):
    with pytest.raises(ValueError, match="effective date"):
        validate(
            body(row(quote=excerpt)),
            [
                {
                    **SOURCE,
                    "snippet": excerpt,
                    "article_evidence": [
                        {
                            "origin": "summary",
                            "text": excerpt,
                            "extraction_version": 1,
                            "raw_text": excerpt,
                        }
                    ],
                }
            ],
        )


def test_regulatory_change_matches_prompt_encoded_source_url():
    source = {**SOURCE, "url": "https://www.sec.gov/rules/final/example_(test)"}
    encoded_url = "https://www.sec.gov/rules/final/example_%28test%29"
    changes = validate(body(row(date="Unknown", url=encoded_url)), [source])
    assert changes[0].source_url == encoded_url


def test_no_sourced_change_preserves_inference_and_unknown_dates():
    assert validate(body(), [SOURCE]) == []
    changes = validate(body(row("Unknown", "Unknown")), [SOURCE])
    assert changes[0].jurisdiction is None
    assert changes[0].document_effective_date is None


@pytest.mark.parametrize(
    "excerpt",
    [
        "The final reporting rule requires business entities to file reports.",
        "Covered entities must comply with the final reporting rule.",
        "The final reporting rule protects customer trust.",
    ],
)
def test_short_jurisdiction_must_be_a_complete_evidenced_token(excerpt):
    source = {
        **SOURCE,
        "snippet": excerpt,
        "article_evidence": [
            {"origin": "summary", "text": excerpt, "extraction_version": 1, "raw_text": excerpt}
        ],
    }
    with pytest.raises(ValueError, match="jurisdiction"):
        validate(body(row(jurisdiction="US", date="Unknown", quote=excerpt)), [source])


def test_short_jurisdiction_matches_a_complete_evidenced_token():
    excerpt = "The US final reporting rule applies to covered entities."
    source = {
        **SOURCE,
        "snippet": excerpt,
        "article_evidence": [
            {"origin": "summary", "text": excerpt, "extraction_version": 1, "raw_text": excerpt}
        ],
    }
    changes = validate(body(row(jurisdiction="US", date="Unknown", quote=excerpt)), [source])
    assert changes[0].jurisdiction == "US"


@pytest.mark.parametrize("change", ["US", "Final reporting rule"])
def test_regulatory_change_must_be_an_exact_complete_evidenced_phrase(change):
    excerpt = "The United States final reporting rule requires business entities to file reports."
    source = {
        **SOURCE,
        "snippet": excerpt,
        "article_evidence": [
            {"origin": "summary", "text": excerpt, "extraction_version": 1, "raw_text": excerpt}
        ],
    }
    with pytest.raises(ValueError, match="quote an evidenced clause"):
        validate(
            body(row(date="Unknown", quote=excerpt)).replace(
                "| final reporting rule |", f"| {change} |"
            ),
            [source],
        )


@pytest.mark.parametrize(
    "claim",
    [
        "The final reporting rule takes effect on 2027-01-01.",
        "2027-01-01 is the effective date of the final reporting rule.",
        "The compliance deadline is 2027-01-01.",
    ],
)
def test_regulatory_timing_claims_are_rejected_outside_sourced_table(claim):
    from core.report_plan import render_report_plan, validate_rendered_report

    plan = selection_plan()
    report = render_report_plan(plan, [SOURCE]) + "\n" + claim
    with pytest.raises(ValueError, match="retained report plan"):
        validate_rendered_report(report, plan, [SOURCE])


def test_unrelated_dated_prose_is_allowed_outside_sourced_table():
    report = "## Executive Summary\nThe regulator published the rule on 2027-01-01.\n\n" + body(
        row(date="Unknown")
    )
    assert validate(report, [SOURCE])[0].document_effective_date is None


@pytest.mark.parametrize("empty_table", [False, True])
@pytest.mark.parametrize(
    "claim",
    [
        "The rule takes effect on January 1, 2027.",
        "The rule takes effect in thirty days.",
        "The rule takes\neffect on 2027-01-01.",
        "The rule **takes** *effect* on 2027-01-01.",
        "The compliance deadline is tomorrow.",
        "The rule is effective immediately.",
        "The rule applies from January 2027.",
        "The rule enters into force next year.",
    ],
)
def test_timing_guard_does_not_depend_on_a_date_format(claim, empty_table):
    from core.report_plan import render_report_plan, validate_rendered_report

    plan = selection_plan()
    if empty_table:
        plan["regulatory_changes"] = []
    report = render_report_plan(plan, [SOURCE]) + "\n" + claim
    with pytest.raises(ValueError, match="retained report plan"):
        validate_rendered_report(report, plan, [SOURCE])


def test_timing_guard_preserves_exact_source_titles_and_unrelated_analysis():
    from core.report_plan import render_report_plan, validate_rendered_report

    title = "Final rule takes effect on 2027-01-01"
    sources = [{**SOURCE, "title": title}]
    plan = selection_plan()
    report = render_report_plan(plan, sources)
    validate_rendered_report(report, plan, sources)
    with pytest.raises(ValueError, match="retained report plan"):
        validate_rendered_report(
            report.replace(title, "Invented deadline: tomorrow"), plan, sources
        )


@pytest.mark.parametrize(
    "change",
    [
        {"url": "https://news.example/security"},
        {"url": "https://sec.gov.evil.example/rules"},
        {"url": "https://sec.gov@evil.example/rules"},
        {"quote": "A fabricated legal announcement."},
        {"date": "2028-01-01"},
        {"jurisdiction": "California"},
    ],
)
def test_regulatory_validation_rejects_unattested_claims(change):
    source = {**SOURCE, "url": change.get("url", SOURCE["url"])}
    with pytest.raises(ValueError):
        validate(body(row(**change)), [source])


def test_inferred_mapping_cannot_be_a_sourced_change():
    with pytest.raises(ValueError):
        validate(body(row().replace("final reporting rule |", "GDPR (implied) |")), [SOURCE])
    with pytest.raises(ValueError):
        validate("## Sourced Regulatory Changes\nGDPR requires consent.\n", [SOURCE])


def test_reader_citations_are_compact_accessible_and_deduplicated():
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    markdown = """# Report
## Executive Summary
A claim [Long title](https://example.com/a). Another [Long title](https://example.com/a).
| Finding | Evidence |
|---|---|
| Claim | [Long title](https://example.com/b) |
## Source Highlights
- [Long title](https://example.com/a) · [View in SentryDigest](https://example.com/archive/2026-10-05/#one)
- [Long title](https://example.com/b)
- [Long title](https://example.com/a)
"""
    rendered = builder["render_report"](markdown)
    before, highlights = rendered.split("<h2>Source Highlights</h2>")
    assert ">Long title</a>" not in before
    assert before.count('class="report-citation"') == 3
    assert before.count(">[1]</a>") == 2
    assert ">[2]</a>" in before
    assert 'aria-label="Source 1: Long title"' in before
    assert highlights.count('id="source-1"') == 1
    assert ">Long title</a>" in highlights
    assert "https://example.com/archive/2026-10-05/#one" in highlights
    assert rendered == builder["render_report"](markdown)


def test_reader_only_compacts_sources_listed_in_highlights():
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    markdown = """# Report
## Executive Summary
A highlighted [Known source](https://example.com/known) and an unlisted [Other source](https://example.com/other).
## Source Highlights
- [Known source](https://example.com/known)
"""
    rendered = builder["render_report"](markdown)
    before, highlights = rendered.split("<h2>Source Highlights</h2>")
    assert 'class="report-citation"' in before
    assert ">[1]</a>" in before
    assert ">Other source</a>" in before
    assert "Source 2:" not in rendered
    assert 'id="source-1"' in highlights


def test_reader_keeps_duplicate_url_citations_tied_to_source_titles():
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    markdown = """# Report
## Executive Summary
[First source](https://example.com/shared) and [Second source](https://example.com/shared).
## Source Highlights
- [First source](https://example.com/shared)
- [Second source](https://example.com/shared)
"""
    rendered = builder["render_report"](markdown)
    before, highlights = rendered.split("<h2>Source Highlights</h2>")
    assert ">[1]</a>" in before
    assert ">[2]</a>" in before
    assert 'aria-label="Source 1: First source"' in before
    assert 'aria-label="Source 2: Second source"' in before
    assert highlights.count('id="source-1"') == 1
    assert highlights.count('id="source-2"') == 1


def test_retained_report_projects_implied_mappings_honestly():
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    markdown = (ROOT / "site/archive/2026-10-05T15-24-23Z/report.md").read_text()
    rendered = builder["render_report"](markdown)
    assert "<h2>Inferred Control and Governance Implications</h2>" in rendered
    assert "<h2>Key Regulatory Developments</h2>" not in rendered
    assert "These are inferred mappings, not verified regulatory changes." in rendered
    assert "report-citation" in rendered
    assert "GDPR / CCPA (implied)" in rendered


def test_notice_leads_with_exact_report_and_attempt_times_across_days():
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    state = {
        "outcome": "retained",
        "report_generated_at": "2026-10-04T15:24:23Z",
        "attempted_at": "2026-10-05T18:24:03Z",
        "refusal_category": "unclassified_provider_failure",
    }
    rendered = builder["publication_notice_html"](
        state, {"schedule": {"cadence": "daily", "time_utc": "13:00"}}
    )
    lead, details = rendered.split("<details>")
    assert "Showing the report generated on" in lead
    assert "October 4, 2026 at 15:24:23 UTC" in lead
    assert "October 5, 2026 at 18:24:03 UTC" in lead
    assert "refresh failed" in lead
    assert "provider" not in lead and "model" not in lead
    assert "unclassified provider failure" in details
    assert "publication-state.json" in details


def test_archive_rebuild_uses_reader_projection_without_rewriting_evidence(tmp_path, monkeypatch):
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    site = ROOT / "site"
    state = json.loads((site / "publication-state.json").read_text())
    history = json.loads((site / "publication-history.json").read_text())
    report = site / "archive/2026-10-05T15-24-23Z/report.md"
    original = report.read_bytes()
    manifest = report.with_name("evidence-manifest.json").read_bytes()
    snapshot = tmp_path / report.parent.name
    snapshot.mkdir()
    (snapshot / "report.md").write_bytes(original)
    (snapshot / "index.html").write_text("<html>Old retained reading view</html>")
    (snapshot / "evidence-manifest.json").write_bytes(manifest)
    monkeypatch.setitem(builder["expected_outputs"].__globals__, "ARCHIVE_DIR", tmp_path)
    outputs = builder["expected_outputs"](
        (site / "index.md").read_text(),
        (site / "index.html").read_text(),
        state,
        history,
    )
    assert "report-citation" in outputs[snapshot / "index.html"]
    assert "Inferred Control and Governance Implications" in outputs[snapshot / "index.html"]
    assert original == report.read_bytes()

    assert (snapshot / "evidence-manifest.json").read_bytes() == manifest
    assert (snapshot / "report.md").read_bytes() == original


def test_citations_keep_highlights_after_fenced_code_and_escape_attributes():
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    rendered = builder["render_report"]("""# Report
## Executive Summary
```
not a citation [Hidden](https://example.com/code)
```
Claim [A "quoted" <title>](https://example.com/a?x=1&y=2).
## Source Highlights
- [A "quoted" <title>](https://example.com/a?x=1&y=2)
""")
    before, highlights = rendered.split("<h2>Source Highlights</h2>")
    assert ">[1]</a>" in before
    assert 'aria-label="Source 1: A &quot;quoted&quot; &lt;title&gt;"' in before
    assert 'id="source-1"' in highlights
    assert 'href="https://example.com/a?x=1&amp;y=2"' in highlights
    assert 'class="report-citation"' not in highlights


def test_regulatory_change_description_and_date_role_must_match_evidence():
    with pytest.raises(ValueError):
        validate(
            body(row().replace("final reporting rule |", "A new worldwide ban |")),
            [SOURCE],
        )
    excerpt = "The United States final reporting rule was published on 2027-01-01 and takes effect on 2027-02-01."
    with pytest.raises(ValueError):
        validate(
            body(row(quote=excerpt)),
            [
                {
                    **SOURCE,
                    "snippet": excerpt,
                    "article_evidence": [
                        {
                            "origin": "summary",
                            "text": excerpt,
                            "extraction_version": 1,
                            "raw_text": excerpt,
                        }
                    ],
                }
            ],
        )


def selection_plan():
    return {
        "executive_brief": {"decision_frame": "governance", "source_ids": [1]},
        "regulatory_changes": [
            {
                "source_id": 1,
                "change": "final reporting rule",
                "jurisdiction": "United States",
                "evidence_excerpt": SOURCE["snippet"],
            }
        ],
        "control_implications": [
            {
                "control_id": "governance",
                "priority": "medium",
                "source_ids": [1],
                "focus": "final reporting rule",
                "evidence_excerpt": SOURCE["snippet"],
                "evidence_origin": "summary",
            }
        ],
        "industry_impacts": [],
    }


def stored_report(content, plan=None):
    return {
        "status": "completed",
        "title": "GRC Intelligence Report",
        "generated_at": "2026-10-05T15:24:23Z",
        "content": content,
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://digest.example/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-10-05",
            "source_issue_url": "https://digest.example/archive/2026-10-05/",
            "analysis_period": "October 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "requested_model": "openrouter/example/model",
            "resolved_model": "example/model",
            "source_articles": [SOURCE],
            "report_plan": plan,
        },
    }


def full_report(regulatory_body):
    return (
        "## Executive Summary\nReview the cited rule.\n\n"
        + regulatory_body
        + "\n## Industry Impact Analysis\nReview applicability.\n"
        + "\n## Risk Assessment\nReview controls.\n"
        + "\n## Recommendations for Action\nCheck applicability.\n"
        + "\n## Source Highlights\n- [Final reporting rule]("
        + SOURCE["url"]
        + ")\n"
    )


def test_regulatory_contract_survives_composition_manifest_and_publication_validation():
    composer = runpy.run_path(str(ROOT / "scripts/compose_site_report.py"))
    checker = runpy.run_path(str(ROOT / "scripts/check_site_report.py"))
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    from core.report_plan import render_report_plan

    plan = selection_plan()
    data = stored_report(render_report_plan(plan, [SOURCE]), plan)
    markdown = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    sources = composer["source_articles"](data["metadata"])
    manifest = composer["evidence_manifest"](data, sources)
    assert manifest["report_contract_version"] == 5
    assert manifest["sources"][0]["snippet"] == SOURCE["snippet"]
    validate_manifest = checker["validate_evidence_manifest"]
    validate_manifest(
        markdown,
        builder["report_fields"](markdown),
        json.dumps(manifest),
        require_current_schema=True,
    )
    corrupted = markdown.replace("Unknown |", "2028-01-01 |")
    with pytest.raises(SystemExit, match="effective date"):
        validate_manifest(corrupted, builder["report_fields"](markdown), json.dumps(manifest))
    data["content"] = data["content"].replace("Unknown |", "2028-01-01 |")
    with pytest.raises(SystemExit, match="effective date"):
        composer["compose_report"](
            data, "https://digest.example/feed.xml", "openrouter/example/model"
        )


def test_model_rejects_complete_but_unevidenced_legal_change():
    import asyncio
    from services.model_service import GRCModelService
    from services.openrouter_client import OpenRouterGeneration

    service = GRCModelService.__new__(GRCModelService)

    async def invoke(**kwargs):
        return OpenRouterGeneration(
            text=full_report(body(row(date="2028-01-01"))),
            resolved_model="example/model",
        )

    service._invoke = invoke
    result = asyncio.run(service.generate_grc_report({"source_evidence": [SOURCE]}, {}))
    assert result.resolved_model == ""
    assert "Unable to generate report" in result.content


def test_prose_timing_guard_is_shared_by_model_composer_and_publication_checker():
    import asyncio
    from services.model_service import GRCModelService
    from services.openrouter_client import OpenRouterGeneration

    from core.report_plan import render_report_plan

    plan = selection_plan()
    good = render_report_plan(plan, [SOURCE])
    bad = good + "\nThe rule takes effect on January 1, 2027."
    service = GRCModelService.__new__(GRCModelService)

    async def invoke(**kwargs):
        return OpenRouterGeneration(text=bad, resolved_model="example/model")

    service._invoke = invoke
    result = asyncio.run(service.generate_grc_report({"source_evidence": [SOURCE]}, {}))
    assert result.resolved_model == ""
    composer = runpy.run_path(str(ROOT / "scripts/compose_site_report.py"))
    with pytest.raises(SystemExit, match="retained report plan"):
        composer["compose_report"](
            stored_report(bad, plan),
            "https://digest.example/feed.xml",
            "openrouter/example/model",
        )
    data = stored_report(good, plan)
    markdown = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    manifest = composer["evidence_manifest"](data, composer["source_articles"](data["metadata"]))
    checker = runpy.run_path(str(ROOT / "scripts/check_site_report.py"))
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    with pytest.raises(SystemExit, match="retained report plan"):
        checker["validate_evidence_manifest"](
            markdown + "\nThe compliance deadline is tomorrow.",
            builder["report_fields"](markdown),
            json.dumps(manifest),
        )
    data["metadata"].pop("report_plan")
    with pytest.raises(SystemExit, match="report plan"):
        composer["compose_report"](
            data, "https://digest.example/feed.xml", "openrouter/example/model"
        )
    manifest.pop("report_plan")
    with pytest.raises(SystemExit, match="report plan"):
        checker["validate_evidence_manifest"](
            markdown, builder["report_fields"](markdown), json.dumps(manifest)
        )
    manifest["report_contract_version"] = 1
    with pytest.raises(SystemExit, match="current report contract"):
        checker["validate_evidence_manifest"](
            markdown, builder["report_fields"](markdown), json.dumps(manifest)
        )


@pytest.mark.parametrize(
    ("field", "value", "excerpt"),
    [
        (
            "jurisdiction",
            "US",
            "The final reporting rule requires business entities to file reports.",
        ),
        ("jurisdiction", "US", "The final reporting rule asks entities to contact us."),
        (
            "jurisdiction",
            "IN",
            "The final reporting rule is in force for listed entities.",
        ),
        (
            "change",
            "US",
            "The final reporting rule requires business entities to file reports.",
        ),
        (
            "change",
            "Final reporting rule",
            "The final reporting rule applies to listed entities.",
        ),
    ],
)
def test_regulatory_values_require_complete_source_phrases_at_every_boundary(field, value, excerpt):
    from copy import deepcopy
    from core.report_plan import parse_report_plan, render_report_plan

    sources = [
        {
            **SOURCE,
            "snippet": excerpt,
            "article_evidence": [
                {"origin": "summary", "text": excerpt, "extraction_version": 1, "raw_text": excerpt}
            ],
        }
    ]
    plan = selection_plan()
    plan["regulatory_changes"][0].update(jurisdiction="Unknown", evidence_excerpt=excerpt)
    plan["control_implications"][0]["evidence_excerpt"] = excerpt
    valid = render_report_plan(plan, sources)
    invalid_plan = deepcopy(plan)
    invalid_plan["regulatory_changes"][0][field] = value
    error = "jurisdiction" if field == "jurisdiction" else "evidenced clause"
    old_cell = "| Unknown | Unknown |" if field == "jurisdiction" else "| final reporting rule |"
    new_cell = f"| {value} | Unknown |" if field == "jurisdiction" else f"| {value} |"
    with pytest.raises(ValueError, match=error):
        parse_report_plan(json.dumps(invalid_plan), sources)

    composer = runpy.run_path(str(ROOT / "scripts/compose_site_report.py"))
    checker = runpy.run_path(str(ROOT / "scripts/check_site_report.py"))
    builder = runpy.run_path(str(ROOT / "scripts/build_site.py"))
    data = stored_report(valid, plan)
    data["metadata"]["source_articles"] = sources
    markdown = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    manifest = composer["evidence_manifest"](data, composer["source_articles"](data["metadata"]))
    manifest["report_plan"] = invalid_plan
    bad_markdown = markdown.replace(old_cell, new_cell)
    with pytest.raises(SystemExit, match=error):
        checker["validate_evidence_manifest"](
            bad_markdown, builder["report_fields"](markdown), json.dumps(manifest)
        )
    data["metadata"]["report_plan"] = invalid_plan
    data["content"] = valid.replace(old_cell, new_cell)
    with pytest.raises(SystemExit, match=error):
        composer["compose_report"](
            data, "https://digest.example/feed.xml", "openrouter/example/model"
        )
