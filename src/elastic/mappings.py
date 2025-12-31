"""Elasticsearch index mappings configuration."""

from typing import Any

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

# Product index settings
PRODUCT_SETTINGS: dict[str, Any] = {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
        "analyzer": {
            "standard": {
                "type": "standard",
                "stopwords": "_english_",
            }
        }
    },
}


def get_product_index_config() -> dict[str, Any]:
    """Get the complete index configuration for products.

    Returns:
        Dictionary with mappings and settings.
    """
    return {
        "mappings": PRODUCT_MAPPINGS,
        "settings": PRODUCT_SETTINGS,
    }
