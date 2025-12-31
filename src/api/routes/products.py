"""Products API endpoints for CRUD operations."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from src.models.product import (
    BulkOperationResult,
    IndexResponse,
    Product,
    ProductCreate,
)
from src.services.indexing import get_indexing_service

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post("", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def create_product(product_data: ProductCreate) -> IndexResponse:
    """Create a new product.

    Args:
        product_data: Product data to create.

    Returns:
        IndexResponse with the created product ID.
    """
    indexing_service = get_indexing_service()

    # Generate a unique ID for the new product
    product_id = str(uuid.uuid4())

    product = Product(
        id=product_id,
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        category=product_data.category,
    )

    result = await indexing_service.index_product(product)

    return IndexResponse(
        id=product_id,
        result=result.get("result", "created"),
        index=indexing_service.index_name,
    )


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: str) -> Product:
    """Get a product by ID.

    Args:
        product_id: ID of the product to retrieve.

    Returns:
        Product if found.

    Raises:
        HTTPException: 404 if product not found.
    """
    indexing_service = get_indexing_service()

    product = await indexing_service.get_product(product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found",
        )

    return product


@router.put("/{product_id}", response_model=IndexResponse)
async def update_product(product_id: str, product_data: ProductCreate) -> IndexResponse:
    """Update an existing product.

    Args:
        product_id: ID of the product to update.
        product_data: New product data.

    Returns:
        IndexResponse with the update result.
    """
    indexing_service = get_indexing_service()

    product = Product(
        id=product_id,
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        category=product_data.category,
    )

    result = await indexing_service.index_product(product)

    return IndexResponse(
        id=product_id,
        result=result.get("result", "updated"),
        index=indexing_service.index_name,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: str) -> Response:
    """Delete a product by ID.

    Args:
        product_id: ID of the product to delete.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException: 404 if product not found.
    """
    indexing_service = get_indexing_service()

    result = await indexing_service.delete_product(product_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bulk", response_model=BulkOperationResult)
async def bulk_index_products(products: list[Product]) -> BulkOperationResult:
    """Bulk index multiple products.

    Args:
        products: List of products to index.

    Returns:
        BulkOperationResult with success/error counts.
    """
    indexing_service = get_indexing_service()

    return await indexing_service.bulk_index_products(products)


@router.post("/bulk/delete", response_model=BulkOperationResult)
async def bulk_delete_products(product_ids: list[str]) -> BulkOperationResult:
    """Bulk delete multiple products.

    Args:
        product_ids: List of product IDs to delete.

    Returns:
        BulkOperationResult with success/error counts.
    """
    indexing_service = get_indexing_service()

    return await indexing_service.bulk_delete_products(product_ids)
