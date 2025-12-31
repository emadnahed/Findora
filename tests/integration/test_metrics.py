"""Integration tests for the metrics endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


class TestMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_returns_200(self, client: AsyncClient) -> None:
        """Test that metrics endpoint returns 200."""
        response = await client.get("/metrics")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_returns_plain_text(self, client: AsyncClient) -> None:
        """Test that metrics endpoint returns plain text."""
        response = await client.get("/metrics")
        assert "text/plain" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_metrics_contains_prometheus_format(
        self, client: AsyncClient
    ) -> None:
        """Test that metrics contain Prometheus format."""
        response = await client.get("/metrics")
        content = response.text

        assert "# HELP" in content
        assert "# TYPE" in content
        assert "findora_uptime_seconds" in content
        assert "findora_requests_total" in content

    @pytest.mark.asyncio
    async def test_metrics_contains_search_metrics(self, client: AsyncClient) -> None:
        """Test that metrics contain search-related metrics."""
        response = await client.get("/metrics")
        content = response.text

        assert "findora_search_queries_total" in content
        assert "findora_search_cache_hits_total" in content
        assert "findora_search_cache_hit_rate" in content

    @pytest.mark.asyncio
    async def test_metrics_contains_elasticsearch_metrics(
        self, client: AsyncClient
    ) -> None:
        """Test that metrics contain Elasticsearch metrics."""
        response = await client.get("/metrics")
        content = response.text

        assert "findora_elasticsearch_queries_total" in content
        assert "findora_elasticsearch_errors_total" in content


class TestMetricsJsonEndpoint:
    """Tests for the /metrics/json endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_json_returns_200(self, client: AsyncClient) -> None:
        """Test that JSON metrics endpoint returns 200."""
        response = await client.get("/metrics/json")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_json_returns_json(self, client: AsyncClient) -> None:
        """Test that JSON metrics endpoint returns JSON."""
        response = await client.get("/metrics/json")
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_metrics_json_structure(self, client: AsyncClient) -> None:
        """Test JSON metrics structure."""
        response = await client.get("/metrics/json")
        data = response.json()

        assert "uptime_seconds" in data
        assert "requests" in data
        assert "latency_ms" in data
        assert "search" in data
        assert "elasticsearch" in data

    @pytest.mark.asyncio
    async def test_metrics_json_request_details(self, client: AsyncClient) -> None:
        """Test JSON metrics request details."""
        response = await client.get("/metrics/json")
        data = response.json()

        requests = data["requests"]
        assert "total" in requests
        assert "errors" in requests
        assert "error_rate" in requests
        assert "by_status" in requests
        assert "by_endpoint" in requests

    @pytest.mark.asyncio
    async def test_metrics_json_search_details(self, client: AsyncClient) -> None:
        """Test JSON metrics search details."""
        response = await client.get("/metrics/json")
        data = response.json()

        search = data["search"]
        assert "total_queries" in search
        assert "cache_hits" in search
        assert "cache_misses" in search
        assert "cache_hit_rate" in search


class TestImprovedHealthCheck:
    """Tests for the improved health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_includes_uptime(self, client: AsyncClient) -> None:
        """Test that health check includes uptime."""
        with patch("src.main.get_elasticsearch_client") as mock_es:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_client.health_check.return_value = {"status": "green"}
            mock_es.return_value = mock_client

            response = await client.get("/health")
            data = response.json()

            assert "uptime_seconds" in data

    @pytest.mark.asyncio
    async def test_health_includes_cache_stats(self, client: AsyncClient) -> None:
        """Test that health check includes cache stats when enabled."""
        with patch("src.main.get_elasticsearch_client") as mock_es:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_client.health_check.return_value = {"status": "green"}
            mock_es.return_value = mock_client

            response = await client.get("/health")
            data = response.json()

            # Cache should be included when enabled
            if "cache" in data:
                cache = data["cache"]
                assert "size" in cache
                assert "max_size" in cache
                assert "hit_rate" in cache

    @pytest.mark.asyncio
    async def test_health_elasticsearch_details(self, client: AsyncClient) -> None:
        """Test that health check includes detailed ES info."""
        with patch("src.main.get_elasticsearch_client") as mock_es:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_client.health_check.return_value = {
                "status": "green",
                "number_of_nodes": 3,
            }
            mock_es.return_value = mock_client

            response = await client.get("/health")
            data = response.json()

            es = data["elasticsearch"]
            assert "connected" in es
            assert "cluster_status" in es
            assert "number_of_nodes" in es
