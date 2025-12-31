"""Elasticsearch index mappings configuration."""

from typing import Any

from src.config.settings import Settings, get_settings

# Product index mappings
PRODUCT_MAPPINGS: dict[str, Any] = {
    "properties": {
        "name": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {
                    "type": "keyword",
                    "ignore_above": 256,
                }
            },
        },
        "description": {
            "type": "text",
            "analyzer": "standard",
        },
        "price": {
            "type": "float",
        },
        "category": {
            "type": "keyword",
        },
    }
}


def get_product_settings(settings: Settings | None = None) -> dict[str, Any]:
    """Get product index settings.

    Args:
        settings: Application settings. If None, uses default settings.

    Returns:
        Dictionary with index settings.
    """
    if settings is None:
        settings = get_settings()

    return {
        "number_of_shards": settings.elasticsearch_number_of_shards,
        "number_of_replicas": settings.elasticsearch_number_of_replicas,
        "analysis": {
            "analyzer": {
                "standard": {
                    "type": "standard",
                    "stopwords": "_english_",
                }
            }
        },
    }


def get_product_index_config(settings: Settings | None = None) -> dict[str, Any]:
    """Get the complete index configuration for products.

    Args:
        settings: Application settings. If None, uses default settings.

    Returns:
        Dictionary with mappings and settings.
    """
    return {
        "mappings": PRODUCT_MAPPINGS,
        "settings": get_product_settings(settings),
    }
