from datetime import datetime, timezone
import json
from pathlib import Path
import runpy
import tomllib

from core import workflow as workflow_mod
from models.api import ArticleInput
from services.model_service import GRCModelService

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
MODEL_SERVICE = REPO_ROOT / "agent" / "services" / "model_service.py"
RENDERER_JS = REPO_ROOT / "site" / "static" / "renderer.js"
WORKFLOWS = (CI_WORKFLOW, DEPLOY_WORKFLOW, DEPLOY_SITE_WORKFLOW, REPORT_WORKFLOW)
PUBLISHED_AT = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_report_generation_workflow_accepts_repository_dispatch_payloads():
    workflow = REPORT_WORKFLOW.read_text()

    assert "repository_dispatch:" in workflow
    assert "github.event.client_payload.feed_url" in workflow


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

    assert "LLM_MODEL: ${{ vars.LLM_MODEL" in workflow
    assert (
        "Invalid LLM_MODEL; report generation requires openrouter/provider-model format" in workflow
    )
    assert '--arg model "$LLM_MODEL"' in workflow
    assert "model: $model" in workflow
    assert "claude-opus-4-6" not in workflow


def test_integration_report_payload_uses_openrouter_provider_model():
    integration_script = (REPO_ROOT / "scripts" / "integration" / "run_e2e.sh").read_text()

    assert '"model": "openrouter/openrouter/free"' in integration_script
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
    assert "Use inline Markdown links with the exact source title and URL" in prompt
    assert "Every report-specific regulatory and CVE claim" in prompt
    assert "Do not emit incomplete, truncated, or ellipsized CVE identifiers" in prompt
    assert "Use exact framework, standard, regulation, or publication names" in prompt
    assert "Source Highlights" in prompt
    assert "Never use superscript footnotes" in prompt
    assert "Do not invent counts" in prompt
    assert "publication layer adds those values" in prompt


def test_report_prompt_globally_bounds_cve_evidence():
    service = GRCModelService.__new__(GRCModelService)
    cves = [f"CVE-2026-{10000 + index}" for index in range(12)]

    prompt = service._create_report_prompt(
        {
            "summary": {"total_articles": 1, "grc_relevant_count": 1},
            "analysis": {},
            "source_evidence": [
                {
                    "title": "Patch roundup",
                    "url": f"https://example.com/advisory/{cves[10]}",
                    "snippet": "A vendor published fixes for " + ", ".join(cves) + ".",
                    "cves": cves,
                }
            ],
        },
        {"title": "Test Feed"},
    )

    assert cves[9] in prompt
    assert cves[10] not in prompt
    assert cves[11] not in prompt
    assert "[additional CVE omitted]" in prompt


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
            "content": "# Duplicate title\n**Generated:** stale\n\n1. Executive Summary\nCareful analysis.\n\n---\n\n6) Source Highlights\n- [Evidence](https://example.com/evidence)",
            "metadata": {
                "analysis_mode": "model",
                "source_name": "SentryDigest",
                "source_url": "https://example.com/feed.xml",
                "source_articles": [{"title": "Evidence", "url": "https://example.com/evidence"}],
                "analysis_period": "August 2026",
                "article_count": 30,
                "grc_article_count": 12,
                "model": "openrouter/example/model",
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
    assert "**Model:** openrouter/example/model" in report
    assert "**Analysis Mode:** Model-backed" in report
    assert "## Executive Summary" in report
    assert "## Source Highlights" in report
    assert "\n---\n" not in report
    assert "stale" not in report


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
            "source_articles": [{"title": "Evidence", "url": "https://example.com/evidence"}],
            "analysis_period": "August 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "model": "openrouter/example/model",
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
            "content": (
                "## **1. EXECUTIVE SUMMARY:**\nCareful analysis.\n\n"
                "**6) source highlights.**\n"
                "- [Evidence](https://example.com/evidence)"
            ),
            "metadata": {
                "analysis_mode": "model",
                "source_name": "SentryDigest\\",
                "source_url": feed_url,
                "source_articles": [{"title": "Evidence", "url": "https://example.com/evidence"}],
                "analysis_period": "August 2026",
                "article_count": 1,
                "grc_article_count": 1,
                "model": "openrouter/example/model",
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
        "content": (
            "## Executive Summary\n"
            "[Invented evidence](https://invented.example/advisory)\n\n"
            "## Source Highlights\n"
            "- [Invented evidence](https://invented.example/advisory)"
        ),
        "metadata": {
            "analysis_mode": "model",
            "source_name": "SentryDigest",
            "source_url": "https://example.com/feed.xml",
            "source_articles": [{"title": "Real evidence", "url": "https://example.com/real"}],
            "analysis_period": "August 2026",
            "article_count": 1,
            "grc_article_count": 1,
            "model": "openrouter/example/model",
        },
    }

    try:
        compose_report(data, "https://example.com/feed.xml", "openrouter/example/model")
    except SystemExit as error:
        assert "absent from source articles" in str(error)
    else:
        raise AssertionError("composer accepted an invented evidence URL")


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
        "[Evidence](https://example.com/a_(b).html)\n\n"
        "## Source Highlights\n"
        "- [Evidence](https://example.com/a_(b).html)"
    )
    metadata = {
        "generated": "2026-08-13T13:00:00Z",
        "source": "[Feed](https://example.com/feed(1).xml)",
    }
    manifest = {
        "generated_at": "2026-08-13T13:00:00Z",
        "feed_url": "https://example.com/feed%281%29.xml",
        "sources": [{"title": "Evidence", "url": "https://example.com/a_%28b%29.html"}],
    }

    validate_manifest(markdown, metadata, json.dumps(manifest))


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
