# Findora - Search System MVP

A **production-grade search backend** built using **FastAPI** and **Elasticsearch**, developed with strict **Test-Driven Development (TDD)** practices.

---

## Architecture Overview

```
Client (Frontend / Postman)
        ↓
   FastAPI API
        ↓
 Elasticsearch Index
```

**Key idea:**
FastAPI handles HTTP & business logic, while Elasticsearch handles **search, scoring, and text analysis**.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| API Framework | FastAPI |
| Search Engine | Elasticsearch 8.12 |
| Language | Python 3.11+ |
| Runtime | Uvicorn |
| Testing | Pytest, HTTPX |
| Linting | Ruff, Black, MyPy |
| Infrastructure | Docker |

---

## Project Structure

```
findora/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── config/
│   │   └── settings.py      # Configuration management
│   ├── api/
│   │   └── routes/          # API endpoints
│   ├── services/            # Business logic
│   ├── elastic/             # Elasticsearch client & indices
│   ├── models/              # Pydantic schemas
│   └── utils/               # Utilities & logging
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── e2e/                 # End-to-end tests
├── .env.example
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── README.md
```

---

## Quick Start

### 1. Clone and Install

```bash
# Clone repository
git clone <repository-url>
cd findora

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
make install-dev
```

### 2. Start Elasticsearch

```bash
make docker-up
```

### 3. Run the API

```bash
make run
```

### 4. Verify

```bash
curl http://localhost:8000/health
```

---

## Development Commands

```bash
# Code Quality
make lint           # Run linter
make format         # Format code
make typecheck      # Run type checker
make check          # Run all checks

# Testing
make test           # Run all tests
make test-unit      # Unit tests only
make test-int       # Integration tests only
make test-e2e       # E2E tests (requires Elasticsearch)
make test-cov       # Tests with coverage report

# Docker
make docker-up      # Start Elasticsearch
make docker-down    # Stop containers
make docker-logs    # View logs
```

---

## TDD Development Phases

### Phase 0: Setup ✅
- [x] Project structure
- [x] Linting & formatting (Ruff, Black, MyPy)
- [x] Test frameworks (Pytest, pytest-asyncio, HTTPX)
- [x] Configuration management
- [x] Docker Compose for Elasticsearch
- [x] Git initialization

### Phase 1: Elasticsearch Foundation
- [ ] **Tests First:** Elasticsearch client connection tests
- [ ] **Tests First:** Index creation/deletion tests
- [ ] Elasticsearch client wrapper
- [ ] Index management service
- [ ] Health check with ES status
- [ ] Connection retry logic

### Phase 2: Core Search API
- [ ] **Tests First:** Search endpoint unit tests
- [ ] **Tests First:** Search service tests with mocked ES
- [ ] **Tests First:** E2E search flow tests
- [ ] Product schema (Pydantic models)
- [ ] Search endpoint (`GET /search?q=`)
- [ ] Multi-field search (name, description)
- [ ] Fuzzy matching (typo tolerance)
- [ ] Relevance scoring

### Phase 3: Data Ingestion
- [ ] **Tests First:** Index document tests
- [ ] **Tests First:** Bulk indexing tests
- [ ] Single document indexing endpoint
- [ ] Bulk indexing endpoint
- [ ] Sample data seeder
- [ ] Index mapping configuration

### Phase 4: Advanced Search Features
- [ ] **Tests First:** Pagination tests
- [ ] **Tests First:** Filter tests
- [ ] **Tests First:** Sorting tests
- [ ] Pagination (limit, offset)
- [ ] Filters (price range, category)
- [ ] Sorting (price, relevance)
- [ ] Highlighting matched terms

### Phase 5: Production Hardening
- [ ] **Tests First:** Error handling tests
- [ ] **Tests First:** Validation tests
- [ ] **Tests First:** Rate limiting tests
- [ ] Structured logging (structlog)
- [ ] Error handling middleware
- [ ] Request validation
- [ ] Rate limiting
- [ ] API documentation (OpenAPI)

### Phase 6: Performance & Monitoring
- [ ] **Tests First:** Performance benchmark tests
- [ ] Query caching
- [ ] Connection pooling
- [ ] Metrics endpoint
- [ ] Health check improvements
- [ ] Load testing suite

---

## Non-Negotiable Rules

1. **TDD Only:** Write failing tests before implementation
2. **Full Test Coverage:** Unit, integration, and E2E tests for every feature
3. **Phase Delivery:** Each phase ends in a deployable state
4. **E2E Validation:** Real HTTP → DB → response flows
5. **Git Best Practices:** Feature branches, atomic commits, conventional messages
6. **Production Mindset:** Validation, errors, logging, security, scalability

---

## Commit Convention

```
feat: Add new feature
test: Add or update tests
fix: Bug fix
refactor: Code refactoring
docs: Documentation changes
chore: Maintenance tasks
```

---

## License

MIT
