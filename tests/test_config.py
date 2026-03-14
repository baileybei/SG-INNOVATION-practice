"""Tests for configuration module."""

import pytest

from src.vision_agent.config import Settings, VLMProvider, get_settings

# Env vars that .env file sets — must be cleared for "default" tests
_ENV_KEYS = [
    "VLM_PROVIDER", "GEMINI_API_KEY", "SEALION_API_KEY",
    "SEALION_API_URL", "LOG_LEVEL",
]


@pytest.fixture()
def clean_env(monkeypatch):
    """Remove all .env-sourced vars so Settings() returns true defaults."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


class TestSettingsDefaults:
    """Test default values when no .env file is loaded."""

    def test_defaults_to_mock_provider(self, clean_env):
        s = Settings(_env_file=None)
        assert s.vlm_provider == VLMProvider.MOCK

    def test_log_level_default(self, clean_env):
        s = Settings(_env_file=None)
        assert s.log_level == "INFO"

    def test_max_image_size_default(self, clean_env):
        s = Settings(_env_file=None)
        assert s.max_image_size_mb == 10.0

    def test_retry_defaults(self, clean_env):
        s = Settings(_env_file=None)
        assert s.vlm_max_retries == 3
        assert s.vlm_retry_delay_s == 1.0


class TestProviderValidation:
    """Test validate_provider_config for each provider."""

    def test_sealion_raises_without_key(self):
        s = Settings(vlm_provider=VLMProvider.SEALION, sealion_api_key="", sealion_api_url="")
        with pytest.raises(ValueError, match="SEALION_API_KEY"):
            s.validate_provider_config()

    def test_sealion_raises_without_url(self):
        s = Settings(vlm_provider=VLMProvider.SEALION, sealion_api_key="key123", sealion_api_url="")
        with pytest.raises(ValueError, match="SEALION_API_URL"):
            s.validate_provider_config()

    def test_sealion_passes_with_both(self):
        s = Settings(
            vlm_provider=VLMProvider.SEALION,
            sealion_api_key="key123",
            sealion_api_url="https://api.example.com",
        )
        s.validate_provider_config()  # should not raise

    def test_gemini_raises_without_key(self, clean_env):
        s = Settings(_env_file=None, vlm_provider=VLMProvider.GEMINI, gemini_api_key="")
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            s.validate_provider_config()

    def test_gemini_passes_with_key(self):
        s = Settings(vlm_provider=VLMProvider.GEMINI, gemini_api_key="test-key")
        s.validate_provider_config()  # should not raise

    def test_mock_skips_validation(self):
        s = Settings(vlm_provider=VLMProvider.MOCK)
        s.validate_provider_config()  # no-op, should not raise


class TestSettingsOverride:
    def test_get_settings_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("VLM_MAX_RETRIES", "5")
        s = Settings(_env_file=None)
        assert s.log_level == "WARNING"
        assert s.vlm_max_retries == 5
