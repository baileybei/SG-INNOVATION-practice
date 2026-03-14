"""Configuration management for Vision Agent.

Reads settings from environment variables (with .env file support).
All configuration is validated at startup via Pydantic.
"""

import os
from enum import Enum
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class VLMProvider(str, Enum):
    MOCK = "mock"
    SEALION = "sealion"
    GEMINI = "gemini"


class Settings(BaseSettings):
    # VLM provider selection
    vlm_provider: VLMProvider = VLMProvider.MOCK

    # SEA-LION API (required only when vlm_provider=sealion)
    sealion_api_key: str = Field(default="", description="SEA-LION API key")
    sealion_api_url: str = Field(default="", description="SEA-LION API base URL")

    # Gemini API (required only when vlm_provider=gemini)
    gemini_api_key: str = Field(default="", description="Google Gemini API key")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Image constraints
    max_image_size_mb: float = Field(default=10.0, gt=0)

    # VLM retry settings
    vlm_max_retries: int = Field(default=3, ge=1, le=10)
    vlm_retry_delay_s: float = Field(default=1.0, ge=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("sealion_api_key", "sealion_api_url", "gemini_api_key", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    def validate_provider_config(self) -> None:
        """Raise ValueError if selected provider credentials are missing."""
        if self.vlm_provider == VLMProvider.SEALION:
            if not self.sealion_api_key:
                raise ValueError("SEALION_API_KEY must be set when vlm_provider=sealion")
            if not self.sealion_api_url:
                raise ValueError("SEALION_API_URL must be set when vlm_provider=sealion")
        elif self.vlm_provider == VLMProvider.GEMINI:
            if not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY must be set when vlm_provider=gemini")


def get_settings() -> Settings:
    """Return validated application settings."""
    return Settings()
