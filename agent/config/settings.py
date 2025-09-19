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
    
    # OpenAI configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-5"
    openai_max_tokens: int = 4000
    
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
