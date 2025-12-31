"""Product models and search schemas."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SortField(str, Enum):
    """Available fields for sorting search results."""

    RELEVANCE = "relevance"
    PRICE = "price"
    NAME = "name"


class SortOrder(str, Enum):
    """Sort order direction."""

    ASC = "asc"
    DESC = "desc"


class Product(BaseModel):
    """Product model for Elasticsearch documents."""

    id: str = Field(..., description="Unique product identifier")
    name: str = Field(..., min_length=1, description="Product name")
    description: str = Field(..., min_length=1, description="Product description")
    price: float = Field(..., gt=0, description="Product price (must be positive)")
    category: str | None = Field(default=None, description="Product category")


class SearchQuery(BaseModel):
    """Search query parameters."""

    q: str = Field(..., min_length=1, description="Search query string")
    fuzzy: bool = Field(default=True, description="Enable fuzzy matching")
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    size: int = Field(default=10, ge=1, le=100, description="Results per page")
    min_price: float | None = Field(default=None, description="Minimum price filter")
    max_price: float | None = Field(default=None, description="Maximum price filter")
    category: str | None = Field(default=None, description="Single category filter")
    categories: list[str] | None = Field(
        default=None, description="Multiple categories filter (OR logic)"
    )
    sort_by: SortField = Field(
        default=SortField.RELEVANCE, description="Field to sort results by"
    )
    sort_order: SortOrder = Field(
        default=SortOrder.DESC, description="Sort order (asc/desc)"
    )


class SearchResult(Product):
    """Search result with relevance score and highlights."""

    score: float = Field(..., description="Relevance score from Elasticsearch")
    highlights: dict[str, list[str]] | None = Field(
        default=None, description="Highlighted matching text fragments"
    )


class SearchResponse(BaseModel):
    """Search response with results and pagination."""

    query: str = Field(..., description="Original search query")
    total: int = Field(..., ge=0, description="Total number of matching documents")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Results per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    results: list[SearchResult] = Field(
        default_factory=list, description="Search results"
    )
    took_ms: int | None = Field(default=None, description="Query execution time in ms")


class ProductCreate(BaseModel):
    """Schema for creating a new product."""

    name: str = Field(..., min_length=1, description="Product name")
    description: str = Field(..., min_length=1, description="Product description")
    price: float = Field(..., gt=0, description="Product price (must be positive)")
    category: str | None = Field(default=None, description="Product category")


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""

    success_count: int = Field(..., ge=0, description="Number of successful operations")
    error_count: int = Field(..., ge=0, description="Number of failed operations")
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="Details of failed operations"
    )


class IndexResponse(BaseModel):
    """Response for single document indexing."""

    id: str = Field(..., description="Document ID")
    result: str = Field(..., description="Operation result (created/updated)")
    index: str = Field(..., description="Index name")
