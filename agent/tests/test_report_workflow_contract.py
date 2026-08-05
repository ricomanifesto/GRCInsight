from datetime import datetime, timezone
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
REPORT_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "lambda-report-generation.yml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SITE_REPORT_CHECK = REPO_ROOT / "scripts" / "check_site_report.py"
MODEL_SERVICE = REPO_ROOT / "agent" / "services" / "model_service.py"
RENDERER_JS = REPO_ROOT / "site" / "static" / "renderer.js"
WORKFLOWS = (CI_WORKFLOW, DEPLOY_WORKFLOW, REPORT_WORKFLOW)
PUBLISHED_AT = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_report_generation_workflow_accepts_repository_dispatch_payloads():
    workflow = REPORT_WORKFLOW.read_text()

    assert "repository_dispatch:" in workflow
    assert "github.event.client_payload.feed_url" in workflow


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
                    "actor_ids": ["APT1"],
                },
                {
                    "title": "Cloud Security Alliance publishes guidance",
                    "url": "https://example.com/guidance",
                    "snippet": "The industry group called Cloud Security Alliance published guidance.",
                    "cves": [],
                    "actor_ids": [],
                },
            ],
        },
        {"title": "Test Feed"},
    )

    assert "Source Evidence for Entity Sections:" in prompt
    assert "Threat Actor Activities" in prompt
    assert "CVE and Vulnerability Highlights" in prompt
    assert "Executive Summary must be 2-4 short paragraphs" in prompt
    assert "APT1" in prompt
    assert "CVE-2026-12345" in prompt
    assert "structured actor identifiers are hints, not an exhaustive actor list" in prompt
    assert "Do not classify industry, standards, regulatory, or working groups" in prompt
    assert "List every article-supported CVE identifier up to 10 items" in prompt


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
                    "actor_ids": [],
                }
            ],
        },
        {"title": "Test Feed"},
    )

    assert cves[9] in prompt
    assert cves[10] not in prompt
    assert cves[11] not in prompt
    assert "[additional CVE omitted]" in prompt


def test_source_evidence_preserves_distinct_cves_and_safe_actor_context():
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
    actor_ids = {actor for item in evidence for actor in item["actor_ids"]}

    assert len(evidence) <= workflow_mod.SOURCE_EVIDENCE_LIMIT
    assert "https://example.com/apt1" in evidence_urls
    assert "https://example.com/named-actor" in evidence_urls
    assert "https://example.com/long-cve" in evidence_urls
    assert {"CVE-2026-11111", "CVE-2026-22222", "CVE-2026-12345678"} <= cves
    assert {"APT1", "FIN7"} <= actor_ids
    assert "FINRA" not in actor_ids
    assert "Cloud Security Alliance" not in actor_ids
    named_actor_evidence = next(
        item for item in evidence if item["url"] == "https://example.com/named-actor"
    )
    assert named_actor_evidence["has_threat_context"] is True
    assert (
        workflow_mod._has_threat_actor_context(
            "The industry group called Cloud Security Alliance published guidance."
        )
        is False
    )


def test_actor_id_extraction_excludes_mitre_attack_tactics():
    actor_ids = workflow_mod._extract_actor_ids(
        "MITRE ATT&CK maps tactics TA0001, TA-0002, and TA 0003. "
        "Threat actor TA 505 remains active."
    )

    assert actor_ids == ["TA505"]


def test_source_evidence_reserves_room_for_actor_context_after_cve_volume():
    articles = [
        ArticleInput(
            title=f"CVE source {index}",
            url=f"https://example.com/cve-{index}",
            content=f"CVE-2026-{10000 + index} affects an appliance.",
            summary="",
            published=PUBLISHED_AT,
        )
        for index in range(14)
    ]
    articles.append(
        ArticleInput(
            title="Named actor source",
            url="https://example.com/named-actor-late",
            content="The threat-actor group Volt Typhoon targeted government agencies.",
            summary="",
            published=PUBLISHED_AT,
        )
    )

    evidence = workflow_mod._build_source_evidence(articles)

    assert len(evidence) == workflow_mod.SOURCE_EVIDENCE_LIMIT
    assert any(item["url"] == "https://example.com/named-actor-late" for item in evidence)


def test_threat_actor_context_matches_normalized_state_actor_phrases():
    assert workflow_mod._has_threat_actor_context(
        "Nation-state actor Volt Typhoon targeted government agencies."
    )
    assert workflow_mod._has_threat_actor_context(
        "A state-sponsored group targeted critical infrastructure."
    )


def test_fallback_report_links_named_actor_context_to_its_reserved_source():
    articles = [
        ArticleInput(
            title=f"CVE source {index}",
            url=f"https://example.com/cve-{index}",
            content=f"CVE-2026-{10000 + index} affects an appliance.",
            summary="",
            published=PUBLISHED_AT,
        )
        for index in range(12)
    ]
    articles.append(
        ArticleInput(
            title="Late actor source",
            url="https://example.com/late-actor",
            content="Nation-state actor Volt Typhoon targeted government agencies.",
            summary="",
            published=PUBLISHED_AT,
        )
    )
    local_signals, analysis = workflow_mod._build_local_analysis(articles)

    report = workflow_mod._build_fallback_report(
        {"title": "Test Feed"},
        articles,
        local_signals,
        analysis,
        "model unavailable",
    )

    assert "[Late actor source](https://example.com/late-actor)" in report
    assert "does not infer actor names" in report


def test_fallback_report_includes_structured_and_named_only_actor_sources():
    articles = [
        ArticleInput(
            title="APT1 targets banks",
            url="https://example.com/apt1",
            content="Threat actor APT1 targeted bank systems.",
            summary="",
            published=PUBLISHED_AT,
        ),
        ArticleInput(
            title="Volt Typhoon targets agencies",
            url="https://example.com/volt-typhoon",
            content="Nation-state actor Volt Typhoon targeted government agencies.",
            summary="",
            published=PUBLISHED_AT,
        ),
    ]
    local_signals, analysis = workflow_mod._build_local_analysis(articles)

    report = workflow_mod._build_fallback_report(
        {"title": "Test Feed"},
        articles,
        local_signals,
        analysis,
        "model unavailable",
    )
    actor_section = report.split("4) Threat Actor Activities", 1)[1].split(
        "5) CVE and Vulnerability Highlights", 1
    )[0]

    assert "APT1: Mentioned in [APT1 targets banks](https://example.com/apt1)" in actor_section
    assert "[Volt Typhoon targets agencies](https://example.com/volt-typhoon)" in actor_section


def test_fallback_report_does_not_infer_named_actor_aliases():
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

    assert "4) Threat Actor Activities" in report
    assert "5) CVE and Vulnerability Highlights" in report
    assert "does not infer actor names" in report
    assert "Volt Typhoon: Article-supported activity" not in report


def test_renderer_and_site_check_recognize_entity_sections():
    check_script = SITE_REPORT_CHECK.read_text()
    renderer = RENDERER_JS.read_text()

    for section in ("Threat Actor Activities", "CVE and Vulnerability Highlights"):
        assert section in check_script
        assert section in renderer


def test_report_generation_workflow_does_not_dump_lambda_response_body():
    workflow = REPORT_WORKFLOW.read_text()

    assert "cat lambda-response.json" not in workflow
    assert "Lambda status code:" in workflow


def test_report_generation_workflow_does_not_dump_failed_report_body():
    workflow = REPORT_WORKFLOW.read_text()

    assert "cat report-data.json" not in workflow
    assert "Report status is 'failed'. Aborting early." in workflow


def test_report_generation_workflow_strips_duplicate_report_title():
    workflow = REPORT_WORKFLOW.read_text()

    assert 'echo "# ${SAFE_TITLE}" > site/index.md' in workflow
    assert "REPORT_BODY=$(printf '%s\\n' \"$SAFE_CONTENT\" | awk" in workflow
    assert 'echo "${REPORT_BODY}" >> site/index.md' in workflow


def test_report_generation_workflow_strips_duplicate_generated_timestamp():
    workflow = REPORT_WORKFLOW.read_text()

    assert "seen_generated = 0" in workflow
    assert "/^\\*\\*Generated:\\*\\*/" in workflow


def test_report_generation_workflow_validates_generated_site_before_publish():
    workflow = REPORT_WORKFLOW.read_text()

    assert "Validate generated site report" in workflow
    assert workflow.count("python3 scripts/check_site_report.py") >= 2
    assert workflow.index("Validate generated site report") < workflow.index(
        "Commit and push report"
    )
    assert workflow.index("Validate generated site report") < workflow.index(
        "Upload Pages artifact"
    )
    rebase_index = workflow.index('git rebase -X theirs "origin/$GITHUB_REF_NAME"')
    assert workflow.index("python3 scripts/check_site_report.py", rebase_index) < workflow.index(
        "git push origin HEAD"
    )


def test_site_report_check_rejects_internal_distribution_labels():
    check_script = SITE_REPORT_CHECK.read_text()

    assert "find_public_report_forbidden_label" in check_script
    assert "FORBIDDEN_METADATA_FIELDS" in check_script
    assert "PRIVATE_VALUE_FIELDS" in check_script
    assert "PRIVATE_VALUE_TERMS" in check_script
    assert "normalize_label_text" in check_script
    assert r"\bCONFIDENTIAL\b" not in check_script


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
    assert "actions/cache@v6" in workflow_text
    assert "hashicorp/setup-terraform@v4" in workflow_text
    assert "actions/upload-pages-artifact@v5" in workflow_text
    assert "actions/deploy-pages@v5" in workflow_text
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
    assert "OPENCODE_BASE_URL=" not in workflow
    assert "ANTHROPIC_API_KEY=" not in workflow


def test_manual_lambda_deploy_uses_openrouter_secret():
    script = DEPLOY_SCRIPT.read_text()

    assert "OPENROUTER_API_KEY is not set" in script
    assert "openrouter/provider-model format" in script
    assert "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" in script
    assert "OPENCODE_BASE_URL=${OPENCODE_BASE_URL}" not in script


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
