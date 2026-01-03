"""Tests for the rate limiting module."""

from unittest.mock import MagicMock, patch

from fastapi import Request
from slowapi import Limiter

from src.core.rate_limit import (
    get_client_ip,
    get_limiter,
    rate_limit_exceeded_handler,
)


class TestGetClientIp:
    """Tests for get_client_ip function."""

    def test_get_client_ip_from_x_forwarded_for(self) -> None:
        """Test getting IP from X-Forwarded-For header."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}

        result = get_client_ip(mock_request)

        assert result == "192.168.1.100"

    def test_get_client_ip_single_forwarded_ip(self) -> None:
        """Test getting IP when only one IP in X-Forwarded-For."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Forwarded-For": "172.16.0.50"}

        result = get_client_ip(mock_request)

        assert result == "172.16.0.50"

    def test_get_client_ip_strips_whitespace(self) -> None:
        """Test that IP addresses are stripped of whitespace."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Forwarded-For": "  192.168.1.100  , 10.0.0.1"}

        result = get_client_ip(mock_request)

        assert result == "192.168.1.100"

    def test_get_client_ip_fallback_to_remote_address(self) -> None:
        """Test fallback to direct client address when no X-Forwarded-For."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.50"

        with patch("src.core.rate_limit.get_remote_address") as mock_get_remote:
            mock_get_remote.return_value = "10.0.0.50"

            result = get_client_ip(mock_request)

            assert result == "10.0.0.50"
            mock_get_remote.assert_called_once_with(mock_request)


class TestGetLimiter:
    """Tests for get_limiter function."""

    def test_get_limiter_returns_limiter(self) -> None:
        """Test that get_limiter returns a Limiter instance."""
        # Clear the cache to ensure fresh instance
        get_limiter.cache_clear()

        with patch("src.core.rate_limit.get_settings") as mock_settings:
            mock_settings.return_value.rate_limit_default = "100/minute"
            mock_settings.return_value.redis_url = None
            mock_settings.return_value.rate_limit_enabled = True

            limiter = get_limiter()

            assert isinstance(limiter, Limiter)

    def test_get_limiter_returns_singleton(self) -> None:
        """Test that get_limiter returns the same instance."""
        get_limiter.cache_clear()

        with patch("src.core.rate_limit.get_settings") as mock_settings:
            mock_settings.return_value.rate_limit_default = "100/minute"
            mock_settings.return_value.redis_url = None
            mock_settings.return_value.rate_limit_enabled = True

            limiter1 = get_limiter()
            limiter2 = get_limiter()

            assert limiter1 is limiter2

    def test_get_limiter_uses_settings(self) -> None:
        """Test that get_limiter uses settings values."""
        get_limiter.cache_clear()

        with patch("src.core.rate_limit.get_settings") as mock_settings:
            mock_settings.return_value.rate_limit_default = "50/minute"
            mock_settings.return_value.redis_url = None
            mock_settings.return_value.rate_limit_enabled = False

            limiter = get_limiter()

            assert isinstance(limiter, Limiter)


class TestRateLimitExceededHandler:
    """Tests for rate_limit_exceeded_handler function."""

    def test_handler_returns_429_response(self) -> None:
        """Test that handler returns 429 status code."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.url = MagicMock()
        mock_request.url.path = "/api/v1/search"

        mock_exc = MagicMock()
        mock_exc.detail = "5 per 1 minute"
        mock_exc.retry_after = 30

        with (
            patch("src.core.rate_limit.get_remote_address", return_value="127.0.0.1"),
            patch("src.core.rate_limit.request_id_var") as mock_request_id,
        ):
            mock_request_id.get.return_value = None

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            assert response.status_code == 429

    def test_handler_includes_retry_after_header(self) -> None:
        """Test that handler includes Retry-After header."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.url = MagicMock()
        mock_request.url.path = "/api/v1/search"

        mock_exc = MagicMock()
        mock_exc.detail = "5 per 1 minute"
        mock_exc.retry_after = 45

        with (
            patch("src.core.rate_limit.get_remote_address", return_value="127.0.0.1"),
            patch("src.core.rate_limit.request_id_var") as mock_request_id,
        ):
            mock_request_id.get.return_value = None

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            assert response.headers.get("Retry-After") == "45"

    def test_handler_includes_request_id_when_available(self) -> None:
        """Test that handler includes request_id when available."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.url = MagicMock()
        mock_request.url.path = "/api/v1/search"

        mock_exc = MagicMock()
        mock_exc.detail = "5 per 1 minute"
        mock_exc.retry_after = 60

        with (
            patch("src.core.rate_limit.get_remote_address", return_value="127.0.0.1"),
            patch("src.core.rate_limit.request_id_var") as mock_request_id,
        ):
            mock_request_id.get.return_value = "req-12345"

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            # Check response body contains request_id
            import json
            body = json.loads(response.body.decode())
            assert body["error"]["request_id"] == "req-12345"

    def test_handler_error_response_structure(self) -> None:
        """Test that error response has correct structure."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        mock_exc = MagicMock()
        mock_exc.detail = "rate limit"
        mock_exc.retry_after = 60

        with (
            patch("src.core.rate_limit.get_remote_address", return_value="127.0.0.1"),
            patch("src.core.rate_limit.request_id_var") as mock_request_id,
        ):
            mock_request_id.get.return_value = None

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            import json
            body = json.loads(response.body.decode())
            assert "error" in body
            assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
            assert "message" in body["error"]
            assert "retry_after" in body["error"]

    def test_handler_default_retry_after(self) -> None:
        """Test that handler uses default retry_after when not provided."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        mock_exc = MagicMock(spec=[])  # No retry_after attribute
        mock_exc.detail = "rate limit"

        with (
            patch("src.core.rate_limit.get_remote_address", return_value="127.0.0.1"),
            patch("src.core.rate_limit.request_id_var") as mock_request_id,
        ):
            mock_request_id.get.return_value = None

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            # Should use default of 60
            assert response.headers.get("Retry-After") == "60"
