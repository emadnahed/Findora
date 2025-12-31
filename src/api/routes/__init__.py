"""API route modules."""

from src.api.routes.products import router as products_router
from src.api.routes.search import router as search_router

__all__ = ["products_router", "search_router"]
