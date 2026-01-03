"""Load testing suite for Findora Search API using Locust."""

import random
import string
from http import HTTPStatus
from typing import ClassVar

from locust import HttpUser, between, task


class SearchUser(HttpUser):
    """Simulates a user performing search operations."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    # Sample search terms (class-level constants, safe for sharing)
    search_terms: ClassVar[list[str]] = [
        "laptop",
        "phone",
        "headphones",
        "camera",
        "tablet",
        "keyboard",
        "mouse",
        "monitor",
        "speakers",
        "charger",
        "wireless",
        "bluetooth",
        "gaming",
        "professional",
        "portable",
    ]

    categories: ClassVar[list[str]] = [
        "Electronics",
        "Computers",
        "Audio",
        "Accessories",
        "Gaming",
    ]

    @task(10)
    def search_products(self) -> None:
        """Perform a basic search query."""
        query = random.choice(self.search_terms)
        self.client.get(f"/api/v1/search?q={query}")

    @task(5)
    def search_with_fuzzy(self) -> None:
        """Perform a search with fuzzy matching."""
        query = random.choice(self.search_terms)
        fuzzy = random.choice(["true", "false"])
        self.client.get(f"/api/v1/search?q={query}&fuzzy={fuzzy}")

    @task(3)
    def search_with_pagination(self) -> None:
        """Perform a paginated search."""
        query = random.choice(self.search_terms)
        page = random.randint(1, 5)
        size = random.choice([10, 20, 50])
        self.client.get(f"/api/v1/search?q={query}&page={page}&size={size}")

    @task(3)
    def search_with_price_filter(self) -> None:
        """Perform a search with price filters."""
        query = random.choice(self.search_terms)
        min_price = random.randint(0, 500)
        max_price = min_price + random.randint(100, 1000)
        self.client.get(
            f"/api/v1/search?q={query}&min_price={min_price}&max_price={max_price}"
        )

    @task(3)
    def search_with_category(self) -> None:
        """Perform a search with category filter."""
        query = random.choice(self.search_terms)
        category = random.choice(self.categories)
        self.client.get(f"/api/v1/search?q={query}&category={category}")

    @task(2)
    def search_with_sorting(self) -> None:
        """Perform a sorted search."""
        query = random.choice(self.search_terms)
        sort_by = random.choice(["relevance", "price", "name"])
        sort_order = random.choice(["asc", "desc"])
        self.client.get(
            f"/api/v1/search?q={query}&sort_by={sort_by}&sort_order={sort_order}"
        )

    @task(1)
    def complex_search(self) -> None:
        """Perform a complex search with multiple parameters."""
        query = random.choice(self.search_terms)
        page = random.randint(1, 3)
        size = random.choice([10, 20])
        min_price = random.randint(0, 200)
        max_price = min_price + random.randint(100, 500)
        category = random.choice(self.categories)
        sort_by = random.choice(["relevance", "price"])
        sort_order = random.choice(["asc", "desc"])

        self.client.get(
            f"/api/v1/search?q={query}&page={page}&size={size}"
            f"&min_price={min_price}&max_price={max_price}"
            f"&category={category}&sort_by={sort_by}&sort_order={sort_order}"
        )


class ProductUser(HttpUser):
    """Simulates a user performing product CRUD operations."""

    wait_time = between(1, 5)

    def on_start(self) -> None:
        """Initialize user-specific state.

        Each user maintains its own list of created product IDs to avoid
        race conditions in multi-user/distributed load tests.
        """
        self.created_product_ids: list[str] = []

    def _generate_product_data(self) -> dict:
        """Generate random product data."""
        name = f"Test Product {''.join(random.choices(string.ascii_uppercase, k=5))}"
        return {
            "name": name,
            "description": f"A test product with random description {random.randint(1, 1000)}",
            "price": round(random.uniform(10.0, 1000.0), 2),
            "category": random.choice(
                ["Electronics", "Computers", "Audio", "Accessories"]
            ),
        }

    @task(3)
    def create_product(self) -> None:
        """Create a new product."""
        product_data = self._generate_product_data()
        response = self.client.post(
            "/api/v1/products",
            json=product_data,
        )
        if response.status_code == HTTPStatus.CREATED:
            product_id = response.json().get("id")
            if product_id:
                self.created_product_ids.append(product_id)

    @task(5)
    def get_product(self) -> None:
        """Get an existing product."""
        if self.created_product_ids:
            product_id = random.choice(self.created_product_ids)
            self.client.get(f"/api/v1/products/{product_id}")

    @task(2)
    def update_product(self) -> None:
        """Update an existing product."""
        if self.created_product_ids:
            product_id = random.choice(self.created_product_ids)
            product_data = self._generate_product_data()
            self.client.put(
                f"/api/v1/products/{product_id}",
                json=product_data,
            )

    @task(1)
    def delete_product(self) -> None:
        """Delete an existing product."""
        if self.created_product_ids:
            product_id = self.created_product_ids.pop()
            self.client.delete(f"/api/v1/products/{product_id}")


class HealthCheckUser(HttpUser):
    """Simulates health check and monitoring requests."""

    wait_time = between(5, 10)

    @task(5)
    def health_check(self) -> None:
        """Check application health."""
        self.client.get("/health")

    @task(3)
    def metrics_json(self) -> None:
        """Get JSON metrics."""
        self.client.get("/metrics/json")

    @task(2)
    def metrics_prometheus(self) -> None:
        """Get Prometheus metrics."""
        self.client.get("/metrics")


class MixedUser(HttpUser):
    """Simulates a realistic mix of user behaviors."""

    wait_time = between(1, 5)

    # Class-level constants (safe for sharing, read-only)
    search_terms: ClassVar[list[str]] = ["laptop", "phone", "headphones", "camera", "tablet"]
    categories: ClassVar[list[str]] = ["Electronics", "Computers", "Audio"]

    @task(20)
    def search(self) -> None:
        """Perform a search (most common operation)."""
        query = random.choice(self.search_terms)
        self.client.get(f"/api/v1/search?q={query}")

    @task(5)
    def health_check(self) -> None:
        """Check health."""
        self.client.get("/health")

    @task(2)
    def view_metrics(self) -> None:
        """View metrics."""
        self.client.get("/metrics/json")
