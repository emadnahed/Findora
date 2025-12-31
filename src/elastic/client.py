"""Elasticsearch client wrapper with connection management."""

import asyncio
from functools import lru_cache
from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch import ConnectionError as ESConnectionError

from src.config.settings import Settings, get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class ElasticsearchClient:
    """Wrapper for AsyncElasticsearch with connection management."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the client with settings.

        Args:
            settings: Application settings containing ES configuration.
        """
        self.settings = settings
        self._client: AsyncElasticsearch | None = None

    async def get_client(self) -> AsyncElasticsearch:
        """Get or create the Elasticsearch client.

        Returns:
            AsyncElasticsearch instance.
        """
        if self._client is None:
            self._client = AsyncElasticsearch(
                hosts=[self.settings.elasticsearch_url],
                request_timeout=self.settings.elasticsearch_timeout,
            )
        return self._client

    async def ping(self) -> bool:
        """Check if Elasticsearch is reachable.

        Returns:
            True if ES responds to ping, False otherwise.
        """
        try:
            client = await self.get_client()
            result = await client.ping()
            logger.debug("elasticsearch_ping", success=result)
            return result
        except ESConnectionError as e:
            logger.warning("elasticsearch_ping_failed", error=str(e))
            return False

    async def get_cluster_info(self) -> dict[str, Any]:
        """Get Elasticsearch cluster information.

        Returns:
            Dictionary containing cluster info.
        """
        client = await self.get_client()
        response = await client.info()
        return dict(response)

    async def health_check(self) -> dict[str, Any]:
        """Get cluster health status.

        Returns:
            Dictionary containing health status or error info.
        """
        try:
            client = await self.get_client()
            response = await client.cluster.health()
            result = dict(response)
            logger.debug(
                "elasticsearch_health_check",
                status=result.get("status"),
                number_of_nodes=result.get("number_of_nodes"),
            )
            return result
        except ESConnectionError as e:
            logger.error("elasticsearch_health_check_failed", error=str(e))
            return {"status": "unavailable", "error": str(e)}

    async def connect_with_retry(
        self, max_retries: int = 5, delay: float = 1.0
    ) -> bool:
        """Connect to Elasticsearch with retry logic.

        Uses exponential backoff between retries.

        Args:
            max_retries: Maximum number of connection attempts.
            delay: Initial delay between retries in seconds.

        Returns:
            True if connection successful, False otherwise.
        """
        current_delay = delay

        for attempt in range(max_retries):
            try:
                client = await self.get_client()
                if await client.ping():
                    logger.info(
                        "elasticsearch_connected",
                        attempt=attempt + 1,
                        url=self.settings.elasticsearch_url,
                    )
                    return True
            except ESConnectionError:
                pass

            logger.warning(
                "elasticsearch_connection_retry",
                attempt=attempt + 1,
                max_retries=max_retries,
                next_delay_seconds=current_delay,
            )

            # Wait before next attempt (except on last attempt)
            if attempt < max_retries - 1:
                await asyncio.sleep(current_delay)
                current_delay *= 2  # Exponential backoff

        # All retries failed - clean up
        logger.error(
            "elasticsearch_connection_failed",
            max_retries=max_retries,
            url=self.settings.elasticsearch_url,
        )
        await self.close()
        return False

    async def close(self) -> None:
        """Close the Elasticsearch connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None


@lru_cache
def get_elasticsearch_client() -> ElasticsearchClient:
    """Get a singleton ElasticsearchClient instance.

    Returns:
        Cached ElasticsearchClient instance.
    """
    return ElasticsearchClient(get_settings())


async def wait_for_elasticsearch(max_retries: int = 5, delay: float = 1.0) -> bool:
    """Wait for Elasticsearch to become available.

    Convenience function that uses the singleton client.

    Args:
        max_retries: Maximum number of connection attempts.
        delay: Initial delay between retries in seconds.

    Returns:
        True if connection successful, False otherwise.
    """
    client = get_elasticsearch_client()
    return await client.connect_with_retry(max_retries=max_retries, delay=delay)
