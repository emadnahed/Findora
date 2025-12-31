"""Unit tests for Elasticsearch index management."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from elasticsearch import AsyncElasticsearch
from elasticsearch import NotFoundError as ESNotFoundError

from src.config.settings import Settings


class TestIndexManager:
    """Tests for IndexManager service."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Provide test settings."""
        return Settings(
            elasticsearch_url="http://localhost:9200",
            elasticsearch_index="test_products",
            elasticsearch_timeout=30,
        )

    @pytest.fixture
    def mock_es_client(self) -> MagicMock:
        """Provide mock Elasticsearch client."""
        mock = MagicMock(spec=AsyncElasticsearch)
        mock.indices = MagicMock()
        mock.indices.exists = AsyncMock(return_value=True)
        mock.indices.create = AsyncMock(return_value={"acknowledged": True})
        mock.indices.delete = AsyncMock(return_value={"acknowledged": True})
        mock.indices.get_mapping = AsyncMock(return_value={})
        mock.indices.put_mapping = AsyncMock(return_value={"acknowledged": True})
        mock.indices.refresh = AsyncMock()
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

    def test_index_manager_initialization(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test IndexManager initializes with client and settings."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)

        assert manager.client == mock_elastic_client
        assert manager.settings == mock_settings
        assert manager.index_name == mock_settings.elasticsearch_index

    @pytest.mark.asyncio
    async def test_index_exists_true(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test index_exists returns True when index exists."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.exists = AsyncMock(return_value=True)

        result = await manager.index_exists()

        assert result is True
        mock_elastic_client._client.indices.exists.assert_called_once_with(
            index=mock_settings.elasticsearch_index
        )

    @pytest.mark.asyncio
    async def test_index_exists_false(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test index_exists returns False when index doesn't exist."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.exists = AsyncMock(return_value=False)

        result = await manager.index_exists()

        assert result is False

    @pytest.mark.asyncio
    async def test_create_index_success(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test successful index creation."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.exists = AsyncMock(return_value=False)
        mock_elastic_client._client.indices.create = AsyncMock(
            return_value={"acknowledged": True, "index": "test_products"}
        )

        result = await manager.create_index()

        assert result["acknowledged"] is True
        mock_elastic_client._client.indices.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_index_with_mappings(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test index creation with custom mappings."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.exists = AsyncMock(return_value=False)

        mappings = {
            "properties": {
                "name": {"type": "text"},
                "description": {"type": "text"},
                "price": {"type": "float"},
            }
        }

        await manager.create_index(mappings=mappings)

        call_kwargs = mock_elastic_client._client.indices.create.call_args.kwargs
        assert "mappings" in call_kwargs
        assert call_kwargs["mappings"] == mappings

    @pytest.mark.asyncio
    async def test_create_index_with_settings(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test index creation with custom settings."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.exists = AsyncMock(return_value=False)

        index_settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }

        await manager.create_index(settings=index_settings)

        call_kwargs = mock_elastic_client._client.indices.create.call_args.kwargs
        assert "settings" in call_kwargs
        assert call_kwargs["settings"] == index_settings

    @pytest.mark.asyncio
    async def test_create_index_already_exists(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test create_index returns None when index already exists."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.exists = AsyncMock(return_value=True)

        result = await manager.create_index()

        assert result is None
        mock_elastic_client._client.indices.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_index_success(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test successful index deletion."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.exists = AsyncMock(return_value=True)
        mock_elastic_client._client.indices.delete = AsyncMock(
            return_value={"acknowledged": True}
        )

        result = await manager.delete_index()

        assert result["acknowledged"] is True
        mock_elastic_client._client.indices.delete.assert_called_once_with(
            index=mock_settings.elasticsearch_index
        )

    @pytest.mark.asyncio
    async def test_delete_index_not_exists(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test delete_index returns None when index doesn't exist."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.exists = AsyncMock(return_value=False)

        result = await manager.delete_index()

        assert result is None
        mock_elastic_client._client.indices.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_mapping(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test getting index mappings."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        expected_mapping = {
            "test_products": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                    }
                }
            }
        }
        mock_elastic_client._client.indices.get_mapping = AsyncMock(
            return_value=expected_mapping
        )

        result = await manager.get_mapping()

        assert result == expected_mapping
        mock_elastic_client._client.indices.get_mapping.assert_called_once_with(
            index=mock_settings.elasticsearch_index
        )

    @pytest.mark.asyncio
    async def test_get_mapping_not_found(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test get_mapping returns None when index doesn't exist."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.get_mapping = AsyncMock(
            side_effect=ESNotFoundError(
                message="index_not_found",
                meta=MagicMock(),
                body={"error": {"type": "index_not_found_exception"}},
            )
        )

        result = await manager.get_mapping()

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_index(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test refreshing index."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)

        await manager.refresh()

        mock_elastic_client._client.indices.refresh.assert_called_once_with(
            index=mock_settings.elasticsearch_index
        )

    @pytest.mark.asyncio
    async def test_ensure_index_creates_if_not_exists(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test ensure_index creates index if it doesn't exist."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.exists = AsyncMock(return_value=False)
        mock_elastic_client._client.indices.create = AsyncMock(
            return_value={"acknowledged": True}
        )

        result = await manager.ensure_index()

        assert result is True
        mock_elastic_client._client.indices.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_index_skips_if_exists(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test ensure_index skips creation if index exists."""
        from src.elastic.index_manager import IndexManager

        manager = IndexManager(mock_elastic_client, mock_settings)
        mock_elastic_client._client.indices.exists = AsyncMock(return_value=True)

        result = await manager.ensure_index()

        assert result is True
        mock_elastic_client._client.indices.create.assert_not_called()


class TestGetIndexManager:
    """Tests for get_index_manager factory function."""

    def test_get_index_manager_returns_instance(self) -> None:
        """Test get_index_manager returns IndexManager instance."""
        from src.elastic.index_manager import get_index_manager

        manager = get_index_manager()

        assert manager is not None
        assert manager.index_name is not None
