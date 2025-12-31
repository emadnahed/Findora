# ==============================================================================
# Findora Search API - Makefile
# ==============================================================================

.PHONY: help install install-dev lint format typecheck test test-unit test-integration test-e2e test-cov clean docker-up docker-down docker-logs run

# Default target
help:
	@echo "Findora Search API - Available Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install production dependencies"
	@echo "  make install-dev    Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run Ruff linter"
	@echo "  make format         Format code with Black and Ruff"
	@echo "  make typecheck      Run MyPy type checker"
	@echo "  make check          Run all code quality checks"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run all tests"
	@echo "  make test-unit      Run unit tests only"
	@echo "  make test-int       Run integration tests only"
	@echo "  make test-e2e       Run end-to-end tests only"
	@echo "  make test-cov       Run tests with coverage report"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      Start Elasticsearch container"
	@echo "  make docker-down    Stop all containers"
	@echo "  make docker-logs    View container logs"
	@echo ""
	@echo "Development:"
	@echo "  make run            Start development server"
	@echo "  make clean          Remove cache and build files"

# ==============================================================================
# Setup
# ==============================================================================

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

# ==============================================================================
# Code Quality
# ==============================================================================

lint:
	ruff check src tests

format:
	black src tests
	ruff check --fix src tests

typecheck:
	mypy src

check: lint typecheck
	@echo "All code quality checks passed!"

# ==============================================================================
# Testing
# ==============================================================================

test:
	pytest

test-unit:
	pytest -m unit tests/unit

test-int:
	pytest -m integration tests/integration

test-e2e:
	pytest -m e2e tests/e2e

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term-missing

# ==============================================================================
# Docker
# ==============================================================================

docker-up:
	docker-compose up -d elasticsearch
	@echo "Waiting for Elasticsearch to be ready..."
	@sleep 10
	@curl -s http://localhost:9200/_cluster/health | python -m json.tool

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-test-up:
	docker-compose --profile test up -d elasticsearch-test
	@echo "Waiting for test Elasticsearch to be ready..."
	@sleep 10

# ==============================================================================
# Development
# ==============================================================================

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# ==============================================================================
# Cleanup
# ==============================================================================

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage coverage.xml
	rm -rf build dist *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
