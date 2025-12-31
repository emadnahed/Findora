"""Core module for production hardening: logging, exceptions, and rate limiting."""

from src.core.exceptions import (
    ElasticsearchError,
    FindoraException,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from src.core.logging import get_logger, setup_logging
from src.core.rate_limit import get_limiter, rate_limit_exceeded_handler

__all__ = [
    "ElasticsearchError",
    "FindoraException",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
    "get_limiter",
    "get_logger",
    "rate_limit_exceeded_handler",
    "setup_logging",
]
