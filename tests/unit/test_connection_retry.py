"""Unit tests for Elasticsearch connection retry logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from elasticsearch import ConnectionError as ESConnectionError

from src.config.settings import Settings


class TestConnectionWithRetry:
    """Tests for connection retry functionality."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Provide test settings with retry configuration."""
        return Settings(
            elasticsearch_url="http://localhost:9200",
            elasticsearch_index="test_products",
            elasticsearch_timeout=30,
        )

    @pytest.mark.asyncio
    async def test_connect_with_retry_success_first_attempt(
        self, mock_settings: Settings
    ) -> None:
        """Test connection succeeds on first attempt."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        with patch("src.elastic.client.AsyncElasticsearch") as mock_es:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(return_value=True)
            mock_es.return_value = mock_instance

            result = await client.connect_with_retry(max_retries=3, delay=0.1)

            assert result is True
            assert mock_instance.ping.call_count == 1

    @pytest.mark.asyncio
    async def test_connect_with_retry_success_after_failures(
        self, mock_settings: Settings
    ) -> None:
        """Test connection succeeds after initial failures."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        with patch("src.elastic.client.AsyncElasticsearch") as mock_es:
            mock_instance = MagicMock()
            # Fail twice, then succeed
            mock_instance.ping = AsyncMock(
                side_effect=[
                    ESConnectionError("Connection refused"),
                    ESConnectionError("Connection refused"),
                    True,
                ]
            )
            mock_es.return_value = mock_instance

            result = await client.connect_with_retry(max_retries=3, delay=0.01)

            assert result is True
            assert mock_instance.ping.call_count == 3

    @pytest.mark.asyncio
    async def test_connect_with_retry_all_attempts_fail(
        self, mock_settings: Settings
    ) -> None:
        """Test connection returns False when all retries fail."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        with patch("src.elastic.client.AsyncElasticsearch") as mock_es:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(
                side_effect=ESConnectionError("Connection refused")
            )
            mock_instance.close = AsyncMock()
            mock_es.return_value = mock_instance

            result = await client.connect_with_retry(max_retries=3, delay=0.01)

            assert result is False
            assert mock_instance.ping.call_count == 3

    @pytest.mark.asyncio
    async def test_connect_with_retry_ping_returns_false(
        self, mock_settings: Settings
    ) -> None:
        """Test connection retries when ping returns False."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        with patch("src.elastic.client.AsyncElasticsearch") as mock_es:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(side_effect=[False, False, True])
            mock_es.return_value = mock_instance

            result = await client.connect_with_retry(max_retries=3, delay=0.01)

            assert result is True
            assert mock_instance.ping.call_count == 3

    @pytest.mark.asyncio
    async def test_connect_with_retry_uses_exponential_backoff(
        self, mock_settings: Settings
    ) -> None:
        """Test that retries use exponential backoff."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        with (
            patch("src.elastic.client.AsyncElasticsearch") as mock_es,
            patch("asyncio.sleep") as mock_sleep,
        ):
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(side_effect=[False, False, True])
            mock_es.return_value = mock_instance

            await client.connect_with_retry(max_retries=3, delay=1.0)

            # Check exponential backoff: 1.0, 2.0 (delay doubles each retry)
            sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
            assert len(sleep_calls) == 2
            assert sleep_calls[0] == 1.0
            assert sleep_calls[1] == 2.0

    @pytest.mark.asyncio
    async def test_connect_with_retry_default_parameters(
        self, mock_settings: Settings
    ) -> None:
        """Test connect_with_retry uses sensible defaults."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        with patch("src.elastic.client.AsyncElasticsearch") as mock_es:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(return_value=True)
            mock_es.return_value = mock_instance

            result = await client.connect_with_retry()

            assert result is True

    @pytest.mark.asyncio
    async def test_connect_with_retry_cleans_up_on_failure(
        self, mock_settings: Settings
    ) -> None:
        """Test that client is cleaned up after all retries fail."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)

        with patch("src.elastic.client.AsyncElasticsearch") as mock_es:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(
                side_effect=ESConnectionError("Connection refused")
            )
            mock_instance.close = AsyncMock()
            mock_es.return_value = mock_instance

            result = await client.connect_with_retry(max_retries=2, delay=0.01)

            assert result is False
            # Client should be closed after failures
            mock_instance.close.assert_called_once()
            assert client._client is None


class TestWaitForElasticsearch:
    """Tests for wait_for_elasticsearch utility function."""

    @pytest.mark.asyncio
    async def test_wait_for_elasticsearch_success(self) -> None:
        """Test wait_for_elasticsearch returns True when ES is available."""
        from src.elastic.client import wait_for_elasticsearch

        with patch("src.elastic.client.get_elasticsearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.connect_with_retry = AsyncMock(return_value=True)
            mock_get_client.return_value = mock_client

            result = await wait_for_elasticsearch()

            assert result is True
            mock_client.connect_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_elasticsearch_failure(self) -> None:
        """Test wait_for_elasticsearch returns False when ES is unavailable."""
        from src.elastic.client import wait_for_elasticsearch

        with patch("src.elastic.client.get_elasticsearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.connect_with_retry = AsyncMock(return_value=False)
            mock_get_client.return_value = mock_client

            result = await wait_for_elasticsearch()

            assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_elasticsearch_custom_retries(self) -> None:
        """Test wait_for_elasticsearch accepts custom retry parameters."""
        from src.elastic.client import wait_for_elasticsearch

        with patch("src.elastic.client.get_elasticsearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.connect_with_retry = AsyncMock(return_value=True)
            mock_get_client.return_value = mock_client

            await wait_for_elasticsearch(max_retries=5, delay=2.0)

            mock_client.connect_with_retry.assert_called_once_with(
                max_retries=5, delay=2.0
            )
