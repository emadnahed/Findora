"""Indexing service for Elasticsearch document operations."""

from functools import lru_cache
from typing import Any

from elasticsearch import NotFoundError as ESNotFoundError
from elasticsearch.helpers import async_bulk

from src.config.settings import Settings, get_settings
from src.core.logging import get_logger
from src.elastic.client import ElasticsearchClient, get_elasticsearch_client
from src.models.product import BulkOperationResult, Product

logger = get_logger(__name__)


class IndexingService:
    """Service for indexing and managing documents in Elasticsearch."""

    def __init__(self, client: ElasticsearchClient, settings: Settings) -> None:
        """Initialize the indexing service.

        Args:
            client: ElasticsearchClient instance.
            settings: Application settings.
        """
        self.client = client
        self.settings = settings
        self.index_name = settings.elasticsearch_index

    async def index_product(self, product: Product) -> dict[str, Any]:
        """Index a single product.

        Args:
            product: Product to index.

        Returns:
            Elasticsearch response with result status.
        """
        es_client = await self.client.get_client()

        # Convert product to document (exclude id from body, use as doc id)
        document = product.model_dump(exclude={"id"})

        response = await es_client.index(
            index=self.index_name,
            id=product.id,
            document=document,
        )

        logger.debug(
            "product_indexed",
            product_id=product.id,
            index=self.index_name,
            result=response.get("result"),
        )

        return dict(response)

    async def delete_product(self, product_id: str) -> dict[str, Any] | None:
        """Delete a product by ID.

        Args:
            product_id: ID of the product to delete.

        Returns:
            Elasticsearch response or None if not found.
        """
        try:
            es_client = await self.client.get_client()
            response = await es_client.delete(
                index=self.index_name,
                id=product_id,
            )
            logger.debug(
                "product_deleted_from_index",
                product_id=product_id,
                index=self.index_name,
            )
            return dict(response)
        except ESNotFoundError:
            logger.debug(
                "product_not_found_for_delete",
                product_id=product_id,
                index=self.index_name,
            )
            return None

    async def get_product(self, product_id: str) -> Product | None:
        """Get a product by ID.

        Args:
            product_id: ID of the product to retrieve.

        Returns:
            Product if found, None otherwise.
        """
        try:
            es_client = await self.client.get_client()
            response = await es_client.get(
                index=self.index_name,
                id=product_id,
            )
            source = response["_source"]
            return Product(id=response["_id"], **source)
        except ESNotFoundError:
            return None

    async def product_exists(self, product_id: str) -> bool:
        """Check if a product exists.

        Args:
            product_id: ID of the product to check.

        Returns:
            True if product exists, False otherwise.
        """
        es_client = await self.client.get_client()
        response = await es_client.exists(
            index=self.index_name,
            id=product_id,
        )
        return bool(response)

    async def bulk_index_products(self, products: list[Product]) -> BulkOperationResult:
        """Bulk index multiple products.

        Args:
            products: List of products to index.

        Returns:
            BulkOperationResult with success/error counts.
        """
        if not products:
            return BulkOperationResult(
                success_count=0,
                error_count=0,
                errors=[],
            )

        es_client = await self.client.get_client()

        # Generate bulk actions
        actions = [
            {
                "_index": self.index_name,
                "_id": product.id,
                "_source": product.model_dump(exclude={"id"}),
            }
            for product in products
        ]

        success_count, errors = await async_bulk(
            es_client,
            actions,
            raise_on_error=False,
        )

        # errors can be int (count mode) or list (actual errors)
        error_list = errors if isinstance(errors, list) else []

        logger.debug(
            "bulk_index_completed",
            total=len(products),
            success_count=success_count,
            error_count=len(error_list),
            index=self.index_name,
        )

        return BulkOperationResult(
            success_count=success_count,
            error_count=len(error_list),
            errors=error_list,
        )

    async def bulk_delete_products(self, product_ids: list[str]) -> BulkOperationResult:
        """Bulk delete multiple products.

        Args:
            product_ids: List of product IDs to delete.

        Returns:
            BulkOperationResult with success/error counts.
        """
        if not product_ids:
            return BulkOperationResult(
                success_count=0,
                error_count=0,
                errors=[],
            )

        es_client = await self.client.get_client()

        # Generate bulk delete actions
        actions = [
            {
                "_op_type": "delete",
                "_index": self.index_name,
                "_id": product_id,
            }
            for product_id in product_ids
        ]

        success_count, errors = await async_bulk(
            es_client,
            actions,
            raise_on_error=False,
        )

        # errors can be int (count mode) or list (actual errors)
        error_list = errors if isinstance(errors, list) else []

        logger.debug(
            "bulk_delete_completed",
            total=len(product_ids),
            success_count=success_count,
            error_count=len(error_list),
            index=self.index_name,
        )

        return BulkOperationResult(
            success_count=success_count,
            error_count=len(error_list),
            errors=error_list,
        )


@lru_cache
def get_indexing_service() -> IndexingService:
    """Get a singleton IndexingService instance.

    Returns:
        Cached IndexingService instance.
    """
    return IndexingService(get_elasticsearch_client(), get_settings())
