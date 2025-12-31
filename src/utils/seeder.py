"""Sample data seeder for development and testing."""

from typing import Any

from src.elastic.index_manager import get_index_manager
from src.elastic.mappings import PRODUCT_MAPPINGS, get_product_settings
from src.models.product import Product
from src.services.indexing import get_indexing_service

# Sample product data
SAMPLE_PRODUCTS: list[Product] = [
    Product(
        id="1",
        name="iPhone 15 Pro",
        description="Apple's flagship smartphone with A17 Pro chip, titanium design, and advanced camera system",
        price=999.99,
        category="Electronics",
    ),
    Product(
        id="2",
        name="iPhone 15",
        description="Apple smartphone with A16 Bionic chip and Dynamic Island",
        price=799.99,
        category="Electronics",
    ),
    Product(
        id="3",
        name="Samsung Galaxy S24 Ultra",
        description="Samsung's premium Android phone with Snapdragon 8 Gen 3 and S Pen",
        price=1199.99,
        category="Electronics",
    ),
    Product(
        id="4",
        name="Samsung Galaxy S24",
        description="Android flagship with AI features and excellent display",
        price=799.99,
        category="Electronics",
    ),
    Product(
        id="5",
        name="Google Pixel 8 Pro",
        description="Google's flagship phone with Tensor G3 chip and best-in-class AI camera",
        price=899.99,
        category="Electronics",
    ),
    Product(
        id="6",
        name="Google Pixel 8",
        description="Google phone with Tensor G3 processor and 7 years of updates",
        price=699.99,
        category="Electronics",
    ),
    Product(
        id="7",
        name="MacBook Pro 14",
        description="Apple laptop with M3 Pro chip, stunning Liquid Retina XDR display",
        price=1999.99,
        category="Computers",
    ),
    Product(
        id="8",
        name="MacBook Air 15",
        description="Thin and light laptop with M2 chip and all-day battery life",
        price=1299.99,
        category="Computers",
    ),
    Product(
        id="9",
        name="Dell XPS 15",
        description="Premium Windows laptop with OLED display and Intel Core Ultra processor",
        price=1799.99,
        category="Computers",
    ),
    Product(
        id="10",
        name="Sony WH-1000XM5",
        description="Industry-leading noise cancelling wireless headphones",
        price=349.99,
        category="Audio",
    ),
    Product(
        id="11",
        name="Apple AirPods Pro 2",
        description="Active noise cancellation earbuds with spatial audio",
        price=249.99,
        category="Audio",
    ),
    Product(
        id="12",
        name="iPad Pro 12.9",
        description="Apple tablet with M2 chip and stunning Liquid Retina XDR display",
        price=1099.99,
        category="Tablets",
    ),
    Product(
        id="13",
        name="Samsung Galaxy Tab S9 Ultra",
        description="Large Android tablet with S Pen and AMOLED display",
        price=1199.99,
        category="Tablets",
    ),
    Product(
        id="14",
        name="Apple Watch Ultra 2",
        description="Rugged smartwatch with precision GPS and 36-hour battery",
        price=799.99,
        category="Wearables",
    ),
    Product(
        id="15",
        name="Samsung Galaxy Watch 6",
        description="Android smartwatch with health monitoring and Wear OS",
        price=299.99,
        category="Wearables",
    ),
]


async def create_index_with_mappings() -> bool:
    """Create the products index with proper mappings.

    Returns:
        True if index was created, False if it already exists.
    """
    index_manager = get_index_manager()

    if await index_manager.index_exists():
        return False

    await index_manager.create_index(
        mappings=PRODUCT_MAPPINGS,
        settings=get_product_settings(),
    )

    return True


async def seed_sample_data() -> int:
    """Seed the database with sample products.

    Returns:
        Number of products successfully indexed.
    """
    indexing_service = get_indexing_service()

    result = await indexing_service.bulk_index_products(SAMPLE_PRODUCTS)

    return result.success_count


async def setup_and_seed() -> dict[str, Any]:
    """Setup index and seed with sample data.

    Creates the index with mappings if it doesn't exist,
    then seeds the sample products.

    Returns:
        Dictionary with setup results.
    """
    index_created = await create_index_with_mappings()
    products_seeded = await seed_sample_data()

    return {
        "index_created": index_created,
        "products_seeded": products_seeded,
    }


async def clear_all_data() -> bool:
    """Delete and recreate the index.

    Returns:
        True if successful.
    """
    index_manager = get_index_manager()

    # Delete existing index
    if await index_manager.index_exists():
        await index_manager.delete_index()

    # Recreate with mappings
    await index_manager.create_index(
        mappings=PRODUCT_MAPPINGS,
        settings=get_product_settings(),
    )

    return True
