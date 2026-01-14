# LinkedIn Connection Search Tool - PRD

## 1. Problem Statement

### Background
When job hunting, doing sales outreach, or recruiting, warm introductions through mutual connections dramatically increase response rates. LinkedIn shows connection paths but makes it tedious to:
- Search across multiple friends' networks
- Filter by specific criteria (job title, company, location)
- Track which connections are 1st vs 2nd degree from different accounts

### User Pain Points
1. **Fragmented visibility**: No way to aggregate "who do I know" across multiple LinkedIn accounts
2. **Manual searching**: Each search requires logging into LinkedIn, navigating UI, scrolling through results
3. **No persistence**: Search results disappear; can't easily compare or export

### Target Users
- Job seekers looking for referrals at target companies
- Sales/BD professionals seeking warm intros to prospects
- Recruiters mapping talent networks

---

## 2. Product Overview

### What It Is
A command-line tool that searches LinkedIn connections using session cookies, allowing users to:
- Search their own and friends' LinkedIn networks (with their permission/cookies)
- Filter by job title, location, company, and connection degree
- Export results to CSV for analysis

### What It Is NOT
- A browser extension
- A web application
- A tool for mass messaging or automation beyond search
- A replacement for LinkedIn Sales Navigator

### Key Differentiator
Uses friends' cookies (with consent) to search their networks, aggregating visibility across multiple accounts.

---

## 3. User Stories

### US-1: Store LinkedIn Cookie
> As a user, I want to securely store my LinkedIn cookie so I can run searches without re-entering it each time.

**Acceptance Criteria:**
- User can paste their `li_at` cookie from browser dev tools
- Cookie is stored securely using OS keyring (macOS Keychain, Windows Credential Manager)
- User can verify stored cookie is valid
- User can delete/replace stored cookie

### US-2: Search Connections by Job Title
> As a job seeker, I want to search for "Software Engineers" in my network so I can identify potential referral sources.

**Acceptance Criteria:**
- User can specify keyword search terms
- Results include 1st and 2nd degree connections by default
- Each result shows: name, headline, company, location, connection degree
- Results are displayed in terminal with Rich formatting

### US-3: Filter by Location
> As a user, I want to filter search results by location so I can find connections in specific regions.

**Acceptance Criteria:**
- User can specify location filter (e.g., "United States", "San Francisco Bay Area")
- Location filter combines with other filters (AND logic)

### US-4: Filter by Company
> As a sales rep, I want to find connections who work at Disney so I can request warm introductions.

**Acceptance Criteria:**
- User can specify company name filter
- Tool resolves company name to LinkedIn company ID
- Results only include people at specified company

### US-5: Export to CSV
> As a user, I want to export search results to CSV so I can analyze them in a spreadsheet.

**Acceptance Criteria:**
- User can export stored results to CSV file
- CSV includes all profile fields: name, headline, company, title, location, profile URL, connection degree
- Export includes timestamp and search query metadata

### US-6: Rate Limit Protection
> As a user, I want the tool to protect my account by enforcing rate limits so I don't get banned.

**Acceptance Criteria:**
- Tool enforces max 25 searches per day per account
- Minimum 60 seconds between API calls
- Random jitter (30-120s) added between requests
- Warning displayed when approaching daily limit
- Status command shows remaining quota

### US-7: Multi-Account Support
> As a user, I want to store cookies for multiple LinkedIn accounts so I can search across friends' networks.

**Acceptance Criteria:**
- User can store multiple cookies with labels (e.g., "my-account", "john-friend")
- User can specify which account to use for each search
- Results indicate which account found each connection

---

## 4. Functional Requirements

### FR-1: Authentication
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | Accept `li_at` cookie via CLI prompt | P0 |
| FR-1.2 | Store cookies in OS keyring | P0 |
| FR-1.3 | Validate cookie before storing (test API call) | P1 |
| FR-1.4 | Support multiple named accounts | P1 |
| FR-1.5 | Cookie expiration warning (>30 days old) | P2 |

### FR-2: Search
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Keyword search (job title, skills) | P0 |
| FR-2.2 | Network depth filter (1st, 2nd, 3rd degree) | P0 |
| FR-2.3 | Location filter | P0 |
| FR-2.4 | Company filter | P0 |
| FR-2.5 | Configurable result limit (default 100) | P1 |
| FR-2.6 | Pagination for large result sets | P1 |

### FR-3: Output
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Rich terminal output with table formatting | P0 |
| FR-3.2 | CSV export | P0 |
| FR-3.3 | Store results in local SQLite database | P1 |
| FR-3.4 | De-duplicate results across searches | P2 |

### FR-4: Safety
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | Enforce 25 actions/day limit | P0 |
| FR-4.2 | Minimum 60s delay between requests | P0 |
| FR-4.3 | Random jitter (30-120s) | P0 |
| FR-4.4 | Persist rate limit state across sessions | P1 |
| FR-4.5 | Display rate limit status | P1 |

---

## 5. Non-Functional Requirements

### NFR-1: Security
- Cookies stored in OS keyring, never in plaintext files
- No logging of cookie values
- Database stored locally, never transmitted

### NFR-2: Reliability
- Graceful handling of LinkedIn API errors
- Resume capability if interrupted mid-search
- Clear error messages with actionable guidance

### NFR-3: Usability
- Single command to install and run
- Sensible defaults for all options
- Comprehensive `--help` output

### NFR-4: Compliance
- Display ToS warning on first run
- User must acknowledge risks before proceeding

---

## 6. Technical Architecture

### System Diagram
```
┌──────────────────────────────────────────────────────────────┐
│                      CLI Interface (Typer)                   │
│  Commands: login, search, export, status                     │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Search Orchestrator                       │
│  - Validates inputs                                          │
│  - Coordinates rate limiting                                 │
│  - Handles pagination                                        │
└──────────────────────────────────────────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌────────────────┐   ┌────────────────┐   ┌────────────────────┐
│  Rate Limiter  │   │ LinkedIn Client│   │   Cookie Manager   │
│  - Track calls │   │ - Voyager API  │   │   - OS Keyring     │
│  - Enforce     │   │ - search_people│   │   - Validation     │
│    limits      │   │                │   │                    │
└────────────────┘   └────────────────┘   └────────────────────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│               Database Layer (SQLite + SQLModel)             │
│  Tables: connection_profiles, rate_limit_entries             │
└──────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│                      Export Layer                            │
│  - CSV writer                                                │
│  - Rich console formatter                                    │
└──────────────────────────────────────────────────────────────┘
```

### Technology Stack
| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.12 | Modern async, type hints |
| Package Manager | uv | Fast, modern, lockfile support |
| CLI Framework | Typer | Type-safe, Rich integration |
| LinkedIn API | `linkedin-api` library | Maintained Voyager wrapper |
| Cookie Storage | keyring | OS-native secure storage |
| Database | SQLite + SQLModel | Portable, Pydantic-compatible |
| Output | Rich | Beautiful terminal tables |

### Data Models

**ConnectionProfile**
```
- id: UUID (primary key)
- linkedin_urn_id: str (indexed)
- public_id: str (indexed)
- first_name: str
- last_name: str
- headline: str | None
- location: str | None
- current_company: str | None
- current_title: str | None
- profile_url: str
- connection_degree: int (1-3)
- search_query: str | None
- found_at: datetime
```

**RateLimitEntry**
```
- id: int (primary key)
- action_type: enum (search, profile_view)
- timestamp: datetime
```

---

## 7. CLI Interface Design

### Commands

```bash
# Store LinkedIn cookie
linkedin-scraper login
linkedin-scraper login --account "john"  # Named account

# Search connections
linkedin-scraper search --keywords "Software Engineer"
linkedin-scraper search --keywords "HR Manager" --company "Disney"
linkedin-scraper search --keywords "Consultant" --location "US" --degree 1,2
linkedin-scraper search --keywords "Engineer" --limit 50 --account "john"

# Export results
linkedin-scraper export --output results.csv
linkedin-scraper export --query "last"  # Export last search
linkedin-scraper export --all           # Export all stored results

# Check status
linkedin-scraper status                 # Show rate limits, cookie status
```

### Output Example
```
╭──────────────────────────────────────────────────────────────╮
│ Search Results: "Software Engineer" (23 found)               │
╰──────────────────────────────────────────────────────────────╯
┏━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ #  ┃ Name            ┃ Headline                ┃ Degree     ┃
┡━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 1  │ Jane Smith      │ Staff Engineer @ Google │ 1st        │
│ 2  │ John Doe        │ SWE at Meta             │ 2nd        │
│ 3  │ Alice Johnson   │ Principal Engineer      │ 2nd        │
└────┴─────────────────┴─────────────────────────┴────────────┘

Rate limit: 3/25 actions today (22 remaining)
```

---

## 8. Risk Assessment

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LinkedIn API changes | High | High | Pin `linkedin-api` version, monitor for updates |
| Account ban | Medium | High | Conservative rate limits, random delays |
| Cookie expiration | High | Low | Validation on use, clear error messages |
| Detection improvements | Medium | High | Mimic human behavior patterns |

### Legal/Compliance Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ToS violation | Certain | Medium | User acknowledgment, personal use only |
| Data privacy | Low | Medium | Local storage only, no transmission |

---

## 9. Success Metrics

### MVP Success Criteria
- [ ] Can store and retrieve LinkedIn cookie securely
- [ ] Can search by keyword and return results
- [ ] Can filter by location and company
- [ ] Can export to CSV
- [ ] Rate limiting prevents more than 25 searches/day
- [ ] Works without account ban for 1 week of normal use

### Quality Metrics
- Unit test coverage >80%
- All mypy strict checks pass
- All ruff checks pass
- E2E tests for each CLI command

---

## 10. Open Questions

1. **Multi-account aggregation**: Should results from different accounts be merged or kept separate?
2. **Company ID resolution**: Should we auto-resolve company names to IDs, or require user to provide IDs?
3. **Result persistence**: How long to keep results in local DB? Forever, or auto-purge after N days?
4. **Profile enrichment**: Should we fetch full profile details for search results, or just basic info?

---

## 11. Out of Scope (Future Phases)

- Web UI
- Browser extension for cookie extraction
- Message sending / connection requests
- Profile change tracking
- Team/shared access
- LinkedIn Sales Navigator integration
