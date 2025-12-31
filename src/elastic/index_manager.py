"""Elasticsearch index management service."""

from functools import lru_cache
from typing import Any

from elasticsearch import NotFoundError as ESNotFoundError

from src.config.settings import Settings, get_settings
from src.elastic.client import ElasticsearchClient, get_elasticsearch_client


class IndexManager:
    """Manages Elasticsearch index operations."""

    def __init__(self, client: ElasticsearchClient, settings: Settings) -> None:
        """Initialize the index manager.

        Args:
            client: ElasticsearchClient instance.
            settings: Application settings.
        """
        self.client = client
        self.settings = settings
        self.index_name = settings.elasticsearch_index

    async def index_exists(self) -> bool:
        """Check if the configured index exists.

        Returns:
            True if index exists, False otherwise.
        """
        es_client = await self.client.get_client()
        response = await es_client.indices.exists(index=self.index_name)
        return bool(response)

    async def create_index(
        self,
        mappings: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Create the configured index.

        Args:
            mappings: Optional index mappings.
            settings: Optional index settings.

        Returns:
            Creation response or None if index already exists.
        """
        if await self.index_exists():
            return None

        es_client = await self.client.get_client()

        body: dict[str, Any] = {}
        if mappings:
            body["mappings"] = mappings
        if settings:
            body["settings"] = settings

        response = await es_client.indices.create(index=self.index_name, **body)
        return dict(response)

    async def delete_index(self) -> dict[str, Any] | None:
        """Delete the configured index.

        Returns:
            Deletion response or None if index doesn't exist.
        """
        if not await self.index_exists():
            return None

        es_client = await self.client.get_client()
        response = await es_client.indices.delete(index=self.index_name)
        return dict(response)

    async def get_mapping(self) -> dict[str, Any] | None:
        """Get the index mappings.

        Returns:
            Index mappings or None if index doesn't exist.
        """
        try:
            es_client = await self.client.get_client()
            response = await es_client.indices.get_mapping(index=self.index_name)
            return dict(response)
        except ESNotFoundError:
            return None

    async def refresh(self) -> None:
        """Refresh the index to make recent changes searchable."""
        es_client = await self.client.get_client()
        await es_client.indices.refresh(index=self.index_name)

    async def ensure_index(
        self,
        mappings: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> bool:
        """Ensure the index exists, creating it if necessary.

        Args:
            mappings: Optional index mappings for creation.
            settings: Optional index settings for creation.

        Returns:
            True if index exists (created or already existed).
        """
        if await self.index_exists():
            return True

        await self.create_index(mappings=mappings, settings=settings)
        return True


@lru_cache
def get_index_manager() -> IndexManager:
    """Get a singleton IndexManager instance.

    Returns:
        Cached IndexManager instance.
    """
    return IndexManager(get_elasticsearch_client(), get_settings())
