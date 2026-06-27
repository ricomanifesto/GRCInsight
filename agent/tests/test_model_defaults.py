from config.settings import Settings
from models.api import GRCAnalysisConfig
from services import model_service
from services.model_service import GRCModelService
from services.opencode_client import parse_model_selection
from services.openrouter_client import OpenRouterClient


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


def test_model_service_uses_openrouter_client_when_api_key_is_configured(monkeypatch):
    monkeypatch.setattr(model_service.settings, "openrouter_api_key", "test-key")

    service = GRCModelService(
        model_name="openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
        max_tokens=4096,
    )

    assert service.client_kind == "openrouter"
    assert isinstance(service.client, OpenRouterClient)
    assert service.client.max_tokens == 4096


def test_model_service_keeps_opencode_for_local_runs_without_openrouter_key(monkeypatch):
    monkeypatch.setattr(model_service.settings, "openrouter_api_key", "")

    service = GRCModelService(
        model_name="openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
        max_tokens=4096,
    )

    assert service.client_kind == "opencode"


def test_model_service_rejects_non_openrouter_models_when_api_key_is_configured(monkeypatch):
    monkeypatch.setattr(model_service.settings, "openrouter_api_key", "test-key")

    try:
        GRCModelService(model_name="anthropic/claude-sonnet-4-6", max_tokens=4096)
    except ValueError as exc:
        assert "openrouter/* model" in str(exc)
    else:
        raise AssertionError("OpenRouter Lambda config must reject non-OpenRouter models")
