import pytest
from pydantic import ValidationError

from config.settings import Settings
from models.api import GRCAnalysisConfig
from services import model_service
from services.model_service import GRCModelService
from services.openai_client import OpenAIClient


def test_settings_default_uses_gpt_5_6_sol():
    assert Settings.model_fields["llm_model"].default == "gpt-5.6-sol"
    assert Settings.model_fields["openai_reasoning_effort"].default == "xhigh"


def test_settings_reject_unknown_reasoning_effort(monkeypatch):
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "extreme")

    with pytest.raises(ValidationError):
        Settings()


def test_analysis_config_default_uses_gpt_5_6_sol():
    config = GRCAnalysisConfig()

    assert config.model == "gpt-5.6-sol"


def test_model_service_uses_openai_client(monkeypatch):
    monkeypatch.setattr(model_service.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(model_service.settings, "openai_reasoning_effort", "xhigh")

    service = GRCModelService(
        model_name="gpt-5.6-sol",
        max_tokens=4096,
    )

    assert service.client_kind == "openai"
    assert isinstance(service.client, OpenAIClient)
    assert service.client.max_output_tokens == 4096
    assert service.client.reasoning_effort == "xhigh"


def test_model_service_requires_openai_api_key(monkeypatch):
    monkeypatch.setattr(model_service.settings, "openai_api_key", "")

    try:
        GRCModelService(model_name="gpt-5.6-sol", max_tokens=4096)
    except ValueError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("OpenAI configuration must require an API key")
