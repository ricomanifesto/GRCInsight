import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import tomllib

from core import workflow as workflow_mod
from models.api import ArticleInput
from services.model_service import GRCModelService
from services.openrouter_client import OpenRouterGeneration

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_PYPROJECT = REPO_ROOT / "agent" / "pyproject.toml"
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deploy-lambda.sh"
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-lambda.yml"
DEPLOY_SITE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-site.yml"
REPORT_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "lambda-report-generation.yml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SITE_REPORT_CHECK = REPO_ROOT / "scripts" / "check_site_report.py"
SITE_REPORT_COMPOSER = REPO_ROOT / "scripts" / "compose_site_report.py"
SITE_BUILDER = REPO_ROOT / "scripts" / "build_site.py"
REPORTING_IDENTITY_CONTRACT = REPO_ROOT / "contracts" / "reporting-identity-v1.json"
MODEL_SERVICE = REPO_ROOT / "agent" / "services" / "model_service.py"
RENDERER_JS = REPO_ROOT / "site" / "static" / "renderer.js"
WORKFLOWS = (CI_WORKFLOW, DEPLOY_WORKFLOW, DEPLOY_SITE_WORKFLOW, REPORT_WORKFLOW)
PUBLISHED_AT = datetime(2026, 6, 1, tzinfo=timezone.utc)
DEFAULT_LLM_MODEL = "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"


def complete_report_body(
    executive_content: str,
    source_content: str,
    *,
    executive_heading: str = "## Executive Summary",
    source_heading: str = "## Source Highlights",
) -> str:
    return "\n\n".join(
        (
            f"{executive_heading}\n{executive_content}",
            "## Key Regulatory Developments\nCareful regulatory analysis.",
            "## Industry Impact Analysis\nCareful industry analysis.",
            "## Risk Assessment\nCareful risk analysis.",
            "## Recommendations for Action\nCareful recommendations.",
            f"{source_heading}\n{source_content}",
        )
    )


def test_report_generation_workflow_accepts_repository_dispatch_payloads():
    workflow = REPORT_WORKFLOW.read_text()

    assert "repository_dispatch:" in workflow
    assert "github.event.client_payload.feed_url" in workflow


def test_release_workflows_verify_the_canonical_reporting_identity_contract():
    canonical_contract = (
        "https://raw.githubusercontent.com/ricomanifesto/SentryDigest/"
        "main/contracts/reporting-identity-v1.json"
    )

    for workflow_path in WORKFLOWS:
        workflow = workflow_path.read_text()
        assert canonical_contract in workflow, workflow_path.name
        assert "Fetch canonical reporting identity contract" in workflow
        assert "Could not verify canonical reporting identity contract" in workflow
        assert "Check reporting identity contract drift" in workflow
        assert "Reporting identity contract drift" in workflow
        assert "cmp -s contracts/reporting-identity-v1.json" in workflow
        assert workflow.index("Fetch canonical reporting identity contract") < workflow.index(
            "Check reporting identity contract drift"
        )


def test_static_site_deploys_main_branch_site_changes():
    workflow = DEPLOY_SITE_WORKFLOW.read_text()

    assert "push:" in workflow
    assert "branches: [ main ]" in workflow
    assert "- 'site/**'" in workflow
    assert "workflow_dispatch:" in workflow
    assert "group: github-pages" in workflow
    assert "run: make check-site" in workflow
    assert "playwright@1.62.1 screenshot" in workflow
    assert "--color-scheme dark" in workflow
    assert "--color-scheme light" in workflow
    assert "actions/upload-artifact@v7" in workflow


def test_report_generation_payload_treats_feed_url_as_json_data():
    workflow = REPORT_WORKFLOW.read_text()

    assert "Invalid FEED_URL; expected http(s) URL without whitespace" in workflow
    assert "jq -n --arg feed_url" in workflow
    assert '\\"feed_url\\": \\"${{ steps.feed-url.outputs.FEED_URL }}\\"' not in workflow


def test_report_generation_payload_uses_provider_model_runtime_config():
    workflow = REPORT_WORKFLOW.read_text()
    deploy_workflow = DEPLOY_WORKFLOW.read_text()

    assert "LLM_MODEL: ${{ vars.LLM_MODEL" in workflow
    assert f"vars.LLM_MODEL || '{DEFAULT_LLM_MODEL}'" in workflow
    assert f"vars.LLM_MODEL || '{DEFAULT_LLM_MODEL}'" in deploy_workflow
    assert (
        "Invalid LLM_MODEL; report generation requires openrouter/provider-model format" in workflow
    )
    assert '--arg model "$LLM_MODEL"' in workflow
    assert "model: $model" in workflow
    assert "claude-opus-4-6" not in workflow


def test_integration_report_payload_uses_openrouter_provider_model():
    integration_script = (REPO_ROOT / "scripts" / "integration" / "run_e2e.sh").read_text()

    assert f'"model": "{DEFAULT_LLM_MODEL}"' in integration_script
    assert '"model": "gpt-5"' not in integration_script


def test_site_report_check_accepts_fallback_numbered_sections():
    check_script = SITE_REPORT_CHECK.read_text()

    assert "REPORT_SECTION_LABELS" in check_script
    assert "NUMBERED_SECTION_PATTERN" in check_script
    assert "is_report_section" in check_script
    assert "1) Executive Summary" not in check_script


def test_report_prompt_requires_current_source_entities_and_readable_summary():
    service = GRCModelService.__new__(GRCModelService)
    prompt = service._create_report_prompt(
        {
            "summary": {"total_articles": 2, "grc_relevant_count": 2},
            "analysis": {
                "regulations_mentioned": ["SEC"],
                "industries_affected": ["Financial services"],
                "risk_categories": ["Vulnerability and patch management"],
            },
            "source_evidence": [
                {
                    "title": "APT1 exploits CVE-2026-12345 in bank systems",
                    "url": "https://example.com/apt1",
                    "snippet": "Threat actor APT1 exploited CVE-2026-12345 against banks.",
                    "cves": ["CVE-2026-12345"],
                },
                {
                    "title": "Cloud Security Alliance publishes guidance",
                    "url": "https://example.com/guidance",
                    "snippet": "The industry group called Cloud Security Alliance published guidance.",
                    "cves": [],
                },
            ],
        },
        {"title": "Test Feed"},
    )

    assert "Source Evidence:" in prompt
    assert "Threat Actor Activities" not in prompt
    assert "CVE and Vulnerability Highlights" not in prompt
    assert "Executive Summary must be 2-4 short paragraphs" in prompt
    assert "APT1" in prompt
    assert "CVE-2026-12345" in prompt
    assert "structured actor identifiers are hints, not an exhaustive actor list" not in prompt
    assert "Do not classify industry, standards, regulatory, or working groups" not in prompt
    assert "Copy the exact Markdown Link supplied above" in prompt
    assert "Every report-specific regulatory and CVE claim" in prompt
    assert "Do not emit incomplete, truncated, or ellipsized CVE identifiers" in prompt
    assert "Use exact framework, standard, regulation, or publication names" in prompt
    assert "Source Highlights" in prompt
    assert "Never use superscript footnotes" in prompt
    assert "Do not invent counts" in prompt
    assert "publication layer adds those values" in prompt
    assert 'Do not emit a top-level "# " heading' in prompt


def test_report_prompt_globally_bounds_cve_evidence():
    service = GRCModelService.__new__(GRCModelService)
    cves = [f"CVE-2026-{10000 + index}" for index in range(12)]

    prompt = service._create_report_prompt(
        {
            "summary": {"total_articles": 1, "grc_relevant_count": 1},
            "analysis": {},
            "source_evidence": [
                {
                    "title": f"Patch roundup for {cves[10]}",
                    "url": f"https://example.com/advisory/{cves[11]}",
                    "snippet": "A vendor published fixes for " + ", ".join(cves) + ".",
                    "cves": cves,
                }
            ],
        },
        {"title": "Test Feed"},
    )

    assert cves[9] in prompt
    assert prompt.count(cves[10]) == 1
    assert prompt.count(cves[11]) == 1
    assert f"Patch roundup for {cves[10]}" in prompt
    assert (
        f"Markdown Link: [Patch roundup for {cves[10]}]"
        f"(https://example.com/advisory/{cves[11]})" in prompt
    )
    assert "[additional CVE omitted]" in prompt


def test_report_prompt_serializes_exact_source_links_for_markdown():
    service = GRCModelService.__new__(GRCModelService)
    title = r"Windows C:\[Temp] and C:\(Logs) advisory"
    url = "https://example.com/advisory)1?edition=(daily)"

    prompt = service._create_report_prompt(
        {
            "summary": {"total_articles": 1, "grc_relevant_count": 1},
            "analysis": {},
            "source_evidence": [
                {
                    "title": title,
                    "url": url,
                    "snippet": "Review the affected Windows paths.",
                    "cves": [],
                }
            ],
        },
        {"title": "Test Feed"},
    )

    escaped_title = (
        title.replace("\\", "\\\\")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )
    assert (
        f"Markdown Link: [{escaped_title}]"
        "(https://example.com/advisory%291?edition=%28daily%29)" in prompt
    )
    assert "including every label escape and URL character" in prompt


def test_report_generation_retries_scratch_work_and_returns_complete_report():
    service = GRCModelService.__new__(GRCModelService)
    valid_report = complete_report_body(
        "Careful executive analysis.",
        "- [Evidence](https://example.com/evidence)",
    )
    responses = iter(
        (
            OpenRouterGeneration(
                text="Here's a thinking process:\n1. Analyze the request",
                resolved_model="google/rejected-draft",
            ),
            OpenRouterGeneration(
                text=valid_report,
                resolved_model="google/final-report-model",
            ),
        )
    )
    prompts = []

    async def fake_invoke(**kwargs):
        prompts.append(kwargs)
        return next(responses)

    service._invoke = fake_invoke
    result = asyncio.run(
        service.generate_grc_report(
            {"summary": {}, "analysis": {}, "source_evidence": []},
            {"title": "Test Feed"},
        )
    )

    assert result.content == valid_report
    assert result.resolved_model == "google/final-report-model"
    assert len(prompts) == 2
    assert prompts[1]["title"] == "GRC intelligence report retry"
    assert "prior response output did not begin" in prompts[1]["user_prompt"]


def test_report_generation_fails_closed_after_two_malformed_drafts():
    service = GRCModelService.__new__(GRCModelService)
    responses = iter(
        (
            OpenRouterGeneration(
                text="## Executive Summary\nIncomplete draft.",
                resolved_model="google/first-model",
            ),
            OpenRouterGeneration(
                text="## Executive Summary\nStill incomplete.",
                resolved_model="google/retry-model",
            ),
        )
    )

    async def fake_invoke(**_kwargs):
        return next(responses)

    service._invoke = fake_invoke
    result = asyncio.run(
        service.generate_grc_report(
            {"summary": {}, "analysis": {}, "source_evidence": []},
            {"title": "Test Feed"},
        )
    )

    assert result.content.startswith("# GRC Intelligence Report - Error")
    assert "complete report after retry" in result.content
    assert result.resolved_model == ""


def test_source_evidence_preserves_distinct_cves_without_actor_priority():
    articles = [
        ArticleInput(
            title=f"Duplicate CVE article {index}",
            url=f"https://example.com/duplicate-{index}",
            content="CVE-2026-11111 affects a common appliance.",
            summary="",
            published=PUBLISHED_AT,
        )
        for index in range(12)
    ]
    articles.extend(
        [
            ArticleInput(
                title="Threat actor APT1 targets banks",
                url="https://example.com/apt1",
                content="The threat actor APT1 exploited CVE-2026-22222. FIN7 assisted.",
                summary="FINRA issued unrelated cybersecurity guidance.",
                published=PUBLISHED_AT,
            ),
            ArticleInput(
                title="Volt Typhoon targets agencies",
                url="https://example.com/named-actor",
                content="The threat actor Volt Typhoon targeted government agencies.",
                summary="",
                published=PUBLISHED_AT,
            ),
            ArticleInput(
                title="Long CVE sequence",
                url="https://example.com/long-cve",
                content="Researchers documented CVE-2026-12345678 in a gateway.",
                summary="",
                published=PUBLISHED_AT,
            ),
            ArticleInput(
                title="Standards group update",
                url="https://example.com/benign-group",
                content="The industry group called Cloud Security Alliance published guidance.",
                summary="",
                published=PUBLISHED_AT,
            ),
        ]
    )

    evidence = workflow_mod._build_source_evidence(articles)
    evidence_urls = {item["url"] for item in evidence}
    cves = {cve for item in evidence for cve in item["cves"]}

    assert len(evidence) <= workflow_mod.SOURCE_EVIDENCE_LIMIT
    assert "https://example.com/apt1" in evidence_urls
    assert "https://example.com/named-actor" not in evidence_urls
    assert "https://example.com/long-cve" in evidence_urls
    assert {"CVE-2026-11111", "CVE-2026-22222", "CVE-2026-12345678"} <= cves
    assert all("actor_ids" not in item for item in evidence)
    assert all("has_threat_context" not in item for item in evidence)


def test_sentrydigest_item_identity_matches_the_public_reporting_contract():
    article_url = (
        "https://www.bleepingcomputer.com/news/security/"
        "akira-hackers-disable-edr-with-safe-mode-steal-data-but-fail-to-encrypt/"
    )

    assert workflow_mod._sentrydigest_item_url(
        "https://ricomanifesto.github.io/SentryDigest/",
        "2026-08-13",
        article_url,
    ) == (
        "https://ricomanifesto.github.io/SentryDigest/archive/2026-08-13/" "#reporting-dace2be75c67"
    )


def test_all_grc_reporting_identities_satisfy_versioned_contract():
    contract = json.loads(REPORTING_IDENTITY_CONTRACT.read_text())
    composer = runpy.run_path(str(SITE_REPORT_COMPOSER))
    checker = runpy.run_path(str(SITE_REPORT_CHECK))
    normalizers = (
        workflow_mod._canonical_public_url,
        composer["canonical_public_url"],
        checker["canonical_public_url"],
    )
    item_urls = (
        workflow_mod._sentrydigest_item_url,
        composer["sentrydigest_item_url"],
        checker["sentrydigest_item_url"],
    )

    assert contract["schema_version"] == 1
    assert contract["contract"] == "sentry-reporting-identity"
    assert contract["contract_version"] == 1
    assert hashlib.sha256(REPORTING_IDENTITY_CONTRACT.read_bytes()).hexdigest() == (
        "16c52db11b981aba115f4a1a127458def99b809c3e768028bebb66b880e33671"
    )
    for example in contract["accepted"]:
        for normalize in normalizers:
            assert normalize(example["input"], example["name"]) == example["normalized"]
        for item_url in item_urls:
            assert item_url(
                "https://ricomanifesto.github.io/SentryDigest/",
                "2026-08-13",
                example["input"],
            ) == (
                "https://ricomanifesto.github.io/SentryDigest/archive/2026-08-13/"
                f"#{example['reporting_fragment']}"
            )

    for example in contract["rejected"]:
        for normalize in normalizers:
            try:
                normalize(example["input"], example["name"])
            except (SystemExit, ValueError):
                pass
            else:
                raise AssertionError(f"{normalize.__module__} accepted {example['name']}")


def test_all_grc_reporting_entry_points_share_one_identity_owner():
    entry_points = (
        REPO_ROOT / "agent" / "core" / "workflow.py",
        SITE_REPORT_COMPOSER,
        SITE_REPORT_CHECK,
    )

    for entry_point in entry_points:
        source = entry_point.read_text()
        assert "from core.reporting_identity import" in source
        assert "def normalize_reporting_path" not in source
        assert "def idna_hostname" not in source
        assert "def dot_segment" not in source


def test_sentrydigest_issue_date_is_owned_by_timezone_aware_feed_metadata():
    assert (
        workflow_mod._sentrydigest_issue_date({"last_updated": "Thu, 13 Aug 2026 22:42:08 GMT"})
        == "2026-08-13"
    )
    assert (
        workflow_mod._sentrydigest_issue_date({"last_updated": "2026-08-14T00:30:00+02:00"})
        == "2026-08-13"
    )

    for invalid in ("", "2026-08-13T22:42:08"):
        try:
            workflow_mod._sentrydigest_issue_date({"last_updated": invalid})
        except ValueError:
            pass
        else:
            raise AssertionError("feed issue date accepted missing timezone evidence")


def test_source_evidence_bounds_persisted_cves_to_prompt_limit():
    articles = [
        ArticleInput(
            title=f"Advisory {index}",
            url=f"https://example.com/advisory-{index}",
            content=f"CVE-2026-{20000 + index} affects the product.",
            summary="",
            published=PUBLISHED_AT,
        )
        for index in range(12)
    ]

    evidence = workflow_mod._build_source_evidence(articles)
    persisted_cves = {cve for item in evidence for cve in item["cves"]}

    assert len(evidence) <= workflow_mod.SOURCE_EVIDENCE_LIMIT
    assert len(persisted_cves) == workflow_mod.REPORT_CVE_LIMIT
    assert all(set(item["cves"]) <= persisted_cves for item in evidence)


def test_source_evidence_preserves_cves_in_exact_title_or_url_identity():
    articles = [
        ArticleInput(
            title=f"Advisory {index}",
            url=(
                "https://example.com/CVE-2026-30010"
                if index == 10
                else f"https://example.com/advisory-{index}"
            ),
            content=(
                "The identifier appears only in this source URL."
                if index == 10
                else f"CVE-2026-{30000 + index} affects the product."
            ),
            summary="",
            published=PUBLISHED_AT,
        )
        for index in range(11)
    ]

    evidence = workflow_mod._build_source_evidence(articles)
    identity_source = next(item for item in evidence if "CVE-2026-30010" in item["url"])

    assert "CVE-2026-30010" not in identity_source["title"]
    assert "CVE-2026-30010" not in identity_source["snippet"]
    assert "CVE-2026-30010" in identity_source["cves"]


def test_fallback_report_excludes_dedicated_threat_actor_section():
    articles = [
        ArticleInput(
            title="Volt Typhoon targets agencies",
            url="https://example.com/named-actor",
            content="The threat actor Volt Typhoon targeted government agencies.",
            summary="",
            published=PUBLISHED_AT,
        )
    ]
    local_signals, analysis = workflow_mod._build_local_analysis(articles)

    report = workflow_mod._build_fallback_report(
        {"title": "Test Feed"},
        articles,
        local_signals,
        analysis,
        "model unavailable",
    )

    assert "Threat Actor Activities" not in report
    assert "CVE and Vulnerability Highlights" not in report
    assert "4) Risk Assessment" in report
    assert "5) Recommendations for Action" in report


def test_fallback_report_links_regulatory_claims_without_a_cve_section():
    articles = [
        ArticleInput(
            title="GDPR Article 32 advisory covers CVE-2026-54321",
            url="https://example.com/gdpr-cve",
            content="GDPR Article 32 guidance addresses remediation evidence for CVE-2026-54321.",
            summary="",
            published=PUBLISHED_AT,
        )
    ]
    local_signals, analysis = workflow_mod._build_local_analysis(articles)

    report = workflow_mod._build_fallback_report(
        {"title": "Test Feed"},
        articles,
        local_signals,
        analysis,
        "model unavailable",
    )

    source = "[GDPR Article 32 advisory covers CVE-2026-54321](https://example.com/gdpr-cve)"
    regulatory_line = next(
        line
        for line in report.splitlines()
        if line.startswith("- Explicit regulation references detected:")
    )
    assert f"Sources: {source}." in regulatory_line
    assert "CVE and Vulnerability Highlights" not in report
    assert "Review business impact, exposure, and remediation ownership" not in report


def test_renderer_and_site_check_enforce_the_current_report_sections():
    check_script = SITE_REPORT_CHECK.read_text()
    renderer = RENDERER_JS.read_text()

    assert "FORBIDDEN_REPORT_SECTION_LABELS" in check_script
    assert "cve and vulnerability highlights" in check_script
    assert "threat actor activities" in check_script
    assert "'CVE and Vulnerability Highlights'," not in renderer
    assert "'Threat Actor Activities'," not in renderer


def test_report_generation_workflow_does_not_dump_lambda_response_body():
    workflow = REPORT_WORKFLOW.read_text()

    assert "cat lambda-response.json" not in workflow
    assert "Lambda status code:" in workflow


def test_report_generation_workflow_does_not_dump_failed_report_body():
    workflow = REPORT_WORKFLOW.read_text()

    assert "cat report-data.json" not in workflow
    assert "Report status is 'failed'. Aborting early." in workflow


def test_report_generation_workflow_refuses_fallback_reports():
    workflow = REPORT_WORKFLOW.read_text()

    assert "ANALYSIS_MODE=$(jq -r '.metadata.analysis_mode // empty' report-data.json)" in workflow
    assert 'if [ "$ANALYSIS_MODE" != "model" ]; then' in workflow
    assert "Refusing to publish a fallback-mode report" in workflow


def test_report_generation_workflow_classifies_fallback_without_dumping_provider_text():
    workflow = REPORT_WORKFLOW.read_text()

    assert (
        "FALLBACK_REASON=$(jq -r '.metadata.fallback_reason // empty' report-data.json)" in workflow
    )
    assert 'echo "Fallback category: $FALLBACK_CATEGORY" >&2' in workflow
    assert 'echo "$FALLBACK_REASON"' not in workflow


def test_report_generation_workflow_requires_resolved_model_provenance():
    workflow = REPORT_WORKFLOW.read_text()

    assert ".metadata.requested_model // empty" in workflow
    assert ".metadata.resolved_model // empty" in workflow
    assert 'if [ "$REQUESTED_MODEL" != "$LLM_MODEL" ]; then' in workflow
    assert "Refusing to publish a report without an upstream resolved model" in workflow


def test_report_generation_workflow_requires_feed_owned_issue_provenance():
    workflow = REPORT_WORKFLOW.read_text()

    assert ".metadata.source_issue_date // empty" in workflow
    assert ".metadata.source_issue_url // empty" in workflow
    assert (
        'EXPECTED_SOURCE_ISSUE_URL="${SOURCE_HOME_URL%/}/archive/${SOURCE_ISSUE_DATE}/"' in workflow
    )
    assert "Refusing to publish a report with mismatched digest issue provenance" in workflow


def test_report_generation_workflow_bounds_the_completion_budget():
    workflow = REPORT_WORKFLOW.read_text()

    assert "max_tokens: 8000" in workflow
    assert "max_tokens: 16000" not in workflow


def test_report_generation_workflow_uses_deterministic_report_composer():
    workflow = REPORT_WORKFLOW.read_text()

    assert "python3 scripts/compose_site_report.py" in workflow
    assert "--input report-data.json" in workflow
    assert '--feed-url "$FEED_URL"' in workflow
    assert '--model "$LLM_MODEL"' in workflow


def test_report_generation_workflow_builds_prerender_and_archive():
    workflow = REPORT_WORKFLOW.read_text()

    assert workflow.count("python3 scripts/build_site.py --archive-current") >= 2
    assert (
        "git add site/index.md site/index.html site/evidence-manifest.json site/archive" in workflow
    )
    assert "[skip ci]" not in workflow
    assert "actions: write" in workflow
    assert "gh workflow run deploy-site.yml" in workflow
    assert "steps.publish.outputs.published == 'true'" in workflow


def test_report_generation_workflow_validates_generated_site_before_publish():
    workflow = REPORT_WORKFLOW.read_text()

    assert "Validate generated site report" in workflow
    assert workflow.count("make check-site") >= 2
    assert workflow.index("Validate generated site report") < workflow.index(
        "Commit and push report"
    )
    assert "actions/upload-pages-artifact" not in workflow
    assert "actions/deploy-pages" not in workflow
    rebase_index = workflow.index('git rebase -X theirs "origin/$GITHUB_REF_NAME"')
    assert workflow.index("make check-site", rebase_index) < workflow.index("git push origin HEAD")


def test_site_report_composer_owns_public_provenance_and_body_shape():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    report = compose_report(
        {
            "status": "completed",
            "title": "GRC Intelligence Report - 2026-08-13",
            "generated_at": "2026-08-13T13:00:00Z",
            "content": (
                "# Duplicate title\n**Generated:** stale\n\n"
                + complete_report_body(
                    "Careful analysis.\n\n---",
                    "- [Evidence](https://example.com/evidence)",
                    executive_heading="1. Executive Summary",
                    source_heading="6) Source Highlights",
                )
            ),
            "metadata": {
                "analysis_mode": "model",
                "source_name": "SentryDigest",
                "source_url": "https://example.com/feed.xml",
                "source_home_url": "https://digest.example/",
                "source_issue_date": "2026-08-13",
                "source_issue_url": "https://digest.example/archive/2026-08-13/",
                "source_articles": [
                    {"title": "Linkless item", "url": ""},
                    {"title": "Evidence", "url": "https://example.com/evidence"},
                ],
                "analysis_period": "August 2026",
                "article_count": 30,
                "grc_article_count": 12,
                "requested_model": "openrouter/example/model",
                "resolved_model": "google/example-model",
            },
        },
        "https://example.com/feed.xml",
        "openrouter/example/model",
    )

    assert report.count("# GRC Intelligence Report - 2026-08-13") == 1
    assert report.count("**Generated:** 2026-08-13T13:00:00Z") == 1
    assert "**Source:** [SentryDigest](https://example.com/feed.xml)" in report
    assert "**Articles Analyzed:** 30" in report
    assert "**GRC-Relevant Articles:** 12" in report
    assert "**Authoring Model:** google/example-model" in report
    assert "**Requested Route:** openrouter/example/model" in report
    assert "**Analysis Mode:** Model-backed" in report
    assert (
        "[View in SentryDigest]" "(https://digest.example/archive/2026-08-13/#reporting-" in report
    )
    assert (
        "**Source Issue:** [SentryDigest 2026-08-13]"
        "(https://digest.example/archive/2026-08-13/)" in report
    )
    assert "## Executive Summary" in report
    assert "## Source Highlights" in report
    assert "\n---\n" not in report
    assert "stale" not in report


def test_site_report_composer_requires_each_canonical_section_exactly_once():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    canonical_body = namespace["canonical_body"]

    for malformed, expected in (
        (
            complete_report_body("Careful analysis.", "- Evidence").replace(
                "## Risk Assessment\nCareful risk analysis.\n\n", ""
            ),
            "missing section: Risk Assessment",
        ),
        (
            complete_report_body("Careful analysis.", "- Evidence")
            + "\n\n## Risk Assessment\nDuplicate risk analysis.",
            "repeats section: Risk Assessment",
        ),
    ):
        try:
            canonical_body(malformed)
        except SystemExit as error:
            assert expected in str(error)
        else:
            raise AssertionError(f"composer accepted malformed section structure: {expected}")


def test_site_builder_treats_report_backslashes_as_literal_content():
    namespace = runpy.run_path(str(SITE_BUILDER))
    current_index_html = namespace["current_index_html"]
    template = (
        '<time class="subtitle" id="generated">Loading</time>'
        "<!-- REPORT_CONTENT_START --><!-- REPORT_CONTENT_END -->"
    )
    markdown = (
        "# GRC Intelligence Report\n"
        "**Generated:** 2026-08-13T13:00:00Z\n\n"
        "## Risk Assessment\n"
        "Review C:\\Windows access controls."
    )

    built = current_index_html(template, markdown)

    assert "C:\\Windows" in built


def test_site_builder_gives_same_day_reports_unique_archive_keys():
    namespace = runpy.run_path(str(SITE_BUILDER))
    archive_slug = namespace["archive_slug"]

    morning = datetime(2026, 8, 13, 13, 0, 0, tzinfo=timezone.utc)
    rerun = datetime(2026, 8, 13, 15, 45, 12, tzinfo=timezone.utc)

    assert archive_slug(morning) == "2026-08-13T13-00-00Z"
    assert archive_slug(rerun) == "2026-08-13T15-45-12Z"
    assert archive_slug(morning) != archive_slug(rerun)


def test_site_builder_preserves_published_archive_pages():
    builder = SITE_BUILDER.read_text()

    assert "if not archive_page.exists():" in builder
    assert "outputs[archive_page] = archive_detail_html(archived_markdown)" in builder


def test_site_report_check_validates_every_archive_manifest(tmp_path):
    namespace = runpy.run_path(str(SITE_REPORT_CHECK))
    validate_archive_history = namespace["validate_archive_history"]
    archive_key = "2026-08-13T13-00-00Z"
    snapshot = tmp_path / archive_key
    snapshot.mkdir()
    report = (
        "# GRC Intelligence Report\n"
        "**Generated:** 2026-08-13T13:00:00Z\n"
        "**Date of Issue:** August 2026\n"
        "**Analysis Period:** August 2026\n"
        "**Source:** [Feed](https://example.com/feed.xml)\n"
        "**Articles Analyzed:** 1\n"
        "**Model:** openrouter/example/model\n"
        "**Analysis Mode:** Model-backed\n\n"
        + complete_report_body(
            "Careful analysis.",
            "- [Evidence](https://example.com/evidence)",
        )
    )
    manifest = {
        "generated_at": "2026-08-13T13:00:00Z",
        "feed_url": "https://example.com/feed.xml",
        "sources": [{"title": "Evidence", "url": "https://example.com/evidence", "cves": []}],
    }
    (snapshot / "report.md").write_text(report)
    (snapshot / "evidence-manifest.json").write_text(json.dumps(manifest))
    (snapshot / "index.html").write_text(
        '<main class="container archive-report"><section class="card report-provenance">'
        '<a href="evidence-manifest.json">Evidence</a></section></main>'
    )
    archive_html = f'<a href="{archive_key}/">Report</a>'

    validate_archive_history(tmp_path, archive_html)

    (snapshot / "evidence-manifest.json").write_text("{broken")
    try:
        validate_archive_history(tmp_path, archive_html)
    except SystemExit as error:
        assert "evidence-manifest.json is invalid JSON" in str(error)
    else:
        raise AssertionError("archive validation accepted a corrupted historical manifest")


def test_site_report_composer_rejects_provenance_mismatch():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    data = {
        "status": "completed",
        "title": "GRC Intelligence Report - 2026-08-13",
        "generated_at": "2026-08-13T13:00:00Z",
        "content": "## Executive Summary\nCareful analysis.",
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-08-13",
            "source_issue_url": "https://digest.example/archive/2026-08-13/",
            "source_articles": [{"title": "Evidence", "url": "https://example.com/evidence"}],
            "analysis_period": "August 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "requested_model": "openrouter/example/model",
            "resolved_model": "google/example-model",
        },
    }

    try:
        compose_report(data, "https://other.example/feed.xml", "openrouter/example/model")
    except SystemExit as error:
        assert "source URL does not match" in str(error)
    else:
        raise AssertionError("composer accepted mismatched source provenance")


def test_site_report_composer_normalizes_numbered_markdown_headings_and_feed_url():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    feed_url = "https://example.com/feed(1).xml?edition=(daily)"
    report = compose_report(
        {
            "status": "completed",
            "title": "GRC Intelligence Report - 2026-08-13",
            "generated_at": "2026-08-13T13:00:00Z",
            "content": complete_report_body(
                "Careful analysis.",
                "- [Evidence](https://example.com/evidence)",
                executive_heading="## **1. EXECUTIVE SUMMARY:**",
                source_heading="**6) source highlights.**",
            ),
            "metadata": {
                "analysis_mode": "model",
                "source_name": "SentryDigest\\",
                "source_url": feed_url,
                "source_home_url": "https://digest.example/",
                "source_issue_date": "2026-08-13",
                "source_issue_url": "https://digest.example/archive/2026-08-13/",
                "source_articles": [{"title": "Evidence", "url": "https://example.com/evidence"}],
                "analysis_period": "August 2026",
                "article_count": 1,
                "grc_article_count": 1,
                "requested_model": "openrouter/example/model",
                "resolved_model": "google/example-model",
            },
        },
        feed_url,
        "openrouter/example/model",
    )

    assert "## Executive Summary" in report
    assert "## Source Highlights" in report
    assert "## 1." not in report
    assert "feed%281%29.xml?edition=%28daily%29" in report
    assert "**Source:** [SentryDigest\\\\](" in report


def test_site_report_composer_rejects_evidence_urls_absent_from_source_articles():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    data = {
        "status": "completed",
        "title": "GRC Intelligence Report - 2026-08-13",
        "generated_at": "2026-08-13T13:00:00Z",
        "content": complete_report_body(
            "[Invented evidence](https://invented.example/advisory)",
            "- [Invented evidence](https://invented.example/advisory)",
        ),
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-08-13",
            "source_issue_url": "https://digest.example/archive/2026-08-13/",
            "source_articles": [{"title": "Real evidence", "url": "https://example.com/real"}],
            "analysis_period": "August 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "requested_model": "openrouter/example/model",
            "resolved_model": "google/example-model",
        },
    }

    try:
        compose_report(data, "https://example.com/feed.xml", "openrouter/example/model")
    except SystemExit as error:
        assert "absent from source articles" in str(error)
    else:
        raise AssertionError("composer accepted an invented evidence URL")


def test_site_report_composer_decodes_escaped_evidence_url_delimiters():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    http_url = namespace["http_url"]
    evidence_url = "HTTPS://example.com/O'Reilly/a)b"
    report = compose_report(
        {
            "status": "completed",
            "title": "GRC Intelligence Report - 2026-08-13",
            "generated_at": "2026-08-13T13:00:00Z",
            "content": complete_report_body(
                "[Evidence](HTTPS://example.com/O'Reilly/a\\)b)",
                "- [Evidence](HTTPS://example.com/O'Reilly/a\\)b)",
            ),
            "metadata": {
                "analysis_mode": "model",
                "source_name": "SentryDigest",
                "source_url": "https://example.com/feed.xml",
                "source_home_url": "https://digest.example/",
                "source_issue_date": "2026-08-13",
                "source_issue_url": "https://digest.example/archive/2026-08-13/",
                "source_articles": [{"title": "Evidence", "url": evidence_url}],
                "analysis_period": "August 2026",
                "article_count": 1,
                "grc_article_count": 1,
                "requested_model": "openrouter/example/model",
                "resolved_model": "google/example-model",
            },
        },
        "https://example.com/feed.xml",
        "openrouter/example/model",
    )

    assert "[Evidence](HTTPS://example.com/O%27Reilly/a%29b)" in report
    assert http_url(evidence_url, "evidence URL") == "HTTPS://example.com/O%27Reilly/a%29b"


def test_site_report_composer_accepts_serialized_source_link_identity():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    title = r"Windows C:\[Temp] and C:\(Logs) advisory"
    escaped_title = (
        title.replace("\\", "\\\\")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )
    source_url = "https://example.com/advisory)1?edition=(daily)"
    link = f"[{escaped_title}]" "(https://example.com/advisory%291?edition=%28daily%29)"

    report = compose_report(
        {
            "status": "completed",
            "title": "GRC Intelligence Report - 2026-08-13",
            "generated_at": "2026-08-13T13:00:00Z",
            "content": complete_report_body(
                f"Review {link}.",
                f"- {link}",
            ),
            "metadata": {
                "analysis_mode": "model",
                "source_name": "SentryDigest",
                "source_url": "https://example.com/feed.xml",
                "source_home_url": "https://digest.example/",
                "source_issue_date": "2026-08-13",
                "source_issue_url": "https://digest.example/archive/2026-08-13/",
                "source_articles": [{"title": title, "url": source_url}],
                "analysis_period": "August 2026",
                "article_count": 1,
                "grc_article_count": 1,
                "requested_model": "openrouter/example/model",
                "resolved_model": "google/example-model",
            },
        },
        "https://example.com/feed.xml",
        "openrouter/example/model",
    )

    assert link in report


def test_site_report_composer_canonicalizes_title_for_real_evidence_url():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    data = {
        "status": "completed",
        "title": "GRC Intelligence Report - 2026-08-13",
        "generated_at": "2026-08-13T13:00:00Z",
        "content": complete_report_body(
            "[CISA mandates immediate shutdown](https://example.com/neutral)",
            "- [Neutral advisory](https://example.com/neutral)",
        ),
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-08-13",
            "source_issue_url": "https://digest.example/archive/2026-08-13/",
            "source_articles": [
                {"title": "Neutral advisory", "url": "https://example.com/neutral"}
            ],
            "analysis_period": "August 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "requested_model": "openrouter/example/model",
            "resolved_model": "google/example-model",
        },
    }

    report = compose_report(data, "https://example.com/feed.xml", "openrouter/example/model")

    assert "CISA mandates immediate shutdown" not in report
    assert report.count("[Neutral advisory](https://example.com/neutral)") == 2


def test_site_report_composer_canonicalizes_url_for_exact_evidence_title():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    title = "Attackers Exploit SharePoint Authentication Bypass After Public PoC Release"
    trusted_url = "https://thehackernews.com/2026/08/attackers-exploit-sharepoint.html"
    mutated_url = "https://thehackernists.com/2026/08/attackers-exploit-sharepoint.html"
    data = {
        "status": "completed",
        "title": "GRC Intelligence Report - 2026-08-13",
        "generated_at": "2026-08-13T13:00:00Z",
        "content": complete_report_body(
            f"[{title}]({mutated_url})",
            f"- [{title}]({mutated_url})",
        ),
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-08-13",
            "source_issue_url": "https://digest.example/archive/2026-08-13/",
            "source_articles": [{"title": title, "url": trusted_url}],
            "analysis_period": "August 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "requested_model": "openrouter/example/model",
            "resolved_model": "google/example-model",
        },
    }

    report = compose_report(data, "https://example.com/feed.xml", "openrouter/example/model")

    assert mutated_url not in report
    assert report.count(f"[{title}]({trusted_url})") == 2


def test_site_report_composer_rejects_cross_wired_source_identities():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    data = {
        "status": "completed",
        "title": "GRC Intelligence Report - 2026-08-13",
        "generated_at": "2026-08-13T13:00:00Z",
        "content": complete_report_body(
            "[Source A](https://example.com/b)",
            "- [Source A](https://example.com/b)",
        ),
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-08-13",
            "source_issue_url": "https://digest.example/archive/2026-08-13/",
            "source_articles": [
                {"title": "Source A", "url": "https://example.com/a"},
                {"title": "Source B", "url": "https://example.com/b"},
            ],
            "analysis_period": "August 2026",
            "article_count": 2,
            "grc_article_count": 2,
            "requested_model": "openrouter/example/model",
            "resolved_model": "google/example-model",
        },
    }

    try:
        compose_report(data, "https://example.com/feed.xml", "openrouter/example/model")
    except SystemExit as error:
        assert "title/URL pair absent from source articles" in str(error)
    else:
        raise AssertionError("composer accepted cross-wired source identities")


def test_site_report_composer_expands_unique_ellipsized_source_reference():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    title = "Critical VMware vCenter RCE flaw exploited for reverse SSH access"
    source_url = "https://example.com/vmware"
    data = {
        "status": "completed",
        "title": "GRC Intelligence Report - 2026-08-13",
        "generated_at": "2026-08-13T13:00:00Z",
        "content": complete_report_body(
            "Contain the active campaign (Source: " "[Critical VMware vCenter RCE flaw...]).",
            f"- [{title}]({source_url})",
        ),
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-08-13",
            "source_issue_url": "https://digest.example/archive/2026-08-13/",
            "source_articles": [{"title": title, "url": source_url}],
            "analysis_period": "August 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "requested_model": "openrouter/example/model",
            "resolved_model": "google/example-model",
        },
    }

    report = compose_report(data, "https://example.com/feed.xml", "openrouter/example/model")

    assert "[Critical VMware vCenter RCE flaw...]" not in report
    assert report.count(f"[{title}]({source_url})") == 2


def test_site_report_composer_leaves_ambiguous_ellipsized_reference_unresolved():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    expand_references = namespace["expand_ellipsized_evidence_references"]
    reference = "[Critical VMware vCenter RCE flaw...]"
    sources = [
        {
            "title": "Critical VMware vCenter RCE flaw affects product A",
            "url": "https://example.com/a",
        },
        {
            "title": "Critical VMware vCenter RCE flaw affects product B",
            "url": "https://example.com/b",
        },
    ]

    assert expand_references(reference, sources) == reference


def test_site_report_composer_expands_parenthesized_source_ordinal():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    title = "AI watermark removers flood the web"
    source_url = "https://example.com/ai-watermarks"
    data = {
        "status": "completed",
        "title": "GRC Intelligence Report - 2026-08-13",
        "generated_at": "2026-08-13T13:00:00Z",
        "content": complete_report_body(
            "Detection controls are affected (source #1).",
            f"- [{title}]({source_url})",
        ),
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-08-13",
            "source_issue_url": "https://digest.example/archive/2026-08-13/",
            "source_articles": [{"title": title, "url": source_url}],
            "analysis_period": "August 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "requested_model": "openrouter/example/model",
            "resolved_model": "google/example-model",
        },
    }

    report = compose_report(data, "https://example.com/feed.xml", "openrouter/example/model")

    assert "source #1" not in report
    assert f"(Source: [{title}]({source_url}))" in report


def test_site_report_composer_leaves_unknown_source_ordinal_unresolved():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    expand_references = namespace["expand_ordinal_evidence_references"]
    reference = "(source #2)"
    sources = [{"title": "Only source", "url": "https://example.com/only"}]

    assert expand_references(reference, sources) == reference


def test_site_report_composer_adds_links_for_supported_unlinked_cves():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    source_title = "Critical VMware vCenter RCE flaw exploited for reverse SSH access"
    source_url = "https://example.com/vmware"
    data = {
        "status": "completed",
        "title": "GRC Intelligence Report - 2026-08-13",
        "generated_at": "2026-08-13T13:00:00Z",
        "content": complete_report_body(
            "VMware vCenter exploitation (CVE-2026-59310) requires containment.",
            f"- [{source_title}]({source_url})",
        ),
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-08-13",
            "source_issue_url": "https://digest.example/archive/2026-08-13/",
            "source_articles": [
                {
                    "title": source_title,
                    "url": source_url,
                    "cves": ["CVE-2026-59310"],
                }
            ],
            "analysis_period": "August 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "requested_model": "openrouter/example/model",
            "resolved_model": "google/example-model",
        },
    }

    report = compose_report(data, "https://example.com/feed.xml", "openrouter/example/model")

    assert (
        "VMware vCenter exploitation (CVE-2026-59310) requires containment. "
        f"**Evidence:** [{source_title}]({source_url})" in report
    )


def test_site_report_composer_rejects_cve_absent_from_linked_source():
    namespace = runpy.run_path(str(SITE_REPORT_COMPOSER))
    compose_report = namespace["compose_report"]
    data = {
        "status": "completed",
        "title": "GRC Intelligence Report - 2026-08-13",
        "generated_at": "2026-08-13T13:00:00Z",
        "content": complete_report_body(
            "CVE-2026-1111 is described by " "[Different advisory](https://example.com/different).",
            "- [Different advisory](https://example.com/different)",
        ),
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-08-13",
            "source_issue_url": "https://digest.example/archive/2026-08-13/",
            "source_articles": [
                {
                    "title": "Different advisory",
                    "url": "https://example.com/different",
                    "cves": ["CVE-2026-2222"],
                }
            ],
            "analysis_period": "August 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "requested_model": "openrouter/example/model",
            "resolved_model": "google/example-model",
        },
    }

    try:
        compose_report(data, "https://example.com/feed.xml", "openrouter/example/model")
    except SystemExit as error:
        assert "CVE-2026-1111" in str(error)
    else:
        raise AssertionError("composer accepted a CVE absent from its linked source")


def test_site_report_check_rejects_internal_distribution_labels():
    check_script = SITE_REPORT_CHECK.read_text()

    assert "find_public_report_forbidden_label" in check_script
    assert "FORBIDDEN_METADATA_FIELDS" in check_script
    assert "PRIVATE_VALUE_FIELDS" in check_script
    assert "PRIVATE_VALUE_TERMS" in check_script
    assert "normalize_label_text" in check_script
    assert r"\bCONFIDENTIAL\b" not in check_script


def test_site_report_reader_surface_detector_covers_visible_trust_defects():
    namespace = runpy.run_path(str(SITE_REPORT_CHECK))
    find_defect = namespace["find_reader_surface_defect"]
    valid = (
        "## Executive Summary\n"
        "[CVE-2026-12345](https://example.com/cve) is documented.\n\n"
        "## Source Highlights\n"
        "- [Evidence](https://example.com/cve)"
    )

    assert find_defect(valid) is None
    assert (
        find_defect(
            valid.replace("https://example.com/cve", "https://example.com/evidence_(daily).html")
        )
        is None
    )
    assert find_defect(valid.replace("is documented.", "affects ownCloud and openSUSE.")) is None
    assert (
        find_defect(
            valid.replace(
                "[Evidence](https://example.com/cve)",
                "[Microsoft [Update] advisory](https://example.com/cve)",
            )
        )
        is None
    )
    blocked = (
        valid.replace("is documented.", "is documented.[¹]"),
        valid.replace("is documented.", "is documented in [Regulatory Developments]."),
        valid.replace("is documented.", "causes a criticalCommerce flaw."),
        valid.replace("is documented.", "exposes customerCredential data."),
        valid.replace("is documented.", "is documented by Source 1."),
        valid.replace("is documented.", "is documented by source #10."),
        valid.replace("\n\n## Source Highlights", "\n\n---\n\n## Source Highlights"),
        valid.replace("[CVE-2026-12345](https://example.com/cve)", "CVE-2026-12345", 1),
    )
    for markdown in blocked:
        assert find_defect(markdown), markdown


def test_site_report_integrity_detector_rejects_model_artifacts():
    namespace = runpy.run_path(str(SITE_REPORT_CHECK))
    find_failure = namespace["find_public_report_integrity_failure"]

    assert find_failure("## Executive Summary\nCareful analysis.") is None
    assert find_failure("Let me review the source evidence.\n## Executive Summary")
    assert find_failure("## Executive Summary\n[Table]")
    long_preamble = "\n".join([f"preamble {index}" for index in range(31)])
    assert find_failure(long_preamble + "\n## Executive Summary")


def test_evidence_manifest_normalizes_parenthesized_urls():
    namespace = runpy.run_path(str(SITE_REPORT_CHECK))
    validate_manifest = namespace["validate_evidence_manifest"]
    markdown = (
        "# Report\n"
        "**Generated:** 2026-08-13T13:00:00Z\n"
        "**Source:** [Feed](https://example.com/feed(1).xml)\n\n"
        "## Executive Summary\n"
        "[Evidence](HTTPS://example.com/a_(b).html)\n\n"
        "## Source Highlights\n"
        "- [Evidence](HTTPS://example.com/a_(b).html)"
    )
    metadata = {
        "generated": "2026-08-13T13:00:00Z",
        "source": "[Feed](https://example.com/feed(1).xml)",
    }
    manifest = {
        "generated_at": "2026-08-13T13:00:00Z",
        "feed_url": "https://example.com/feed%281%29.xml",
        "sources": [{"title": "Evidence", "url": "HTTPS://example.com/a_%28b%29.html"}],
    }

    validate_manifest(markdown, metadata, json.dumps(manifest))

    escaped_markdown = markdown.replace("a_(b).html", "a_\\)b.html")
    escaped_manifest = {
        **manifest,
        "sources": [{"title": "Evidence", "url": "HTTPS://example.com/a_%29b.html"}],
    }
    validate_manifest(escaped_markdown, metadata, json.dumps(escaped_manifest))


def test_evidence_manifest_v3_attests_model_and_dated_digest_item_identity():
    namespace = runpy.run_path(str(SITE_REPORT_CHECK))
    validate_manifest = namespace["validate_evidence_manifest"]
    source_url = "https://example.com/advisory"
    digest_url = namespace["sentrydigest_item_url"](
        "https://digest.example/", "2026-08-13", source_url
    )
    markdown = (
        "# Report\n"
        "**Generated:** 2026-08-13T13:00:00Z\n"
        "**Source:** [Feed](https://example.com/feed.xml)\n"
        "**Source Issue:** [SentryDigest 2026-08-13]"
        "(https://digest.example/archive/2026-08-13/)\n"
        "**Authoring Model:** google/example-model\n"
        "**Requested Route:** openrouter/openrouter/free\n\n"
        "## Executive Summary\n"
        f"[Evidence]({source_url}) supports the finding.\n\n"
        "## Source Highlights\n"
        f"- [Evidence]({source_url}) · [View in SentryDigest]({digest_url})"
    )
    metadata = {
        "generated": "2026-08-13T13:00:00Z",
        "source": "[Feed](https://example.com/feed.xml)",
        "source issue": (
            "[SentryDigest 2026-08-13]" "(https://digest.example/archive/2026-08-13/)"
        ),
        "authoring model": "google/example-model",
        "requested route": "openrouter/openrouter/free",
    }
    manifest = {
        "schema_version": 3,
        "generated_at": "2026-08-13T13:00:00Z",
        "feed_url": "https://example.com/feed.xml",
        "feed_home_url": "https://digest.example/",
        "digest_issue_date": "2026-08-13",
        "digest_issue_url": "https://digest.example/archive/2026-08-13/",
        "requested_model": "openrouter/openrouter/free",
        "resolved_model": "google/example-model",
        "sources": [
            {
                "title": "Evidence",
                "url": source_url,
                "digest_url": digest_url,
                "cves": [],
            }
        ],
    }

    validate_manifest(
        markdown,
        metadata,
        json.dumps(manifest),
        require_current_schema=True,
    )

    aliased_manifest = {**manifest, "resolved_model": "openrouter/free"}
    try:
        validate_manifest(
            markdown.replace("google/example-model", "openrouter/free"),
            {**metadata, "authoring model": "openrouter/free"},
            json.dumps(aliased_manifest),
            require_current_schema=True,
        )
    except SystemExit as error:
        assert "routing alias" in str(error)
    else:
        raise AssertionError("manifest accepted a router alias as report authorship")


def test_schema2_manifest_is_historical_only():
    namespace = runpy.run_path(str(SITE_REPORT_CHECK))
    validate_manifest = namespace["validate_evidence_manifest"]
    source_url = "https://example.com/advisory"
    digest_url = namespace["legacy_sentrydigest_item_url"]("https://digest.example/", source_url)
    markdown = (
        "# Report\n"
        "**Generated:** 2026-08-13T13:00:00Z\n"
        "**Source:** [Feed](https://example.com/feed.xml)\n"
        "**Authoring Model:** google/example-model\n"
        "**Requested Route:** openrouter/openrouter/free\n\n"
        "## Executive Summary\n"
        f"[Evidence]({source_url}) supports the finding.\n\n"
        "## Source Highlights\n"
        f"- [Evidence]({source_url}) · [View in SentryDigest]({digest_url})"
    )
    metadata = {
        "generated": "2026-08-13T13:00:00Z",
        "source": "[Feed](https://example.com/feed.xml)",
        "authoring model": "google/example-model",
        "requested route": "openrouter/openrouter/free",
    }
    manifest = {
        "schema_version": 2,
        "generated_at": "2026-08-13T13:00:00Z",
        "feed_url": "https://example.com/feed.xml",
        "feed_home_url": "https://digest.example/",
        "requested_model": "openrouter/openrouter/free",
        "resolved_model": "google/example-model",
        "sources": [
            {
                "title": "Evidence",
                "url": source_url,
                "digest_url": digest_url,
                "cves": [],
            }
        ],
    }

    validate_manifest(markdown, metadata, json.dumps(manifest), require_current_schema=False)

    try:
        validate_manifest(markdown, metadata, json.dumps(manifest), require_current_schema=True)
    except SystemExit as error:
        assert "dated digest issue provenance" in str(error)
    else:
        raise AssertionError("current report accepted a schema-2 evidence manifest")


def test_schema3_publication_bridge_is_removed_after_dated_report():
    checker = SITE_REPORT_CHECK.read_text()
    current_manifest = json.loads((REPO_ROOT / "site" / "evidence-manifest.json").read_text())
    archived_manifests = [
        json.loads(path.read_text())
        for path in (REPO_ROOT / "site" / "archive").glob("*/evidence-manifest.json")
    ]

    retired_breadcrumb = "TODO(" + "digest-issue-schema3-publication)"
    assert retired_breadcrumb not in checker
    assert "if require_current_schema and schema_version != 3:" in checker
    assert current_manifest["schema_version"] == 3
    assert any(manifest.get("schema_version") == 3 for manifest in archived_manifests)
    assert any(manifest.get("schema_version") == 2 for manifest in archived_manifests)


def test_evidence_manifest_rejects_invented_title_for_real_url():
    namespace = runpy.run_path(str(SITE_REPORT_CHECK))
    validate_manifest = namespace["validate_evidence_manifest"]
    markdown = (
        "# Report\n"
        "**Generated:** 2026-08-13T13:00:00Z\n"
        "**Source:** [Feed](https://example.com/feed.xml)\n\n"
        "## Executive Summary\n"
        "[Invented claim](https://example.com/neutral)\n\n"
        "## Source Highlights\n"
        "- [Neutral advisory](https://example.com/neutral)"
    )
    metadata = {
        "generated": "2026-08-13T13:00:00Z",
        "source": "[Feed](https://example.com/feed.xml)",
    }
    manifest = {
        "generated_at": "2026-08-13T13:00:00Z",
        "feed_url": "https://example.com/feed.xml",
        "sources": [{"title": "Neutral advisory", "url": "https://example.com/neutral"}],
    }

    try:
        validate_manifest(markdown, metadata, json.dumps(manifest))
    except SystemExit as error:
        assert "Invented claim" in str(error)
    else:
        raise AssertionError("site check accepted an invented evidence title")


def test_evidence_manifest_rejects_cve_absent_from_linked_source():
    namespace = runpy.run_path(str(SITE_REPORT_CHECK))
    validate_manifest = namespace["validate_evidence_manifest"]
    markdown = (
        "# Report\n"
        "**Generated:** 2026-08-13T13:00:00Z\n"
        "**Source:** [Feed](https://example.com/feed.xml)\n\n"
        "## Executive Summary\n"
        "CVE-2026-1111 is described by "
        "[Different advisory](https://example.com/different).\n\n"
        "## Source Highlights\n"
        "- [Different advisory](https://example.com/different)"
    )
    metadata = {
        "generated": "2026-08-13T13:00:00Z",
        "source": "[Feed](https://example.com/feed.xml)",
    }
    manifest = {
        "generated_at": "2026-08-13T13:00:00Z",
        "feed_url": "https://example.com/feed.xml",
        "sources": [
            {
                "title": "Different advisory",
                "url": "https://example.com/different",
                "cves": ["CVE-2026-2222"],
            }
        ],
    }

    try:
        validate_manifest(markdown, metadata, json.dumps(manifest))
    except SystemExit as error:
        assert "CVE-2026-1111" in str(error)
    else:
        raise AssertionError("site check accepted a CVE absent from its linked source")


def test_site_report_forbidden_detector_covers_public_label_variants():
    namespace = runpy.run_path(str(SITE_REPORT_CHECK))
    find_forbidden_label = namespace["find_public_report_forbidden_label"]

    blocked_cases = (
        "| **Classification** | Internal |",
        "**Classification:** Internal Use Only",
        "**Classification**: Internal",
        "Data Classification: Confidential",
        "Report Classification: Internal",
        "**Audience:** Internal stakeholders",
        "| Intended Audience | Internal Use Only |",
        "| **Distribution** | Internal |",
        "| Classification | Internal - Executive Distribution |",
        "| Distribution | Non-public |",
        "**Distribution:** Internal",
        "**Classification:** Nonpublic",
        "**Distribution:** Nonpublic",
        "Internal Use Only",
        "Internal Use Only:",
        "Internal use only: do not distribute",
        "*Internal-only*",
        "*For internal use only.*",
        "For internal use only - do not distribute",
        "**For internal use only:**",
        "*For internal distribution only*",
        "This report is intended for internal use only.",
        "*This report is intended for internal use only. Distribution outside the organization requires approval.*",
        "Internal distribution only",
        "Confidential: Yes",
        "Confidential - Internal Use Only",
        "**Confidential – Internal Distribution**",
        "Company Confidential",
        "Highly Confidential",
        "Sensitive Confidential",
        "Strictly Confidential",
        "Confidential and Proprietary",
        "Internal & Confidential",
        "**PROPRIETARY**",
        "**PRIVATE**",
        "**RESTRICTED**",
        "**NON-PUBLIC**",
        "**PRIVATE & CONFIDENTIAL**",
        "**Proprietary and Confidential**",
        "This report contains confidential and proprietary information.",
        "Unauthorized distribution is prohibited.",
        "**Internal – Executive Distribution**",
        "**Internal Distribution**",
        "**CONFIDENTIAL**",
        "## Classification: Internal Use Only",
        "1. **Classification:** Internal Use Only",
        "1) **Distribution:** Internal",
        "2. ## Confidential - Internal Distribution",
        "### Confidential - Internal Distribution",
        "| **Distribution Approval** | Required |",
        "**Distribution Approval:** Required",
        "**Distribution-Approval:** Required",
        "## Distribution Approval: Required",
        "*Distribution outside the organization requires approval*",
        "**Classification Level:** Internal",
        "**Confidentiality Level:** Confidential",
        "**Confidentiality:** Yes",
        "| Confidentiality | Yes |",
        "**Distribution Approval Status:** Required",
        "**Classification:** Private",
        "**Classification:** Restricted",
        "**Confidentiality:** Proprietary",
        "**Distribution:** Non-public",
        "> ### Confidential - Internal Distribution",
        "- ## Classification: Internal Use Only",
        "| **Prepared By** | Senior GRC Analyst |",
        "**Report Prepared By:** Senior GRC Analyst",
        "| **Report Prepared By** | Senior GRC Analyst |",
        "\n".join(
            (
                "| Date | Classification | Distribution |",
                "|------|----------------|--------------|",
                "| June 2026 | Internal | Internal |",
            )
        ),
        "\n".join(
            (
                "| Date | Classification | Distribution |",
                "|------|----------------|--------------|",
                "| June 2026 | Public | External |",
                "| July 2026 | Internal | Internal |",
            )
        ),
        "\n".join(
            (
                "Field | Detail",
                "------|-------",
                "Classification | Confidential",
            )
        ),
        "\n".join(
            (
                "| Date | Report Classification | Intended Audience |",
                "|------|-----------------------|-------------------|",
                "| June 2026 | Internal | Internal stakeholders |",
            )
        ),
    )
    for markdown in blocked_cases:
        assert find_forbidden_label(markdown), markdown

    allowed_cases = (
        "The report discusses confidential data handling obligations.",
        "Internal controls are mapped to the cited regulatory obligations.",
        "The source describes an internal-only system boundary.",
        "The analysis covers internal distribution system controls.",
        "Ensure distribution outside the organization requires approval before release.",
        "Distribution of policy updates requires approval by Legal.",
        "| Classification | Data classification comparison |",
        "**Classification:** Public report grouping",
        "| Classification | Internal control taxonomy |",
        "\n".join(
            (
                "| Classification | Control Area |",
                "|----------------|--------------|",
                "| Internal control taxonomy | SOX |",
            )
        ),
        "\n".join(
            (
                "| Asset | Classification |",
                "|-------|----------------|",
                "| Customer records | Confidential |",
            )
        ),
    )
    for markdown in allowed_cases:
        assert not find_forbidden_label(markdown), markdown


def test_model_report_prompt_avoids_internal_classification_labels():
    model_service = MODEL_SERVICE.read_text()

    assert "Do not include classification, confidentiality, internal-use" in model_service
    assert "public portfolio report" in model_service


def test_python_lambda_packaging_keeps_runtime_interface_client():
    pyproject = tomllib.loads(AGENT_PYPROJECT.read_text())
    dependencies = pyproject["project"]["dependencies"]

    assert any(dependency.split("==", 1)[0] == "awslambdaric" for dependency in dependencies)


def test_workflows_use_current_node_runtime_action_pins():
    workflow_text = "\n".join(workflow.read_text() for workflow in WORKFLOWS)

    assert "actions/checkout@v7" in workflow_text
    assert "aws-actions/configure-aws-credentials@v6" in workflow_text
    assert "actions/setup-python@v6" in workflow_text
    assert "actions/setup-node@v7" in workflow_text
    assert "actions/cache@v6" in workflow_text
    assert "hashicorp/setup-terraform@v4" in workflow_text
    assert "actions/upload-pages-artifact@v5" in workflow_text
    assert "actions/deploy-pages@v5" in workflow_text
    assert "actions/upload-artifact@v7" in workflow_text
    assert "astral-sh/setup-uv@v8.2.0" in workflow_text
    assert "actions/checkout@v4" not in workflow_text
    assert "aws-actions/configure-aws-credentials@v4" not in workflow_text
    assert "actions/setup-python@v5" not in workflow_text
    assert "actions/cache@v4" not in workflow_text
    assert "hashicorp/setup-terraform@v3" not in workflow_text
    assert "actions/upload-pages-artifact@v3" not in workflow_text
    assert "actions/deploy-pages@v4" not in workflow_text
    assert "astral-sh/setup-uv@v6" not in workflow_text


def test_lambda_deploy_smoke_test_fails_unhealthy_response():
    workflow = DEPLOY_WORKFLOW.read_text()

    assert "Lambda status code: ${STATUS_CODE:-unknown}" in workflow
    assert "Lambda health status: ${HEALTH_STATUS:-unknown}" in workflow
    assert "Lambda health smoke test failed" in workflow
    assert "cat health.json || true" not in workflow


def test_lambda_deploy_sets_explicit_model_runtime_environment():
    workflow = DEPLOY_WORKFLOW.read_text()
    global_env = workflow.split("jobs:", 1)[0]

    assert "LLM_MODEL: ${{ vars.LLM_MODEL" in workflow
    assert "OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}" not in global_env
    assert workflow.count("OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}") == 2
    assert "OPENROUTER_API_KEY secret is required" in workflow
    assert "Invalid LLM_MODEL; expected provider/model format" in workflow
    assert (
        "direct Lambda model-backed analysis requires openrouter/provider-model format" in workflow
    )
    assert "LLM_MODEL=$LLM_MODEL" in workflow
    assert "OPENROUTER_API_KEY=$OPENROUTER_API_KEY" in workflow
    assert "ANTHROPIC_API_KEY=" not in workflow


def test_manual_lambda_deploy_uses_openrouter_secret():
    script = DEPLOY_SCRIPT.read_text()

    assert "OPENROUTER_API_KEY is not set" in script
    assert "openrouter/provider-model format" in script
    assert "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" in script


def test_lambda_configuration_updates_do_not_dump_openrouter_secret():
    workflow = DEPLOY_WORKFLOW.read_text()
    script = DEPLOY_SCRIPT.read_text()

    assert "OPENROUTER_API_KEY=$OPENROUTER_API_KEY" in workflow
    workflow_mutations = (
        workflow.count("aws lambda update-function-code")
        + workflow.count("aws lambda update-function-configuration")
        + workflow.count("aws lambda create-function")
    )
    assert workflow.count("--query 'FunctionName'") >= workflow_mutations
    assert "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" in script
    script_mutations = (
        script.count("aws lambda update-function-code")
        + script.count("aws lambda update-function-configuration")
        + script.count("aws lambda create-function")
    )
    assert script.count("--query 'FunctionName'") >= script_mutations
