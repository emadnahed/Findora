"""Integration tests for indexing API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.models.product import BulkOperationResult, Product


@pytest.mark.integration
class TestProductsEndpoint:
    """Test suite for products API functionality."""

    @pytest.fixture
    def sample_product_data(self) -> dict:
        """Provide sample product data for creating."""
        return {
            "name": "iPhone 15",
            "description": "Apple smartphone with A17 chip",
            "price": 799.99,
            "category": "Electronics",
        }

    @pytest.fixture
    def mock_indexed_product(self) -> Product:
        """Provide mock indexed product."""
        return Product(
            id="1",
            name="iPhone 15",
            description="Apple smartphone with A17 chip",
            price=799.99,
            category="Electronics",
        )

    async def test_create_product_returns_201(
        self, async_client: AsyncClient, sample_product_data: dict
    ) -> None:
        """Test that creating a product returns 201."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.index_product = AsyncMock(
                return_value={"result": "created", "_id": "1"}
            )
            mock_instance.index_name = "test_products"
            mock_service.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/products", json=sample_product_data
            )

            assert response.status_code == 201

    async def test_create_product_response_format(
        self, async_client: AsyncClient, sample_product_data: dict
    ) -> None:
        """Test that create product returns correct format."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.index_product = AsyncMock(
                return_value={"result": "created", "_id": "abc123"}
            )
            mock_instance.index_name = "test_products"
            mock_service.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/products", json=sample_product_data
            )
            data = response.json()

            assert "id" in data
            assert "result" in data
            assert data["result"] == "created"

    async def test_create_product_invalid_data_returns_422(
        self, async_client: AsyncClient
    ) -> None:
        """Test that invalid product data returns 422."""
        invalid_data = {
            "name": "",  # Empty name
            "description": "Test",
            "price": 100.0,
        }

        response = await async_client.post("/api/v1/products", json=invalid_data)

        assert response.status_code == 422

    async def test_create_product_negative_price_returns_422(
        self, async_client: AsyncClient
    ) -> None:
        """Test that negative price returns 422."""
        invalid_data = {
            "name": "Test Product",
            "description": "Test description",
            "price": -10.0,
        }

        response = await async_client.post("/api/v1/products", json=invalid_data)

        assert response.status_code == 422

    async def test_get_product_returns_200(
        self, async_client: AsyncClient, mock_indexed_product: Product
    ) -> None:
        """Test that getting a product returns 200."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_product = AsyncMock(return_value=mock_indexed_product)
            mock_service.return_value = mock_instance

            response = await async_client.get("/api/v1/products/1")

            assert response.status_code == 200

    async def test_get_product_response_format(
        self, async_client: AsyncClient, mock_indexed_product: Product
    ) -> None:
        """Test that get product returns correct format."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_product = AsyncMock(return_value=mock_indexed_product)
            mock_service.return_value = mock_instance

            response = await async_client.get("/api/v1/products/1")
            data = response.json()

            assert data["id"] == "1"
            assert data["name"] == "iPhone 15"
            assert data["price"] == 799.99

    async def test_get_nonexistent_product_returns_404(
        self, async_client: AsyncClient
    ) -> None:
        """Test that getting nonexistent product returns 404."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_product = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance

            response = await async_client.get("/api/v1/products/999")

            assert response.status_code == 404

    async def test_update_product_returns_200(
        self, async_client: AsyncClient, sample_product_data: dict
    ) -> None:
        """Test that updating a product returns 200."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.index_product = AsyncMock(
                return_value={"result": "updated", "_id": "1"}
            )
            mock_instance.index_name = "test_products"
            mock_service.return_value = mock_instance

            response = await async_client.put(
                "/api/v1/products/1", json=sample_product_data
            )

            assert response.status_code == 200

    async def test_delete_product_returns_204(self, async_client: AsyncClient) -> None:
        """Test that deleting a product returns 204."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.delete_product = AsyncMock(return_value={"result": "deleted"})
            mock_service.return_value = mock_instance

            response = await async_client.delete("/api/v1/products/1")

            assert response.status_code == 204

    async def test_delete_nonexistent_product_returns_404(
        self, async_client: AsyncClient
    ) -> None:
        """Test that deleting nonexistent product returns 404."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.delete_product = AsyncMock(return_value=None)
            mock_service.return_value = mock_instance

            response = await async_client.delete("/api/v1/products/999")

            assert response.status_code == 404


@pytest.mark.integration
class TestBulkEndpoints:
    """Test suite for bulk operations API."""

    @pytest.fixture
    def sample_products_data(self) -> list[dict]:
        """Provide sample products data for bulk operations."""
        return [
            {
                "id": "1",
                "name": "iPhone 15",
                "description": "Apple smartphone",
                "price": 799.99,
            },
            {
                "id": "2",
                "name": "Samsung Galaxy",
                "description": "Android phone",
                "price": 899.99,
            },
        ]

    async def test_bulk_index_returns_200(
        self, async_client: AsyncClient, sample_products_data: list[dict]
    ) -> None:
        """Test that bulk index returns 200."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.bulk_index_products = AsyncMock(
                return_value=BulkOperationResult(
                    success_count=2, error_count=0, errors=[]
                )
            )
            mock_service.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/products/bulk", json=sample_products_data
            )

            assert response.status_code == 200

    async def test_bulk_index_response_format(
        self, async_client: AsyncClient, sample_products_data: list[dict]
    ) -> None:
        """Test that bulk index returns correct format."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.bulk_index_products = AsyncMock(
                return_value=BulkOperationResult(
                    success_count=2, error_count=0, errors=[]
                )
            )
            mock_service.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/products/bulk", json=sample_products_data
            )
            data = response.json()

            assert "success_count" in data
            assert "error_count" in data
            assert data["success_count"] == 2
            assert data["error_count"] == 0

    async def test_bulk_index_with_errors(
        self, async_client: AsyncClient, sample_products_data: list[dict]
    ) -> None:
        """Test bulk index response with some errors."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.bulk_index_products = AsyncMock(
                return_value=BulkOperationResult(
                    success_count=1,
                    error_count=1,
                    errors=[{"id": "2", "error": "mapping error"}],
                )
            )
            mock_service.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/products/bulk", json=sample_products_data
            )
            data = response.json()

            assert data["success_count"] == 1
            assert data["error_count"] == 1
            assert len(data["errors"]) == 1

    async def test_bulk_index_empty_list_returns_200(
        self, async_client: AsyncClient
    ) -> None:
        """Test bulk index with empty list."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.bulk_index_products = AsyncMock(
                return_value=BulkOperationResult(
                    success_count=0, error_count=0, errors=[]
                )
            )
            mock_service.return_value = mock_instance

            response = await async_client.post("/api/v1/products/bulk", json=[])

            assert response.status_code == 200

    async def test_bulk_delete_returns_200(self, async_client: AsyncClient) -> None:
        """Test that bulk delete returns 200."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.bulk_delete_products = AsyncMock(
                return_value=BulkOperationResult(
                    success_count=2, error_count=0, errors=[]
                )
            )
            mock_service.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/products/bulk/delete", json=["1", "2"]
            )

            assert response.status_code == 200

    async def test_bulk_delete_response_format(self, async_client: AsyncClient) -> None:
        """Test that bulk delete returns correct format."""
        with patch("src.api.routes.products.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.bulk_delete_products = AsyncMock(
                return_value=BulkOperationResult(
                    success_count=2, error_count=0, errors=[]
                )
            )
            mock_service.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/products/bulk/delete", json=["1", "2"]
            )
            data = response.json()

            assert data["success_count"] == 2
            assert data["error_count"] == 0
