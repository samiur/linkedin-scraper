# LinkedIn Network Scraper: Web App Features PRD

**Version:** 2.0 | **Status:** Draft | **Date:** January 2025
**Source:** Brainstorm session transcript

---

## Background

The LinkedIn Network Scraper currently exists as a command-line tool that takes a LinkedIn session cookie and performs network searches with filtering capabilities (job title, location, company) and CSV export. This PRD outlines the next phase: transforming the CLI tool into a collaborative web application that enables users to leverage their extended networks for outreach, recruiting, and professional networking.

## Current State (v1.0)

- Command-line interface requiring technical knowledge to operate
- Accepts LinkedIn session cookie as input
- Searches user's 1st, 2nd, and 3rd degree connections
- Filters by job title, location, and company
- Exports results to CSV format

## Problem Statement

The current tool is powerful but inaccessible to non-technical users. To maximize network leverage for sales outreach, recruiting, or professional networking, users need an easy way to: (1) collect cookies from multiple people in their network, (2) aggregate search results across multiple LinkedIn accounts, and (3) share this capability as a favor to founders and professionals they want to help.

## Target Users

1. **Founders/Sales professionals** doing warm outbound to specific personas
2. **Recruiters** looking for candidates through extended networks
3. **Networkers** who want to offer value to founders they meet by providing this as a service
4. **Individual users** who want to search their own extended network more effectively

---

## Proposed Features

### Feature 1: Web Application Interface

Transform the command-line tool into a user-friendly web application that non-technical users can operate.

| Attribute | Details |
|-----------|---------|
| Core Functionality | Search interface with filter dropdowns for job title, location, company, and connection degree |
| Cookie Input | Simple text field for pasting LinkedIn session cookie |
| Results Display | Table view of matching connections with export to CSV |
| Priority | High - Foundation for all other features |

### Feature 2: Shareable Collection Spaces

Enable users to create shareable links that allow friends and colleagues to contribute their LinkedIn cookies to a collective search pool.

| Attribute | Details |
|-----------|---------|
| Space Creation | Generate unique URL for a "space" tied to a specific search objective |
| Contributor Flow | Friends receive link → view instructions → submit their cookie |
| Aggregation | All contributed cookies are searched, results deduplicated and merged |
| Use Case | "I'm looking for HR Directors at Fortune 500 companies - share this link with your network" |
| Priority | High - Primary differentiator from existing tools |

### Feature 3: Simplified Cookie Collection

Most users don't know how to extract their LinkedIn session cookie. Provide multiple assistance options to reduce friction.

| Attribute | Details |
|-----------|---------|
| Option A: Instructions | Embedded Loom video or step-by-step guide showing how to extract cookie from browser dev tools |
| Option B: Browser Extension | Similar to Phantom Buster - one-click button that automatically extracts and submits the cookie |
| Fallback | Clear text instructions with screenshots for manual extraction |
| Priority | Medium - Option A for MVP, Option B for v2 |

### Feature 4: Admin Dashboard

Space creators need visibility and control over their collection spaces.

| Attribute | Details |
|-----------|---------|
| Contributor List | View who has contributed cookies to the space |
| Access Control | Ability to revoke access or remove contributors |
| Search Management | Configure default search parameters for the space |
| Export Controls | Download aggregated results, manage export history |
| Priority | Medium - Required before sharing externally |

---

## User Flows

### Flow 1: Networking Favor ("Pay It Forward")

1. User meets a founder at a networking event who needs sales leads
2. User creates a space with search criteria (e.g., "VP of Engineering at Series B+ startups")
3. User shares the space link with the founder
4. Founder shares link with their team/friends who contribute cookies
5. Founder downloads aggregated CSV of warm leads
6. Founder now owes the user a favor - reciprocity unlocked

### Flow 2: Single-Player Use

1. User wants to search their own extended network for a specific role
2. User creates a space and shares with close friends/colleagues
3. Friends contribute their cookies
4. User searches the combined network to find warm paths to targets

### Flow 3: Internal Sales Team Tool

1. Sales manager creates a company-wide space
2. All sales reps contribute their LinkedIn cookies
3. Team searches combined network before cold outreach
4. Warm intros increase response rates and close rates

---

## Technical Considerations

- **Cookie Expiration:** LinkedIn cookies expire - need to handle refresh/re-collection gracefully
- **Rate Limiting:** Existing rate limiter implementation should be preserved to avoid LinkedIn detection
- **Data Privacy:** Cookies should be encrypted at rest; clear data retention policies needed
- **Deduplication:** Results from multiple cookies may overlap - need intelligent merging

## Success Metrics

- Number of spaces created per week
- Average contributors per space
- CSV exports per space
- Cookie submission completion rate (started vs. completed)
- Repeat usage (users creating multiple spaces)

## Implementation Phases

**Phase 1 (MVP):** Basic web UI with single-user cookie input and search/export functionality

**Phase 2:** Shareable spaces with contributor flow and embedded Loom instructions

**Phase 3:** Admin dashboard with access controls and contributor management

**Phase 4 (Future):** Browser extension for one-click cookie extraction

## Not In Scope (v2.0)

- Automated LinkedIn messaging/outreach
- CRM integrations
- Paid/monetization features
- Mobile application
