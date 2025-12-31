"""Unit tests for Elasticsearch mappings configuration."""

from src.elastic.mappings import (
    PRODUCT_MAPPINGS,
    PRODUCT_SETTINGS,
    get_product_index_config,
)


class TestProductMappings:
    """Tests for product index mappings."""

    def test_product_mappings_has_properties(self) -> None:
        """Test that product mappings has properties defined."""
        assert "properties" in PRODUCT_MAPPINGS

    def test_product_mappings_name_field(self) -> None:
        """Test name field mapping."""
        props = PRODUCT_MAPPINGS["properties"]
        assert "name" in props
        assert props["name"]["type"] == "text"
        assert "fields" in props["name"]  # keyword subfield

    def test_product_mappings_description_field(self) -> None:
        """Test description field mapping."""
        props = PRODUCT_MAPPINGS["properties"]
        assert "description" in props
        assert props["description"]["type"] == "text"

    def test_product_mappings_price_field(self) -> None:
        """Test price field mapping."""
        props = PRODUCT_MAPPINGS["properties"]
        assert "price" in props
        assert props["price"]["type"] == "float"

    def test_product_mappings_category_field(self) -> None:
        """Test category field mapping."""
        props = PRODUCT_MAPPINGS["properties"]
        assert "category" in props
        assert props["category"]["type"] == "keyword"


class TestProductSettings:
    """Tests for product index settings."""

    def test_settings_has_shards(self) -> None:
        """Test that settings includes shard configuration."""
        assert "number_of_shards" in PRODUCT_SETTINGS

    def test_settings_has_replicas(self) -> None:
        """Test that settings includes replica configuration."""
        assert "number_of_replicas" in PRODUCT_SETTINGS


class TestGetProductIndexConfig:
    """Tests for get_product_index_config function."""

    def test_returns_mappings_and_settings(self) -> None:
        """Test that config includes both mappings and settings."""
        config = get_product_index_config()

        assert "mappings" in config
        assert "settings" in config

    def test_mappings_match(self) -> None:
        """Test that returned mappings match constant."""
        config = get_product_index_config()

        assert config["mappings"] == PRODUCT_MAPPINGS

    def test_settings_match(self) -> None:
        """Test that returned settings match constant."""
        config = get_product_index_config()

        assert config["settings"] == PRODUCT_SETTINGS
