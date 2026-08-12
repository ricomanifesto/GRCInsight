from pathlib import Path
import tomllib

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
