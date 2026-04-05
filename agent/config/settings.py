"""Configuration settings for the FastAPI application."""

import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8081
    reload: bool = True
    log_level: str = "INFO"
    
    # Anthropic Claude configuration
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-6"
    anthropic_max_tokens: int = 16000
    
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
        "industry standards"
    ]

    # CORS configuration
    cors_allowed_origins: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from .env file


# Global settings instance
settings = Settings()
