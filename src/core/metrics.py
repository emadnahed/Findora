"""Application metrics for monitoring and observability."""

import time
from dataclasses import dataclass, field
from functools import lru_cache
from threading import Lock
from typing import Any

# HTTP status code threshold for client/server errors
HTTP_ERROR_THRESHOLD = 400


@dataclass
class RequestMetrics:
    """Metrics for HTTP requests."""

    total_requests: int = 0
    total_errors: int = 0
    requests_by_status: dict[int, int] = field(default_factory=dict)
    requests_by_endpoint: dict[str, int] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0


class MetricsCollector:
    """Thread-safe metrics collector for application monitoring."""

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self._lock = Lock()
        self._start_time = time.time()
        self._request_metrics = RequestMetrics()
        self._search_queries: int = 0
        self._search_cache_hits: int = 0
        self._search_cache_misses: int = 0
        self._elasticsearch_queries: int = 0
        self._elasticsearch_errors: int = 0

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
        with self._lock:
            self._request_metrics.total_requests += 1
            self._request_metrics.total_latency_ms += latency_ms

            # Track min/max latency
            self._request_metrics.min_latency_ms = min(
                latency_ms, self._request_metrics.min_latency_ms
            )
            self._request_metrics.max_latency_ms = max(
                latency_ms, self._request_metrics.max_latency_ms
            )

            # Track by status code
            self._request_metrics.requests_by_status[status_code] = (
                self._request_metrics.requests_by_status.get(status_code, 0) + 1
            )

            # Track by endpoint
            self._request_metrics.requests_by_endpoint[endpoint] = (
                self._request_metrics.requests_by_endpoint.get(endpoint, 0) + 1
            )

            # Track errors
            if status_code >= HTTP_ERROR_THRESHOLD:
                self._request_metrics.total_errors += 1

    def record_search_query(self, cache_hit: bool = False) -> None:
        """Record a search query.

        Args:
            cache_hit: Whether the query was served from cache.
        """
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
        with self._lock:
            self._elasticsearch_queries += 1
            if error:
                self._elasticsearch_errors += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get all collected metrics.

        Returns:
            Dictionary containing all metrics.
        """
        with self._lock:
            uptime = time.time() - self._start_time
            total = self._request_metrics.total_requests

            avg_latency = (
                self._request_metrics.total_latency_ms / total if total > 0 else 0.0
            )

            search_total = self._search_cache_hits + self._search_cache_misses
            cache_hit_rate = (
                self._search_cache_hits / search_total if search_total > 0 else 0.0
            )

            return {
                "uptime_seconds": round(uptime, 2),
                "requests": {
                    "total": total,
                    "errors": self._request_metrics.total_errors,
                    "error_rate": round(
                        self._request_metrics.total_errors / total if total > 0 else 0,
                        4,
                    ),
                    "by_status": dict(self._request_metrics.requests_by_status),
                    "by_endpoint": dict(self._request_metrics.requests_by_endpoint),
                },
                "latency_ms": {
                    "avg": round(avg_latency, 2),
                    "min": round(
                        self._request_metrics.min_latency_ms
                        if self._request_metrics.min_latency_ms != float("inf")
                        else 0,
                        2,
                    ),
                    "max": round(self._request_metrics.max_latency_ms, 2),
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
        """Get metrics in Prometheus format.

        Returns:
            String containing metrics in Prometheus exposition format.
        """
        metrics = self.get_metrics()
        lines = []

        # Uptime
        lines.append(
            '# HELP findora_uptime_seconds Time since application start'
        )
        lines.append('# TYPE findora_uptime_seconds gauge')
        lines.append(f'findora_uptime_seconds {metrics["uptime_seconds"]}')

        # Request metrics
        lines.append(
            '# HELP findora_requests_total Total number of HTTP requests'
        )
        lines.append('# TYPE findora_requests_total counter')
        lines.append(f'findora_requests_total {metrics["requests"]["total"]}')

        lines.append(
            '# HELP findora_request_errors_total Total number of HTTP errors'
        )
        lines.append('# TYPE findora_request_errors_total counter')
        lines.append(f'findora_request_errors_total {metrics["requests"]["errors"]}')

        # Latency
        lines.append(
            '# HELP findora_request_latency_ms_avg Average request latency'
        )
        lines.append('# TYPE findora_request_latency_ms_avg gauge')
        lines.append(f'findora_request_latency_ms_avg {metrics["latency_ms"]["avg"]}')

        # Search metrics
        lines.append(
            '# HELP findora_search_queries_total Total number of search queries'
        )
        lines.append('# TYPE findora_search_queries_total counter')
        lines.append(f'findora_search_queries_total {metrics["search"]["total_queries"]}')

        lines.append(
            '# HELP findora_search_cache_hits_total Total search cache hits'
        )
        lines.append('# TYPE findora_search_cache_hits_total counter')
        lines.append(f'findora_search_cache_hits_total {metrics["search"]["cache_hits"]}')

        lines.append(
            '# HELP findora_search_cache_hit_rate Search cache hit rate'
        )
        lines.append('# TYPE findora_search_cache_hit_rate gauge')
        lines.append(f'findora_search_cache_hit_rate {metrics["search"]["cache_hit_rate"]}')

        # Elasticsearch metrics
        lines.append(
            '# HELP findora_elasticsearch_queries_total Total ES queries'
        )
        lines.append('# TYPE findora_elasticsearch_queries_total counter')
        lines.append(
            f'findora_elasticsearch_queries_total {metrics["elasticsearch"]["total_queries"]}'
        )

        lines.append(
            '# HELP findora_elasticsearch_errors_total Total ES errors'
        )
        lines.append('# TYPE findora_elasticsearch_errors_total counter')
        lines.append(
            f'findora_elasticsearch_errors_total {metrics["elasticsearch"]["errors"]}'
        )

        return '\n'.join(lines) + '\n'

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._start_time = time.time()
            self._request_metrics = RequestMetrics()
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
