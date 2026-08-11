"""Configuration settings for the FastAPI application."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Literal

OpenAIReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8081
    reload: bool = True
    log_level: str = "INFO"

    # Model configuration
    llm_model: str = "gpt-5.6-sol"
    llm_max_tokens: int = 16000
    openai_api_key: str = ""
    openai_reasoning_effort: OpenAIReasoningEffort = "xhigh"

    # RSS configuration
    rss_timeout: int = 30
    rss_max_retries: int = 3

    # Analysis configuration
    analysis_focus_areas: List[str] = [
        "governance frameworks",
        "compliance requirements",
        "risk management",
        "regulatory updates",
        "audit findings",
        "policy changes",
        "industry standards",
    ]

    # CORS configuration
    cors_allowed_origins: List[str] = ["*"]


# Global settings instance
settings = Settings()
