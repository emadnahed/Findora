"""Integration tests for health check endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestHealthEndpoint:
    """Test suite for health check functionality."""

    async def test_health_check_returns_200(self, async_client: AsyncClient) -> None:
        """Test that health endpoint returns 200 OK."""
        with patch("src.main.get_elasticsearch_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.health_check = AsyncMock(
                return_value={"status": "green", "number_of_nodes": 1}
            )
            mock_get_client.return_value = mock_client

            response = await async_client.get("/health")

            assert response.status_code == 200

    async def test_health_check_response_format(
        self, async_client: AsyncClient
    ) -> None:
        """Test that health endpoint returns correct format."""
        with patch("src.main.get_elasticsearch_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.health_check = AsyncMock(
                return_value={"status": "green", "number_of_nodes": 1}
            )
            mock_get_client.return_value = mock_client

            response = await async_client.get("/health")
            data = response.json()

            assert "status" in data
            assert data["status"] == "healthy"
            assert "version" in data

    async def test_health_check_includes_version(
        self, async_client: AsyncClient
    ) -> None:
        """Test that health endpoint includes version."""
        with patch("src.main.get_elasticsearch_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.health_check = AsyncMock(
                return_value={"status": "green", "number_of_nodes": 1}
            )
            mock_get_client.return_value = mock_client

            response = await async_client.get("/health")
            data = response.json()

            assert data["version"] == "0.1.0"

    async def test_health_check_includes_elasticsearch_status(
        self, async_client: AsyncClient
    ) -> None:
        """Test that health endpoint includes Elasticsearch status."""
        with patch("src.main.get_elasticsearch_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.health_check = AsyncMock(
                return_value={"status": "green", "number_of_nodes": 1}
            )
            mock_get_client.return_value = mock_client

            response = await async_client.get("/health")
            data = response.json()

            assert "elasticsearch" in data
            assert data["elasticsearch"]["connected"] is True
            assert data["elasticsearch"]["cluster_status"] == "green"

    async def test_health_check_elasticsearch_disconnected(
        self, async_client: AsyncClient
    ) -> None:
        """Test health check when Elasticsearch is unavailable."""
        with patch("src.main.get_elasticsearch_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=False)
            mock_client.health_check = AsyncMock(
                return_value={"status": "unavailable", "error": "Connection failed"}
            )
            mock_get_client.return_value = mock_client

            response = await async_client.get("/health")
            data = response.json()

            # Should still return 200 but with degraded status
            assert response.status_code == 200
            assert data["status"] == "degraded"
            assert data["elasticsearch"]["connected"] is False

    async def test_health_check_elasticsearch_yellow_status(
        self, async_client: AsyncClient
    ) -> None:
        """Test health check with yellow cluster status."""
        with patch("src.main.get_elasticsearch_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.health_check = AsyncMock(
                return_value={"status": "yellow", "number_of_nodes": 1}
            )
            mock_get_client.return_value = mock_client

            response = await async_client.get("/health")
            data = response.json()

            assert response.status_code == 200
            assert data["elasticsearch"]["cluster_status"] == "yellow"
