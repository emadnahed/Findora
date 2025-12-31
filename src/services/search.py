"""Search service for Elasticsearch queries."""

from functools import lru_cache
from typing import Any, cast

from src.config.settings import Settings, get_settings
from src.core.cache import SearchCache, get_search_cache
from src.core.logging import get_logger
from src.elastic.client import ElasticsearchClient, get_elasticsearch_client
from src.models.product import (
    SearchQuery,
    SearchResponse,
    SearchResult,
    SortField,
)

logger = get_logger(__name__)


class SearchService:
    """Service for executing search queries against Elasticsearch."""

    def __init__(
        self,
        client: ElasticsearchClient,
        settings: Settings,
        cache: SearchCache | None = None,
    ) -> None:
        """Initialize the search service.

        Args:
            client: ElasticsearchClient instance.
            settings: Application settings.
            cache: Optional SearchCache instance for query caching.
        """
        self.client = client
        self.settings = settings
        self.index_name = settings.elasticsearch_index
        self.cache = cache
        self.cache_enabled = settings.cache_enabled and cache is not None

    def _get_cache_key_params(self, query: SearchQuery) -> dict[str, Any]:
        """Get cache key parameters from a search query.

        Args:
            query: Search query parameters.

        Returns:
            Dictionary of cache key parameters.
        """
        return {
            "q": query.q,
            "fuzzy": query.fuzzy,
            "page": query.page,
            "size": query.size,
            "min_price": query.min_price,
            "max_price": query.max_price,
            "category": query.category,
            "categories": query.categories,
            "sort_by": query.sort_by.value,
            "sort_order": query.sort_order.value,
            "index": self.index_name,
        }

    async def search(self, query: SearchQuery) -> SearchResponse:
        """Execute a search query.

        Args:
            query: Search query parameters.

        Returns:
            SearchResponse with results and metadata.
        """
        # Check cache first
        if self.cache_enabled and self.cache:
            cache_params = self._get_cache_key_params(query)
            cached_result = self.cache.get(cache_params)
            if cached_result is not None:
                logger.debug("search_cache_hit", query=query.q)
                # Cache stores SearchResponse objects
                return cast("SearchResponse", cached_result)

        es_client = await self.client.get_client()

        # Build the query
        es_query = self._build_query(query)

        # Calculate pagination
        from_ = (query.page - 1) * query.size

        # Build sort configuration
        sort = self._build_sort(query)

        # Execute search
        search_params: dict[str, Any] = {
            "index": self.index_name,
            "query": es_query,
            "from_": from_,
            "size": query.size,
            "highlight": self._build_highlight(),
        }

        # Only add sort if not sorting by relevance (default ES behavior)
        if sort:
            search_params["sort"] = sort

        logger.debug(
            "executing_search",
            query=query.q,
            fuzzy=query.fuzzy,
            page=query.page,
            size=query.size,
            index=self.index_name,
        )

        es_response = await es_client.search(**search_params)

        # Parse results
        result = self._parse_response(query, dict(es_response))

        logger.debug(
            "search_completed",
            query=query.q,
            total_hits=result.total,
            took_ms=result.took_ms,
        )

        # Cache the result
        if self.cache_enabled and self.cache:
            cache_params = self._get_cache_key_params(query)
            self.cache.set(cache_params, result)

        return result

    def _build_query(self, query: SearchQuery) -> dict[str, Any]:
        """Build Elasticsearch query from SearchQuery.

        Args:
            query: Search query parameters.

        Returns:
            Elasticsearch query dict.
        """
        # Base multi_match query
        multi_match: dict[str, Any] = {
            "query": query.q,
            "fields": ["name^2", "description"],  # boost name field
            "type": "best_fields",
        }

        # Add fuzziness if enabled
        if query.fuzzy:
            multi_match["fuzziness"] = "AUTO"

        # Check if we need filters
        filters = self._build_filters(query)

        if filters:
            # Use bool query with must + filter
            return {
                "bool": {
                    "must": {"multi_match": multi_match},
                    "filter": filters,
                }
            }

        # Simple multi_match without filters
        return {"multi_match": multi_match}

    def _build_sort(self, query: SearchQuery) -> list[dict[str, Any]] | None:
        """Build sort configuration for the query.

        Args:
            query: Search query parameters.

        Returns:
            List of sort clauses or None for relevance sorting.
        """
        # Relevance sorting uses default ES behavior (no explicit sort)
        if query.sort_by == SortField.RELEVANCE:
            return None

        order = query.sort_order.value

        if query.sort_by == SortField.PRICE:
            return [{"price": {"order": order}}]
        elif query.sort_by == SortField.NAME:
            # Use .keyword for exact sorting on text fields
            return [{"name.keyword": {"order": order}}]

        return None

    def _build_filters(self, query: SearchQuery) -> list[dict[str, Any]]:
        """Build filter clauses for the query.

        Args:
            query: Search query parameters.

        Returns:
            List of filter clauses.
        """
        filters: list[dict[str, Any]] = []

        # Price range filter
        if query.min_price is not None or query.max_price is not None:
            price_range: dict[str, Any] = {}
            if query.min_price is not None:
                price_range["gte"] = query.min_price
            if query.max_price is not None:
                price_range["lte"] = query.max_price
            filters.append({"range": {"price": price_range}})

        # Multi-category filter (OR logic) takes precedence
        if query.categories:
            filters.append({"terms": {"category": query.categories}})
        # Single category filter (backwards compatible)
        elif query.category is not None:
            filters.append({"term": {"category": query.category}})

        return filters

    def _build_highlight(self) -> dict[str, Any]:
        """Build highlight configuration.

        Returns:
            Highlight configuration dict.
        """
        return {
            "fields": {
                "name": {},
                "description": {},
            },
            "pre_tags": ["<em>"],
            "post_tags": ["</em>"],
        }

    def _parse_response(
        self, query: SearchQuery, response: dict[str, Any]
    ) -> SearchResponse:
        """Parse Elasticsearch response into SearchResponse.

        Args:
            query: Original search query.
            response: Raw Elasticsearch response.

        Returns:
            Parsed SearchResponse.
        """
        hits = response["hits"]
        total = hits["total"]["value"]
        took = response.get("took", 0)

        # Calculate pagination metadata
        total_pages = (total + query.size - 1) // query.size if total > 0 else 0
        has_next = query.page < total_pages
        has_previous = query.page > 1

        results: list[SearchResult] = []
        for hit in hits["hits"]:
            source = hit["_source"]
            # When sorting by non-relevance fields, _score may be None
            score = hit.get("_score") or 0.0
            result = SearchResult(
                id=hit["_id"],
                name=source["name"],
                description=source["description"],
                price=source["price"],
                category=source.get("category"),
                score=score,
                highlights=hit.get("highlight"),
            )
            results.append(result)

        return SearchResponse(
            query=query.q,
            total=total,
            page=query.page,
            size=query.size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
            results=results,
            took_ms=took,
        )


@lru_cache
def get_search_service() -> SearchService:
    """Get a singleton SearchService instance.

    Returns:
        Cached SearchService instance.
    """
    settings = get_settings()
    cache = get_search_cache() if settings.cache_enabled else None
    return SearchService(get_elasticsearch_client(), settings, cache)
