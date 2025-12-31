"""Unit tests for indexing service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config.settings import Settings
from src.models.product import Product


class TestIndexingService:
    """Tests for IndexingService."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Provide test settings."""
        return Settings(
            elasticsearch_url="http://localhost:9200",
            elasticsearch_index="test_products",
        )

    @pytest.fixture
    def mock_es_client(self) -> MagicMock:
        """Provide mock Elasticsearch client."""
        mock = MagicMock()
        mock.index = AsyncMock()
        mock.delete = AsyncMock()
        mock.get = AsyncMock()
        mock.exists = AsyncMock()
        return mock

    @pytest.fixture
    def mock_elastic_client(
        self, mock_settings: Settings, mock_es_client: MagicMock
    ) -> MagicMock:
        """Provide mock ElasticsearchClient."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)
        client._client = mock_es_client
        return client

    @pytest.fixture
    def sample_product(self) -> Product:
        """Provide sample product."""
        return Product(
            id="1",
            name="iPhone 15",
            description="Apple smartphone with A17 chip",
            price=799.99,
            category="Electronics",
        )

    def test_indexing_service_initialization(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test IndexingService initializes correctly."""
        from src.services.indexing import IndexingService

        service = IndexingService(mock_elastic_client, mock_settings)

        assert service.client == mock_elastic_client
        assert service.index_name == mock_settings.elasticsearch_index

    @pytest.mark.asyncio
    async def test_index_single_product(
        self,
        mock_elastic_client: MagicMock,
        mock_settings: Settings,
        sample_product: Product,
    ) -> None:
        """Test indexing a single product."""
        from src.services.indexing import IndexingService

        mock_elastic_client._client.index = AsyncMock(
            return_value={"result": "created", "_id": "1"}
        )

        service = IndexingService(mock_elastic_client, mock_settings)

        result = await service.index_product(sample_product)

        assert result["result"] == "created"
        mock_elastic_client._client.index.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_product_with_id(
        self,
        mock_elastic_client: MagicMock,
        mock_settings: Settings,
        sample_product: Product,
    ) -> None:
        """Test that product ID is used as document ID."""
        from src.services.indexing import IndexingService

        mock_elastic_client._client.index = AsyncMock(
            return_value={"result": "created", "_id": "1"}
        )

        service = IndexingService(mock_elastic_client, mock_settings)

        await service.index_product(sample_product)

        call_kwargs = mock_elastic_client._client.index.call_args.kwargs
        assert call_kwargs["id"] == "1"
        assert call_kwargs["index"] == mock_settings.elasticsearch_index

    @pytest.mark.asyncio
    async def test_index_product_document_body(
        self,
        mock_elastic_client: MagicMock,
        mock_settings: Settings,
        sample_product: Product,
    ) -> None:
        """Test that product data is indexed correctly."""
        from src.services.indexing import IndexingService

        mock_elastic_client._client.index = AsyncMock(
            return_value={"result": "created", "_id": "1"}
        )

        service = IndexingService(mock_elastic_client, mock_settings)

        await service.index_product(sample_product)

        call_kwargs = mock_elastic_client._client.index.call_args.kwargs
        doc = call_kwargs["document"]
        assert doc["name"] == "iPhone 15"
        assert doc["description"] == "Apple smartphone with A17 chip"
        assert doc["price"] == 799.99
        assert doc["category"] == "Electronics"

    @pytest.mark.asyncio
    async def test_update_product(
        self,
        mock_elastic_client: MagicMock,
        mock_settings: Settings,
        sample_product: Product,
    ) -> None:
        """Test updating an existing product."""
        from src.services.indexing import IndexingService

        mock_elastic_client._client.index = AsyncMock(
            return_value={"result": "updated", "_id": "1"}
        )

        service = IndexingService(mock_elastic_client, mock_settings)

        result = await service.index_product(sample_product)

        # index with same ID updates the document
        assert result["result"] in ("created", "updated")

    @pytest.mark.asyncio
    async def test_delete_product(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test deleting a product."""
        from src.services.indexing import IndexingService

        mock_elastic_client._client.delete = AsyncMock(
            return_value={"result": "deleted", "_id": "1"}
        )

        service = IndexingService(mock_elastic_client, mock_settings)

        result = await service.delete_product("1")

        assert result["result"] == "deleted"
        mock_elastic_client._client.delete.assert_called_once_with(
            index=mock_settings.elasticsearch_index, id="1"
        )

    @pytest.mark.asyncio
    async def test_delete_nonexistent_product(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test deleting a product that doesn't exist."""
        from elasticsearch import NotFoundError as ESNotFoundError

        from src.services.indexing import IndexingService

        mock_elastic_client._client.delete = AsyncMock(
            side_effect=ESNotFoundError(
                message="not_found",
                meta=MagicMock(),
                body={"result": "not_found"},
            )
        )

        service = IndexingService(mock_elastic_client, mock_settings)

        result = await service.delete_product("999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_product(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test getting a product by ID."""
        from src.services.indexing import IndexingService

        mock_elastic_client._client.get = AsyncMock(
            return_value={
                "_id": "1",
                "_source": {
                    "name": "iPhone 15",
                    "description": "Apple smartphone",
                    "price": 799.99,
                    "category": "Electronics",
                },
            }
        )

        service = IndexingService(mock_elastic_client, mock_settings)

        result = await service.get_product("1")

        assert result is not None
        assert result.id == "1"
        assert result.name == "iPhone 15"

    @pytest.mark.asyncio
    async def test_get_nonexistent_product(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test getting a product that doesn't exist."""
        from elasticsearch import NotFoundError as ESNotFoundError

        from src.services.indexing import IndexingService

        mock_elastic_client._client.get = AsyncMock(
            side_effect=ESNotFoundError(
                message="not_found",
                meta=MagicMock(),
                body={"found": False},
            )
        )

        service = IndexingService(mock_elastic_client, mock_settings)

        result = await service.get_product("999")

        assert result is None

    @pytest.mark.asyncio
    async def test_product_exists(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test checking if product exists."""
        from src.services.indexing import IndexingService

        mock_elastic_client._client.exists = AsyncMock(return_value=True)

        service = IndexingService(mock_elastic_client, mock_settings)

        result = await service.product_exists("1")

        assert result is True
        mock_elastic_client._client.exists.assert_called_once_with(
            index=mock_settings.elasticsearch_index, id="1"
        )

    @pytest.mark.asyncio
    async def test_product_not_exists(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test checking if product doesn't exist."""
        from src.services.indexing import IndexingService

        mock_elastic_client._client.exists = AsyncMock(return_value=False)

        service = IndexingService(mock_elastic_client, mock_settings)

        result = await service.product_exists("999")

        assert result is False


class TestBulkIndexing:
    """Tests for bulk indexing operations."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Provide test settings."""
        return Settings(
            elasticsearch_url="http://localhost:9200",
            elasticsearch_index="test_products",
        )

    @pytest.fixture
    def mock_es_client(self) -> MagicMock:
        """Provide mock Elasticsearch client."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_elastic_client(
        self, mock_settings: Settings, mock_es_client: MagicMock
    ) -> MagicMock:
        """Provide mock ElasticsearchClient."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)
        client._client = mock_es_client
        return client

    @pytest.fixture
    def sample_products(self) -> list[Product]:
        """Provide sample products for bulk indexing."""
        return [
            Product(
                id="1",
                name="iPhone 15",
                description="Apple smartphone with A17 chip",
                price=799.99,
                category="Electronics",
            ),
            Product(
                id="2",
                name="Samsung Galaxy S24",
                description="Android flagship phone",
                price=899.99,
                category="Electronics",
            ),
            Product(
                id="3",
                name="Google Pixel 8",
                description="Google phone with Tensor chip",
                price=699.99,
                category="Electronics",
            ),
        ]

    @pytest.mark.asyncio
    async def test_bulk_index_products(
        self,
        mock_elastic_client: MagicMock,
        mock_settings: Settings,
        sample_products: list[Product],
    ) -> None:
        """Test bulk indexing multiple products."""
        from unittest.mock import patch

        from src.services.indexing import IndexingService

        with patch("src.services.indexing.async_bulk") as mock_bulk:
            mock_bulk.return_value = (3, [])  # (success_count, errors)

            service = IndexingService(mock_elastic_client, mock_settings)

            result = await service.bulk_index_products(sample_products)

            assert result.success_count == 3
            assert result.error_count == 0
            assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_bulk_index_empty_list(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test bulk indexing with empty list."""
        from src.services.indexing import IndexingService

        service = IndexingService(mock_elastic_client, mock_settings)

        result = await service.bulk_index_products([])

        assert result.success_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_bulk_index_with_errors(
        self,
        mock_elastic_client: MagicMock,
        mock_settings: Settings,
        sample_products: list[Product],
    ) -> None:
        """Test bulk indexing with some failures."""
        from unittest.mock import patch

        from src.services.indexing import IndexingService

        errors = [
            {
                "index": {
                    "_id": "2",
                    "error": {"type": "mapper_parsing_exception"},
                }
            }
        ]

        with patch("src.services.indexing.async_bulk") as mock_bulk:
            mock_bulk.return_value = (2, errors)

            service = IndexingService(mock_elastic_client, mock_settings)

            result = await service.bulk_index_products(sample_products)

            assert result.success_count == 2
            assert result.error_count == 1
            assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_bulk_index_generates_actions(
        self,
        mock_elastic_client: MagicMock,
        mock_settings: Settings,
        sample_products: list[Product],
    ) -> None:
        """Test that bulk index generates correct actions."""
        from unittest.mock import patch

        from src.services.indexing import IndexingService

        captured_actions: list = []

        async def capture_bulk(
            client: MagicMock, actions: list, **kwargs: dict
        ) -> tuple:
            captured_actions.extend(list(actions))
            return (len(captured_actions), [])

        with patch("src.services.indexing.async_bulk", side_effect=capture_bulk):
            service = IndexingService(mock_elastic_client, mock_settings)

            await service.bulk_index_products(sample_products)

            assert len(captured_actions) == 3
            assert captured_actions[0]["_index"] == mock_settings.elasticsearch_index
            assert captured_actions[0]["_id"] == "1"
            assert captured_actions[0]["_source"]["name"] == "iPhone 15"


class TestBulkDeleteProducts:
    """Tests for bulk delete operations."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Provide test settings."""
        return Settings(
            elasticsearch_url="http://localhost:9200",
            elasticsearch_index="test_products",
        )

    @pytest.fixture
    def mock_elastic_client(self, mock_settings: Settings) -> MagicMock:
        """Provide mock ElasticsearchClient."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)
        client._client = MagicMock()
        return client

    @pytest.mark.asyncio
    async def test_bulk_delete_products(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test bulk deleting multiple products."""
        from unittest.mock import patch

        from src.services.indexing import IndexingService

        with patch("src.services.indexing.async_bulk") as mock_bulk:
            mock_bulk.return_value = (3, [])

            service = IndexingService(mock_elastic_client, mock_settings)

            result = await service.bulk_delete_products(["1", "2", "3"])

            assert result.success_count == 3
            assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_empty_list(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test bulk delete with empty list."""
        from src.services.indexing import IndexingService

        service = IndexingService(mock_elastic_client, mock_settings)

        result = await service.bulk_delete_products([])

        assert result.success_count == 0
        assert result.error_count == 0


class TestGetIndexingService:
    """Tests for get_indexing_service factory."""

    def test_get_indexing_service_returns_instance(self) -> None:
        """Test factory returns IndexingService instance."""
        from src.services.indexing import get_indexing_service

        service = get_indexing_service()

        assert service is not None
        assert service.index_name is not None
