"""Integration tests for health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestHealthEndpoint:
    """Test suite for health check functionality."""

    async def test_health_check_returns_200(
        self, async_client: AsyncClient
    ) -> None:
        """Test that health endpoint returns 200 OK."""
        response = await async_client.get("/health")

        assert response.status_code == 200

    async def test_health_check_response_format(
        self, async_client: AsyncClient
    ) -> None:
        """Test that health endpoint returns correct format."""
        response = await async_client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data

    async def test_health_check_includes_version(
        self, async_client: AsyncClient
    ) -> None:
        """Test that health endpoint includes version."""
        response = await async_client.get("/health")
        data = response.json()

        assert data["version"] == "0.1.0"
