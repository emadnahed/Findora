"""Application metrics for monitoring and observability.

Uses prometheus-client for robust metric types with label support
and automatic exposition format generation.
"""

import time
from functools import lru_cache
from threading import Lock
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client.core import CollectorRegistry

# Custom registry to avoid conflicts with default metrics
FINDORA_REGISTRY = CollectorRegistry()

# Define Prometheus metrics with labels for powerful querying
REQUESTS_TOTAL = Counter(
    "findora_requests_total",
    "Total number of HTTP requests",
    ["endpoint", "status_code"],
    registry=FINDORA_REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "findora_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=FINDORA_REGISTRY,
)

UPTIME_SECONDS = Gauge(
    "findora_uptime_seconds",
    "Time since application start in seconds",
    registry=FINDORA_REGISTRY,
)

SEARCH_QUERIES = Counter(
    "findora_search_queries_total",
    "Total number of search queries",
    ["cache_status"],
    registry=FINDORA_REGISTRY,
)

ELASTICSEARCH_QUERIES = Counter(
    "findora_elasticsearch_queries_total",
    "Total number of Elasticsearch queries",
    ["status"],
    registry=FINDORA_REGISTRY,
)

CACHE_SIZE = Gauge(
    "findora_cache_size",
    "Current number of items in cache",
    registry=FINDORA_REGISTRY,
)

# HTTP status code threshold for client/server errors
HTTP_ERROR_THRESHOLD = 400


class MetricsCollector:
    """Thread-safe metrics collector using prometheus-client.

    Provides both Prometheus format output with labels and a JSON
    format for human-readable consumption.
    """

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self._lock = Lock()
        self._start_time = time.time()
        # Internal tracking for JSON output (Prometheus handles its own)
        self._total_requests = 0
        self._total_errors = 0
        self._total_latency_ms = 0.0
        self._min_latency_ms = float("inf")
        self._max_latency_ms = 0.0
        self._requests_by_status: dict[int, int] = {}
        self._requests_by_endpoint: dict[str, int] = {}
        self._search_queries = 0
        self._search_cache_hits = 0
        self._search_cache_misses = 0
        self._elasticsearch_queries = 0
        self._elasticsearch_errors = 0

    def record_request(
        self,
        endpoint: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """Record a request metric.

        Args:
            endpoint: The request endpoint path.
            status_code: HTTP response status code.
            latency_ms: Request latency in milliseconds.
        """
        # Update Prometheus metrics
        REQUESTS_TOTAL.labels(endpoint=endpoint, status_code=str(status_code)).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency_ms / 1000.0)

        with self._lock:
            self._total_requests += 1
            self._total_latency_ms += latency_ms

            # Track min/max latency
            self._min_latency_ms = min(latency_ms, self._min_latency_ms)
            self._max_latency_ms = max(latency_ms, self._max_latency_ms)

            # Track by status code
            self._requests_by_status[status_code] = (
                self._requests_by_status.get(status_code, 0) + 1
            )

            # Track by endpoint
            self._requests_by_endpoint[endpoint] = (
                self._requests_by_endpoint.get(endpoint, 0) + 1
            )

            # Track errors
            if status_code >= HTTP_ERROR_THRESHOLD:
                self._total_errors += 1

    def record_search_query(self, cache_hit: bool = False) -> None:
        """Record a search query.

        Args:
            cache_hit: Whether the query was served from cache.
        """
        cache_status = "hit" if cache_hit else "miss"
        SEARCH_QUERIES.labels(cache_status=cache_status).inc()

        with self._lock:
            self._search_queries += 1
            if cache_hit:
                self._search_cache_hits += 1
            else:
                self._search_cache_misses += 1

    def record_elasticsearch_query(self, error: bool = False) -> None:
        """Record an Elasticsearch query.

        Args:
            error: Whether the query resulted in an error.
        """
        status = "error" if error else "success"
        ELASTICSEARCH_QUERIES.labels(status=status).inc()

        with self._lock:
            self._elasticsearch_queries += 1
            if error:
                self._elasticsearch_errors += 1

    def update_cache_size(self, size: int) -> None:
        """Update the cache size gauge.

        Args:
            size: Current number of items in cache.
        """
        CACHE_SIZE.set(size)

    def get_metrics(self) -> dict[str, Any]:
        """Get all collected metrics in JSON format.

        Returns:
            Dictionary containing all metrics.
        """
        with self._lock:
            uptime = time.time() - self._start_time
            total = self._total_requests

            avg_latency = self._total_latency_ms / total if total > 0 else 0.0

            search_total = self._search_cache_hits + self._search_cache_misses
            cache_hit_rate = (
                self._search_cache_hits / search_total if search_total > 0 else 0.0
            )

            return {
                "uptime_seconds": round(uptime, 2),
                "requests": {
                    "total": total,
                    "errors": self._total_errors,
                    "error_rate": round(
                        self._total_errors / total if total > 0 else 0,
                        4,
                    ),
                    "by_status": dict(self._requests_by_status),
                    "by_endpoint": dict(self._requests_by_endpoint),
                },
                "latency_ms": {
                    "avg": round(avg_latency, 2),
                    "min": round(
                        self._min_latency_ms
                        if self._min_latency_ms != float("inf")
                        else 0,
                        2,
                    ),
                    "max": round(self._max_latency_ms, 2),
                },
                "search": {
                    "total_queries": self._search_queries,
                    "cache_hits": self._search_cache_hits,
                    "cache_misses": self._search_cache_misses,
                    "cache_hit_rate": round(cache_hit_rate, 4),
                },
                "elasticsearch": {
                    "total_queries": self._elasticsearch_queries,
                    "errors": self._elasticsearch_errors,
                    "error_rate": round(
                        self._elasticsearch_errors / self._elasticsearch_queries
                        if self._elasticsearch_queries > 0
                        else 0,
                        4,
                    ),
                },
            }

    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus exposition format.

        Uses prometheus-client's generate_latest for proper formatting
        with full label support.

        Returns:
            String containing metrics in Prometheus exposition format.
        """
        # Update uptime gauge before generating output
        UPTIME_SECONDS.set(time.time() - self._start_time)
        return generate_latest(FINDORA_REGISTRY).decode("utf-8")

    def reset(self) -> None:
        """Reset all internal metrics counters.

        Note: Prometheus counters cannot be reset (they are monotonic).
        This only resets the internal tracking for JSON output.
        """
        with self._lock:
            self._start_time = time.time()
            self._total_requests = 0
            self._total_errors = 0
            self._total_latency_ms = 0.0
            self._min_latency_ms = float("inf")
            self._max_latency_ms = 0.0
            self._requests_by_status = {}
            self._requests_by_endpoint = {}
            self._search_queries = 0
            self._search_cache_hits = 0
            self._search_cache_misses = 0
            self._elasticsearch_queries = 0
            self._elasticsearch_errors = 0


@lru_cache
def get_metrics_collector() -> MetricsCollector:
    """Get a singleton MetricsCollector instance.

    Returns:
        Cached MetricsCollector instance.
    """
    return MetricsCollector()
