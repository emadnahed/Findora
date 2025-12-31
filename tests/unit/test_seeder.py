"""Unit tests for sample data seeder."""

from unittest.mock import AsyncMock, patch

import pytest

from src.models.product import BulkOperationResult
from src.utils.seeder import (
    SAMPLE_PRODUCTS,
    clear_all_data,
    create_index_with_mappings,
    seed_sample_data,
    setup_and_seed,
)


class TestSampleProducts:
    """Tests for sample products data."""

    def test_sample_products_not_empty(self) -> None:
        """Test that sample products list is not empty."""
        assert len(SAMPLE_PRODUCTS) > 0

    def test_sample_products_have_required_fields(self) -> None:
        """Test that all sample products have required fields."""
        for product in SAMPLE_PRODUCTS:
            assert product.id
            assert product.name
            assert product.description
            assert product.price > 0

    def test_sample_products_have_categories(self) -> None:
        """Test that sample products have categories."""
        categories = {p.category for p in SAMPLE_PRODUCTS if p.category}
        assert len(categories) > 0

    def test_sample_products_unique_ids(self) -> None:
        """Test that all sample products have unique IDs."""
        ids = [p.id for p in SAMPLE_PRODUCTS]
        assert len(ids) == len(set(ids))


class TestCreateIndexWithMappings:
    """Tests for create_index_with_mappings function."""

    @pytest.mark.asyncio
    async def test_creates_index_when_not_exists(self) -> None:
        """Test that index is created when it doesn't exist."""
        with patch("src.utils.seeder.get_index_manager") as mock_manager:
            mock_instance = AsyncMock()
            mock_instance.index_exists = AsyncMock(return_value=False)
            mock_instance.create_index = AsyncMock()
            mock_manager.return_value = mock_instance

            result = await create_index_with_mappings()

            assert result is True
            mock_instance.create_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_creation_when_exists(self) -> None:
        """Test that index creation is skipped when it exists."""
        with patch("src.utils.seeder.get_index_manager") as mock_manager:
            mock_instance = AsyncMock()
            mock_instance.index_exists = AsyncMock(return_value=True)
            mock_manager.return_value = mock_instance

            result = await create_index_with_mappings()

            assert result is False
            mock_instance.create_index.assert_not_called()


class TestSeedSampleData:
    """Tests for seed_sample_data function."""

    @pytest.mark.asyncio
    async def test_seeds_products(self) -> None:
        """Test that sample products are seeded."""
        with patch("src.utils.seeder.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.bulk_index_products = AsyncMock(
                return_value=BulkOperationResult(
                    success_count=len(SAMPLE_PRODUCTS),
                    error_count=0,
                    errors=[],
                )
            )
            mock_service.return_value = mock_instance

            result = await seed_sample_data()

            assert result == len(SAMPLE_PRODUCTS)
            mock_instance.bulk_index_products.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_success_count(self) -> None:
        """Test that function returns the success count."""
        with patch("src.utils.seeder.get_indexing_service") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.bulk_index_products = AsyncMock(
                return_value=BulkOperationResult(
                    success_count=10,
                    error_count=5,
                    errors=[],
                )
            )
            mock_service.return_value = mock_instance

            result = await seed_sample_data()

            assert result == 10


class TestSetupAndSeed:
    """Tests for setup_and_seed function."""

    @pytest.mark.asyncio
    async def test_returns_setup_results(self) -> None:
        """Test that function returns setup results."""
        with (
            patch("src.utils.seeder.create_index_with_mappings") as mock_create,
            patch("src.utils.seeder.seed_sample_data") as mock_seed,
        ):
            mock_create.return_value = True
            mock_seed.return_value = 15

            result = await setup_and_seed()

            assert result["index_created"] is True
            assert result["products_seeded"] == 15


class TestClearAllData:
    """Tests for clear_all_data function."""

    @pytest.mark.asyncio
    async def test_deletes_and_recreates_index(self) -> None:
        """Test that index is deleted and recreated."""
        with patch("src.utils.seeder.get_index_manager") as mock_manager:
            mock_instance = AsyncMock()
            mock_instance.index_exists = AsyncMock(return_value=True)
            mock_instance.delete_index = AsyncMock()
            mock_instance.create_index = AsyncMock()
            mock_manager.return_value = mock_instance

            result = await clear_all_data()

            assert result is True
            mock_instance.delete_index.assert_called_once()
            mock_instance.create_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_index_if_not_exists(self) -> None:
        """Test that index is created if it doesn't exist."""
        with patch("src.utils.seeder.get_index_manager") as mock_manager:
            mock_instance = AsyncMock()
            mock_instance.index_exists = AsyncMock(return_value=False)
            mock_instance.delete_index = AsyncMock()
            mock_instance.create_index = AsyncMock()
            mock_manager.return_value = mock_instance

            result = await clear_all_data()

            assert result is True
            mock_instance.delete_index.assert_not_called()
            mock_instance.create_index.assert_called_once()
