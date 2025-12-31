"""Unit tests for Elasticsearch client wrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from elasticsearch import AsyncElasticsearch
from elasticsearch import ConnectionError as ESConnectionError

from src.config.settings import Settings


class TestElasticsearchClient:
    """Tests for ElasticsearchClient wrapper."""

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
        mock.info = AsyncMock(return_value={"version": {"number": "8.12.0"}})
        mock.ping = AsyncMock(return_value=True)
        mock.close = AsyncMock()
        return mock

    def test_client_initialization(self, mock_settings: Settings) -> None:
        """Test that client initializes with correct settings."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        assert client.settings == mock_settings
        assert client._client is None  # Lazy initialization

    @pytest.mark.asyncio
    async def test_get_client_creates_connection(self, mock_settings: Settings) -> None:
        """Test that get_client creates AsyncElasticsearch instance."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        with patch("src.elastic.client.AsyncElasticsearch") as mock_es:
            mock_instance = MagicMock(spec=AsyncElasticsearch)
            mock_es.return_value = mock_instance

            result = await client.get_client()

            mock_es.assert_called_once_with(
                hosts=[mock_settings.elasticsearch_url],
                request_timeout=mock_settings.elasticsearch_timeout,
            )
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_get_client_returns_cached_connection(
        self, mock_settings: Settings
    ) -> None:
        """Test that get_client returns cached client on subsequent calls."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        with patch("src.elastic.client.AsyncElasticsearch") as mock_es:
            mock_instance = MagicMock(spec=AsyncElasticsearch)
            mock_es.return_value = mock_instance

            result1 = await client.get_client()
            result2 = await client.get_client()

            # Should only create client once
            mock_es.assert_called_once()
            assert result1 == result2

    @pytest.mark.asyncio
    async def test_ping_success(
        self, mock_settings: Settings, mock_es_client: MagicMock
    ) -> None:
        """Test successful ping returns True."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)
        client._client = mock_es_client

        result = await client.ping()

        assert result is True
        mock_es_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_failure(
        self, mock_settings: Settings, mock_es_client: MagicMock
    ) -> None:
        """Test ping returns False when connection fails."""
        from src.elastic.client import ElasticsearchClient

        mock_es_client.ping = AsyncMock(return_value=False)

        client = ElasticsearchClient(mock_settings)
        client._client = mock_es_client

        result = await client.ping()

        assert result is False

    @pytest.mark.asyncio
    async def test_ping_handles_connection_error(
        self, mock_settings: Settings, mock_es_client: MagicMock
    ) -> None:
        """Test ping returns False on connection error."""
        from src.elastic.client import ElasticsearchClient

        mock_es_client.ping = AsyncMock(
            side_effect=ESConnectionError("Connection failed")
        )

        client = ElasticsearchClient(mock_settings)
        client._client = mock_es_client

        result = await client.ping()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_cluster_info(
        self, mock_settings: Settings, mock_es_client: MagicMock
    ) -> None:
        """Test getting cluster info."""
        from src.elastic.client import ElasticsearchClient

        expected_info = {
            "name": "test-node",
            "cluster_name": "test-cluster",
            "version": {"number": "8.12.0"},
        }
        mock_es_client.info = AsyncMock(return_value=expected_info)

        client = ElasticsearchClient(mock_settings)
        client._client = mock_es_client

        result = await client.get_cluster_info()

        assert result == expected_info
        mock_es_client.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_connection(
        self, mock_settings: Settings, mock_es_client: MagicMock
    ) -> None:
        """Test closing the connection."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)
        client._client = mock_es_client

        await client.close()

        mock_es_client.close.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self, mock_settings: Settings) -> None:
        """Test close does nothing when not connected."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        # Should not raise
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_returns_status(
        self, mock_settings: Settings, mock_es_client: MagicMock
    ) -> None:
        """Test health check returns cluster health status."""
        from src.elastic.client import ElasticsearchClient

        mock_es_client.cluster = MagicMock()
        mock_es_client.cluster.health = AsyncMock(
            return_value={"status": "green", "number_of_nodes": 1}
        )

        client = ElasticsearchClient(mock_settings)
        client._client = mock_es_client

        result = await client.health_check()

        assert result["status"] == "green"
        assert result["number_of_nodes"] == 1

    @pytest.mark.asyncio
    async def test_health_check_handles_error(
        self, mock_settings: Settings, mock_es_client: MagicMock
    ) -> None:
        """Test health check returns error status on failure."""
        from src.elastic.client import ElasticsearchClient

        mock_es_client.cluster = MagicMock()
        mock_es_client.cluster.health = AsyncMock(
            side_effect=ESConnectionError("Connection failed")
        )

        client = ElasticsearchClient(mock_settings)
        client._client = mock_es_client

        result = await client.health_check()

        assert result["status"] == "unavailable"
        assert "error" in result


class TestGetElasticsearchClient:
    """Tests for get_elasticsearch_client factory function."""

    def test_get_client_returns_singleton(self) -> None:
        """Test that get_elasticsearch_client returns singleton."""
        from src.elastic.client import get_elasticsearch_client

        client1 = get_elasticsearch_client()
        client2 = get_elasticsearch_client()

        assert client1 is client2

    def test_get_client_uses_settings(self) -> None:
        """Test that get_elasticsearch_client uses application settings."""
        from src.elastic.client import get_elasticsearch_client

        client = get_elasticsearch_client()

        assert client.settings.elasticsearch_url is not None
