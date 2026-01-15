# LinkedIn Network Scraper - Todo

## Progress Tracker

Track completion of each prompt by checking the box when done.

---

## Phase 1: CLI Tool (Complete)

### Phase 1.1: Core Infrastructure
- [x] **Prompt 1**: Database Service Foundation
- [x] **Prompt 2**: Cookie Manager Service
- [x] **Prompt 3**: Configuration Module
- [x] **Prompt 4**: CLI Skeleton with Typer

### Phase 1.2: Rate Limiting
- [x] **Prompt 5**: Rate Limiter Core Logic
- [x] **Prompt 6**: Rate Limiter Delay Logic
- [x] **Prompt 7**: Rate Limiter Status Display

### Phase 1.3: LinkedIn Integration
- [x] **Prompt 8**: LinkedIn Client Wrapper
- [x] **Prompt 9**: LinkedIn Search Functionality
- [x] **Prompt 10**: Company ID Resolution

### Phase 1.4: CLI Commands
- [x] **Prompt 11**: Login Command Implementation
- [x] **Prompt 12**: Search Command Implementation
- [x] **Prompt 13**: Status Command Implementation
- [x] **Prompt 14**: Export Command Implementation

### Phase 1.5: Export & Polish
- [x] **Prompt 15**: Rich Output Formatting
- [x] **Prompt 16**: Error Handling and User Messages
- [x] **Prompt 17**: Final Integration and Polish

---

## Phase 2: Web Application

### Phase 2.1: Database Schema & Models
- [ ] **Prompt 18**: Web Database Models - Space
- [ ] **Prompt 19**: Web Database Models - Contributor ⭐ *CookieStatus enum, validation fields*
- [ ] **Prompt 20**: Web Database Models - Search Result

### Phase 2.2: Core API Services
- [ ] **Prompt 21**: Web Database Service
- [ ] **Prompt 22**: Space Service
- [ ] **Prompt 23**: Cookie Service ⭐ *Validation, refresh, expiration detection*
- [ ] **Prompt 24**: Aggregated Search Service

### Phase 2.3: API Endpoints
- [ ] **Prompt 25**: FastAPI App Setup
- [ ] **Prompt 26**: Space API Endpoints
- [ ] **Prompt 27**: Contributor API Endpoints ⭐ *Cookie refresh endpoints*
- [ ] **Prompt 28**: Search API Endpoints

### Phase 2.4: Frontend Foundation
- [ ] **Prompt 29**: Frontend Project Setup
- [ ] **Prompt 30**: API Client Generation
- [ ] **Prompt 31**: UI Component Library Setup
- [ ] **Prompt 32**: Landing Page

### Phase 2.5: Cookie Management UI ⭐ PRIORITY
- [ ] **Prompt 33**: Space Creation Flow
- [ ] **Prompt 34**: Space Admin Dashboard ⭐ *Cookie health indicators, status badges*
- [ ] **Prompt 35**: Shareable Link View
- [ ] **Prompt 36**: Cookie Contribution & Refresh Page ⭐ *Refresh flow for expired cookies*

### Phase 2.6: Background Cookie Validation ⭐ PRIORITY
- [ ] **Prompt 37**: Background Cookie Validation ⭐ *Proactive expiration detection, notifications*

### Phase 2.7: Search & Export UI
- [ ] **Prompt 38**: Search Interface
- [ ] **Prompt 39**: Results Table & Export
- [ ] **Prompt 40**: Settings & Space Management
- [ ] **Prompt 41**: Error Handling & Loading States

### Phase 2.8: Polish & Integration
- [ ] **Prompt 42**: Backend - Rate Limiting for Web API
- [ ] **Prompt 43**: Integration Testing - Backend
- [ ] **Prompt 44**: Integration Testing - Frontend
- [ ] **Prompt 45**: Documentation
- [ ] **Prompt 46**: Deployment Configuration
- [ ] **Prompt 47**: Final Integration & Polish

---

## Current Status

**Current Phase**: Phase 2 - Web Application
**Current Prompt**: 18 (Web Database Models - Space)
**Last Updated**: 2026-01-15

---

## Cookie Expiration Priority Items

The following prompts are critical for handling cookie expiration:

| Prompt | Component | Cookie Feature |
|--------|-----------|----------------|
| **19** | Contributor Model | `CookieStatus` enum, `validation_error`, `last_validated_at`, `updated_at` |
| **23** | Cookie Service | `validate_contributor_cookies()`, `update_contributor_cookies()`, `get_contributors_needing_refresh()` |
| **27** | Contributor API | `PUT /contributors/{id}` for refresh, `GET /contributors/stale` |
| **34** | Admin Dashboard | Cookie health banner, status badges (Valid/Expired/Stale) |
| **36** | Contribution Page | `/s/{slug}/refresh/{contributor_id}` for cookie refresh flow |
| **37** | Background Tasks | Proactive validation, refresh notifications |

---

## Quick Reference

### Backend Commands (Python/uv)
```bash
# Run tests
uv run pytest tests/

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Format code
uv run ruff format src/

# Coverage report
uv run pytest --cov-report=html
```

### Frontend Commands (pnpm)
```bash
# Install dependencies
pnpm install

# Development server
pnpm dev

# Run tests
pnpm test

# Linting
pnpm lint

# Build
pnpm build
```

### Docker Commands
```bash
# Start development stack
docker-compose up -d

# View logs
docker-compose logs -f

# Stop stack
docker-compose down
```

---

## Notes

- Phase 1 (CLI) is complete - do not modify unless bug fixes needed
- Start each Phase 2 prompt by writing tests first (TDD)
- Verify quality gates after each prompt completion
- Web app reuses existing LinkedIn client from Phase 1
- **Cookie expiration is a critical UX concern** - prioritize prompts marked with ⭐
