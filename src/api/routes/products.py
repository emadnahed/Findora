"""Products API endpoints for CRUD operations."""

import uuid

from fastapi import APIRouter, Request, Response, status

from src.core.exceptions import NotFoundError
from src.core.logging import get_logger
from src.core.rate_limit import get_limiter
from src.models.product import (
    BulkOperationResult,
    IndexResponse,
    Product,
    ProductCreate,
)
from src.services.indexing import get_indexing_service

router = APIRouter(prefix="/api/v1/products", tags=["products"])
logger = get_logger(__name__)
limiter = get_limiter()


@router.post("", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("100/minute")
async def create_product(
    request: Request, response: Response, product_data: ProductCreate
) -> IndexResponse:
    """Create a new product.

    Args:
        request: The incoming request (required for rate limiting).
        response: The response object (required for rate limit headers).
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

    logger.info(
        "product_created",
        product_id=product_id,
        category=product_data.category,
    )

    return IndexResponse(
        id=product_id,
        result=result["result"],
        index=indexing_service.index_name,
    )


@router.get("/{product_id}", response_model=Product)
@limiter.limit("100/minute")
async def get_product(
    request: Request, response: Response, product_id: str
) -> Product:
    """Get a product by ID.

    Args:
        request: The incoming request (required for rate limiting).
        response: The response object (required for rate limit headers).
        product_id: ID of the product to retrieve.

    Returns:
        Product if found.

    Raises:
        NotFoundError: 404 if product not found.
    """
    indexing_service = get_indexing_service()

    product = await indexing_service.get_product(product_id)

    if product is None:
        raise NotFoundError(
            message=f"Product with ID '{product_id}' not found",
            details={"product_id": product_id},
        )

    return product


@router.put("/{product_id}", response_model=IndexResponse)
@limiter.limit("100/minute")
async def update_product(
    request: Request, response: Response, product_id: str, product_data: ProductCreate
) -> IndexResponse:
    """Update an existing product.

    Args:
        request: The incoming request (required for rate limiting).
        response: The response object (required for rate limit headers).
        product_id: ID of the product to update.
        product_data: New product data.

    Returns:
        IndexResponse with the update result.

    Raises:
        NotFoundError: 404 if product not found.
    """
    indexing_service = get_indexing_service()

    if not await indexing_service.product_exists(product_id):
        raise NotFoundError(
            message=f"Product with ID '{product_id}' not found",
            details={"product_id": product_id},
        )

    product = Product(
        id=product_id,
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        category=product_data.category,
    )

    result = await indexing_service.index_product(product)

    logger.info(
        "product_updated",
        product_id=product_id,
        category=product_data.category,
    )

    return IndexResponse(
        id=product_id,
        result=result["result"],
        index=indexing_service.index_name,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("100/minute")
async def delete_product(
    request: Request, response: Response, product_id: str
) -> Response:
    """Delete a product by ID.

    Args:
        request: The incoming request (required for rate limiting).
        response: The response object (required for rate limit headers).
        product_id: ID of the product to delete.

    Returns:
        204 No Content on success.

    Raises:
        NotFoundError: 404 if product not found.
    """
    indexing_service = get_indexing_service()

    result = await indexing_service.delete_product(product_id)

    if result is None:
        raise NotFoundError(
            message=f"Product with ID '{product_id}' not found",
            details={"product_id": product_id},
        )

    logger.info("product_deleted", product_id=product_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bulk", response_model=BulkOperationResult)
@limiter.limit("50/minute")
async def bulk_index_products(
    request: Request, response: Response, products: list[Product]
) -> BulkOperationResult:
    """Bulk index multiple products.

    Args:
        request: The incoming request (required for rate limiting).
        response: The response object (required for rate limit headers).
        products: List of products to index.

    Returns:
        BulkOperationResult with success/error counts.
    """
    indexing_service = get_indexing_service()

    result = await indexing_service.bulk_index_products(products)

    logger.info(
        "bulk_products_indexed",
        total=len(products),
        success_count=result.success_count,
        error_count=result.error_count,
    )

    return result


@router.post("/bulk/delete", response_model=BulkOperationResult)
@limiter.limit("50/minute")
async def bulk_delete_products(
    request: Request, response: Response, product_ids: list[str]
) -> BulkOperationResult:
    """Bulk delete multiple products.

    Args:
        request: The incoming request (required for rate limiting).
        response: The response object (required for rate limit headers).
        product_ids: List of product IDs to delete.

    Returns:
        BulkOperationResult with success/error counts.
    """
    indexing_service = get_indexing_service()

    result = await indexing_service.bulk_delete_products(product_ids)

    logger.info(
        "bulk_products_deleted",
        total=len(product_ids),
        success_count=result.success_count,
        error_count=result.error_count,
    )

    return result
