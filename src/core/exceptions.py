"""Custom exception classes for the Findora API."""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from src.core.logging import get_logger, request_id_var

logger = get_logger(__name__)

# HTTP status code threshold for server errors
SERVER_ERROR_THRESHOLD = 500


class FindoraException(Exception):
    """Base exception for all Findora API errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            details: Additional error details.
        """
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        response: dict[str, Any] = {
            "error": {
                "code": self.error_code,
                "message": self.message,
            }
        }

        # Add request_id if available
        request_id = request_id_var.get()
        if request_id:
            response["error"]["request_id"] = request_id

        # Add details if present
        if self.details:
            response["error"]["details"] = self.details

        return response


class NotFoundError(FindoraException):
    """Resource not found error (404)."""

    status_code = 404
    error_code = "NOT_FOUND"
    message = "The requested resource was not found"


class ValidationError(FindoraException):
    """Validation error (400)."""

    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Invalid request data"


class ElasticsearchError(FindoraException):
    """Elasticsearch service error (503)."""

    status_code = 503
    error_code = "ELASTICSEARCH_ERROR"
    message = "Search service temporarily unavailable"


class RateLimitError(FindoraException):
    """Rate limit exceeded error (429)."""

    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later"


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for all unhandled exceptions.

    Args:
        request: The incoming request.
        exc: The exception that was raised.

    Returns:
        JSONResponse with error details.
    """
    request_id = request_id_var.get()

    if isinstance(exc, FindoraException):
        # Log at appropriate level based on status code
        if exc.status_code >= SERVER_ERROR_THRESHOLD:
            logger.error(
                "server_error",
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
                path=str(request.url.path),
            )
        else:
            logger.warning(
                "client_error",
                error_code=exc.error_code,
                message=exc.message,
                path=str(request.url.path),
            )

        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    # Unexpected exception - log full details
    logger.exception(
        "unhandled_exception",
        exc_type=type(exc).__name__,
        exc_message=str(exc),
        path=str(request.url.path),
    )

    # Return generic error response
    error_response: dict[str, Any] = {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
        }
    }
    if request_id:
        error_response["error"]["request_id"] = request_id

    return JSONResponse(
        status_code=500,
        content=error_response,
    )
