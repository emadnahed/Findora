"""Pytest configuration and shared fixtures."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from src.config.settings import Settings, get_settings
from src.main import app

# ============================================================================
# Settings Fixtures
# ============================================================================


@pytest.fixture
def test_settings() -> Settings:
    """Provide test settings with overrides."""
    return Settings(
        debug=True,
        elasticsearch_url="http://localhost:9200",
        elasticsearch_index="test_products",
        log_level="DEBUG",
    )


@pytest.fixture
def override_settings(test_settings: Settings) -> None:
    """Override application settings for testing."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


# ============================================================================
# HTTP Client Fixtures
# ============================================================================


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide async HTTP client for testing FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ============================================================================
# Mock Data Fixtures
# ============================================================================


@pytest.fixture
def sample_product() -> dict[str, Any]:
    """Provide sample product data for tests."""
    return {
        "id": 1,
        "name": "iPhone 15",
        "description": "Apple smartphone with A17 chip",
        "price": 799.99,
    }


@pytest.fixture
def sample_products() -> list[dict[str, Any]]:
    """Provide multiple sample products for tests."""
    return [
        {
            "id": 1,
            "name": "iPhone 15",
            "description": "Apple smartphone with A17 chip",
            "price": 799.99,
        },
        {
            "id": 2,
            "name": "Samsung Galaxy S24",
            "description": "Android flagship with Snapdragon 8 Gen 3",
            "price": 899.99,
        },
        {
            "id": 3,
            "name": "Google Pixel 8",
            "description": "Google phone with Tensor G3 processor",
            "price": 699.99,
        },
    ]
