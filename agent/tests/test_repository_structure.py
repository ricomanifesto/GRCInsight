from pathlib import Path
import os
import subprocess
import textwrap
import tomllib

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_legacy_monolith_is_not_kept_in_active_repo():
    assert not (REPO_ROOT / "legacy").exists()


def test_grc_model_service_name_is_domain_specific():
    service_source = (REPO_ROOT / "agent/services/model_service.py").read_text(encoding="utf-8")
    api_source = (REPO_ROOT / "agent/models/api.py").read_text(encoding="utf-8")

    assert "class GRCModelService" in service_source
    assert "class GRCAnalysisConfig" in api_source
    assert "class ModelService" not in service_source
    assert "class AnalysisConfig" not in api_source


def test_obsolete_python_scaffolding_is_not_kept():
    assert not (REPO_ROOT / "requirements.txt").exists()
    assert not (REPO_ROOT / "docs/templates/grc_report.md").exists()

    project = tomllib.loads((REPO_ROOT / "agent/pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]

    assert not any(dependency.startswith("langchain") for dependency in dependencies)
    assert not any(dependency.startswith("python-dotenv") for dependency in dependencies)


def test_removed_compatibility_helpers_stay_removed():
    workflow_source = (REPO_ROOT / "agent/core/workflow.py").read_text(encoding="utf-8")
    logger_source = (REPO_ROOT / "internal/utils/logger.go").read_text(encoding="utf-8")
    report_model_source = (REPO_ROOT / "internal/database/models/report.go").read_text(
        encoding="utf-8"
    )

    assert "def extract_from_analysis" not in workflow_source
    assert "func WithRequestID" not in logger_source
    assert "func WithUserID" not in logger_source
    assert "func (r *Report) BeforeCreate" not in report_model_source
    assert "func (m ReportMetadata) Value" not in report_model_source
    assert "func (m *ReportMetadata) Scan" not in report_model_source


def test_lambda_deploy_wait_fails_closed():
    workflow_source = (REPO_ROOT / ".github/workflows/deploy-lambda.yml").read_text(
        encoding="utf-8"
    )

    assert 'grep -q "Active\\tSuccessful"' not in workflow_source
    assert 'read -r STATE UPDATE_STATUS <<< "$STATUS"' in workflow_source
    assert 'if [ "$ready" != true ]; then' in workflow_source


def test_lambda_deploy_forwards_relevance_pilot_configuration():
    workflow_source = (REPO_ROOT / ".github/workflows/deploy-lambda.yml").read_text(
        encoding="utf-8"
    )

    for name, default in (
        ("GRC_RELEVANCE_MODE", "off"),
        ("GRC_RELEVANCE_MIN_PROBABILITY", "0.95"),
        ("GRC_RELEVANCE_TIMEOUT_SECONDS", "4"),
    ):
        assert f"{name}: ${{{{ vars.{name} || '{default}' }}}}" in workflow_source
        assert f"{name}=${name}" in workflow_source


@pytest.mark.parametrize(
    ("mode", "probability", "timeout", "valid"),
    [
        ("off", "0.95", "4", True),
        ("shadow", "0.5", "10", True),
        ("enabled", "1", "0.1", True),
        ("enabled,LOG_LEVEL=DEBUG", "0.95", "4", False),
        ("off", "nan", "4", False),
        ("off", "0.49", "4", False),
        ("off", "1.01", "4", False),
        ("off", "0.95", "inf", False),
        ("off", "0.95", "0", False),
        ("off", "0.95", "11", False),
        ("off", "invalid", "4", False),
    ],
)
def test_lambda_configuration_is_validated_before_deployment(mode, probability, timeout, valid):
    workflow_source = (REPO_ROOT / ".github/workflows/deploy-lambda.yml").read_text()
    validation = workflow_source.split("- name: Validate model runtime configuration", 1)[1]
    script = textwrap.dedent(validation.split("run: |\n", 1)[1].split("\n      - name:", 1)[0])
    result = subprocess.run(
        ["bash", "-c", script],
        env={
            **os.environ,
            "LLM_MODEL": "openrouter/test/model",
            "OPENROUTER_API_KEY": "dummy-test-key",
            "GRC_RELEVANCE_MODE": mode,
            "GRC_RELEVANCE_MIN_PROBABILITY": probability,
            "GRC_RELEVANCE_TIMEOUT_SECONDS": timeout,
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert (result.returncode == 0) is valid
    assert "dummy-test-key" not in result.stdout + result.stderr
