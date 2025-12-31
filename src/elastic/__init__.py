"""Elasticsearch client and index management."""

from src.elastic.client import (
    ElasticsearchClient,
    get_elasticsearch_client,
    wait_for_elasticsearch,
)
from src.elastic.index_manager import IndexManager, get_index_manager
from src.elastic.mappings import (
    PRODUCT_MAPPINGS,
    get_product_index_config,
    get_product_settings,
)

__all__ = [
    "PRODUCT_MAPPINGS",
    "ElasticsearchClient",
    "IndexManager",
    "get_elasticsearch_client",
    "get_index_manager",
    "get_product_index_config",
    "get_product_settings",
    "wait_for_elasticsearch",
]
