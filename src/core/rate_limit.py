"""Rate limiting configuration using SlowAPI."""

from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.logging import get_logger, request_id_var

if TYPE_CHECKING:
    from slowapi.errors import RateLimitExceeded

logger = get_logger(__name__)


def get_client_ip(request: Request) -> str:
    """Get client IP address from request.

    Handles X-Forwarded-For header for proxied requests.

    Args:
        request: The incoming request.

    Returns:
        Client IP address string.
    """
    # Check for X-Forwarded-For header (common with reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()

    # Fall back to direct client address
    return get_remote_address(request)


@lru_cache
def get_limiter() -> Limiter:
    """Get the rate limiter instance.

    Returns:
        Configured SlowAPI Limiter instance.
    """
    return Limiter(
        key_func=get_client_ip,
        default_limits=["100/minute"],
        headers_enabled=True,
        strategy="fixed-window",
    )


def rate_limit_exceeded_handler(
    request: Request, exc: "RateLimitExceeded"
) -> JSONResponse:
    """Handle rate limit exceeded errors.

    Args:
        request: The incoming request.
        exc: The rate limit exception.

    Returns:
        JSONResponse with rate limit error details.
    """
    request_id = request_id_var.get()
    client_ip = get_client_ip(request)

    logger.warning(
        "rate_limit_exceeded",
        client_ip=client_ip,
        path=str(request.url.path),
        limit=str(exc.detail),
    )

    error_response: dict[str, object] = {
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please try again later.",
            "retry_after": getattr(exc, "retry_after", 60),
        }
    }

    if request_id:
        error_response["error"]["request_id"] = request_id  # type: ignore[index]

    response = JSONResponse(
        status_code=429,
        content=error_response,
    )

    # Add retry-after header
    retry_after = getattr(exc, "retry_after", 60)
    response.headers["Retry-After"] = str(retry_after)

    return response
