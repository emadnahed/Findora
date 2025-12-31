"""Elasticsearch client and index management."""

from src.elastic.client import (
    ElasticsearchClient,
    get_elasticsearch_client,
    wait_for_elasticsearch,
)
from src.elastic.index_manager import IndexManager, get_index_manager
from src.elastic.mappings import (
    PRODUCT_MAPPINGS,
    PRODUCT_SETTINGS,
    get_product_index_config,
)

__all__ = [
    "PRODUCT_MAPPINGS",
    "PRODUCT_SETTINGS",
    "ElasticsearchClient",
    "IndexManager",
    "get_elasticsearch_client",
    "get_index_manager",
    "get_product_index_config",
    "wait_for_elasticsearch",
]
