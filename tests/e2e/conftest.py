"""E2E test configuration and fixtures.

These fixtures handle Elasticsearch client lifecycle for E2E tests,
ensuring each test gets a fresh client to avoid event loop issues.
"""

import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from src.config.settings import Settings, get_settings
from src.elastic.client import get_elasticsearch_client
from src.main import app
from src.services.search import get_search_service


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
    """Reset singleton caches before each test.

    This prevents event loop issues when running multiple async tests.
    """
    get_elasticsearch_client.cache_clear()
    get_search_service.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def e2e_settings() -> Settings:
    """Provide E2E test settings."""
    return Settings(
        debug=True,
        elasticsearch_url=os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"),
        elasticsearch_index=os.getenv("ELASTICSEARCH_INDEX", "test_products"),
        log_level="DEBUG",
        cache_enabled=False,  # Disable caching for E2E tests
    )


@pytest.fixture(autouse=True)
def override_settings(e2e_settings: Settings) -> None:
    """Override application settings for E2E tests."""
    app.dependency_overrides[get_settings] = lambda: e2e_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(
    e2e_settings: Settings,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide async HTTP client for E2E tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_product() -> dict[str, Any]:
    """Provide sample product data for tests."""
    return {
        "id": 1,
        "name": "iPhone 15",
        "description": "Apple smartphone with A17 chip",
        "price": 799.99,
    }
