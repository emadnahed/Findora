"""Tests for the exceptions module."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from src.core.exceptions import (
    ElasticsearchError,
    FindoraException,
    NotFoundError,
    RateLimitError,
    ValidationError,
    global_exception_handler,
)


class TestFindoraException:
    """Tests for FindoraException base class."""

    def test_default_values(self) -> None:
        """Test default values for base exception."""
        exc = FindoraException()

        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.message == "An unexpected error occurred"
        assert exc.details == {}

    def test_custom_message(self) -> None:
        """Test exception with custom message."""
        exc = FindoraException(message="Custom error message")

        assert exc.message == "Custom error message"

    def test_custom_details(self) -> None:
        """Test exception with custom details."""
        details = {"field": "value", "count": 42}
        exc = FindoraException(details=details)

        assert exc.details == details

    def test_to_dict_basic(self) -> None:
        """Test to_dict without request_id."""
        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None
            exc = FindoraException(message="Test error")

            result = exc.to_dict()

            assert result["error"]["code"] == "INTERNAL_ERROR"
            assert result["error"]["message"] == "Test error"
            assert "request_id" not in result["error"]

    def test_to_dict_with_request_id(self) -> None:
        """Test to_dict with request_id."""
        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = "req-12345"
            exc = FindoraException()

            result = exc.to_dict()

            assert result["error"]["request_id"] == "req-12345"

    def test_to_dict_with_details(self) -> None:
        """Test to_dict with details."""
        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None
            exc = FindoraException(details={"key": "value"})

            result = exc.to_dict()

            assert result["error"]["details"] == {"key": "value"}

    def test_to_dict_without_details(self) -> None:
        """Test to_dict without details."""
        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None
            exc = FindoraException()

            result = exc.to_dict()

            assert "details" not in result["error"]


class TestNotFoundError:
    """Tests for NotFoundError exception."""

    def test_default_values(self) -> None:
        """Test default values for NotFoundError."""
        exc = NotFoundError()

        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"
        assert exc.message == "The requested resource was not found"

    def test_custom_message(self) -> None:
        """Test NotFoundError with custom message."""
        exc = NotFoundError(message="Product not found")

        assert exc.message == "Product not found"


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_default_values(self) -> None:
        """Test default values for ValidationError."""
        exc = ValidationError()

        assert exc.status_code == 400
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.message == "Invalid request data"


class TestElasticsearchError:
    """Tests for ElasticsearchError exception."""

    def test_default_values(self) -> None:
        """Test default values for ElasticsearchError."""
        exc = ElasticsearchError()

        assert exc.status_code == 503
        assert exc.error_code == "ELASTICSEARCH_ERROR"
        assert exc.message == "Search service temporarily unavailable"


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_default_values(self) -> None:
        """Test default values for RateLimitError."""
        exc = RateLimitError()

        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.message == "Too many requests. Please try again later"


class TestGlobalExceptionHandler:
    """Tests for global_exception_handler function."""

    @pytest.mark.asyncio
    async def test_handles_findora_exception(self) -> None:
        """Test handling FindoraException."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        exc = NotFoundError(message="Item not found")

        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None

            response = await global_exception_handler(mock_request, exc)

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_handles_server_error(self) -> None:
        """Test handling server error (5xx)."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        exc = ElasticsearchError()

        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None

            response = await global_exception_handler(mock_request, exc)

            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_handles_client_error(self) -> None:
        """Test handling client error (4xx)."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        exc = ValidationError(message="Invalid input")

        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None

            response = await global_exception_handler(mock_request, exc)

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_handles_unhandled_exception(self) -> None:
        """Test handling generic unhandled exception."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        exc = RuntimeError("Something went wrong")

        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None

            response = await global_exception_handler(mock_request, exc)

            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_unhandled_exception_returns_generic_message(self) -> None:
        """Test that unhandled exceptions return generic error message."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        exc = ValueError("Sensitive internal error")

        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None

            response = await global_exception_handler(mock_request, exc)

            import json
            body = json.loads(response.body.decode())
            # Should NOT expose internal error details
            assert body["error"]["message"] == "An unexpected error occurred"
            assert body["error"]["code"] == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_logs_server_error_at_error_level(self) -> None:
        """Test that server errors are logged at error level."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        exc = ElasticsearchError(message="ES down")

        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None
            with patch("src.core.exceptions.logger") as mock_logger:
                await global_exception_handler(mock_request, exc)

                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_client_error_at_warning_level(self) -> None:
        """Test that client errors are logged at warning level."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        exc = NotFoundError()

        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None
            with patch("src.core.exceptions.logger") as mock_logger:
                await global_exception_handler(mock_request, exc)

                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_unhandled_exception(self) -> None:
        """Test that unhandled exceptions are logged."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.path = "/test"

        exc = RuntimeError("Unexpected error")

        with patch("src.core.exceptions.request_id_var") as mock_var:
            mock_var.get.return_value = None
            with patch("src.core.exceptions.logger") as mock_logger:
                await global_exception_handler(mock_request, exc)

                mock_logger.exception.assert_called_once()
