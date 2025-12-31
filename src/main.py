"""FastAPI application entry point."""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from slowapi.errors import RateLimitExceeded

from src.api.routes.products import router as products_router
from src.api.routes.search import router as search_router
from src.config.settings import get_settings
from src.core.cache import get_search_cache
from src.core.exceptions import FindoraException, global_exception_handler
from src.core.logging import (
    bind_request_context,
    clear_request_context,
    get_logger,
    setup_logging,
)
from src.core.metrics import get_metrics_collector
from src.core.rate_limit import get_limiter, rate_limit_exceeded_handler
from src.elastic.client import get_elasticsearch_client

settings = get_settings()
logger = get_logger(__name__)
limiter = get_limiter()
metrics = get_metrics_collector()


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore[no-untyped-def]
    """Application lifespan handler for startup/shutdown.

    Args:
        _app: FastAPI application instance (required by lifespan signature).
    """
    # Startup
    setup_logging(log_level=settings.log_level, log_format=settings.log_format)
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    yield
    # Shutdown
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Add rate limiter state
app.state.limiter = limiter

# Register exception handlers
app.add_exception_handler(FindoraException, global_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]


@app.middleware("http")
async def request_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Middleware for request tracking and logging."""
    # Generate unique request ID
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    # Bind request context for logging
    bind_request_context(
        request_id=request_id,
        method=request.method,
        path=str(request.url.path),
    )

    # Track request timing
    start_time = time.perf_counter()

    try:
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Record metrics (skip for metrics endpoint to avoid recursion)
        if not request.url.path.startswith("/metrics"):
            metrics.record_request(
                endpoint=str(request.url.path),
                status_code=response.status_code,
                latency_ms=duration_ms,
            )

        # Log request completion
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
    except Exception:
        # Log unhandled exceptions (let them propagate for default handling)
        logger.exception(
            "unhandled_exception",
            path=str(request.url.path),
            method=request.method,
        )
        raise
    finally:
        clear_request_context()


# Include routers
app.include_router(search_router)
app.include_router(products_router)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint with Elasticsearch status."""
    es_client = get_elasticsearch_client()

    # Check Elasticsearch connectivity
    es_connected = await es_client.ping()
    es_health = await es_client.health_check()

    # Get cache stats
    cache_stats = get_search_cache().stats() if settings.cache_enabled else None

    # Get metrics summary
    app_metrics = metrics.get_metrics()

    # Determine overall status
    cluster_status = es_health.get("status", "unavailable")
    if es_connected and cluster_status in ("green", "yellow"):
        overall_status = "healthy"
    else:
        overall_status = "degraded"

    response: dict[str, Any] = {
        "status": overall_status,
        "version": settings.app_version,
        "uptime_seconds": app_metrics["uptime_seconds"],
        "elasticsearch": {
            "connected": es_connected,
            "cluster_status": cluster_status,
            "number_of_nodes": es_health.get("number_of_nodes"),
        },
    }

    if cache_stats:
        response["cache"] = cache_stats

    return response


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics_endpoint() -> str:
    """Prometheus-format metrics endpoint."""
    return metrics.get_prometheus_metrics()


@app.get("/metrics/json")
async def metrics_json() -> dict[str, Any]:
    """JSON format metrics endpoint."""
    return metrics.get_metrics()
