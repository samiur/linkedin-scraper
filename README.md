# LinkedIn Connection Search CLI

A command-line tool to search your LinkedIn connections by keywords, company, and location. Results are stored locally and can be exported to CSV.

## Warning

This tool uses an unofficial LinkedIn API and may violate LinkedIn's Terms of Service. Your account could be restricted or banned. Use at your own risk.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd linkedin-scraper

# Install dependencies
uv sync
```

## Getting Your LinkedIn Cookies

The tool authenticates using two LinkedIn session cookies (`li_at` and `JSESSIONID`):

1. Log in to [LinkedIn](https://www.linkedin.com) in your browser
2. Open DevTools (F12 or right-click → Inspect)
3. Go to **Application** tab (Chrome) or **Storage** tab (Firefox)
4. Expand **Cookies** → **https://www.linkedin.com**
5. Find and copy these two cookies:
   - `li_at` - a long string starting with "AQ..."
   - `JSESSIONID` - looks like "ajax:1234567890..."

Both cookies are required. They expire periodically - get fresh ones if authentication fails.

## Usage

### Login

Store your LinkedIn cookie for authentication:

```bash
# Store cookie for default account
uv run linkedin-scraper login

# Store cookie for a named account
uv run linkedin-scraper login --account work
```

### Search

Search for connections by keywords, company, or location:

```bash
# Basic keyword search
uv run linkedin-scraper search -k "software engineer"

# Search for managers at Google
uv run linkedin-scraper search -k "manager" -c "Google"

# Search developers in New York across all connection degrees
uv run linkedin-scraper search -k "developer" -l "New York" -d "1,2,3"

# Limit results and use a specific account
uv run linkedin-scraper search -k "data scientist" --limit 50 -a work
```

**Options:**
- `-k, --keywords` - Search keywords (required)
- `-c, --company` - Filter by company name
- `-l, --location` - Filter by location
- `-d, --degree` - Connection degrees, comma-separated (default: "1,2")
- `--limit` - Maximum results (default: 100)
- `-a, --account` - Account to use (default: "default")

### Export

Export stored results to CSV:

```bash
# Export all results to timestamped file
uv run linkedin-scraper export

# Export to specific file
uv run linkedin-scraper export -o results.csv

# Export only results from a specific search
uv run linkedin-scraper export -q "engineer" -o engineers.csv

# Export limited records
uv run linkedin-scraper export --limit 100 -o top100.csv
```

### Status

View rate limits, stored accounts, and database statistics:

```bash
# Show all status info
uv run linkedin-scraper status

# Validate a specific account's session
uv run linkedin-scraper status -a default
```

## Rate Limiting

To avoid triggering LinkedIn's rate limits, this tool enforces:
- Maximum 25 searches per day (resets at midnight UTC)
- 60-120 second delay between searches

These limits can be configured via environment variables:

```bash
export LINKEDIN_SCRAPER_MAX_ACTIONS_PER_DAY=25
export LINKEDIN_SCRAPER_MIN_DELAY_SECONDS=60
export LINKEDIN_SCRAPER_MAX_DELAY_SECONDS=120
```

## Data Storage

- **Database**: `~/.linkedin-scraper/data.db` (SQLite)
- **Accounts list**: `~/.linkedin-scraper/accounts.json`
- **Credentials**: Stored in OS keyring (macOS Keychain, Windows Credential Manager, etc.)

## Configuration

All settings can be overridden via environment variables with the `LINKEDIN_SCRAPER_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `LINKEDIN_SCRAPER_DB_PATH` | `~/.linkedin-scraper/data.db` | Database file path |
| `LINKEDIN_SCRAPER_MAX_ACTIONS_PER_DAY` | `25` | Daily search limit |
| `LINKEDIN_SCRAPER_MIN_DELAY_SECONDS` | `60` | Minimum delay between searches |
| `LINKEDIN_SCRAPER_MAX_DELAY_SECONDS` | `120` | Maximum delay between searches |
| `LINKEDIN_SCRAPER_TOS_ACCEPTED` | `false` | Skip ToS prompt |

## Development

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Format code
uv run ruff format src/
```

## License

MIT
