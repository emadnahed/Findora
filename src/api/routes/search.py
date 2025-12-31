"""Search API endpoints."""

from fastapi import APIRouter, Query

from src.models.product import SearchQuery, SearchResponse, SortField, SortOrder
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
    category: str | None = Query(default=None, description="Single category filter"),
    categories: list[str] | None = Query(
        default=None, description="Multiple categories filter (OR logic)"
    ),
    sort_by: SortField = Query(
        default=SortField.RELEVANCE, description="Field to sort by"
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.DESC, description="Sort order (asc/desc)"
    ),
) -> SearchResponse:
    """Search for products.

    Performs a full-text search across product names and descriptions
    with optional fuzzy matching, filters, pagination, and sorting.

    Args:
        q: Search query string.
        fuzzy: Enable fuzzy matching for typo tolerance.
        page: Page number for pagination.
        size: Number of results per page.
        min_price: Filter by minimum price.
        max_price: Filter by maximum price.
        category: Filter by single category.
        categories: Filter by multiple categories (OR logic).
        sort_by: Field to sort results by (relevance, price, name).
        sort_order: Sort direction (asc/desc).

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
        categories=categories,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return await search_service.search(query)
