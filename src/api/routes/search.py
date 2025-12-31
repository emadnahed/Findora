"""Search API endpoints."""

from fastapi import APIRouter, Query

from src.models.product import SearchQuery, SearchResponse
from src.services.search import get_search_service

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search_products(
    q: str = Query(..., min_length=1, description="Search query string"),
    fuzzy: bool = Query(default=True, description="Enable fuzzy matching"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(default=10, ge=1, le=100, description="Results per page"),
    min_price: float | None = Query(default=None, description="Minimum price filter"),
    max_price: float | None = Query(default=None, description="Maximum price filter"),
    category: str | None = Query(default=None, description="Category filter"),
) -> SearchResponse:
    """Search for products.

    Performs a full-text search across product names and descriptions
    with optional fuzzy matching, price filtering, and category filtering.

    Args:
        q: Search query string.
        fuzzy: Enable fuzzy matching for typo tolerance.
        page: Page number for pagination.
        size: Number of results per page.
        min_price: Filter by minimum price.
        max_price: Filter by maximum price.
        category: Filter by category.

    Returns:
        SearchResponse with matching products and metadata.
    """
    search_service = get_search_service()

    query = SearchQuery(
        q=q,
        fuzzy=fuzzy,
        page=page,
        size=size,
        min_price=min_price,
        max_price=max_price,
        category=category,
    )

    return await search_service.search(query)
