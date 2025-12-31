"""Unit tests for search service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config.settings import Settings
from src.models.product import SearchQuery


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


class TestGetSearchService:
    """Tests for get_search_service factory."""

    def test_get_search_service_returns_instance(self) -> None:
        """Test factory returns SearchService instance."""
        from src.services.search import get_search_service

        service = get_search_service()

        assert service is not None
        assert service.index_name is not None
