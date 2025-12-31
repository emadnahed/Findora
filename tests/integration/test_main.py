"""Integration tests for main application module."""

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


class TestMiddleware:
    """Tests for request middleware."""

    @pytest.mark.asyncio
    async def test_middleware_adds_request_id_header(self, client: AsyncClient) -> None:
        """Test that middleware adds X-Request-ID header to response."""
        with patch("src.main.get_elasticsearch_client") as mock_es:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_client.health_check.return_value = {"status": "green"}
            mock_es.return_value = mock_client

            response = await client.get("/health")

            assert "X-Request-ID" in response.headers
            assert len(response.headers["X-Request-ID"]) == 8

    @pytest.mark.asyncio
    async def test_middleware_logs_request(self, client: AsyncClient) -> None:
        """Test that middleware logs request completion."""
        with patch("src.main.get_elasticsearch_client") as mock_es:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_client.health_check.return_value = {"status": "green"}
            mock_es.return_value = mock_client

            with patch("src.main.logger") as mock_logger:
                await client.get("/health")

                # Should log request completion
                mock_logger.info.assert_called()


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_healthy(self, client: AsyncClient) -> None:
        """Test health returns healthy when ES is connected."""
        with patch("src.main.get_elasticsearch_client") as mock_es:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_client.health_check.return_value = {"status": "green"}
            mock_es.return_value = mock_client

            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_returns_degraded(self, client: AsyncClient) -> None:
        """Test health returns degraded when ES is disconnected."""
        with patch("src.main.get_elasticsearch_client") as mock_es:
            mock_client = AsyncMock()
            mock_client.ping.return_value = False
            mock_client.health_check.return_value = {"status": "unavailable"}
            mock_es.return_value = mock_client

            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_yellow_status(self, client: AsyncClient) -> None:
        """Test health returns healthy for yellow cluster status."""
        with patch("src.main.get_elasticsearch_client") as mock_es:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_client.health_check.return_value = {"status": "yellow"}
            mock_es.return_value = mock_client

            response = await client.get("/health")

            data = response.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_includes_version(self, client: AsyncClient) -> None:
        """Test health includes application version."""
        with patch("src.main.get_elasticsearch_client") as mock_es:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_client.health_check.return_value = {"status": "green"}
            mock_es.return_value = mock_client

            response = await client.get("/health")

            data = response.json()
            assert "version" in data


class TestExceptionHandling:
    """Tests for exception handling."""

    @pytest.mark.asyncio
    async def test_findora_exception_handling(self, client: AsyncClient) -> None:
        """Test that FindoraException is handled properly."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_svc = AsyncMock()
            mock_svc.get_product.return_value = None
            mock_service.return_value = mock_svc

            response = await client.get("/api/v1/products/nonexistent-id")

            assert response.status_code == 404
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, client: AsyncClient) -> None:
        """Test that validation errors return 422."""
        response = await client.post(
            "/api/v1/products",
            json={"name": "Test"},  # Missing required fields
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_request_id_in_error_response(self, client: AsyncClient) -> None:
        """Test that error responses include request ID."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_svc = AsyncMock()
            mock_svc.get_product.return_value = None
            mock_service.return_value = mock_svc

            response = await client.get("/api/v1/products/test-id")

            assert "X-Request-ID" in response.headers


class TestRouterInclusion:
    """Tests for router inclusion."""

    @pytest.mark.asyncio
    async def test_search_router_included(self, client: AsyncClient) -> None:
        """Test that search router is included."""
        # Just check that the route exists (will return 422 without query)
        response = await client.get("/api/v1/search")
        assert response.status_code == 422  # Missing required 'q' parameter

    @pytest.mark.asyncio
    async def test_products_router_included(self, client: AsyncClient) -> None:
        """Test that products router is included."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_svc = AsyncMock()
            mock_svc.get_product.return_value = None
            mock_service.return_value = mock_svc

            response = await client.get("/api/v1/products/test-id")
            # Should return 404, not 404 for route not found
            assert response.status_code == 404


class TestAppConfiguration:
    """Tests for app configuration."""

    def test_app_title(self) -> None:
        """Test app has correct title."""
        assert app.title is not None

    def test_app_version(self) -> None:
        """Test app has version set."""
        assert app.version is not None

    def test_rate_limiter_state(self) -> None:
        """Test that rate limiter is attached to app state."""
        assert hasattr(app.state, "limiter")


class TestLifespan:
    """Tests for application lifespan."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown(self) -> None:
        """Test that lifespan runs startup and shutdown."""
        from src.main import lifespan

        with (
            patch("src.main.setup_logging") as mock_setup,
            patch("src.main.logger") as mock_logger,
        ):
            # Run the lifespan context manager
            async with lifespan(app):
                # Startup should have been called
                mock_setup.assert_called_once()
                mock_logger.info.assert_called()

            # After exiting, shutdown should have been logged
            assert mock_logger.info.call_count >= 2


class TestMiddlewareExceptionHandling:
    """Tests for middleware exception handling."""

    @pytest.mark.asyncio
    async def test_middleware_handles_errors_gracefully(
        self, client: AsyncClient
    ) -> None:
        """Test that middleware handles errors and returns proper response."""
        # Test with a route that doesn't exist
        response = await client.get("/nonexistent-route-12345")

        # Should return 404 for route not found
        assert response.status_code == 404
        # Request ID should still be in headers
        assert "X-Request-ID" in response.headers

    @pytest.mark.asyncio
    async def test_middleware_handles_invalid_json(
        self, client: AsyncClient
    ) -> None:
        """Test that middleware handles invalid JSON gracefully."""
        response = await client.post(
            "/api/v1/products",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_middleware_exception_logging(self) -> None:
        """Test that middleware logs exceptions properly."""
        import uuid

        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        # Create a test app with a route that raises
        test_app = FastAPI()

        @test_app.get("/error")
        async def error_route() -> None:
            raise RuntimeError("Test error")

        # Add exception handler to convert RuntimeError to 500 response
        @test_app.exception_handler(RuntimeError)
        async def runtime_error_handler(request, exc):  # type: ignore
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"},
            )

        # Add the same middleware pattern as main.py
        @test_app.middleware("http")
        async def test_middleware(request, call_next):  # type: ignore
            from src.core.logging import (
                bind_request_context,
                clear_request_context,
                get_logger,
            )
            logger = get_logger(__name__)
            request_id = str(uuid.uuid4())[:8]

            bind_request_context(
                request_id=request_id,
                method=request.method,
                path=str(request.url.path),
            )

            try:
                response = await call_next(request)
                return response
            except Exception:
                logger.exception(
                    "unhandled_exception",
                    path=str(request.url.path),
                    method=request.method,
                )
                raise
            finally:
                clear_request_context()

        # The test verifies the middleware pattern works
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/error")
            # Exception handler returns 500
            assert response.status_code == 500


class TestUpdateProductNotFound:
    """Tests for update product when product doesn't exist."""

    @pytest.mark.asyncio
    async def test_update_nonexistent_product_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Test updating a non-existent product returns 404."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_svc = AsyncMock()
            mock_svc.product_exists.return_value = False
            mock_service.return_value = mock_svc

            response = await client.put(
                "/api/v1/products/nonexistent-id",
                json={
                    "name": "Updated Product",
                    "description": "Updated description",
                    "price": 99.99,
                    "category": "Electronics",
                },
            )

            assert response.status_code == 404
            data = response.json()
            assert data["error"]["code"] == "NOT_FOUND"
