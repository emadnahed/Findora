"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from src.models.product import (
    Product,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SortField,
    SortOrder,
)


class TestProductModel:
    """Tests for Product model."""

    def test_product_valid(self) -> None:
        """Test creating a valid product."""
        product = Product(
            id="1",
            name="iPhone 15",
            description="Apple smartphone with A17 chip",
            price=799.99,
        )

        assert product.id == "1"
        assert product.name == "iPhone 15"
        assert product.description == "Apple smartphone with A17 chip"
        assert product.price == 799.99

    def test_product_with_category(self) -> None:
        """Test product with optional category."""
        product = Product(
            id="1",
            name="iPhone 15",
            description="Apple smartphone",
            price=799.99,
            category="Electronics",
        )

        assert product.category == "Electronics"

    def test_product_category_default_none(self) -> None:
        """Test product category defaults to None."""
        product = Product(
            id="1",
            name="iPhone 15",
            description="Apple smartphone",
            price=799.99,
        )

        assert product.category is None

    def test_product_missing_required_field(self) -> None:
        """Test product validation fails without required fields."""
        with pytest.raises(ValidationError):
            Product(
                id="1",
                name="iPhone 15",
                # missing description and price
            )

    def test_product_invalid_price_type(self) -> None:
        """Test product validation fails with invalid price."""
        with pytest.raises(ValidationError):
            Product(
                id="1",
                name="iPhone 15",
                description="Test",
                price="not a number",  # type: ignore[arg-type]
            )

    def test_product_negative_price(self) -> None:
        """Test product validation fails with negative price."""
        with pytest.raises(ValidationError):
            Product(
                id="1",
                name="iPhone 15",
                description="Test",
                price=-100.0,
            )

    def test_product_to_dict(self) -> None:
        """Test product serialization to dict."""
        product = Product(
            id="1",
            name="iPhone 15",
            description="Apple smartphone",
            price=799.99,
        )

        data = product.model_dump()

        assert data["id"] == "1"
        assert data["name"] == "iPhone 15"
        assert data["price"] == 799.99

    def test_product_from_dict(self) -> None:
        """Test product creation from dict."""
        data = {
            "id": "1",
            "name": "iPhone 15",
            "description": "Apple smartphone",
            "price": 799.99,
        }

        product = Product.model_validate(data)

        assert product.id == "1"
        assert product.name == "iPhone 15"


class TestSearchQueryModel:
    """Tests for SearchQuery model."""

    def test_search_query_minimal(self) -> None:
        """Test search query with only required field."""
        query = SearchQuery(q="iphone")

        assert query.q == "iphone"
        assert query.fuzzy is True  # default
        assert query.page == 1  # default
        assert query.size == 10  # default
        assert query.sort_by == SortField.RELEVANCE  # default
        assert query.sort_order == SortOrder.DESC  # default

    def test_search_query_all_fields(self) -> None:
        """Test search query with all fields."""
        query = SearchQuery(
            q="smartphone",
            fuzzy=False,
            page=2,
            size=20,
            min_price=100.0,
            max_price=1000.0,
            category="Electronics",
            categories=["Electronics", "Phones"],
            sort_by=SortField.PRICE,
            sort_order=SortOrder.ASC,
        )

        assert query.q == "smartphone"
        assert query.fuzzy is False
        assert query.page == 2
        assert query.size == 20
        assert query.min_price == 100.0
        assert query.max_price == 1000.0
        assert query.category == "Electronics"
        assert query.categories == ["Electronics", "Phones"]
        assert query.sort_by == SortField.PRICE
        assert query.sort_order == SortOrder.ASC

    def test_search_query_empty_string(self) -> None:
        """Test search query requires non-empty string."""
        with pytest.raises(ValidationError):
            SearchQuery(q="")

    def test_search_query_page_minimum(self) -> None:
        """Test page must be at least 1."""
        with pytest.raises(ValidationError):
            SearchQuery(q="test", page=0)

    def test_search_query_size_minimum(self) -> None:
        """Test size must be at least 1."""
        with pytest.raises(ValidationError):
            SearchQuery(q="test", size=0)

    def test_search_query_size_maximum(self) -> None:
        """Test size must not exceed 100."""
        with pytest.raises(ValidationError):
            SearchQuery(q="test", size=101)


class TestSearchResultModel:
    """Tests for SearchResult model."""

    def test_search_result_with_score(self) -> None:
        """Test search result includes score."""
        result = SearchResult(
            id="1",
            name="iPhone 15",
            description="Apple smartphone",
            price=799.99,
            score=1.5,
        )

        assert result.score == 1.5

    def test_search_result_with_highlights(self) -> None:
        """Test search result with highlighted matches."""
        result = SearchResult(
            id="1",
            name="iPhone 15",
            description="Apple smartphone",
            price=799.99,
            score=1.5,
            highlights={"name": ["<em>iPhone</em> 15"]},
        )

        assert result.highlights is not None
        assert "name" in result.highlights
        assert "<em>iPhone</em>" in result.highlights["name"][0]

    def test_search_result_highlights_default_none(self) -> None:
        """Test highlights default to None."""
        result = SearchResult(
            id="1",
            name="iPhone 15",
            description="Apple smartphone",
            price=799.99,
            score=1.5,
        )

        assert result.highlights is None


class TestSearchResponseModel:
    """Tests for SearchResponse model."""

    def test_search_response_with_results(self) -> None:
        """Test search response with results."""
        results = [
            SearchResult(
                id="1",
                name="iPhone 15",
                description="Apple smartphone",
                price=799.99,
                score=1.5,
            ),
        ]

        response = SearchResponse(
            query="iphone",
            total=1,
            page=1,
            size=10,
            total_pages=1,
            has_next=False,
            has_previous=False,
            results=results,
        )

        assert response.query == "iphone"
        assert response.total == 1
        assert len(response.results) == 1
        assert response.results[0].name == "iPhone 15"

    def test_search_response_empty_results(self) -> None:
        """Test search response with no results."""
        response = SearchResponse(
            query="nonexistent",
            total=0,
            page=1,
            size=10,
            total_pages=0,
            has_next=False,
            has_previous=False,
            results=[],
        )

        assert response.total == 0
        assert len(response.results) == 0
        assert response.total_pages == 0

    def test_search_response_pagination(self) -> None:
        """Test search response pagination fields."""
        response = SearchResponse(
            query="phone",
            total=50,
            page=3,
            size=10,
            total_pages=5,
            has_next=True,
            has_previous=True,
            results=[],
        )

        assert response.page == 3
        assert response.size == 10
        assert response.total == 50
        assert response.total_pages == 5
        assert response.has_next is True
        assert response.has_previous is True

    def test_search_response_first_page(self) -> None:
        """Test search response on first page."""
        response = SearchResponse(
            query="phone",
            total=50,
            page=1,
            size=10,
            total_pages=5,
            has_next=True,
            has_previous=False,
            results=[],
        )

        assert response.has_next is True
        assert response.has_previous is False

    def test_search_response_last_page(self) -> None:
        """Test search response on last page."""
        response = SearchResponse(
            query="phone",
            total=50,
            page=5,
            size=10,
            total_pages=5,
            has_next=False,
            has_previous=True,
            results=[],
        )

        assert response.has_next is False
        assert response.has_previous is True

    def test_search_response_took_field(self) -> None:
        """Test search response includes time taken."""
        response = SearchResponse(
            query="phone",
            total=10,
            page=1,
            size=10,
            total_pages=1,
            has_next=False,
            has_previous=False,
            results=[],
            took_ms=15,
        )

        assert response.took_ms == 15


class TestSortEnums:
    """Tests for sorting enums."""

    def test_sort_field_values(self) -> None:
        """Test SortField enum values."""
        assert SortField.RELEVANCE.value == "relevance"
        assert SortField.PRICE.value == "price"
        assert SortField.NAME.value == "name"

    def test_sort_order_values(self) -> None:
        """Test SortOrder enum values."""
        assert SortOrder.ASC.value == "asc"
        assert SortOrder.DESC.value == "desc"

    def test_sort_field_from_string(self) -> None:
        """Test creating SortField from string."""
        assert SortField("relevance") == SortField.RELEVANCE
        assert SortField("price") == SortField.PRICE
        assert SortField("name") == SortField.NAME

    def test_sort_order_from_string(self) -> None:
        """Test creating SortOrder from string."""
        assert SortOrder("asc") == SortOrder.ASC
        assert SortOrder("desc") == SortOrder.DESC
