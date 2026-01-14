# LinkedIn Connection Search Tool - Implementation Plan

## Overview

This document contains a step-by-step blueprint for building the LinkedIn Connection Search CLI tool. The plan is broken into small, iterative prompts that can be executed in sequence by a code-generation LLM using TDD practices.

## Current State

The project has foundational work in place:
- `pyproject.toml` with dependencies (typer, rich, sqlmodel, keyring, linkedin-api, pydantic)
- SQLModels: `ConnectionProfile`, `RateLimitEntry`, `ActionType`
- Search filters: `SearchFilter`, `NetworkDepth`
- Project structure: `src/linkedin_scraper/`

## Architecture Summary

```
CLI (Typer) → Search Orchestrator → LinkedIn Client
                    ↓                     ↓
              Rate Limiter          Cookie Manager
                    ↓                     ↓
              Database (SQLite)      OS Keyring
                    ↓
              Export Layer (CSV, Rich)
```

## Implementation Phases

### Phase 1: Core Infrastructure (Prompts 1-4)
Database setup, cookie management, and basic CLI skeleton.

### Phase 2: Rate Limiting (Prompts 5-7)
Rate limiter service with persistence and delay logic.

### Phase 3: LinkedIn Integration (Prompts 8-10)
LinkedIn client wrapper and search functionality.

### Phase 4: CLI Commands (Prompts 11-14)
Full CLI implementation with all commands.

### Phase 5: Export & Polish (Prompts 15-17)
CSV export, rich output formatting, and final integration.

---

## Prompts

---

### Prompt 1: Database Service Foundation

```text
We're building a LinkedIn connection search CLI tool. The project already has SQLModels defined in `src/linkedin_scraper/models/`.

Create a database service module that:
1. Manages SQLite database initialization and connections
2. Provides CRUD operations for the existing models
3. Uses SQLModel's session management

Requirements:
- Create `src/linkedin_scraper/database/__init__.py` and `src/linkedin_scraper/database/service.py`
- The database file should be stored at `~/.linkedin-scraper/data.db` (create directory if needed)
- Implement a `DatabaseService` class with methods:
  - `__init__(self, db_path: Path | None = None)` - uses default path if none provided
  - `init_db(self)` - creates tables
  - `get_session(self)` - returns a context manager for database sessions
  - `save_connection(self, profile: ConnectionProfile) -> ConnectionProfile`
  - `get_connections(self, limit: int = 100, offset: int = 0) -> list[ConnectionProfile]`
  - `get_connection_by_urn(self, urn_id: str) -> ConnectionProfile | None`
- All code must be type-checked with mypy strict mode
- Follow TDD: write tests first in `tests/test_database.py`
- Tests should use a temporary database file
- Add ABOUTME comments to new files

The existing models are:
- `ConnectionProfile` in `models/connection.py` with fields: id, linkedin_urn_id, public_id, first_name, last_name, headline, location, current_company, current_title, profile_url, connection_degree, search_query, found_at
- `RateLimitEntry` in `models/rate_limit.py` with fields: id, action_type, timestamp

Start with tests, then implement the service.
```

---

### Prompt 2: Cookie Manager Service

```text
Continue building the LinkedIn connection search CLI. We now have a database service in place.

Create a cookie manager service that securely stores LinkedIn cookies using the OS keyring:

Requirements:
- Create `src/linkedin_scraper/auth/__init__.py` and `src/linkedin_scraper/auth/cookie_manager.py`
- Implement a `CookieManager` class with methods:
  - `store_cookie(self, cookie: str, account_name: str = "default") -> None`
  - `get_cookie(self, account_name: str = "default") -> str | None`
  - `delete_cookie(self, account_name: str = "default") -> None`
  - `list_accounts(self) -> list[str]`
  - `validate_cookie_format(self, cookie: str) -> bool` - basic format validation (non-empty, reasonable length)
- Use the `keyring` library for secure storage
- Service name in keyring should be "linkedin-scraper"
- Account names are stored as keyring usernames
- Maintain a list of account names in the database or a separate config file at `~/.linkedin-scraper/accounts.json`
- All code must pass mypy strict mode
- Follow TDD: write tests first in `tests/test_cookie_manager.py`
- Tests should mock the keyring to avoid actual OS keyring access
- Add ABOUTME comments to new files
- Export CookieManager from the auth package

Start with tests, then implement the service.
```

---

### Prompt 3: Configuration Module

```text
Continue building the LinkedIn connection search CLI. We have database and cookie manager services.

Create a configuration module for application settings:

Requirements:
- Create `src/linkedin_scraper/config.py`
- Use pydantic-settings to define a `Settings` class with:
  - `db_path: Path` - defaults to `~/.linkedin-scraper/data.db`
  - `accounts_file: Path` - defaults to `~/.linkedin-scraper/accounts.json`
  - `max_actions_per_day: int` - defaults to 25
  - `min_delay_seconds: int` - defaults to 60
  - `max_delay_seconds: int` - defaults to 120
  - `tos_accepted: bool` - defaults to False
  - `tos_accepted_at: datetime | None` - defaults to None
- Settings can be overridden via environment variables with prefix `LINKEDIN_SCRAPER_`
- Implement a `get_settings()` function that returns a cached Settings instance
- Implement `ensure_data_dir()` function that creates `~/.linkedin-scraper/` if needed
- All code must pass mypy strict mode
- Follow TDD: write tests first in `tests/test_config.py`
- Tests should use temporary directories and environment variable mocking
- Add ABOUTME comments to the file

Start with tests, then implement the module.
```

---

### Prompt 4: CLI Skeleton with Typer

```text
Continue building the LinkedIn connection search CLI. We have database, cookie manager, and config modules.

Create the CLI skeleton using Typer:

Requirements:
- Create `src/linkedin_scraper/cli.py`
- Define a Typer app with the following command stubs:
  - `login` - Store LinkedIn cookie (placeholder implementation for now)
  - `search` - Search connections (placeholder implementation for now)
  - `export` - Export results to CSV (placeholder implementation for now)
  - `status` - Show rate limits and account status (placeholder implementation for now)
- Each command should just print a "Not implemented yet" message for now
- Add a callback that:
  - Displays a ToS warning on first run if `tos_accepted` is False in settings
  - Prompts user to accept before proceeding
  - Saves acceptance to settings
- Use Rich for console output formatting
- The app should be accessible via `linkedin-scraper` command (already configured in pyproject.toml)
- All code must pass mypy strict mode
- Follow TDD: write tests first in `tests/test_cli.py`
- Tests should use Typer's CliRunner for testing commands
- Add ABOUTME comments to the file

Start with tests, then implement the CLI.
```

---

### Prompt 5: Rate Limiter Core Logic

```text
Continue building the LinkedIn connection search CLI. We have the CLI skeleton in place.

Create a rate limiter service that enforces API call limits:

Requirements:
- Create `src/linkedin_scraper/rate_limit/__init__.py` and `src/linkedin_scraper/rate_limit/service.py`
- Implement a `RateLimiter` class that:
  - Takes `DatabaseService` and `Settings` as dependencies
  - Tracks actions using the existing `RateLimitEntry` model
  - Methods:
    - `can_perform_action(self, action_type: ActionType) -> bool` - checks if under daily limit
    - `record_action(self, action_type: ActionType) -> None` - records an action
    - `get_actions_today(self, action_type: ActionType | None = None) -> int` - count of today's actions
    - `get_remaining_actions(self) -> int` - remaining actions for today
    - `get_last_action_time(self) -> datetime | None` - timestamp of most recent action
    - `seconds_until_next_allowed(self) -> int` - seconds to wait before next action (including jitter)
- Daily limit resets at midnight UTC
- Use the `max_actions_per_day` from Settings
- All code must pass mypy strict mode
- Follow TDD: write tests first in `tests/test_rate_limiter.py`
- Tests should use a mock database or in-memory database
- Tests should mock datetime to test day boundary behavior
- Add ABOUTME comments to new files
- Export RateLimiter from the package

Start with tests, then implement the service.
```

---

### Prompt 6: Rate Limiter Delay Logic

```text
Continue building the LinkedIn connection search CLI. We have the core rate limiter.

Extend the rate limiter with delay enforcement and jitter:

Requirements:
- Add to `RateLimiter` class in `src/linkedin_scraper/rate_limit/service.py`:
  - `calculate_delay(self) -> float` - returns delay in seconds with random jitter
  - `wait_if_needed(self) -> None` - sleeps if minimum delay hasn't passed since last action
  - Use `min_delay_seconds` and `max_delay_seconds` from Settings
  - Jitter should be random between min and max delay
- Add a `RateLimitExceeded` exception class in `src/linkedin_scraper/rate_limit/exceptions.py`
- Add a `check_and_wait(self, action_type: ActionType) -> None` method that:
  - Raises `RateLimitExceeded` if daily limit reached
  - Otherwise waits the appropriate delay
  - Records the action after waiting
- All code must pass mypy strict mode
- Follow TDD: write tests first in `tests/test_rate_limiter.py` (extend existing tests)
- Tests should mock `time.sleep` to avoid actual delays
- Tests should mock `random.uniform` for deterministic jitter testing
- Add ABOUTME comments to new files

Start with tests, then implement the additions.
```

---

### Prompt 7: Rate Limiter Status Display

```text
Continue building the LinkedIn connection search CLI. We have rate limiter with delay logic.

Add a status display helper for the rate limiter:

Requirements:
- Create `src/linkedin_scraper/rate_limit/display.py`
- Implement a `RateLimitDisplay` class that:
  - Takes `RateLimiter` as a dependency
  - Methods:
    - `get_status_dict(self) -> dict[str, Any]` - returns current status as dictionary
    - `render_status(self) -> Panel` - returns a Rich Panel showing:
      - Actions used today / max actions
      - Remaining actions
      - Time until daily reset
      - Last action timestamp
      - Warning if approaching limit (< 5 remaining)
- Use Rich formatting (colors, progress bars if appropriate)
- All code must pass mypy strict mode
- Follow TDD: write tests first in `tests/test_rate_limit_display.py`
- Add ABOUTME comments to the file
- Export RateLimitDisplay from the rate_limit package

Start with tests, then implement the display helper.
```

---

### Prompt 8: LinkedIn Client Wrapper

```text
Continue building the LinkedIn connection search CLI. We have rate limiting in place.

Create a LinkedIn client wrapper around the linkedin-api library:

Requirements:
- Create `src/linkedin_scraper/linkedin/__init__.py` and `src/linkedin_scraper/linkedin/client.py`
- Implement a `LinkedInClient` class that:
  - Wraps the `linkedin_api.Linkedin` class
  - Constructor takes `cookie: str` and initializes the underlying client
  - Provides a clean interface for search operations
  - Methods:
    - `__init__(self, cookie: str)` - creates authenticated client from li_at cookie
    - `validate_session(self) -> bool` - tests if the session is valid by making a simple API call
    - `get_profile_id(self) -> str | None` - returns the logged-in user's profile ID
- Use `linkedin_api.Linkedin` with `refresh_cookies=False` since we're using stored cookies
- Handle common exceptions from linkedin-api and wrap in custom exceptions
- Create `src/linkedin_scraper/linkedin/exceptions.py` with:
  - `LinkedInError` (base exception)
  - `LinkedInAuthError` (invalid/expired cookie)
  - `LinkedInRateLimitError` (LinkedIn's own rate limiting)
- All code must pass mypy strict mode
- Follow TDD: write tests first in `tests/test_linkedin_client.py`
- Tests should mock the linkedin_api.Linkedin class to avoid real API calls
- Add ABOUTME comments to new files
- Export LinkedInClient and exceptions from the package

Start with tests, then implement the client.
```

---

### Prompt 9: LinkedIn Search Functionality

```text
Continue building the LinkedIn connection search CLI. We have the LinkedIn client wrapper.

Add search functionality to the LinkedIn client:

Requirements:
- Extend `LinkedInClient` in `src/linkedin_scraper/linkedin/client.py`:
  - Add `search_people(self, filter: SearchFilter) -> list[dict[str, Any]]` method that:
    - Converts `SearchFilter` to linkedin-api parameters
    - Calls the underlying `search_people` method
    - Returns raw result dictionaries
- Create `src/linkedin_scraper/linkedin/mapper.py` with:
  - `map_search_result_to_profile(result: dict[str, Any], search_query: str | None = None) -> ConnectionProfile`
    - Extracts: urn_id, public_id, first_name, last_name, headline, location, profile_url
    - Determines connection_degree from the result
    - Sets search_query and found_at
    - Handles missing fields gracefully
- The `SearchFilter` already exists in `search/filters.py`
- All code must pass mypy strict mode
- Follow TDD: write tests first (extend `tests/test_linkedin_client.py` and create `tests/test_mapper.py`)
- Tests should use fixture data that mimics linkedin-api response structure
- Add ABOUTME comments to new files

Start with tests, then implement the functionality.
```

---

### Prompt 10: Company ID Resolution

```text
Continue building the LinkedIn connection search CLI. We have search functionality.

Add company ID resolution to the LinkedIn client:

Requirements:
- Extend `LinkedInClient` in `src/linkedin_scraper/linkedin/client.py`:
  - Add `search_companies(self, name: str, limit: int = 5) -> list[dict[str, Any]]` method
  - Add `resolve_company_id(self, name: str) -> str | None` method that:
    - Searches for companies by name
    - Returns the ID of the best match (first result)
    - Returns None if no match found
- Update `src/linkedin_scraper/linkedin/mapper.py`:
  - Add `map_company_result(result: dict[str, Any]) -> dict[str, Any]` that extracts:
    - company_id
    - name
    - industry
    - employee_count (if available)
- All code must pass mypy strict mode
- Follow TDD: write tests first (extend `tests/test_linkedin_client.py`)
- Tests should mock company search responses
- Add ABOUTME comments to new/modified files

Start with tests, then implement the functionality.
```

---

### Prompt 11: Login Command Implementation

```text
Continue building the LinkedIn connection search CLI. We have LinkedIn client and company resolution.

Implement the `login` command in the CLI:

Requirements:
- Update `src/linkedin_scraper/cli.py` to implement the `login` command:
  - Prompt user to paste their `li_at` cookie (use Rich prompt with password masking)
  - Validate cookie format using CookieManager
  - Validate cookie by testing with LinkedInClient
  - Store cookie in keyring using CookieManager
  - Options:
    - `--account` / `-a`: Account name (default: "default")
    - `--validate/--no-validate`: Whether to validate cookie online (default: validate)
  - Display success/failure with Rich formatting
  - If validation fails, show helpful error message about how to get the cookie
- Add a helper function `get_cookie_instructions() -> str` that returns instructions for extracting li_at cookie from browser
- All code must pass mypy strict mode
- Follow TDD: update tests in `tests/test_cli.py`
- Tests should mock CookieManager and LinkedInClient
- Tests should cover: successful login, invalid cookie format, failed validation, account naming

Start with tests, then implement the command.
```

---

### Prompt 12: Search Command Implementation

```text
Continue building the LinkedIn connection search CLI. We have the login command.

Implement the `search` command in the CLI:

Requirements:
- Update `src/linkedin_scraper/cli.py` to implement the `search` command:
  - Options:
    - `--keywords` / `-k`: Search keywords (required)
    - `--company` / `-c`: Company name to filter by (optional, will resolve to ID)
    - `--location` / `-l`: Location filter (optional)
    - `--degree` / `-d`: Connection degrees, comma-separated (default: "1,2")
    - `--limit`: Max results (default: 100)
    - `--account` / `-a`: Account to use (default: "default")
  - Flow:
    1. Load cookie from keyring
    2. Check rate limits (display warning if low)
    3. If company name provided, resolve to company ID
    4. Perform search via LinkedInClient
    5. Map results to ConnectionProfile models
    6. Save results to database
    7. Display results in Rich table
    8. Show rate limit status after search
- Create `src/linkedin_scraper/search/orchestrator.py` with `SearchOrchestrator` class:
  - Coordinates between RateLimiter, LinkedInClient, and DatabaseService
  - Method: `execute_search(self, filter: SearchFilter, account: str) -> list[ConnectionProfile]`
- All code must pass mypy strict mode
- Follow TDD: update tests in `tests/test_cli.py` and create `tests/test_orchestrator.py`
- Tests should mock all external dependencies

Start with tests, then implement the command.
```

---

### Prompt 13: Status Command Implementation

```text
Continue building the LinkedIn connection search CLI. We have login and search commands.

Implement the `status` command in the CLI:

Requirements:
- Update `src/linkedin_scraper/cli.py` to implement the `status` command:
  - Display:
    - Rate limit status (using RateLimitDisplay)
    - Stored accounts list with validation status
    - Database statistics (total stored connections, unique companies, etc.)
  - Options:
    - `--account` / `-a`: Show details for specific account (validates cookie)
- Create `src/linkedin_scraper/database/stats.py` with `get_database_stats()` function:
  - Returns dict with: total_connections, unique_companies, unique_locations, recent_searches_count
- All code must pass mypy strict mode
- Follow TDD: update tests in `tests/test_cli.py` and create `tests/test_database_stats.py`
- Tests should verify correct display formatting

Start with tests, then implement the command.
```

---

### Prompt 14: Export Command Implementation

```text
Continue building the LinkedIn connection search CLI. We have login, search, and status commands.

Implement the `export` command in the CLI:

Requirements:
- Update `src/linkedin_scraper/cli.py` to implement the `export` command:
  - Options:
    - `--output` / `-o`: Output file path (default: `linkedin_export_{timestamp}.csv`)
    - `--query` / `-q`: Filter by search query string (optional)
    - `--all`: Export all stored results (default behavior if no filters)
    - `--limit`: Max records to export (default: no limit)
- Create `src/linkedin_scraper/export/__init__.py` and `src/linkedin_scraper/export/csv_exporter.py`
- Implement `CSVExporter` class:
  - Method: `export(self, profiles: list[ConnectionProfile], output_path: Path) -> Path`
  - Columns: name, first_name, last_name, headline, company, title, location, profile_url, degree, search_query, found_at
  - Include metadata row at top with export timestamp and query info
  - Use Python's csv module with proper escaping
- All code must pass mypy strict mode
- Follow TDD: create `tests/test_csv_exporter.py` and update `tests/test_cli.py`
- Tests should verify CSV output format and content

Start with tests, then implement the export.
```

---

### Prompt 15: Rich Output Formatting

```text
Continue building the LinkedIn connection search CLI. We have all commands implemented.

Enhance terminal output with Rich formatting:

Requirements:
- Create `src/linkedin_scraper/display/__init__.py` and `src/linkedin_scraper/display/tables.py`
- Implement `ConnectionTable` class:
  - Method: `render(self, profiles: list[ConnectionProfile], title: str | None = None) -> Table`
  - Columns: #, Name, Headline, Company, Location, Degree
  - Truncate long headlines/company names with ellipsis
  - Color-code connection degrees (1st=green, 2nd=yellow, 3rd=red)
  - Show row numbers
- Create `src/linkedin_scraper/display/status.py`:
  - Function: `display_search_summary(count: int, query: str, duration_seconds: float) -> Panel`
  - Function: `display_rate_limit_warning(remaining: int) -> Panel | None` - returns warning if < 5 remaining
- Update CLI commands to use these display helpers
- All code must pass mypy strict mode
- Follow TDD: create `tests/test_display.py`
- Tests should verify Rich renderables are created correctly

Start with tests, then implement the display helpers.
```

---

### Prompt 16: Error Handling and User Messages

```text
Continue building the LinkedIn connection search CLI. We have Rich formatting.

Add comprehensive error handling and user-friendly messages:

Requirements:
- Create `src/linkedin_scraper/errors.py` with a base `LinkedInScraperError` exception
- Create `src/linkedin_scraper/display/errors.py` with error display helpers:
  - `display_error(error: Exception) -> Panel` - formats errors with Rich
  - `display_cookie_help() -> Panel` - shows how to get li_at cookie
  - `display_rate_limit_exceeded(reset_time: datetime) -> Panel` - shows when limit resets
- Update CLI to catch and display errors gracefully:
  - LinkedInAuthError -> show cookie help
  - RateLimitExceeded -> show when to try again
  - Network errors -> show retry suggestion
  - Generic errors -> show error details with traceback option (`--debug` flag)
- Add `--debug` flag to main CLI for verbose error output
- All code must pass mypy strict mode
- Follow TDD: update `tests/test_cli.py` to test error scenarios
- Tests should verify correct error messages are displayed

Start with tests, then implement error handling.
```

---

### Prompt 17: Final Integration and Polish

```text
Continue building the LinkedIn connection search CLI. We have error handling in place.

Final integration, testing, and polish:

Requirements:
1. Update `src/linkedin_scraper/__init__.py`:
   - Export version from pyproject.toml
   - Add `__version__` attribute

2. Add `--version` flag to CLI

3. Create `tests/test_integration.py` with end-to-end tests:
   - Test full login -> search -> export flow (with mocked LinkedIn API)
   - Test rate limit enforcement across multiple searches
   - Test database persistence across command invocations

4. Update all modules to ensure consistent:
   - ABOUTME comments at top of each file
   - Type annotations passing mypy strict
   - Ruff linting compliance

5. Create a CLI help improvement:
   - Add examples to each command's help text using Typer's rich help
   - Ensure `--help` output matches PRD examples

6. Run full test suite and fix any issues:
   - `uv run pytest`
   - `uv run mypy src/`
   - `uv run ruff check src/`

All code must pass mypy strict mode, ruff checks, and have >80% test coverage.

Start with integration tests, then implement remaining polish items.
```

---

## Dependency Graph

```
Prompt 1 (Database) ─────────────────────────────────────────────────────┐
    ↓                                                                    │
Prompt 2 (Cookie Manager) ───────────────────────────────────────────┐   │
    ↓                                                                │   │
Prompt 3 (Config) ───────────────────────────────────────────────┐   │   │
    ↓                                                            │   │   │
Prompt 4 (CLI Skeleton) ←────────────────────────────────────────┴───┴───┘
    ↓
Prompt 5 (Rate Limiter Core) ←── Prompt 1
    ↓
Prompt 6 (Rate Limiter Delay)
    ↓
Prompt 7 (Rate Limiter Display)
    ↓
Prompt 8 (LinkedIn Client) ←── Prompt 2
    ↓
Prompt 9 (LinkedIn Search)
    ↓
Prompt 10 (Company Resolution)
    ↓
Prompt 11 (Login Command) ←── Prompts 4, 8
    ↓
Prompt 12 (Search Command) ←── Prompts 5-7, 9-10
    ↓
Prompt 13 (Status Command) ←── Prompts 7, 12
    ↓
Prompt 14 (Export Command)
    ↓
Prompt 15 (Rich Output)
    ↓
Prompt 16 (Error Handling)
    ↓
Prompt 17 (Final Integration)
```

## Quality Gates

After each prompt, verify:
1. All new tests pass: `uv run pytest tests/`
2. Type checking passes: `uv run mypy src/`
3. Linting passes: `uv run ruff check src/`
4. Coverage remains >80%

## Notes

- Each prompt is designed to be self-contained while building on previous work
- All prompts emphasize TDD: tests are written before implementation
- No mock modes or fake data - tests mock external dependencies (keyring, linkedin-api)
- Database tests use temporary files, not in-memory, to match production behavior
- The existing models in `models/` should be used as-is (no modifications needed)
