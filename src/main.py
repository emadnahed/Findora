"""FastAPI application entry point."""

from typing import Any

from fastapi import FastAPI

from src.api.routes.search import router as search_router
from src.config.settings import get_settings
from src.elastic.client import get_elasticsearch_client

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

# Include routers
app.include_router(search_router)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint with Elasticsearch status."""
    es_client = get_elasticsearch_client()

    # Check Elasticsearch connectivity
    es_connected = await es_client.ping()
    es_health = await es_client.health_check()

    # Determine overall status
    cluster_status = es_health.get("status", "unavailable")
    if es_connected and cluster_status in ("green", "yellow"):
        overall_status = "healthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "version": settings.app_version,
        "elasticsearch": {
            "connected": es_connected,
            "cluster_status": cluster_status,
        },
    }
