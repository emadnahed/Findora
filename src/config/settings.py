"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Findora Search API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "products"
    elasticsearch_timeout: int = 30
    elasticsearch_number_of_shards: int = 1
    elasticsearch_number_of_replicas: int = 0

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # 'json' for production, 'console' for development

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"
    rate_limit_search: str = "20/minute"
    redis_url: str | None = None  # Optional Redis URL for distributed rate limiting


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
