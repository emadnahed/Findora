"""In-memory cache with TTL for search results using cachetools.

Uses cachetools.TTLCache for O(1) get/set operations and efficient
automatic expiration and eviction of entries.
"""

import hashlib
import json
from functools import lru_cache
from threading import Lock
from typing import Any

from cachetools import TTLCache

from src.config.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class SearchCache:
    """Thread-safe TTL cache for search results using cachetools.

    Uses cachetools.TTLCache which provides O(1) get/set operations
    and efficient automatic expiration of entries, avoiding the O(N)
    eviction overhead of manual implementations.
    """

    def __init__(self, ttl_seconds: int = 60, max_size: int = 1000) -> None:
        """Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds.
            max_size: Maximum number of entries to store.
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _generate_key(self, query_params: dict[str, Any]) -> str:
        """Generate a cache key from query parameters.

        Args:
            query_params: Dictionary of query parameters.

        Returns:
            SHA256 hash of the serialized parameters.
        """
        serialized = json.dumps(query_params, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def get(self, query_params: dict[str, Any]) -> Any | None:
        """Get a cached value if it exists and hasn't expired.

        Args:
            query_params: Dictionary of query parameters.

        Returns:
            Cached value or None if not found/expired.
        """
        key = self._generate_key(query_params)

        with self._lock:
            # TTLCache automatically handles expiration
            result = self._cache.get(key)

            if result is None:
                self._misses += 1
                logger.debug("cache_miss", key=key[:16])
                return None

            self._hits += 1
            logger.debug("cache_hit", key=key[:16])
            return result

    def set(self, query_params: dict[str, Any], value: Any) -> None:
        """Store a value in the cache.

        Args:
            query_params: Dictionary of query parameters.
            value: Value to cache.
        """
        key = self._generate_key(query_params)

        with self._lock:
            # TTLCache automatically handles eviction when at max size
            self._cache[key] = value
            logger.debug("cache_set", key=key[:16], ttl=self.ttl_seconds)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            logger.info("cache_cleared")

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
            }

    def reset_stats(self) -> None:
        """Reset hit/miss counters."""
        with self._lock:
            self._hits = 0
            self._misses = 0


@lru_cache
def get_search_cache() -> SearchCache:
    """Get a singleton SearchCache instance.

    Returns:
        Cached SearchCache instance.
    """
    settings = get_settings()
    return SearchCache(
        ttl_seconds=settings.cache_ttl_seconds,
        max_size=settings.cache_max_size,
    )
