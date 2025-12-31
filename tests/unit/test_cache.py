"""Tests for the search cache module."""

import time
from unittest.mock import patch

from src.core.cache import CacheEntry, SearchCache, get_search_cache


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_creation(self) -> None:
        """Test creating a cache entry."""
        entry = CacheEntry(value={"test": "data"}, expires_at=time.time() + 60)
        assert entry.value == {"test": "data"}
        assert entry.expires_at > time.time()


class TestSearchCache:
    """Tests for SearchCache class."""

    def test_cache_initialization(self) -> None:
        """Test cache initialization with defaults."""
        cache = SearchCache()
        assert cache.ttl_seconds == 60
        assert cache.max_size == 1000
        assert cache._hits == 0
        assert cache._misses == 0

    def test_cache_initialization_custom_values(self) -> None:
        """Test cache initialization with custom values."""
        cache = SearchCache(ttl_seconds=120, max_size=500)
        assert cache.ttl_seconds == 120
        assert cache.max_size == 500

    def test_generate_key_deterministic(self) -> None:
        """Test that key generation is deterministic."""
        cache = SearchCache()
        params = {"q": "test", "page": 1, "size": 10}
        key1 = cache._generate_key(params)
        key2 = cache._generate_key(params)
        assert key1 == key2

    def test_generate_key_different_for_different_params(self) -> None:
        """Test that different params generate different keys."""
        cache = SearchCache()
        key1 = cache._generate_key({"q": "test1"})
        key2 = cache._generate_key({"q": "test2"})
        assert key1 != key2

    def test_generate_key_order_independent(self) -> None:
        """Test that key is independent of param order."""
        cache = SearchCache()
        key1 = cache._generate_key({"a": 1, "b": 2})
        key2 = cache._generate_key({"b": 2, "a": 1})
        assert key1 == key2

    def test_set_and_get(self) -> None:
        """Test setting and getting a value."""
        cache = SearchCache()
        params = {"q": "laptop"}
        value = {"results": [{"id": "1", "name": "Laptop"}]}

        cache.set(params, value)
        result = cache.get(params)

        assert result == value

    def test_get_miss(self) -> None:
        """Test cache miss returns None."""
        cache = SearchCache()
        result = cache.get({"q": "nonexistent"})
        assert result is None

    def test_get_expired_entry(self) -> None:
        """Test that expired entries return None."""
        cache = SearchCache(ttl_seconds=1)
        params = {"q": "test"}
        cache.set(params, {"data": "test"})

        # Wait for entry to expire
        time.sleep(1.1)

        result = cache.get(params)
        assert result is None

    def test_hit_counter_increments(self) -> None:
        """Test that hits counter increments on cache hit."""
        cache = SearchCache()
        params = {"q": "test"}
        cache.set(params, {"data": "test"})

        cache.get(params)
        cache.get(params)

        assert cache._hits == 2

    def test_miss_counter_increments(self) -> None:
        """Test that misses counter increments on cache miss."""
        cache = SearchCache()
        cache.get({"q": "miss1"})
        cache.get({"q": "miss2"})

        assert cache._misses == 2

    def test_max_size_eviction(self) -> None:
        """Test that old entries are evicted when max size is reached."""
        cache = SearchCache(max_size=3)

        cache.set({"q": "1"}, "value1")
        cache.set({"q": "2"}, "value2")
        cache.set({"q": "3"}, "value3")
        cache.set({"q": "4"}, "value4")

        # Should have evicted one entry
        assert len(cache._cache) <= 3

    def test_clear(self) -> None:
        """Test clearing the cache."""
        cache = SearchCache()
        cache.set({"q": "test1"}, "value1")
        cache.set({"q": "test2"}, "value2")

        cache.clear()

        assert len(cache._cache) == 0
        assert cache.get({"q": "test1"}) is None

    def test_stats(self) -> None:
        """Test getting cache statistics."""
        cache = SearchCache(ttl_seconds=60, max_size=100)
        cache.set({"q": "test"}, "value")
        cache.get({"q": "test"})  # hit
        cache.get({"q": "miss"})  # miss

        stats = cache.stats()

        assert stats["size"] == 1
        assert stats["max_size"] == 100
        assert stats["ttl_seconds"] == 60
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_stats_zero_requests(self) -> None:
        """Test stats with zero requests doesn't divide by zero."""
        cache = SearchCache()
        stats = cache.stats()

        assert stats["hit_rate"] == 0.0

    def test_reset_stats(self) -> None:
        """Test resetting statistics."""
        cache = SearchCache()
        cache.set({"q": "test"}, "value")
        cache.get({"q": "test"})
        cache.get({"q": "miss"})

        cache.reset_stats()

        assert cache._hits == 0
        assert cache._misses == 0


class TestGetSearchCache:
    """Tests for get_search_cache singleton."""

    def test_get_search_cache_returns_instance(self) -> None:
        """Test that get_search_cache returns a SearchCache instance."""
        # Clear the cache to ensure fresh instance
        get_search_cache.cache_clear()

        with patch("src.core.cache.get_settings") as mock_settings:
            mock_settings.return_value.cache_ttl_seconds = 30
            mock_settings.return_value.cache_max_size = 500

            cache = get_search_cache()

            assert isinstance(cache, SearchCache)
            assert cache.ttl_seconds == 30
            assert cache.max_size == 500

    def test_get_search_cache_returns_singleton(self) -> None:
        """Test that get_search_cache returns the same instance."""
        get_search_cache.cache_clear()

        with patch("src.core.cache.get_settings") as mock_settings:
            mock_settings.return_value.cache_ttl_seconds = 60
            mock_settings.return_value.cache_max_size = 1000

            cache1 = get_search_cache()
            cache2 = get_search_cache()

            assert cache1 is cache2
