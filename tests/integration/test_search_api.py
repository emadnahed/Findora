"""Integration tests for search API endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.models.product import SearchResponse, SearchResult


@pytest.mark.integration
class TestSearchEndpoint:
    """Test suite for search API functionality."""

    @pytest.fixture
    def mock_search_response(self) -> SearchResponse:
        """Provide mock search response."""
        return SearchResponse(
            query="iphone",
            total=2,
            page=1,
            size=10,
            results=[
                SearchResult(
                    id="1",
                    name="iPhone 15",
                    description="Apple smartphone with A17 chip",
                    price=799.99,
                    score=2.5,
                    highlights={"name": ["<em>iPhone</em> 15"]},
                ),
                SearchResult(
                    id="2",
                    name="iPhone 14",
                    description="Apple smartphone with A16 chip",
                    price=699.99,
                    score=2.0,
                ),
            ],
            took_ms=10,
        )

    async def test_search_returns_200(
        self, async_client: AsyncClient, mock_search_response: SearchResponse
    ) -> None:
        """Test that search endpoint returns 200 OK."""
        with patch("src.api.routes.search.get_search_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=mock_search_response)
            mock_service.return_value = mock_instance

            response = await async_client.get("/api/v1/search", params={"q": "iphone"})

            assert response.status_code == 200

    async def test_search_response_format(
        self, async_client: AsyncClient, mock_search_response: SearchResponse
    ) -> None:
        """Test that search endpoint returns correct format."""
        with patch("src.api.routes.search.get_search_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=mock_search_response)
            mock_service.return_value = mock_instance

            response = await async_client.get("/api/v1/search", params={"q": "iphone"})
            data = response.json()

            assert "query" in data
            assert "total" in data
            assert "results" in data
            assert "page" in data
            assert "size" in data

    async def test_search_returns_results(
        self, async_client: AsyncClient, mock_search_response: SearchResponse
    ) -> None:
        """Test that search endpoint returns results."""
        with patch("src.api.routes.search.get_search_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=mock_search_response)
            mock_service.return_value = mock_instance

            response = await async_client.get("/api/v1/search", params={"q": "iphone"})
            data = response.json()

            assert data["total"] == 2
            assert len(data["results"]) == 2
            assert data["results"][0]["name"] == "iPhone 15"

    async def test_search_includes_scores(
        self, async_client: AsyncClient, mock_search_response: SearchResponse
    ) -> None:
        """Test that search results include relevance scores."""
        with patch("src.api.routes.search.get_search_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=mock_search_response)
            mock_service.return_value = mock_instance

            response = await async_client.get("/api/v1/search", params={"q": "iphone"})
            data = response.json()

            assert data["results"][0]["score"] == 2.5
            assert data["results"][1]["score"] == 2.0

    async def test_search_includes_highlights(
        self, async_client: AsyncClient, mock_search_response: SearchResponse
    ) -> None:
        """Test that search results include highlights."""
        with patch("src.api.routes.search.get_search_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=mock_search_response)
            mock_service.return_value = mock_instance

            response = await async_client.get("/api/v1/search", params={"q": "iphone"})
            data = response.json()

            assert data["results"][0]["highlights"] is not None
            assert "name" in data["results"][0]["highlights"]

    async def test_search_missing_query_returns_422(
        self, async_client: AsyncClient
    ) -> None:
        """Test that missing query parameter returns 422."""
        response = await async_client.get("/api/v1/search")

        assert response.status_code == 422

    async def test_search_empty_query_returns_422(
        self, async_client: AsyncClient
    ) -> None:
        """Test that empty query parameter returns 422."""
        response = await async_client.get("/api/v1/search", params={"q": ""})

        assert response.status_code == 422

    async def test_search_with_pagination(
        self, async_client: AsyncClient, mock_search_response: SearchResponse
    ) -> None:
        """Test search with pagination parameters."""
        with patch("src.api.routes.search.get_search_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=mock_search_response)
            mock_service.return_value = mock_instance

            response = await async_client.get(
                "/api/v1/search", params={"q": "phone", "page": 2, "size": 20}
            )

            assert response.status_code == 200
            # Verify search was called with pagination
            mock_instance.search.assert_called_once()

    async def test_search_with_fuzzy_disabled(
        self, async_client: AsyncClient, mock_search_response: SearchResponse
    ) -> None:
        """Test search with fuzzy matching disabled."""
        with patch("src.api.routes.search.get_search_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=mock_search_response)
            mock_service.return_value = mock_instance

            response = await async_client.get(
                "/api/v1/search", params={"q": "iphone", "fuzzy": "false"}
            )

            assert response.status_code == 200

    async def test_search_with_price_filters(
        self, async_client: AsyncClient, mock_search_response: SearchResponse
    ) -> None:
        """Test search with price range filters."""
        with patch("src.api.routes.search.get_search_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=mock_search_response)
            mock_service.return_value = mock_instance

            response = await async_client.get(
                "/api/v1/search",
                params={"q": "phone", "min_price": 500, "max_price": 1000},
            )

            assert response.status_code == 200

    async def test_search_with_category_filter(
        self, async_client: AsyncClient, mock_search_response: SearchResponse
    ) -> None:
        """Test search with category filter."""
        with patch("src.api.routes.search.get_search_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=mock_search_response)
            mock_service.return_value = mock_instance

            response = await async_client.get(
                "/api/v1/search", params={"q": "phone", "category": "Electronics"}
            )

            assert response.status_code == 200

    async def test_search_invalid_page_returns_422(
        self, async_client: AsyncClient
    ) -> None:
        """Test that invalid page parameter returns 422."""
        response = await async_client.get(
            "/api/v1/search", params={"q": "phone", "page": 0}
        )

        assert response.status_code == 422

    async def test_search_invalid_size_returns_422(
        self, async_client: AsyncClient
    ) -> None:
        """Test that invalid size parameter returns 422."""
        response = await async_client.get(
            "/api/v1/search", params={"q": "phone", "size": 200}
        )

        assert response.status_code == 422

    async def test_search_includes_took_time(
        self, async_client: AsyncClient, mock_search_response: SearchResponse
    ) -> None:
        """Test that search response includes query time."""
        with patch("src.api.routes.search.get_search_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.search = AsyncMock(return_value=mock_search_response)
            mock_service.return_value = mock_instance

            response = await async_client.get("/api/v1/search", params={"q": "iphone"})
            data = response.json()

            assert "took_ms" in data
            assert data["took_ms"] == 10
