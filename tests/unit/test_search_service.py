"""Unit tests for search service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config.settings import Settings
from src.models.product import SearchQuery, SortField, SortOrder


class TestSearchService:
    """Tests for SearchService."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Provide test settings."""
        return Settings(
            elasticsearch_url="http://localhost:9200",
            elasticsearch_index="test_products",
        )

    @pytest.fixture
    def mock_es_client(self) -> MagicMock:
        """Provide mock Elasticsearch client."""
        mock = MagicMock()
        mock.search = AsyncMock()
        return mock

    @pytest.fixture
    def mock_elastic_client(
        self, mock_settings: Settings, mock_es_client: MagicMock
    ) -> MagicMock:
        """Provide mock ElasticsearchClient."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)
        client._client = mock_es_client
        return client

    def test_search_service_initialization(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test SearchService initializes correctly."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)

        assert service.client == mock_elastic_client
        assert service.index_name == mock_settings.elasticsearch_index

    @pytest.mark.asyncio
    async def test_search_basic_query(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test basic search query execution."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 10,
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_id": "1",
                            "_score": 1.5,
                            "_source": {
                                "name": "iPhone 15",
                                "description": "Apple smartphone",
                                "price": 799.99,
                            },
                        }
                    ],
                },
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="iphone")

        response = await service.search(query)

        assert response.total == 1
        assert response.query == "iphone"
        assert len(response.results) == 1
        assert response.results[0].name == "iPhone 15"

    @pytest.mark.asyncio
    async def test_search_returns_score(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test search results include relevance score."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_id": "1",
                            "_score": 2.5,
                            "_source": {
                                "name": "iPhone 15",
                                "description": "Apple smartphone",
                                "price": 799.99,
                            },
                        }
                    ],
                },
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="iphone")

        response = await service.search(query)

        assert response.results[0].score == 2.5

    @pytest.mark.asyncio
    async def test_search_with_highlights(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test search results include highlights."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_id": "1",
                            "_score": 2.5,
                            "_source": {
                                "name": "iPhone 15",
                                "description": "Apple smartphone",
                                "price": 799.99,
                            },
                            "highlight": {
                                "name": ["<em>iPhone</em> 15"],
                            },
                        }
                    ],
                },
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="iphone")

        response = await service.search(query)

        assert response.results[0].highlights is not None
        assert "name" in response.results[0].highlights

    @pytest.mark.asyncio
    async def test_search_no_results(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test search with no matching results."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 2,
                "hits": {
                    "total": {"value": 0},
                    "hits": [],
                },
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="nonexistent")

        response = await service.search(query)

        assert response.total == 0
        assert len(response.results) == 0

    @pytest.mark.asyncio
    async def test_search_pagination(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test search pagination parameters."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {
                    "total": {"value": 50},
                    "hits": [],
                },
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", page=3, size=20)

        response = await service.search(query)

        # Verify pagination in response
        assert response.page == 3
        assert response.size == 20

        # Verify ES was called with correct from/size
        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        assert call_kwargs["from_"] == 40  # (page-1) * size
        assert call_kwargs["size"] == 20

    @pytest.mark.asyncio
    async def test_search_took_time(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test search response includes query time."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 15,
                "hits": {
                    "total": {"value": 0},
                    "hits": [],
                },
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="test")

        response = await service.search(query)

        assert response.took_ms == 15


class TestSearchQueryBuilder:
    """Tests for search query building."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Provide test settings."""
        return Settings(
            elasticsearch_url="http://localhost:9200",
            elasticsearch_index="test_products",
        )

    @pytest.fixture
    def mock_elastic_client(self, mock_settings: Settings) -> MagicMock:
        """Provide mock ElasticsearchClient."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)
        client._client = MagicMock()
        client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {"total": {"value": 0}, "hits": []},
            }
        )
        return client

    @pytest.mark.asyncio
    async def test_fuzzy_search_enabled(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test fuzzy matching is applied when enabled."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="iphon", fuzzy=True)

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        query_body = call_kwargs["query"]

        # Should use multi_match with fuzziness
        assert "multi_match" in query_body
        assert query_body["multi_match"]["fuzziness"] == "AUTO"

    @pytest.mark.asyncio
    async def test_fuzzy_search_disabled(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test exact matching when fuzzy is disabled."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="iphone", fuzzy=False)

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        query_body = call_kwargs["query"]

        # Should use multi_match without fuzziness
        assert "multi_match" in query_body
        assert "fuzziness" not in query_body["multi_match"]

    @pytest.mark.asyncio
    async def test_multi_field_search(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test search queries multiple fields."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="smartphone")

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        query_body = call_kwargs["query"]

        # Should search across name and description fields
        fields = query_body["multi_match"]["fields"]
        assert "name^2" in fields  # name boosted
        assert "description" in fields

    @pytest.mark.asyncio
    async def test_price_filter_min(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test minimum price filter."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", min_price=500.0)

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        query_body = call_kwargs["query"]

        # Should have bool query with filter
        assert "bool" in query_body
        assert "filter" in query_body["bool"]

    @pytest.mark.asyncio
    async def test_price_filter_max(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test maximum price filter."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", max_price=1000.0)

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        query_body = call_kwargs["query"]

        assert "bool" in query_body
        assert "filter" in query_body["bool"]

    @pytest.mark.asyncio
    async def test_category_filter(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test category filter."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", category="Electronics")

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        query_body = call_kwargs["query"]

        assert "bool" in query_body
        assert "filter" in query_body["bool"]

    @pytest.mark.asyncio
    async def test_highlight_configuration(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test highlight configuration is sent."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone")

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs

        assert "highlight" in call_kwargs
        assert "fields" in call_kwargs["highlight"]

    @pytest.mark.asyncio
    async def test_multi_category_filter(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test multiple categories filter with OR logic."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", categories=["Electronics", "Phones"])

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        query_body = call_kwargs["query"]

        # Should have bool query with terms filter
        assert "bool" in query_body
        assert "filter" in query_body["bool"]

        # Find the terms filter
        filters = query_body["bool"]["filter"]
        terms_filter = next(
            (f for f in filters if "terms" in f and "category" in f["terms"]), None
        )
        assert terms_filter is not None
        assert terms_filter["terms"]["category"] == ["Electronics", "Phones"]

    @pytest.mark.asyncio
    async def test_multi_category_overrides_single_category(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test categories filter takes precedence over single category."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(
            q="phone", category="Single", categories=["Electronics", "Phones"]
        )

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        query_body = call_kwargs["query"]

        filters = query_body["bool"]["filter"]
        # Should use terms (multi) not term (single)
        terms_filter = next((f for f in filters if "terms" in f), None)
        term_filter = next((f for f in filters if "term" in f), None)

        assert terms_filter is not None
        assert term_filter is None


class TestSortBuilder:
    """Tests for sort building functionality."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Provide test settings."""
        return Settings(
            elasticsearch_url="http://localhost:9200",
            elasticsearch_index="test_products",
        )

    @pytest.fixture
    def mock_elastic_client(self, mock_settings: Settings) -> MagicMock:
        """Provide mock ElasticsearchClient."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)
        client._client = MagicMock()
        client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {"total": {"value": 0}, "hits": []},
            }
        )
        return client

    @pytest.mark.asyncio
    async def test_sort_by_relevance_no_sort_param(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test relevance sorting does not add sort parameter."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", sort_by=SortField.RELEVANCE)

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        assert "sort" not in call_kwargs

    @pytest.mark.asyncio
    async def test_sort_by_price_asc(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test sorting by price ascending."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", sort_by=SortField.PRICE, sort_order=SortOrder.ASC)

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        assert "sort" in call_kwargs
        assert call_kwargs["sort"] == [{"price": {"order": "asc"}}]

    @pytest.mark.asyncio
    async def test_sort_by_price_desc(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test sorting by price descending."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(
            q="phone", sort_by=SortField.PRICE, sort_order=SortOrder.DESC
        )

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        assert "sort" in call_kwargs
        assert call_kwargs["sort"] == [{"price": {"order": "desc"}}]

    @pytest.mark.asyncio
    async def test_sort_by_name_asc(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test sorting by name ascending uses keyword field."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", sort_by=SortField.NAME, sort_order=SortOrder.ASC)

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        assert "sort" in call_kwargs
        assert call_kwargs["sort"] == [{"name.keyword": {"order": "asc"}}]

    @pytest.mark.asyncio
    async def test_sort_by_name_desc(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test sorting by name descending uses keyword field."""
        from src.services.search import SearchService

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", sort_by=SortField.NAME, sort_order=SortOrder.DESC)

        await service.search(query)

        call_kwargs = mock_elastic_client._client.search.call_args.kwargs
        assert "sort" in call_kwargs
        assert call_kwargs["sort"] == [{"name.keyword": {"order": "desc"}}]


class TestPaginationMetadata:
    """Tests for enhanced pagination metadata."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Provide test settings."""
        return Settings(
            elasticsearch_url="http://localhost:9200",
            elasticsearch_index="test_products",
        )

    @pytest.fixture
    def mock_elastic_client(self, mock_settings: Settings) -> MagicMock:
        """Provide mock ElasticsearchClient."""
        from src.elastic.client import ElasticsearchClient

        client = ElasticsearchClient(mock_settings)
        client._client = MagicMock()
        return client

    @pytest.mark.asyncio
    async def test_pagination_first_page(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test pagination metadata on first page."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {"total": {"value": 50}, "hits": []},
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", page=1, size=10)

        response = await service.search(query)

        assert response.total_pages == 5
        assert response.has_next is True
        assert response.has_previous is False

    @pytest.mark.asyncio
    async def test_pagination_middle_page(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test pagination metadata on middle page."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {"total": {"value": 50}, "hits": []},
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", page=3, size=10)

        response = await service.search(query)

        assert response.total_pages == 5
        assert response.has_next is True
        assert response.has_previous is True

    @pytest.mark.asyncio
    async def test_pagination_last_page(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test pagination metadata on last page."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {"total": {"value": 50}, "hits": []},
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", page=5, size=10)

        response = await service.search(query)

        assert response.total_pages == 5
        assert response.has_next is False
        assert response.has_previous is True

    @pytest.mark.asyncio
    async def test_pagination_single_page(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test pagination metadata when only one page."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {"total": {"value": 5}, "hits": []},
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", page=1, size=10)

        response = await service.search(query)

        assert response.total_pages == 1
        assert response.has_next is False
        assert response.has_previous is False

    @pytest.mark.asyncio
    async def test_pagination_no_results(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test pagination metadata with no results."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {"total": {"value": 0}, "hits": []},
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="nonexistent", page=1, size=10)

        response = await service.search(query)

        assert response.total_pages == 0
        assert response.has_next is False
        assert response.has_previous is False

    @pytest.mark.asyncio
    async def test_pagination_partial_last_page(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test total_pages calculation with partial last page."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {"total": {"value": 45}, "hits": []},
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", page=1, size=10)

        response = await service.search(query)

        # 45 results / 10 per page = 5 pages (4 full + 1 partial)
        assert response.total_pages == 5

    @pytest.mark.asyncio
    async def test_score_defaults_to_zero_when_none(
        self, mock_elastic_client: MagicMock, mock_settings: Settings
    ) -> None:
        """Test score defaults to 0.0 when ES returns None (non-relevance sort)."""
        from src.services.search import SearchService

        mock_elastic_client._client.search = AsyncMock(
            return_value={
                "took": 5,
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_id": "1",
                            "_score": None,  # ES returns null for non-relevance sort
                            "_source": {
                                "name": "Test Product",
                                "description": "Description",
                                "price": 99.99,
                            },
                        }
                    ],
                },
            }
        )

        service = SearchService(mock_elastic_client, mock_settings)
        query = SearchQuery(q="phone", sort_by=SortField.PRICE)

        response = await service.search(query)

        assert response.results[0].score == 0.0


class TestGetSearchService:
    """Tests for get_search_service factory."""

    def test_get_search_service_returns_instance(self) -> None:
        """Test factory returns SearchService instance."""
        from src.services.search import get_search_service

        service = get_search_service()

        assert service is not None
        assert service.index_name is not None
