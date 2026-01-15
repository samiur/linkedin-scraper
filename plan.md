# LinkedIn Network Scraper - Implementation Plan

## Overview

This document contains a step-by-step blueprint for building the LinkedIn Network Scraper. The plan is broken into phases, with Phase 1 (CLI tool) completed and Phase 2 (Web Application) outlined below.

## Current State

**Phase 1 Complete:** The CLI tool is fully functional with:
- SQLModels: `ConnectionProfile`, `RateLimitEntry`, `ActionType`
- Search filters: `SearchFilter`, `NetworkDepth`
- Services: `DatabaseService`, `CookieManager`, `RateLimiter`, `LinkedInClient`
- Orchestration: `SearchOrchestrator` coordinating all search operations
- CLI: Full Typer CLI with login, search, status, export commands
- Export: CSV export functionality

## Architecture Evolution

### Phase 1 Architecture (CLI - Complete)
```
CLI (Typer) → Search Orchestrator → LinkedIn Client
                    ↓                     ↓
              Rate Limiter          Cookie Manager
                    ↓                     ↓
              Database (SQLite)      OS Keyring
                    ↓
              Export Layer (CSV, Rich)
```

### Phase 2 Architecture (Web App)
```
React Frontend (Next.js)
        ↓
FastAPI Backend ←─────────────────────────┐
        ↓                                 │
  ┌─────┴─────┐                          │
  │           │                          │
Space       Search                    Cookie
Service    Orchestrator              Service
  │           │                          │
  └─────┬─────┘                          │
        ↓                                │
PostgreSQL Database ←────────────────────┘
        │
        └── Models: Space, Contributor, SearchResult
```

---

## Phase 2: Web Application

### Implementation Phases

**Phase 2.1:** Database Schema & Models (Prompts 18-20)
New models for spaces, contributors (with CookieStatus), and search results.

**Phase 2.2:** Core API Services (Prompts 21-24)
Space management, cookie service with validation/refresh, and search aggregation.

**Phase 2.3:** API Endpoints (Prompts 25-28)
FastAPI routes for spaces, contributors, and search operations.

**Phase 2.4:** Frontend Foundation (Prompts 29-32)
Next.js setup, API client, and basic layouts.

**Phase 2.5:** Cookie Management UI (Prompts 33-36) ⭐ PRIORITY
Space creation, admin dashboard with cookie health, and cookie refresh flow.

**Phase 2.6:** Background Cookie Validation (Prompt 37) ⭐ PRIORITY
Proactive validation and refresh notifications.

**Phase 2.7:** Search & Export UI (Prompts 38-41)
Search interface, results table, and export functionality.

**Phase 2.8:** Polish & Integration (Prompts 42-47)
Rate limiting, error handling, testing, docs, and deployment.

---

## Prompts

---

### Prompt 18: Web Database Models - Space

```text
We're extending the LinkedIn Network Scraper CLI into a web application. The CLI is complete in `src/linkedin_scraper/`.

Create the web application backend structure and Space model:

Requirements:
1. Create new directory structure:
   - `src/web/` - FastAPI backend
   - `src/web/models/` - SQLModel definitions
   - `src/web/models/__init__.py`
   - `src/web/models/space.py`

2. Implement `Space` model in `src/web/models/space.py`:
   - `id: UUID` - Primary key (uuid4)
   - `name: str` - Human-readable space name
   - `description: str | None` - Optional description
   - `slug: str` - URL-friendly identifier (unique, indexed)
   - `owner_email: str` - Email of space creator
   - `search_criteria: dict` - JSON field storing default search params (keywords, company, location, degrees)
   - `is_active: bool` - Whether space accepts contributions (default True)
   - `created_at: datetime` - Creation timestamp
   - `updated_at: datetime` - Last update timestamp

3. Add a `generate_slug()` function that creates URL-safe slugs from space names

4. All code must pass mypy strict mode
5. Follow TDD: write tests first in `tests/web/test_space_model.py`
6. Add ABOUTME comments to new files

Start with tests, then implement the model.
```

---

### Prompt 19: Web Database Models - Contributor

```text
Continue building the web application. We have the Space model.

Create the Contributor model for tracking cookie contributions:

Requirements:
1. Create `src/web/models/contributor.py`

2. Implement `Contributor` model:
   - `id: UUID` - Primary key
   - `space_id: UUID` - Foreign key to Space (indexed)
   - `name: str` - Contributor's display name
   - `email: str | None` - Optional email for notifications
   - `cookies_encrypted: str` - Encrypted cookie data (li_at + JSESSIONID as JSON)
   - `is_valid: bool` - Whether cookies are currently valid (default True)
   - `validation_error: str | None` - Error message if validation failed (e.g., "Session expired", "Invalid credentials")
   - `last_validated_at: datetime | None` - Last validation timestamp
   - `last_used_at: datetime | None` - Last time cookies were used for a search
   - `contributed_at: datetime` - When cookies were submitted
   - `updated_at: datetime | None` - When cookies were last updated/refreshed
   - `revoked_at: datetime | None` - When access was revoked (null if active)

3. Create relationship: Space has many Contributors

4. Implement cookie encryption/decryption helpers:
   - `encrypt_cookies(cookies: dict[str, str], key: bytes) -> str`
   - `decrypt_cookies(encrypted: str, key: bytes) -> dict[str, str]`
   - Use Fernet symmetric encryption from cryptography library

5. Create `CookieStatus` enum:
   - `VALID` - Cookies are working
   - `EXPIRED` - Session has expired
   - `INVALID` - Credentials are invalid/revoked
   - `UNKNOWN` - Not yet validated
   - `RATE_LIMITED` - LinkedIn rate limited this account

6. All code must pass mypy strict mode
7. Follow TDD: write tests first in `tests/web/test_contributor_model.py`
8. Add ABOUTME comments

Start with tests, then implement the model.
```

---

### Prompt 20: Web Database Models - Search Result

```text
Continue building the web application. We have Space and Contributor models.

Create the SearchResult model for aggregated search results:

Requirements:
1. Create `src/web/models/search_result.py`

2. Implement `SearchResult` model:
   - `id: UUID` - Primary key
   - `space_id: UUID` - Foreign key to Space (indexed)
   - `contributor_id: UUID` - Foreign key to Contributor who found this result
   - `linkedin_urn_id: str` - LinkedIn profile URN (indexed)
   - `public_id: str` - URL-friendly LinkedIn ID
   - `first_name: str`
   - `last_name: str`
   - `headline: str | None`
   - `location: str | None`
   - `current_company: str | None`
   - `current_title: str | None`
   - `profile_url: str`
   - `connection_degree: int` - Degree from the contributor
   - `mutual_connection_name: str | None` - Name of mutual connection (for intro path)
   - `found_at: datetime`

3. Add composite unique constraint on (space_id, linkedin_urn_id) for deduplication

4. Create `src/web/models/__init__.py` exporting all models

5. All code must pass mypy strict mode
6. Follow TDD: write tests first in `tests/web/test_search_result_model.py`
7. Add ABOUTME comments

Start with tests, then implement the model.
```

---

### Prompt 21: Web Database Service

```text
Continue building the web application. We have all web models defined.

Create the web database service:

Requirements:
1. Create `src/web/database/__init__.py` and `src/web/database/service.py`

2. Implement `WebDatabaseService` class:
   - `__init__(self, database_url: str)` - Initialize with connection string
   - `init_db(self)` - Create tables
   - `get_session(self)` - Context manager for sessions

   Space operations:
   - `create_space(self, space: Space) -> Space`
   - `get_space_by_slug(self, slug: str) -> Space | None`
   - `get_space_by_id(self, space_id: UUID) -> Space | None`
   - `list_spaces_by_owner(self, email: str) -> list[Space]`
   - `update_space(self, space: Space) -> Space`
   - `deactivate_space(self, space_id: UUID) -> None`

   Contributor operations:
   - `add_contributor(self, contributor: Contributor) -> Contributor`
   - `get_contributors_for_space(self, space_id: UUID, include_revoked: bool = False) -> list[Contributor]`
   - `revoke_contributor(self, contributor_id: UUID) -> None`
   - `update_contributor_validity(self, contributor_id: UUID, is_valid: bool) -> None`

   Search result operations:
   - `save_search_result(self, result: SearchResult) -> SearchResult`
   - `get_results_for_space(self, space_id: UUID, limit: int = 100, offset: int = 0) -> list[SearchResult]`
   - `get_deduplicated_results(self, space_id: UUID) -> list[SearchResult]` - Returns unique profiles

3. Support PostgreSQL via SQLModel

4. All code must pass mypy strict mode
5. Follow TDD: write tests first in `tests/web/test_database_service.py`
6. Use test PostgreSQL database or SQLite for tests
7. Add ABOUTME comments

Start with tests, then implement the service.
```

---

### Prompt 22: Space Service

```text
Continue building the web application. We have the database service.

Create a Space service for business logic:

Requirements:
1. Create `src/web/services/__init__.py` and `src/web/services/space_service.py`

2. Implement `SpaceService` class:
   - `__init__(self, db_service: WebDatabaseService)`

   Methods:
   - `create_space(self, name: str, owner_email: str, description: str | None, search_criteria: dict) -> Space`
     - Generates unique slug from name
     - Handles slug collisions by appending random suffix

   - `get_space(self, slug: str) -> Space | None`

   - `get_shareable_url(self, space: Space, base_url: str) -> str`
     - Returns full URL for sharing: `{base_url}/s/{slug}`

   - `get_space_stats(self, space_id: UUID) -> dict[str, Any]`
     - Returns: contributor_count, valid_contributor_count, total_results, unique_results

   - `can_accept_contributions(self, space: Space) -> bool`
     - Checks is_active status

3. All code must pass mypy strict mode
4. Follow TDD: write tests first in `tests/web/test_space_service.py`
5. Add ABOUTME comments

Start with tests, then implement the service.
```

---

### Prompt 23: Cookie Service

```text
Continue building the web application. We have the Space service.

Create a Cookie service for handling contributor cookies:

Requirements:
1. Create `src/web/services/cookie_service.py`

2. Implement `CookieService` class:
   - `__init__(self, db_service: WebDatabaseService, encryption_key: bytes)`

   Methods:
   - `add_contributor(self, space_id: UUID, name: str, email: str | None, li_at: str, jsessionid: str) -> Contributor`
     - Encrypts cookies before storage
     - Returns saved Contributor

   - `update_contributor_cookies(self, contributor_id: UUID, li_at: str, jsessionid: str) -> Contributor`
     - Updates existing contributor with fresh cookies
     - Resets is_valid to True, clears validation_error
     - Sets updated_at timestamp
     - Returns updated Contributor

   - `validate_contributor_cookies(self, contributor_id: UUID) -> tuple[CookieStatus, str | None]`
     - Decrypts cookies
     - Creates LinkedInClient to test session
     - Catches specific exceptions to determine status:
       - LinkedInAuthError -> CookieStatus.EXPIRED or INVALID
       - LinkedInRateLimitError -> CookieStatus.RATE_LIMITED
       - Success -> CookieStatus.VALID
     - Updates is_valid, validation_error, and last_validated_at
     - Returns (status, error_message)

   - `validate_all_contributors(self, space_id: UUID) -> dict[UUID, CookieStatus]`
     - Validates all active contributors in a space
     - Adds delay between validations to avoid triggering LinkedIn
     - Returns map of contributor_id -> CookieStatus

   - `get_valid_cookies_for_space(self, space_id: UUID) -> list[tuple[Contributor, dict[str, str]]]`
     - Returns list of (Contributor, decrypted_cookies) for valid contributors
     - Includes contributor so caller knows who each cookie belongs to

   - `get_contributors_needing_refresh(self, space_id: UUID, stale_days: int = 7) -> list[Contributor]`
     - Returns contributors whose cookies haven't been validated in stale_days
     - Or contributors marked as EXPIRED/INVALID

   - `revoke_contributor(self, contributor_id: UUID) -> None`
     - Marks contributor as revoked

3. Import LinkedInClient and exceptions from existing linkedin_scraper package

4. All code must pass mypy strict mode
5. Follow TDD: write tests first in `tests/web/test_cookie_service.py`
6. Mock LinkedInClient for validation tests
7. Add ABOUTME comments

Start with tests, then implement the service.
```

---

### Prompt 24: Aggregated Search Service

```text
Continue building the web application. We have Cookie service.

Create an Aggregated Search service that searches across multiple contributors:

Requirements:
1. Create `src/web/services/search_service.py`

2. Implement `AggregatedSearchService` class:
   - `__init__(self, db_service: WebDatabaseService, cookie_service: CookieService)`

   Methods:
   - `execute_space_search(self, space_id: UUID, search_criteria: dict | None = None) -> list[SearchResult]`
     - If search_criteria is None, uses space's default criteria
     - Gets valid cookies from CookieService
     - For each valid contributor:
       - Creates LinkedInClient
       - Executes search with space's criteria
       - Saves results linked to contributor
     - Returns all results (caller handles deduplication display)

   - `get_deduplicated_results(self, space_id: UUID) -> list[SearchResult]`
     - Returns unique profiles across all contributors
     - Prefers results with lower connection_degree
     - Includes mutual_connection_name from closest connection

   - `export_results_csv(self, space_id: UUID) -> str`
     - Returns CSV content as string
     - Includes: name, headline, company, location, profile_url, connection_path
     - Deduplicates before export

3. Reuse SearchFilter and LinkedInClient from linkedin_scraper package

4. All code must pass mypy strict mode
5. Follow TDD: write tests first in `tests/web/test_search_service.py`
6. Mock LinkedInClient
7. Add ABOUTME comments

Start with tests, then implement the service.
```

---

### Prompt 25: FastAPI App Setup

```text
Continue building the web application. We have all services.

Create the FastAPI application structure:

Requirements:
1. Create `src/web/api/__init__.py` and `src/web/api/app.py`

2. Set up FastAPI application:
   - Create main FastAPI app instance
   - Add CORS middleware (configurable origins)
   - Add request ID middleware for tracing
   - Health check endpoint at `/api/health`
   - API version prefix `/api/v1`

3. Create `src/web/api/dependencies.py`:
   - `get_db_service() -> WebDatabaseService` - Dependency injection
   - `get_space_service() -> SpaceService`
   - `get_cookie_service() -> CookieService`
   - `get_search_service() -> AggregatedSearchService`

4. Create `src/web/config.py` with `WebSettings` class:
   - `database_url: str` - PostgreSQL connection string
   - `encryption_key: str` - Fernet key for cookie encryption (from env)
   - `cors_origins: list[str]` - Allowed CORS origins
   - `base_url: str` - Base URL for shareable links

5. All code must pass mypy strict mode
6. Follow TDD: write tests first in `tests/web/test_app.py`
7. Add ABOUTME comments

Start with tests, then implement the app setup.
```

---

### Prompt 26: Space API Endpoints

```text
Continue building the web application. We have the FastAPI app setup.

Create Space API endpoints:

Requirements:
1. Create `src/web/api/routes/__init__.py` and `src/web/api/routes/spaces.py`

2. Create Pydantic schemas in `src/web/api/schemas/space.py`:
   - `SpaceCreate` - Input: name, description, owner_email, search_criteria
   - `SpaceResponse` - Output: id, name, slug, description, owner_email, search_criteria, is_active, created_at, shareable_url
   - `SpaceStats` - Output: contributor_count, valid_contributors, total_results, unique_results

3. Implement endpoints in spaces router:
   - `POST /api/v1/spaces` - Create a new space
     - Returns SpaceResponse with shareable_url

   - `GET /api/v1/spaces/{slug}` - Get space by slug
     - Returns SpaceResponse (public info only)

   - `GET /api/v1/spaces/{slug}/stats` - Get space statistics
     - Returns SpaceStats

   - `PUT /api/v1/spaces/{slug}` - Update space
     - Requires owner verification (simple email check for MVP)
     - Updates name, description, search_criteria, is_active

   - `GET /api/v1/spaces/mine` - List spaces by owner
     - Query param: owner_email
     - Returns list of SpaceResponse

4. Register router with main app

5. All code must pass mypy strict mode
6. Follow TDD: write tests first in `tests/web/test_space_routes.py`
7. Add ABOUTME comments

Start with tests, then implement the endpoints.
```

---

### Prompt 27: Contributor API Endpoints

```text
Continue building the web application. We have Space endpoints.

Create Contributor API endpoints:

Requirements:
1. Create `src/web/api/routes/contributors.py`

2. Create Pydantic schemas in `src/web/api/schemas/contributor.py`:
   - `ContributorCreate` - Input: name, email (optional), li_at, jsessionid
   - `ContributorUpdate` - Input: li_at, jsessionid (for refreshing cookies)
   - `ContributorResponse` - Output: id, name, email, status (CookieStatus enum), validation_error, contributed_at, updated_at, last_validated_at, last_used_at
   - `ContributorList` - Output: list of contributors with counts (total, valid, expired, invalid)

3. Implement endpoints:
   - `POST /api/v1/spaces/{slug}/contributors` - Add contributor to space
     - Accepts ContributorCreate
     - Validates cookies before accepting (optional, query param)
     - Returns ContributorResponse

   - `GET /api/v1/spaces/{slug}/contributors` - List contributors
     - Returns ContributorList
     - Query param: include_revoked (default false)
     - Query param: status_filter (optional, filter by CookieStatus)

   - `PUT /api/v1/spaces/{slug}/contributors/{id}` - Update/refresh contributor's cookies
     - Accepts ContributorUpdate with new li_at and jsessionid
     - Validates new cookies
     - Returns updated ContributorResponse
     - This is how contributors refresh expired cookies

   - `POST /api/v1/spaces/{slug}/contributors/{id}/validate` - Validate contributor's cookies
     - Returns updated ContributorResponse with current status

   - `DELETE /api/v1/spaces/{slug}/contributors/{id}` - Revoke contributor access
     - Sets revoked_at timestamp
     - Returns 204 No Content

   - `GET /api/v1/spaces/{slug}/contributors/stale` - Get contributors needing refresh
     - Query param: stale_days (default 7)
     - Returns ContributorList of contributors with expired/stale cookies

4. Register router with main app

5. All code must pass mypy strict mode
6. Follow TDD: write tests first in `tests/web/test_contributor_routes.py`
7. Add ABOUTME comments

Start with tests, then implement the endpoints.
```

---

### Prompt 28: Search API Endpoints

```text
Continue building the web application. We have Contributor endpoints.

Create Search API endpoints:

Requirements:
1. Create `src/web/api/routes/search.py`

2. Create Pydantic schemas in `src/web/api/schemas/search.py`:
   - `SearchCriteria` - Input: keywords, company, location, degrees (list[int])
   - `SearchResultResponse` - Output: id, name, headline, company, location, profile_url, connection_degree, mutual_connection, contributor_name
   - `SearchResultList` - Output: results list, total_count, unique_count
   - `ExportResponse` - Output: csv_url or csv_content

3. Implement endpoints:
   - `POST /api/v1/spaces/{slug}/search` - Execute search across all valid contributors
     - Optional body: SearchCriteria (uses space defaults if not provided)
     - Returns SearchResultList
     - Background job consideration: for MVP, run synchronously but design for future async

   - `GET /api/v1/spaces/{slug}/results` - Get cached search results
     - Query params: limit, offset, deduplicate (bool)
     - Returns SearchResultList

   - `GET /api/v1/spaces/{slug}/export` - Export results as CSV
     - Query param: format (csv only for now)
     - Returns CSV content or download URL

4. Register router with main app

5. All code must pass mypy strict mode
6. Follow TDD: write tests first in `tests/web/test_search_routes.py`
7. Add ABOUTME comments

Start with tests, then implement the endpoints.
```

---

### Prompt 29: Frontend Project Setup

```text
Continue building the web application. The backend API is complete.

Set up the Next.js frontend project:

Requirements:
1. Create frontend directory structure:
   - `frontend/` - Next.js application root
   - Initialize with: `pnpm create next-app frontend --typescript --tailwind --eslint --app`

2. Configure project:
   - Add shadcn/ui: `pnpm dlx shadcn@latest init`
   - Add dependencies: tanstack-query, zustand, framer-motion
   - Configure Biome for formatting/linting
   - Set up path aliases in tsconfig.json (@/ for src/)

3. Create base configuration files:
   - `frontend/src/lib/api.ts` - API client configuration
     - Base URL from environment variable
     - Fetch wrapper with error handling

   - `frontend/src/lib/query-client.ts` - TanStack Query client setup

   - `frontend/src/store/index.ts` - Zustand store skeleton

4. Create basic layout:
   - `frontend/src/app/layout.tsx` - Root layout with providers
   - `frontend/src/app/page.tsx` - Landing page placeholder
   - `frontend/src/components/providers.tsx` - QueryClientProvider wrapper

5. Add environment file template:
   - `frontend/.env.example` with NEXT_PUBLIC_API_URL

6. Follow TDD: write tests in `frontend/__tests__/`
7. Use Jest for unit tests, set up Playwright for E2E (config only for now)

Start by setting up the project, then implement the base files.
```

---

### Prompt 30: API Client Generation

```text
Continue building the frontend. We have the project setup.

Generate typed API client from OpenAPI schema:

Requirements:
1. Add openapi-ts to backend:
   - Configure FastAPI to export OpenAPI schema
   - Add script to pyproject.toml: `generate-openapi`

2. Set up openapi-ts in frontend:
   - Install: `pnpm add -D @hey-api/openapi-ts`
   - Create `frontend/openapi-ts.config.ts`
   - Add script to package.json: `generate-client`

3. Create `frontend/src/lib/api/` directory:
   - Generated client files will go here
   - Create manual types file for any custom types

4. Create TanStack Query hooks wrapper:
   - `frontend/src/hooks/api/useSpaces.ts`
     - `useCreateSpace()`
     - `useSpace(slug)`
     - `useSpaceStats(slug)`
     - `useMySpaces(email)`

   - `frontend/src/hooks/api/useContributors.ts`
     - `useAddContributor(slug)`
     - `useContributors(slug)`
     - `useValidateContributor(slug, id)`
     - `useRevokeContributor(slug, id)`

   - `frontend/src/hooks/api/useSearch.ts`
     - `useExecuteSearch(slug)`
     - `useSearchResults(slug)`
     - `useExportResults(slug)`

5. Follow TDD: write tests for hooks
6. Mock API responses in tests

Start by setting up openapi-ts config, then create the hooks.
```

---

### Prompt 31: UI Component Library Setup

```text
Continue building the frontend. We have the API client.

Set up the shared UI component library:

Requirements:
1. Install shadcn/ui components:
   - button, input, textarea, label
   - card, dialog, dropdown-menu
   - table, tabs
   - toast, alert
   - form (with react-hook-form integration)

2. Create custom components in `frontend/src/components/ui/`:
   - `loading-spinner.tsx` - Animated loading indicator
   - `page-header.tsx` - Consistent page headers with title, description, actions
   - `empty-state.tsx` - Empty state with icon, message, and action
   - `error-boundary.tsx` - Error boundary with fallback UI

3. Create layout components in `frontend/src/components/layout/`:
   - `navbar.tsx` - Top navigation bar
   - `footer.tsx` - Simple footer
   - `container.tsx` - Max-width container with padding

4. Set up Tailwind theme customization:
   - Brand colors
   - Custom spacing if needed
   - Dark mode support (basic)

5. Follow TDD: write component tests
6. Use Storybook or simple test renders to verify components

Start with shadcn installation, then implement custom components.
```

---

### Prompt 32: Landing Page

```text
Continue building the frontend. We have the component library.

Create the landing page:

Requirements:
1. Create `frontend/src/app/page.tsx`:
   - Hero section explaining the tool
   - "Create a Space" CTA button
   - How it works section (3 steps)
   - Simple footer

2. Implement responsive design:
   - Mobile-first approach
   - Proper spacing and typography

3. Add Framer Motion animations:
   - Fade-in on scroll for sections
   - Button hover effects

4. Create reusable section components:
   - `frontend/src/components/landing/hero.tsx`
   - `frontend/src/components/landing/how-it-works.tsx`
   - `frontend/src/components/landing/cta-section.tsx`

5. Follow TDD: write tests for page rendering
6. Test responsive breakpoints

Start with the page structure, then add animations.
```

---

### Prompt 33: Space Creation Flow

```text
Continue building the frontend. We have the landing page.

Create the space creation flow:

Requirements:
1. Create `frontend/src/app/create/page.tsx`:
   - Multi-step form using shadcn Form
   - Step 1: Space basics (name, description)
   - Step 2: Search criteria (keywords, company, location, degrees)
   - Step 3: Your info (email for ownership)
   - Review and submit

2. Create form components:
   - `frontend/src/components/spaces/space-form.tsx` - Main form container
   - `frontend/src/components/spaces/search-criteria-form.tsx` - Search params
   - `frontend/src/components/spaces/step-indicator.tsx` - Progress indicator

3. Implement form validation with Zod schemas:
   - Space name required, min 3 chars
   - Email required, valid format
   - Keywords required for search criteria

4. On successful creation:
   - Show success dialog with shareable link
   - Copy to clipboard button
   - Navigate to space admin page

5. Use Zustand for multi-step form state

6. Follow TDD: write tests for form validation and submission
7. Mock API calls in tests

Start with the page structure, then implement form steps.
```

---

### Prompt 34: Space Admin Dashboard

```text
Continue building the frontend. We have space creation.

Create the space admin dashboard:

Requirements:
1. Create `frontend/src/app/spaces/[slug]/admin/page.tsx`:
   - Space info card (name, description, shareable link)
   - Contributors list with status indicators
   - Search results summary
   - Quick actions (run search, export, settings)

2. Create dashboard components:
   - `frontend/src/components/spaces/space-info-card.tsx`
   - `frontend/src/components/spaces/contributor-list.tsx` - Table with:
     - Name, email
     - Status badge with color coding:
       - Green "Valid" - cookies working
       - Yellow "Stale" - not validated recently
       - Red "Expired" - session expired, needs refresh
       - Gray "Unknown" - not yet validated
       - Orange "Rate Limited" - temporarily unavailable
     - Last validated timestamp
     - Actions: validate, request refresh, revoke
   - `frontend/src/components/spaces/stats-card.tsx` - Key metrics including:
     - Total contributors
     - Valid contributors (can be used for search)
     - Contributors needing attention (expired/stale)
   - `frontend/src/components/spaces/cookie-health-banner.tsx`
     - Shows warning if many contributors have expired cookies
     - "X of Y contributors need to refresh their cookies"
     - Button to send refresh reminders (if emails available)

3. Implement real-time updates:
   - Use TanStack Query's refetch interval for stats
   - Show loading states during actions

4. Add action handlers:
   - Copy shareable link to clipboard
   - Validate contributor (with loading state)
   - Copy individual refresh link for contributor
   - Revoke contributor (with confirmation dialog)

5. Simple authentication check:
   - Query param or localStorage for owner_email
   - Show warning if not owner

6. Follow TDD: write tests for dashboard interactions

Start with page structure, then implement components.
```

---

### Prompt 35: Shareable Link View

```text
Continue building the frontend. We have the admin dashboard.

Create the shareable link view (public space page):

Requirements:
1. Create `frontend/src/app/s/[slug]/page.tsx`:
   - Public view of space
   - Shows space name, description, search target description
   - Large CTA: "Contribute Your Network"
   - Info about what contributing means

2. Show space status:
   - Active: Show contribution form link
   - Inactive: Show "This space is no longer accepting contributions"

3. Create trust-building elements:
   - How cookies are used (encrypted, not shared)
   - What happens when you contribute
   - Privacy notice

4. Link to contribution page: `/s/[slug]/contribute`

5. Responsive design:
   - Works well on mobile (link sharing via messaging)
   - Clear, simple layout

6. Follow TDD: write tests for page rendering and status handling

Start with page layout, then add trust elements.
```

---

### Prompt 36: Cookie Contribution Page

```text
Continue building the frontend. We have the shareable link view.

Create the cookie contribution flow:

Requirements:
1. Create `frontend/src/app/s/[slug]/contribute/page.tsx`:
   - Check space is active, show error if not
   - Contributor info form (name, email optional)
   - Cookie input section

2. Create `frontend/src/app/s/[slug]/refresh/[contributor_id]/page.tsx`:
   - Cookie refresh page for existing contributors
   - Shows contributor name and current status
   - Explains why refresh is needed (e.g., "Your session has expired")
   - Same cookie input form, but updates existing contributor
   - Success message confirms cookies were updated

3. Create cookie instruction components:
   - `frontend/src/components/contribute/cookie-instructions.tsx`
     - Step-by-step guide with screenshots/diagrams
     - Browser-specific tabs (Chrome, Firefox, Safari, Edge)
     - Expandable detailed steps
   - `frontend/src/components/contribute/cookie-input-form.tsx`
     - Input for li_at cookie
     - Input for JSESSIONID cookie
     - Clear labels explaining what each cookie is
     - Reusable for both new contribution and refresh flows

4. Add embedded video placeholder:
   - Section for Loom video embed
   - Fallback text instructions if video fails to load

5. Form submission:
   - Optional validation before submit
   - Success state with thank you message
   - For refresh: "Your cookies have been updated. Thank you!"
   - Error handling with helpful messages

6. Cookie status indicators:
   - If refreshing, show current status (expired, invalid, etc.)
   - Explain what the error means in user-friendly terms

7. Follow TDD: write tests for contribution flow

Start with the page, then implement instruction components.
```

---

### Prompt 37: Background Cookie Validation ⭐ PRIORITY

```text
Continue building the web application. We have the cookie management UI.

Add background task for cookie validation - this is critical for detecting expired cookies:

Requirements:
1. Create `src/web/tasks/__init__.py` and `src/web/tasks/validation.py`

2. Implement validation task:
   - `validate_space_cookies(space_id: UUID) -> ValidationReport`
     - Validates all contributor cookies
     - Marks invalid cookies in database with appropriate CookieStatus
     - Returns summary: total, valid, expired, invalid, rate_limited

   - `validate_all_spaces() -> dict[UUID, ValidationReport]`
     - Validates cookies across all active spaces
     - Adds delays between spaces to avoid LinkedIn detection
     - For use in scheduled jobs

3. Add endpoint to trigger validation:
   - `POST /api/v1/spaces/{slug}/validate-all`
   - Returns immediately with task status
   - For MVP: run synchronously but return quickly

4. Create `src/web/tasks/notifications.py`:
   - `generate_refresh_links(space_id: UUID) -> list[tuple[Contributor, str]]`
     - Returns list of (contributor, refresh_url) for expired contributors

   - `send_refresh_reminder(contributor: Contributor, refresh_url: str) -> bool`
     - Sends email to contributor (if email provided) with refresh link
     - For MVP: just log the email, actual sending is future work
     - Returns whether notification was "sent" (logged)

5. Add periodic validation concept:
   - Create config for validation interval (default: daily)
   - Create config for stale threshold (default: 7 days)
   - Document how to set up cron job externally
   - Example cron: `0 6 * * * curl -X POST http://localhost:8000/api/v1/admin/validate-all`

6. Add admin endpoint:
   - `POST /api/v1/admin/validate-all` - Validates all spaces (for cron job)
   - Protected by admin API key from settings

7. All code must pass mypy strict mode
8. Follow TDD: write tests with mocked LinkedIn client
9. Add ABOUTME comments

Start with tests, then implement task.
```

---

### Prompt 38: Search Interface

```text
Continue building the frontend. We have cookie management and validation in place.

Create the search interface for space admins:

Requirements:
1. Create `frontend/src/app/spaces/[slug]/search/page.tsx`:
   - Search criteria form (pre-filled with space defaults)
   - Run search button
   - Results display area

2. Create search components:
   - `frontend/src/components/search/search-form.tsx`
     - Keywords input
     - Company name input
     - Location input
     - Connection degree checkboxes (1st, 2nd, 3rd)
   - `frontend/src/components/search/search-status.tsx`
     - Shows progress: "Searching X of Y contributor networks..."
     - Results count as they come in

3. Results display:
   - Loading state during search
   - Results table with columns: Name, Headline, Company, Location, Degree, Via (contributor)
   - Deduplication toggle
   - Sort options

4. Handle long-running searches:
   - For MVP: show loading spinner
   - Timeout handling with retry option

5. Follow TDD: write tests for search flow

Start with the page, then implement search components.
```

---

### Prompt 39: Results Table & Export

```text
Continue building the frontend. We have the search interface.

Create the results table and export functionality:

Requirements:
1. Create `frontend/src/components/search/results-table.tsx`:
   - Sortable columns: Name, Headline, Company, Location, Degree
   - Connection path column showing mutual connection
   - Link to LinkedIn profile (opens in new tab)
   - Pagination for large result sets

2. Create export components:
   - `frontend/src/components/search/export-button.tsx`
     - Dropdown with export options
     - CSV export (download file)
   - `frontend/src/components/search/export-preview.tsx`
     - Preview of what will be exported
     - Row count, columns included

3. Implement table features:
   - Client-side sorting
   - Client-side filtering (search within results)
   - Row selection for partial export

4. Export functionality:
   - Call export API endpoint
   - Trigger file download
   - Show toast on success/error

5. Follow TDD: write tests for table and export

Start with the table, then add export functionality.
```

---

### Prompt 40: Settings & Space Management

```text
Continue building the frontend. We have results and export.

Create space settings and management pages:

Requirements:
1. Create `frontend/src/app/spaces/[slug]/settings/page.tsx`:
   - Edit space name and description
   - Update default search criteria
   - Deactivate space (with confirmation)
   - Delete space (with double confirmation)

2. Create settings components:
   - `frontend/src/components/spaces/settings-form.tsx`
   - `frontend/src/components/spaces/danger-zone.tsx`
     - Deactivate button
     - Delete button with warning

3. Implement form submission:
   - Optimistic updates with rollback on error
   - Success/error toasts

4. Add confirmation dialogs:
   - Deactivate: "Contributors won't be able to add cookies"
   - Delete: "This cannot be undone. Type space name to confirm"

5. Follow TDD: write tests for settings operations

Start with the settings form, then add danger zone.
```

---

### Prompt 41: Error Handling & Loading States

```text
Continue building the frontend. We have all main features.

Implement comprehensive error handling and loading states:

Requirements:
1. Create error components:
   - `frontend/src/components/error/error-page.tsx` - Full page error
   - `frontend/src/components/error/error-inline.tsx` - Inline error message
   - `frontend/src/components/error/not-found.tsx` - 404 page for spaces

2. Create loading components:
   - `frontend/src/components/loading/page-skeleton.tsx` - Full page skeleton
   - `frontend/src/components/loading/table-skeleton.tsx` - Table loading state
   - `frontend/src/components/loading/card-skeleton.tsx` - Card loading state

3. Implement error boundary:
   - Wrap main content in error boundary
   - Log errors to console (prepare for future logging service)
   - Show user-friendly error message

4. Create toast notifications system:
   - Success: Green toast for completed actions
   - Error: Red toast with retry action
   - Info: Blue toast for informational messages

5. Update all pages to use proper loading/error states

6. Follow TDD: write tests for error scenarios

Start with error components, then update existing pages.
```

---

### Prompt 42: Backend - Rate Limiting for Web API

```text
Continue building the web application. Frontend is feature-complete.

Add rate limiting to the web API:

Requirements:
1. Create `src/web/api/middleware/rate_limit.py`:
   - IP-based rate limiting for public endpoints
   - Configurable limits per endpoint type
   - Return 429 with Retry-After header

2. Configure limits:
   - Space creation: 10 per hour per IP
   - Contribution: 5 per hour per IP
   - Search execution: 3 per hour per space
   - Read endpoints: 100 per minute per IP

3. Store rate limit state:
   - Use database for persistence (simple table)
   - Or use Redis if available (check settings)

4. Add middleware to FastAPI app

5. All code must pass mypy strict mode
6. Follow TDD: write tests for rate limit scenarios
7. Add ABOUTME comments

Start with tests, then implement middleware.
```

---

### Prompt 43: Integration Testing - Backend

```text
Continue building the web application. We have background tasks.

Create comprehensive backend integration tests:

Requirements:
1. Create `tests/web/test_integration.py`

2. Test full flows:
   - Create space → Add contributors → Execute search → Export results
   - Invalid cookie handling during search
   - Rate limit enforcement
   - Space deactivation preventing new contributions

3. Test edge cases:
   - Duplicate contributor emails
   - Search with no valid contributors
   - Export with no results
   - Slug collision handling

4. Set up test fixtures:
   - Test database with sample data
   - Mocked LinkedIn client responses
   - Sample search results

5. Ensure >80% code coverage for web package

6. All tests must pass
7. Document any manual testing needed

Start with happy path tests, then add edge cases.
```

---

### Prompt 44: Integration Testing - Frontend

```text
Continue building the web application. We have backend integration tests.

Create comprehensive frontend integration tests:

Requirements:
1. Set up Playwright for E2E tests:
   - `frontend/e2e/` directory
   - Configure playwright.config.ts
   - Mock API server for tests

2. Test user flows:
   - Landing → Create space → Get shareable link
   - Open shareable link → Contribute cookies
   - Admin dashboard → View contributors → Run search
   - Search results → Export CSV

3. Test responsive design:
   - Mobile viewport tests
   - Tablet viewport tests

4. Test error scenarios:
   - Invalid space slug (404)
   - API errors (show error message)
   - Form validation errors

5. Create test utilities:
   - API mock helpers
   - Page object models for common pages

6. All tests must pass

Start with happy path E2E tests, then add error scenarios.
```

---

### Prompt 45: Documentation

```text
Continue building the web application. We have all tests.

Create user and developer documentation:

Requirements:
1. Update README.md:
   - Add web application section
   - Development setup instructions
   - Environment variables reference
   - API documentation link

2. Create `docs/` directory:
   - `docs/api.md` - API reference (or link to Swagger)
   - `docs/deployment.md` - Deployment guide
   - `docs/cookie-extraction.md` - User guide for getting LinkedIn cookies

3. Add inline documentation:
   - Docstrings for all public API endpoints
   - TypeScript JSDoc comments for components

4. Create `.env.example` files:
   - Backend: database URL, encryption key, CORS
   - Frontend: API URL

5. Do NOT create excessive documentation - keep it minimal and useful

Start with README updates, then add essential docs only.
```

---

### Prompt 46: Deployment Configuration

```text
Continue building the web application. We have documentation.

Create deployment configuration:

Requirements:
1. Create Docker configuration:
   - `Dockerfile` for backend
   - `frontend/Dockerfile` for frontend
   - `docker-compose.yml` for local development
   - `docker-compose.prod.yml` for production setup

2. Backend Dockerfile:
   - Use Python 3.12 slim image
   - Install uv for dependency management
   - Run with uvicorn

3. Frontend Dockerfile:
   - Multi-stage build
   - Build with pnpm
   - Serve with nginx or Next.js standalone

4. Docker Compose:
   - Backend service
   - Frontend service
   - PostgreSQL service
   - Network configuration

5. Environment configuration:
   - Production environment variables template
   - Secret management notes

6. Do NOT include CI/CD pipelines - just Docker setup

Start with backend Dockerfile, then frontend, then compose.
```

---

### Prompt 47: Final Integration & Polish

```text
Final step: integrate everything and polish.

Requirements:
1. Verify all components work together:
   - Run full Docker Compose stack
   - Test complete user flow end-to-end
   - Fix any integration issues

2. Code cleanup:
   - Remove any TODO comments that are complete
   - Ensure consistent error messages
   - Verify all ABOUTME comments are present

3. Run all quality checks:
   - `uv run pytest` - All tests pass
   - `uv run mypy src/` - No type errors
   - `uv run ruff check src/` - No lint errors
   - `pnpm test` - Frontend tests pass
   - `pnpm run lint` - Frontend lint passes

4. Final testing:
   - Create a test space
   - Add test contributor
   - Execute search
   - Export results

5. Update version in pyproject.toml to 2.0.0

6. Create git tag for release

Document any known limitations or future improvements in README.
```

---

## Dependency Graph

```
Phase 2.1: Database Models
Prompt 18 (Space) ─────────────────────────┐
    ↓                                      │
Prompt 19 (Contributor + CookieStatus) ────┤  ⭐ Cookie expiration fields
    ↓                                      │
Prompt 20 (SearchResult) ──────────────────┘
    ↓
Phase 2.2: Services
Prompt 21 (Database Service) ←── Prompts 18-20
    ↓
Prompt 22 (Space Service) ←── Prompt 21
    ↓
Prompt 23 (Cookie Service) ←── Prompts 21-22  ⭐ Validation & refresh logic
    ↓
Prompt 24 (Search Service) ←── Prompt 23
    ↓
Phase 2.3: API
Prompt 25 (App Setup) ←── Prompts 21-24
    ↓
Prompt 26 (Space Routes) ←── Prompt 25
    ↓
Prompt 27 (Contributor Routes) ←── Prompt 26  ⭐ Refresh endpoints
    ↓
Prompt 28 (Search Routes) ←── Prompt 27
    ↓
Phase 2.4: Frontend Foundation
Prompt 29 (Project Setup) ─── runs parallel to API ───┐
    ↓                                                 │
Prompt 30 (API Client) ←── Prompts 28, 29             │
    ↓                                                 │
Prompt 31 (UI Components) ←── Prompt 30               │
    ↓                                                 │
Prompt 32 (Landing Page) ←── Prompt 31                │
    ↓                                                 │
Phase 2.5: Cookie Management UI ⭐ PRIORITY           │
Prompt 33 (Create Space) ←── Prompt 32 ←──────────────┘
    ↓
Prompt 34 (Admin Dashboard) ←── Prompt 33     ⭐ Cookie health indicators
    ↓
Prompt 35 (Public Space View) ←── Prompt 34
    ↓
Prompt 36 (Contribution/Refresh Page) ←── 35  ⭐ Cookie refresh flow
    ↓
Phase 2.6: Background Cookie Validation ⭐ PRIORITY
Prompt 37 (Validation Tasks) ←── Prompt 36    ⭐ Proactive expiration detection
    ↓
Phase 2.7: Search & Export UI
Prompt 38 (Search Interface) ←── Prompt 37
    ↓
Prompt 39 (Results & Export) ←── Prompt 38
    ↓
Prompt 40 (Settings) ←── Prompt 39
    ↓
Prompt 41 (Error/Loading) ←── Prompt 40
    ↓
Phase 2.8: Polish & Integration
Prompt 42 (Rate Limiting) ←── Prompt 41
    ↓
Prompt 43 (Backend Tests) ←── Prompt 42
    ↓
Prompt 44 (Frontend Tests) ←── Prompt 43
    ↓
Prompt 45 (Documentation) ←── Prompt 44
    ↓
Prompt 46 (Deployment) ←── Prompt 45
    ↓
Prompt 47 (Final Integration) ←── Prompt 46
```

## Quality Gates

After each prompt, verify:
1. All new tests pass: `uv run pytest tests/`
2. Type checking passes: `uv run mypy src/`
3. Linting passes: `uv run ruff check src/`
4. Frontend tests pass: `pnpm test` (when applicable)
5. Frontend lint passes: `pnpm run lint` (when applicable)

## Notes

- Phase 1 (CLI tool) is complete and should not be modified
- Web app reuses existing LinkedIn client and search logic
- Cookie encryption is critical - never store plain cookies
- Start with simple owner verification (email check), add proper auth later
- Rate limiting protects against abuse
- Background tasks are simple for MVP - enhance with job queue later

## Cookie Expiration Strategy

LinkedIn cookies can expire or be invalidated. The system handles this through:

### Detection
- **Proactive validation**: Daily background job validates all contributor cookies
- **On-demand validation**: Validate before searches, mark failures immediately
- **Status tracking**: `CookieStatus` enum tracks VALID, EXPIRED, INVALID, RATE_LIMITED, UNKNOWN

### User Communication
- **Dashboard health banner**: "X of Y contributors need to refresh their cookies"
- **Status badges**: Color-coded indicators for each contributor
- **Refresh links**: Unique URL for each contributor to update their cookies: `/s/{slug}/refresh/{contributor_id}`

### Refresh Flow
1. Space owner sees expired contributors in dashboard
2. Owner copies refresh link or triggers email notification
3. Contributor receives link, visits refresh page
4. Contributor submits fresh cookies using same instructions
5. System validates and updates contributor record

### Minimizing Expiration
- Aggressive rate limiting (lower than LinkedIn's actual limits)
- Random delays between API calls (jitter)
- Spread searches across time (don't hit all accounts simultaneously)
- Use cookies sparingly - only for actual searches, not constant validation
