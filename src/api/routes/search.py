"""Search API endpoints."""

from fastapi import APIRouter, Query, Request, Response

from src.config.settings import get_settings
from src.core.logging import get_logger
from src.core.rate_limit import get_limiter
from src.models.product import SearchQuery, SearchResponse, SortField, SortOrder
from src.services.search import get_search_service

router = APIRouter(prefix="/api/v1", tags=["search"])
logger = get_logger(__name__)
limiter = get_limiter()
settings = get_settings()


@router.get("/search", response_model=SearchResponse)
@limiter.limit(settings.rate_limit_search)
async def search_products(
    request: Request,
    response: Response,
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
        request: The incoming request (required for rate limiting).
        response: The response object (required for rate limit headers).
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

    result = await search_service.search(query)

    logger.info(
        "search_executed",
        query=q,
        fuzzy=fuzzy,
        total_hits=result.total,
        results_returned=len(result.results),
        page=page,
        category=category,
    )

    return result
