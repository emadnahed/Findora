"""Unit tests for configuration settings."""

import pytest

from src.config.settings import Settings, get_settings


class TestSettings:
    """Test suite for Settings configuration."""

    def test_default_settings(self) -> None:
        """Test that default settings are loaded correctly."""
        settings = Settings()

        assert settings.app_name == "Findora Search API"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000

    def test_elasticsearch_defaults(self) -> None:
        """Test Elasticsearch default configuration."""
        settings = Settings()

        assert settings.elasticsearch_url == "http://localhost:9200"
        assert settings.elasticsearch_index == "products"
        assert settings.elasticsearch_timeout == 30

    def test_settings_override(self) -> None:
        """Test that settings can be overridden."""
        settings = Settings(
            debug=True,
            port=9000,
            elasticsearch_index="custom_index",
        )

        assert settings.debug is True
        assert settings.port == 9000
        assert settings.elasticsearch_index == "custom_index"

    def test_get_settings_cached(self) -> None:
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2
