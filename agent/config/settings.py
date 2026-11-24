"""Configuration settings for the FastAPI application."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Literal


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server configuration
    host: str = "127.0.0.1"
    port: int = 8081
    reload: bool = True
    log_level: str = "INFO"

    # Model configuration
    llm_model: str = "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"
    llm_max_tokens: int = 16000
    openrouter_api_key: str = ""
    api_key: str = ""
    # Shared with the Go service; authenticates synchronous report runs.
    grc_internal_token: str = ""
    grc_relevance_mode: Literal["off", "shadow", "enabled"] = "off"
    grc_relevance_min_probability: float = Field(default=0.95, ge=0.5, le=1, allow_inf_nan=False)
    grc_relevance_timeout_seconds: float = Field(default=4, gt=0, le=10, allow_inf_nan=False)

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
    cors_allowed_origins: List[str] = ["https://ricomanifesto.github.io"]

    @field_validator("cors_allowed_origins")
    @classmethod
    def explicit_origins(cls, origins: List[str]) -> List[str]:
        from urllib.parse import urlsplit

        for origin in origins:
            parsed = urlsplit(origin)
            if (
                "*" in origin
                or parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS requires explicit HTTP(S) origins")
        return origins


# Global settings instance
settings = Settings()
