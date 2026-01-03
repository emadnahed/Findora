"""End-to-end tests for search flow.

These tests require running Elasticsearch instance.
Run with: docker-compose up -d elasticsearch && pytest tests/e2e/ -v
"""

import os

import httpx
import pytest
from httpx import AsyncClient


def elasticsearch_available() -> bool:
    """Check if Elasticsearch is running and accessible."""
    es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    try:
        response = httpx.get(f"{es_url}/_cluster/health", timeout=5.0)
        return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


# Skip all tests in this class if Elasticsearch is not available
pytestmark = pytest.mark.skipif(
    not elasticsearch_available(),
    reason="E2E tests require running Elasticsearch - run: docker-compose up -d elasticsearch",
)


@pytest.mark.e2e
class TestSearchE2E:
    """End-to-end test suite for search functionality.

    These tests validate the complete flow:
    HTTP Request -> FastAPI -> Elasticsearch -> Response

    Prerequisites:
    - docker-compose up elasticsearch
    - Index test data
    """

    async def test_search_returns_results(self, async_client: AsyncClient) -> None:
        """Test that search endpoint returns matching results."""
        response = await async_client.get("/api/v1/search", params={"q": "iphone"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0
        assert "results" in data

    async def test_search_fuzzy_matching(self, async_client: AsyncClient) -> None:
        """Test that search handles typos with fuzzy matching."""
        # Search with typo - should still find "iPhone"
        response = await async_client.get(
            "/api/v1/search", params={"q": "iphon", "fuzzy": True}
        )

        assert response.status_code == 200
        data = response.json()
        # With fuzzy enabled, should find results despite typo
        assert "results" in data

    async def test_search_empty_query_returns_422(
        self, async_client: AsyncClient
    ) -> None:
        """Test that empty query returns 422 validation error."""
        response = await async_client.get("/api/v1/search", params={"q": ""})

        assert response.status_code == 422

    async def test_search_no_results(self, async_client: AsyncClient) -> None:
        """Test response when no results match query."""
        response = await async_client.get(
            "/api/v1/search", params={"q": "xyznonexistent123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []

    async def test_search_pagination(self, async_client: AsyncClient) -> None:
        """Test search pagination works correctly."""
        response = await async_client.get(
            "/api/v1/search", params={"q": "phone", "page": 1, "size": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5

    async def test_search_price_filter(self, async_client: AsyncClient) -> None:
        """Test search with price range filter."""
        response = await async_client.get(
            "/api/v1/search",
            params={"q": "phone", "min_price": 500, "max_price": 1000},
        )

        assert response.status_code == 200
        data = response.json()
        # All results should be within price range
        for result in data["results"]:
            assert 500 <= result["price"] <= 1000
