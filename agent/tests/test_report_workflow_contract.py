from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "lambda-report-generation.yml"


def test_report_generation_workflow_accepts_repository_dispatch_payloads():
    workflow = REPORT_WORKFLOW.read_text()

    assert "repository_dispatch:" in workflow
    assert "github.event.client_payload.feed_url" in workflow
