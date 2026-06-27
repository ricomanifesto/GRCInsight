from pathlib import Path
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_PYPROJECT = REPO_ROOT / "agent" / "pyproject.toml"
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-lambda.yml"
REPORT_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "lambda-report-generation.yml"


def test_report_generation_workflow_accepts_repository_dispatch_payloads():
    workflow = REPORT_WORKFLOW.read_text()

    assert "repository_dispatch:" in workflow
    assert "github.event.client_payload.feed_url" in workflow


def test_report_generation_payload_treats_feed_url_as_json_data():
    workflow = REPORT_WORKFLOW.read_text()

    assert "Invalid FEED_URL; expected http(s) URL without whitespace" in workflow
    assert "jq -n --arg feed_url" in workflow
    assert '\\"feed_url\\": \\"${{ steps.feed-url.outputs.FEED_URL }}\\"' not in workflow


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


def test_python_lambda_packaging_keeps_runtime_interface_client():
    pyproject = tomllib.loads(AGENT_PYPROJECT.read_text())
    dependencies = pyproject["project"]["dependencies"]

    assert any(dependency.split("==", 1)[0] == "awslambdaric" for dependency in dependencies)


def test_lambda_deploy_smoke_test_fails_unhealthy_response():
    workflow = DEPLOY_WORKFLOW.read_text()

    assert "Lambda status code: ${STATUS_CODE:-unknown}" in workflow
    assert "Lambda health status: ${HEALTH_STATUS:-unknown}" in workflow
    assert "Lambda health smoke test failed" in workflow
    assert "cat health.json || true" not in workflow
