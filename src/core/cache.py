"""In-memory cache with TTL for search results."""

import hashlib
import json
import time
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Any

from src.config.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """A cached value with expiration time."""

    value: Any
    expires_at: float


class SearchCache:
    """Thread-safe in-memory cache for search results with TTL."""

    def __init__(self, ttl_seconds: int = 60, max_size: int = 1000) -> None:
        """Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds.
            max_size: Maximum number of entries to store.
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
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
        current_time = time.time()

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                logger.debug("cache_miss", key=key[:16])
                return None

            if current_time > entry.expires_at:
                # Entry has expired
                del self._cache[key]
                self._misses += 1
                logger.debug("cache_expired", key=key[:16])
                return None

            self._hits += 1
            logger.debug("cache_hit", key=key[:16])
            return entry.value

    def set(self, query_params: dict[str, Any], value: Any) -> None:
        """Store a value in the cache.

        Args:
            query_params: Dictionary of query parameters.
            value: Value to cache.
        """
        key = self._generate_key(query_params)
        expires_at = time.time() + self.ttl_seconds

        with self._lock:
            # Evict oldest entries if at max size
            if len(self._cache) >= self.max_size:
                self._evict_oldest()

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            logger.debug("cache_set", key=key[:16], ttl=self.ttl_seconds)

    def _evict_oldest(self) -> None:
        """Evict the oldest entries to make room for new ones."""
        # Remove entries that have expired
        current_time = time.time()
        expired_keys = [
            k for k, v in self._cache.items() if current_time > v.expires_at
        ]
        for key in expired_keys:
            del self._cache[key]

        # If still at max, remove oldest by expiration time
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].expires_at)
            del self._cache[oldest_key]
            logger.debug("cache_evicted", key=oldest_key[:16])

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
