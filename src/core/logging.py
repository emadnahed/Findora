"""Structured logging configuration using structlog."""

import logging
import sys
from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any

import structlog

# Context variable for request-scoped data
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def add_request_id(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Add request_id to log entries if available.

    Args:
        _logger: Logger instance (unused, required by structlog processor signature).
        _method_name: Method name (unused, required by structlog processor signature).
        event_dict: Event dictionary to modify.

    Returns:
        Modified event dictionary with request_id if available.
    """
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structlog for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format - 'json' for production, 'console' for development.
    """
    # Common processors for all formats
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        add_request_id,
    ]

    if log_format == "console":
        # Development: colored console output
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Suppress noisy loggers
    logging.getLogger("elasticsearch").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name. If None, uses the calling module's name.

    Returns:
        Configured structlog BoundLogger instance.
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]


def bind_request_context(request_id: str, **kwargs: Any) -> None:
    """Bind request context for structured logging.

    Args:
        request_id: Unique request identifier.
        **kwargs: Additional context to bind.
    """
    request_id_var.set(request_id)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, **kwargs)


def clear_request_context() -> None:
    """Clear request context after request completes."""
    request_id_var.set(None)
    structlog.contextvars.clear_contextvars()
