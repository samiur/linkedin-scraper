# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LinkedIn connection search CLI tool that uses the unofficial linkedin-api library to search connections by keywords, company, and location. Results are persisted to SQLite and can be exported to CSV.

## Common Commands

```bash
# Install dependencies
uv sync

# Run the CLI
uv run linkedin-scraper --help
uv run linkedin-scraper login
uv run linkedin-scraper search -k "software engineer"
uv run linkedin-scraper status
uv run linkedin-scraper export -o results.csv

# Run all tests with coverage
uv run pytest

# Run a single test file
uv run pytest tests/test_cli.py

# Run a specific test
uv run pytest tests/test_cli.py::test_search_command -v

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Format code
uv run ruff format src/
```

## Architecture

### Core Services (src/linkedin_scraper/)

**SearchOrchestrator** (`search/orchestrator.py`) - Central coordinator that ties together all services for search operations:
- Loads cookies from CookieManager
- Enforces rate limits via RateLimiter
- Resolves company names to IDs via LinkedInClient
- Persists results via DatabaseService

**LinkedInClient** (`linkedin/client.py`) - Wrapper around linkedin-api library:
- Cookie-based authentication (requires li_at and JSESSIONID cookies)
- Translates library exceptions to typed LinkedInError subclasses
- search_people() accepts SearchFilter, returns raw dicts
- resolve_company_id() for company name → ID lookup

**RateLimiter** (`rate_limit/service.py`) - Enforces daily API limits:
- Tracks actions in database via RateLimitEntry model
- Daily reset at midnight UTC
- Configurable delays between actions (jitter for human-like behavior)
- check_and_wait() is the main entry point before any API call

**DatabaseService** (`database/service.py`) - SQLite persistence via SQLModel:
- ConnectionProfile for search results
- RateLimitEntry for rate limit tracking
- Default location: ~/.linkedin-scraper/data.db

**CookieManager** (`auth/cookie_manager.py`) - Cookie storage:
- Uses OS keyring for secure storage (stores both li_at and JSESSIONID as JSON)
- Tracks account names in ~/.linkedin-scraper/accounts.json
- Supports multiple named accounts

### Data Flow

1. CLI parses args → builds SearchFilter
2. SearchOrchestrator.execute_search_with_company_name():
   - CookieManager.get_cookies() → load both li_at and JSESSIONID
   - LinkedInClient.resolve_company_id() → convert name to ID
   - RateLimiter.check_and_wait() → enforce limits
   - LinkedInClient.search_people() → execute search
   - mapper.map_search_result_to_profile() → convert to ConnectionProfile
   - DatabaseService.save_connection() → persist

### Configuration

Settings via pydantic-settings (`config.py`):
- Environment variables with LINKEDIN_SCRAPER_ prefix
- Key settings: db_path, max_actions_per_day (default 25), min/max_delay_seconds
- TOS acceptance tracking

### Models (src/linkedin_scraper/models/)

- **ConnectionProfile** - Search result with name, headline, company, location, connection degree
- **RateLimitEntry** - Action timestamp for rate limiting
- **ActionType** - Enum for action types (SEARCH, etc.)
- **SearchFilter** / **NetworkDepth** - Search parameters

## Testing

Tests use in-memory SQLite via fixtures in `conftest.py`. Key fixtures:
- `test_engine` - In-memory SQLite engine
- `test_session` - Database session for test isolation

Test files mirror source structure: test_cli.py, test_orchestrator.py, test_linkedin_client.py, etc.
