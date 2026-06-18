from config.settings import Settings
from models.api import GRCAnalysisConfig
from services.opencode_client import parse_model_selection


def test_settings_default_uses_free_openrouter_report_model():
    assert (
        Settings.model_fields["llm_model"].default
        == "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"
    )


def test_analysis_config_default_uses_free_openrouter_report_model():
    config = GRCAnalysisConfig()

    assert config.model == "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"


def test_openrouter_report_model_parses_to_provider_and_nested_model_id():
    model = parse_model_selection("openrouter/nvidia/nemotron-3-ultra-550b-a55b:free")

    assert model.provider_id == "openrouter"
    assert model.model_id == "nvidia/nemotron-3-ultra-550b-a55b:free"
