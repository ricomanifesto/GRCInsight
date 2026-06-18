from pathlib import Path

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
