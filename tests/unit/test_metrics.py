"""Tests for the metrics module."""

import time

from src.core.metrics import MetricsCollector, RequestMetrics, get_metrics_collector


class TestRequestMetrics:
    """Tests for RequestMetrics dataclass."""

    def test_request_metrics_defaults(self) -> None:
        """Test default values for RequestMetrics."""
        metrics = RequestMetrics()
        assert metrics.total_requests == 0
        assert metrics.total_errors == 0
        assert metrics.requests_by_status == {}
        assert metrics.requests_by_endpoint == {}
        assert metrics.total_latency_ms == 0.0
        assert metrics.min_latency_ms == float("inf")
        assert metrics.max_latency_ms == 0.0


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_collector_initialization(self) -> None:
        """Test metrics collector initialization."""
        collector = MetricsCollector()
        metrics = collector.get_metrics()

        assert metrics["requests"]["total"] == 0
        assert metrics["search"]["total_queries"] == 0
        assert metrics["elasticsearch"]["total_queries"] == 0

    def test_record_request(self) -> None:
        """Test recording a request."""
        collector = MetricsCollector()
        collector.record_request("/api/v1/search", 200, 50.0)

        metrics = collector.get_metrics()
        assert metrics["requests"]["total"] == 1
        assert metrics["requests"]["by_status"][200] == 1
        assert metrics["requests"]["by_endpoint"]["/api/v1/search"] == 1

    def test_record_multiple_requests(self) -> None:
        """Test recording multiple requests."""
        collector = MetricsCollector()
        collector.record_request("/api/v1/search", 200, 50.0)
        collector.record_request("/api/v1/search", 200, 100.0)
        collector.record_request("/api/v1/products", 201, 30.0)

        metrics = collector.get_metrics()
        assert metrics["requests"]["total"] == 3
        assert metrics["requests"]["by_status"][200] == 2
        assert metrics["requests"]["by_status"][201] == 1
        assert metrics["requests"]["by_endpoint"]["/api/v1/search"] == 2
        assert metrics["requests"]["by_endpoint"]["/api/v1/products"] == 1

    def test_record_error_request(self) -> None:
        """Test recording error requests."""
        collector = MetricsCollector()
        collector.record_request("/api/v1/search", 500, 10.0)
        collector.record_request("/api/v1/search", 404, 5.0)
        collector.record_request("/api/v1/search", 200, 20.0)

        metrics = collector.get_metrics()
        assert metrics["requests"]["total"] == 3
        assert metrics["requests"]["errors"] == 2

    def test_latency_tracking(self) -> None:
        """Test latency min/max/avg tracking."""
        collector = MetricsCollector()
        collector.record_request("/test", 200, 10.0)
        collector.record_request("/test", 200, 50.0)
        collector.record_request("/test", 200, 30.0)

        metrics = collector.get_metrics()
        assert metrics["latency_ms"]["min"] == 10.0
        assert metrics["latency_ms"]["max"] == 50.0
        assert metrics["latency_ms"]["avg"] == 30.0

    def test_record_search_query_no_cache(self) -> None:
        """Test recording search query without cache hit."""
        collector = MetricsCollector()
        collector.record_search_query(cache_hit=False)

        metrics = collector.get_metrics()
        assert metrics["search"]["total_queries"] == 1
        assert metrics["search"]["cache_hits"] == 0
        assert metrics["search"]["cache_misses"] == 1

    def test_record_search_query_cache_hit(self) -> None:
        """Test recording search query with cache hit."""
        collector = MetricsCollector()
        collector.record_search_query(cache_hit=True)

        metrics = collector.get_metrics()
        assert metrics["search"]["total_queries"] == 1
        assert metrics["search"]["cache_hits"] == 1
        assert metrics["search"]["cache_misses"] == 0

    def test_cache_hit_rate_calculation(self) -> None:
        """Test cache hit rate calculation."""
        collector = MetricsCollector()
        collector.record_search_query(cache_hit=True)
        collector.record_search_query(cache_hit=True)
        collector.record_search_query(cache_hit=False)
        collector.record_search_query(cache_hit=False)

        metrics = collector.get_metrics()
        assert metrics["search"]["cache_hit_rate"] == 0.5

    def test_record_elasticsearch_query(self) -> None:
        """Test recording Elasticsearch query."""
        collector = MetricsCollector()
        collector.record_elasticsearch_query(error=False)

        metrics = collector.get_metrics()
        assert metrics["elasticsearch"]["total_queries"] == 1
        assert metrics["elasticsearch"]["errors"] == 0

    def test_record_elasticsearch_error(self) -> None:
        """Test recording Elasticsearch error."""
        collector = MetricsCollector()
        collector.record_elasticsearch_query(error=True)

        metrics = collector.get_metrics()
        assert metrics["elasticsearch"]["total_queries"] == 1
        assert metrics["elasticsearch"]["errors"] == 1

    def test_uptime_tracking(self) -> None:
        """Test uptime is tracked."""
        collector = MetricsCollector()
        time.sleep(0.1)
        metrics = collector.get_metrics()

        assert metrics["uptime_seconds"] >= 0.1

    def test_get_prometheus_metrics(self) -> None:
        """Test Prometheus format output."""
        collector = MetricsCollector()
        collector.record_request("/test", 200, 50.0)
        collector.record_search_query(cache_hit=True)

        prometheus_output = collector.get_prometheus_metrics()

        assert "findora_uptime_seconds" in prometheus_output
        assert "findora_requests_total 1" in prometheus_output
        assert "findora_search_queries_total 1" in prometheus_output
        assert "findora_search_cache_hits_total 1" in prometheus_output

    def test_prometheus_format_structure(self) -> None:
        """Test Prometheus output has proper structure."""
        collector = MetricsCollector()
        prometheus_output = collector.get_prometheus_metrics()

        lines = prometheus_output.strip().split('\n')
        # Should have HELP and TYPE comments before each metric
        assert any(line.startswith('# HELP') for line in lines)
        assert any(line.startswith('# TYPE') for line in lines)

    def test_reset_metrics(self) -> None:
        """Test resetting all metrics."""
        collector = MetricsCollector()
        collector.record_request("/test", 200, 50.0)
        collector.record_search_query(cache_hit=True)

        collector.reset()
        metrics = collector.get_metrics()

        assert metrics["requests"]["total"] == 0
        assert metrics["search"]["total_queries"] == 0

    def test_error_rate_calculation(self) -> None:
        """Test error rate calculation."""
        collector = MetricsCollector()
        collector.record_request("/test", 200, 10.0)
        collector.record_request("/test", 500, 10.0)
        collector.record_request("/test", 200, 10.0)
        collector.record_request("/test", 404, 10.0)

        metrics = collector.get_metrics()
        assert metrics["requests"]["error_rate"] == 0.5


class TestGetMetricsCollector:
    """Tests for get_metrics_collector singleton."""

    def test_get_metrics_collector_returns_instance(self) -> None:
        """Test that get_metrics_collector returns a MetricsCollector."""
        get_metrics_collector.cache_clear()
        collector = get_metrics_collector()
        assert isinstance(collector, MetricsCollector)

    def test_get_metrics_collector_returns_singleton(self) -> None:
        """Test that get_metrics_collector returns the same instance."""
        get_metrics_collector.cache_clear()
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        assert collector1 is collector2
