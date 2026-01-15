# ABOUTME: CLI skeleton for LinkedIn connection search tool using Typer.
# ABOUTME: Provides login, search, export, and status commands with ToS acceptance flow.

import urllib.error
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from linkedin_scraper import __version__
from linkedin_scraper.auth import CookieManager
from linkedin_scraper.config import Settings, get_settings
from linkedin_scraper.database import DatabaseService
from linkedin_scraper.database.stats import get_database_stats
from linkedin_scraper.display import ConnectionTable
from linkedin_scraper.display.errors import (
    display_cookie_help,
    display_error,
    display_network_error,
    display_rate_limit_exceeded,
)
from linkedin_scraper.display.status import display_rate_limit_warning
from linkedin_scraper.export.csv_exporter import CSVExporter
from linkedin_scraper.linkedin.client import LinkedInClient
from linkedin_scraper.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInRateLimitError,
)
from linkedin_scraper.models import ConnectionProfile
from linkedin_scraper.rate_limit.display import RateLimitDisplay
from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded
from linkedin_scraper.rate_limit.service import RateLimiter
from linkedin_scraper.search.filters import NetworkDepth
from linkedin_scraper.search.orchestrator import SearchOrchestrator

# Global debug state (set via --debug flag)
_debug_mode: bool = False


def _version_callback(value: bool) -> None:
    """Print version and exit if --version flag is passed.

    Args:
        value: Whether the version flag was provided.

    Raises:
        typer.Exit: Exits after printing version.
    """
    if value:
        typer.echo(f"linkedin-scraper {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="linkedin-scraper",
    help="CLI tool to search LinkedIn connections using cookies.",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()

TOS_WARNING_TEXT = """[bold yellow]⚠️  Terms of Service Warning[/bold yellow]

This tool uses an unofficial LinkedIn API and may violate LinkedIn's Terms of Service.

[bold]By using this tool, you acknowledge that:[/bold]
• You are solely responsible for how you use this tool
• Your LinkedIn account may be restricted or banned
• This tool is provided "as-is" without any warranties
• The authors are not liable for any consequences of using this tool

[bold red]Use at your own risk.[/bold red]"""


def get_cookie_instructions() -> str:
    """Return instructions for extracting LinkedIn cookies from a browser.

    Returns:
        A formatted string with step-by-step instructions for getting
        the LinkedIn cookies from browser DevTools.
    """
    return """[bold cyan]How to get your LinkedIn cookies:[/bold cyan]

1. Open your browser and log in to [link=https://www.linkedin.com]LinkedIn[/link]
2. Open DevTools (F12 or right-click → Inspect)
3. Go to the [bold]Application[/bold] tab (Chrome) or [bold]Storage[/bold] tab (Firefox)
4. In the left sidebar, expand [bold]Cookies[/bold] → [bold]https://www.linkedin.com[/bold]
5. Find and copy these two cookies:
   • [bold yellow]li_at[/bold yellow] - a long string starting with "AQ..."
   • [bold yellow]JSESSIONID[/bold yellow] - looks like "ajax:1234567890..."

[dim]Note: Both cookies are required. They expire periodically.[/dim]"""


def _save_tos_acceptance(settings: Settings) -> None:
    """Save ToS acceptance to environment-compatible format.

    Since pydantic-settings doesn't persist values back to files automatically,
    we rely on the environment variable override mechanism. For now, this is
    a no-op as the acceptance is session-based unless env vars are set.

    In a full implementation, this would write to a config file.
    """
    # The ToS acceptance is handled via environment variables for testing.
    # In production, this would write to a persistent config file.
    pass


def _check_tos_acceptance() -> bool:
    """Check and prompt for ToS acceptance if needed.

    Returns:
        True if ToS is accepted, False otherwise.
    """
    settings = get_settings()

    if settings.tos_accepted:
        return True

    console.print(Panel(TOS_WARNING_TEXT, title="LinkedIn Scraper", border_style="yellow"))
    console.print()

    accepted = Confirm.ask("[bold]Do you accept these terms and wish to continue?[/bold]")

    if accepted:
        _save_tos_acceptance(settings)
        console.print("[green]Terms accepted. Proceeding...[/green]\n")
        return True
    else:
        console.print("[red]Terms declined. Exiting.[/red]")
        return False


def _handle_error(error: Exception) -> None:
    """Handle and display an error based on its type.

    Args:
        error: The exception to handle.

    Raises:
        typer.Exit: Always raises Exit with code 1 after displaying the error.
    """
    global _debug_mode

    if isinstance(error, LinkedInAuthError):
        console.print(display_error(error, verbose=_debug_mode))
        console.print()
        console.print("[yellow]Please run 'linkedin-scraper login' first.[/yellow]")
        console.print()
        console.print(display_cookie_help())
    elif isinstance(error, RateLimitExceeded):
        reset_time = getattr(error, "reset_time", None)
        if reset_time:
            console.print(display_rate_limit_exceeded(reset_time))
        else:
            console.print(display_error(error, verbose=_debug_mode))
    elif isinstance(error, LinkedInRateLimitError):
        console.print(display_error(error, verbose=_debug_mode))
        console.print(
            "[dim]LinkedIn's rate limit was triggered. Wait a few minutes and try again.[/dim]"
        )
    elif isinstance(error, (urllib.error.URLError, ConnectionError, OSError)):
        console.print(display_network_error(error))
    else:
        console.print(display_error(error, verbose=_debug_mode))
        if _debug_mode:
            console.print("[dim]Run with --debug for more details.[/dim]")

    raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Enable debug mode with verbose error output and tracebacks.",
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """LinkedIn connection search CLI tool.

    Search for LinkedIn connections by keywords, company, location, and more.
    Results can be exported to CSV for further analysis.

    [bold]Examples:[/bold]

        [cyan]linkedin-scraper login[/cyan]
            Store your LinkedIn cookie for authentication.

        [cyan]linkedin-scraper search -k "software engineer"[/cyan]
            Search for software engineers in your network.

        [cyan]linkedin-scraper search -k "manager" -c "Google" -l "San Francisco"[/cyan]
            Search for managers at Google in San Francisco.

        [cyan]linkedin-scraper export -o results.csv[/cyan]
            Export stored results to a CSV file.

        [cyan]linkedin-scraper status[/cyan]
            Show rate limits and account status.
    """
    global _debug_mode
    _debug_mode = debug

    if ctx.invoked_subcommand is None:
        console.print("[dim]Use --help to see available commands.[/dim]")


@app.command()
def login(
    account: Annotated[
        str,
        typer.Option(
            "--account",
            "-a",
            help="Account name to store the cookies under.",
        ),
    ] = "default",
    validate: Annotated[
        bool,
        typer.Option(
            "--validate/--no-validate",
            help="Validate the cookies with LinkedIn before storing.",
        ),
    ] = True,
) -> None:
    """Store LinkedIn cookies for authentication.

    Securely stores your LinkedIn session cookies (li_at and JSESSIONID)
    in the OS keyring for use with search operations.

    [bold]Examples:[/bold]

        [cyan]linkedin-scraper login[/cyan]
            Login with the default account.

        [cyan]linkedin-scraper login --account work[/cyan]
            Store cookies under the 'work' account name.

        [cyan]linkedin-scraper login --no-validate[/cyan]
            Skip online validation of the cookies.
    """
    if not _check_tos_acceptance():
        raise typer.Exit(code=1)

    cookie_manager = CookieManager()

    console.print()
    console.print(
        Panel(get_cookie_instructions(), title="Cookie Instructions", border_style="cyan")
    )
    console.print()

    li_at = Prompt.ask("[bold]Paste your li_at cookie value[/bold]", password=True)

    if not cookie_manager.validate_cookie_format(li_at):
        console.print("[red]Error: Invalid li_at cookie format.[/red]")
        console.print("[dim]The cookie should be at least 10 characters long.[/dim]")
        raise typer.Exit(code=1)

    jsessionid = Prompt.ask("[bold]Paste your JSESSIONID cookie value[/bold]", password=True)

    if not cookie_manager.validate_cookie_format(jsessionid):
        console.print("[red]Error: Invalid JSESSIONID cookie format.[/red]")
        console.print("[dim]The cookie should be at least 10 characters long.[/dim]")
        raise typer.Exit(code=1)

    if validate:
        console.print("[dim]Validating cookies with LinkedIn...[/dim]")
        try:
            client = LinkedInClient(li_at, jsessionid)
            if not client.validate_session():
                console.print("[red]Error: Cookie validation failed.[/red]")
                console.print("[yellow]The cookies may be expired or invalid.[/yellow]")
                console.print()
                console.print(
                    Panel(
                        get_cookie_instructions(),
                        title="How to Get Fresh Cookies",
                        border_style="yellow",
                    )
                )
                raise typer.Exit(code=1)
        except LinkedInAuthError as e:
            console.print(f"[red]Error: Authentication failed - {e}[/red]")
            console.print()
            console.print(
                Panel(
                    get_cookie_instructions(),
                    title="How to Get Fresh Cookies",
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=1) from None

    cookie_manager.store_cookies(li_at, jsessionid, account)
    console.print(f"[green]Success! Cookies stored for account '[bold]{account}[/bold]'.[/green]")


def _parse_degrees(degree_str: str) -> list[NetworkDepth]:
    """Parse comma-separated degree string into NetworkDepth list.

    Args:
        degree_str: Comma-separated string of degrees (e.g., "1,2" or "1,2,3").

    Returns:
        List of NetworkDepth enum values.
    """
    degree_map = {
        "1": NetworkDepth.FIRST,
        "2": NetworkDepth.SECOND,
        "3": NetworkDepth.THIRD,
    }
    depths = []
    for part in degree_str.split(","):
        part = part.strip()
        if part in degree_map:
            depths.append(degree_map[part])
    return depths if depths else [NetworkDepth.FIRST, NetworkDepth.SECOND]


@app.command()
def search(
    keywords: Annotated[
        str,
        typer.Option(
            "--keywords",
            "-k",
            help="Search keywords (job title, skills, etc.).",
        ),
    ],
    company: Annotated[
        str | None,
        typer.Option(
            "--company",
            "-c",
            help="Company name to filter by.",
        ),
    ] = None,
    location: Annotated[
        str | None,
        typer.Option(
            "--location",
            "-l",
            help="Location filter.",
        ),
    ] = None,
    degree: Annotated[
        str,
        typer.Option(
            "--degree",
            "-d",
            help="Connection degrees, comma-separated (e.g., '1,2' for 1st and 2nd).",
        ),
    ] = "1,2",
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            help="Maximum number of results to return.",
        ),
    ] = 100,
    account: Annotated[
        str,
        typer.Option(
            "--account",
            "-a",
            help="Account name to use for authentication.",
        ),
    ] = "default",
) -> None:
    """Search LinkedIn connections with filters.

    Search for connections by keywords, company, location, and connection degree.
    Results are saved to the database and displayed in a formatted table.

    [bold]Examples:[/bold]

        [cyan]linkedin-scraper search -k "software engineer"[/cyan]
            Basic keyword search.

        [cyan]linkedin-scraper search -k "manager" -c "Google"[/cyan]
            Search for managers at Google.

        [cyan]linkedin-scraper search -k "developer" -l "New York" -d "1,2,3"[/cyan]
            Search developers in New York across all connection degrees.

        [cyan]linkedin-scraper search -k "data scientist" --limit 50 -a work[/cyan]
            Search with custom limit using 'work' account.
    """
    if not _check_tos_acceptance():
        raise typer.Exit(code=1)

    settings = get_settings()
    db_service = DatabaseService(db_path=settings.db_path)
    db_service.init_db()
    rate_limiter = RateLimiter(db_service, settings)
    cookie_manager = CookieManager()
    orchestrator = SearchOrchestrator(db_service, rate_limiter, cookie_manager)

    # Parse degree filter
    network_depths = _parse_degrees(degree)

    console.print(f"[dim]Searching for '{keywords}'...[/dim]")

    try:
        profiles = orchestrator.execute_search_with_company_name(
            keywords=keywords,
            company_name=company,
            location=location,
            network_depths=network_depths,
            limit=limit,
            account=account,
        )
    except (
        LinkedInAuthError,
        RateLimitExceeded,
        LinkedInRateLimitError,
        urllib.error.URLError,
        ConnectionError,
        OSError,
    ) as e:
        _handle_error(e)
    except Exception as e:
        _handle_error(e)

    # Display results
    if profiles:
        connection_table = ConnectionTable()
        table = connection_table.render(profiles, title="Search Results")
        console.print(table)
        console.print()
        console.print(f"[green]Found {len(profiles)} result(s).[/green]")
    else:
        console.print("[yellow]No results found.[/yellow]")

    # Show rate limit status
    remaining = orchestrator.get_remaining_actions()
    warning_panel = display_rate_limit_warning(remaining)
    if warning_panel:
        console.print()
        console.print(warning_panel)
    else:
        msg = f"[dim]Remaining searches today: [green]{remaining}[/green][/dim]"
        console.print(msg)


def _generate_default_export_path() -> Path:
    """Generate a default export file path with timestamp.

    Returns:
        Path to the default export file.
    """
    from datetime import UTC, datetime

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return Path(f"linkedin_export_{timestamp}.csv")


@app.command()
def export(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path. Defaults to linkedin_export_{timestamp}.csv",
        ),
    ] = None,
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Filter by search query string.",
        ),
    ] = None,
    export_all: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Export all stored results (default if no filters).",
        ),
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            help="Maximum number of records to export.",
        ),
    ] = None,
) -> None:
    """Export search results to CSV.

    Export stored connection profiles to a CSV file for
    further analysis or import into other tools.

    [bold]Examples:[/bold]

        [cyan]linkedin-scraper export[/cyan]
            Export all results to a timestamped file.

        [cyan]linkedin-scraper export -o results.csv[/cyan]
            Export all results to a specific file.

        [cyan]linkedin-scraper export -q "engineer" -o engineers.csv[/cyan]
            Export only results from searches with 'engineer' keyword.

        [cyan]linkedin-scraper export --limit 100 -o top100.csv[/cyan]
            Export only the first 100 records.
    """
    if not _check_tos_acceptance():
        raise typer.Exit(code=1)

    settings = get_settings()
    db_service = DatabaseService(db_path=settings.db_path)
    db_service.init_db()

    # Determine output path
    output_path = output if output is not None else _generate_default_export_path()

    # Fetch profiles based on filters
    profiles: list[ConnectionProfile]
    query_info: str | None = None

    if query:
        profiles = db_service.get_connections_by_query(query, limit=limit)
        query_info = query
    else:
        # Default: export all (or limited)
        if limit is not None:
            profiles = db_service.get_connections(limit=limit)
        else:
            # Get all connections - use a large limit
            profiles = db_service.get_connections(limit=100000)

    # Export to CSV
    exporter = CSVExporter()
    result_path = exporter.export(profiles, output_path, query_info=query_info)

    # Display results
    record_count = len(profiles)
    if record_count == 0:
        console.print("[yellow]No records to export.[/yellow]")
    else:
        console.print(f"[green]Exported {record_count} record(s) to:[/green]")
    console.print(f"  [cyan]{result_path}[/cyan]")


def _render_database_stats_panel(stats: dict[str, object]) -> Panel:
    """Render database statistics as a Rich Panel.

    Args:
        stats: Dictionary of database statistics from get_database_stats.

    Returns:
        Rich Panel containing formatted database statistics.
    """
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Label", style="dim")
    table.add_column("Value")

    total = stats.get("total_connections", 0)
    table.add_row("Total Connections:", f"[cyan]{total}[/cyan]")

    companies = stats.get("unique_companies", 0)
    table.add_row("Unique Companies:", f"[cyan]{companies}[/cyan]")

    locations = stats.get("unique_locations", 0)
    table.add_row("Unique Locations:", f"[cyan]{locations}[/cyan]")

    searches = stats.get("recent_searches_count", 0)
    table.add_row("Search Queries:", f"[cyan]{searches}[/cyan]")

    # Degree distribution
    degree_dist = stats.get("degree_distribution", {})
    if degree_dist and isinstance(degree_dist, dict):
        degree_parts = []
        for degree, count in sorted(degree_dist.items()):
            degree_label = {1: "1st", 2: "2nd", 3: "3rd"}.get(degree, f"{degree}th")
            degree_parts.append(f"{degree_label}: {count}")
        if degree_parts:
            table.add_row("By Degree:", ", ".join(degree_parts))

    return Panel(
        table,
        title="Database Statistics",
        border_style="blue",
        padding=(1, 2),
    )


def _render_accounts_panel(
    accounts: list[str],
    validation_result: tuple[str, bool] | None = None,
) -> Panel:
    """Render stored accounts as a Rich Panel.

    Args:
        accounts: List of stored account names.
        validation_result: Optional tuple of (account_name, is_valid) for a validated account.

    Returns:
        Rich Panel containing formatted account list.
    """
    content: str | Table
    if not accounts:
        content = "[dim]No accounts stored. Run 'linkedin-scraper login' to add one.[/dim]"
    else:
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Account", style="cyan")
        table.add_column("Status", style="dim")

        for account in accounts:
            if validation_result and validation_result[0] == account:
                is_valid = validation_result[1]
                status_text = "[green]Valid[/green]" if is_valid else "[red]Expired/Invalid[/red]"
            else:
                status_text = "[dim]Not checked[/dim]"
            table.add_row(account, status_text)

        content = table

    return Panel(
        content,
        title="Stored Accounts",
        border_style="magenta",
        padding=(1, 2),
    )


@app.command()
def status(
    account: Annotated[
        str | None,
        typer.Option(
            "--account",
            "-a",
            help="Validate and show details for a specific account.",
        ),
    ] = None,
) -> None:
    """Show rate limits and account status.

    Display current rate limit usage, stored accounts,
    and database statistics.

    [bold]Examples:[/bold]

        [cyan]linkedin-scraper status[/cyan]
            Show rate limits, database stats, and accounts.

        [cyan]linkedin-scraper status -a default[/cyan]
            Validate the 'default' account's session.

        [cyan]linkedin-scraper status --account work[/cyan]
            Validate the 'work' account's session.
    """
    if not _check_tos_acceptance():
        raise typer.Exit(code=1)

    settings = get_settings()
    db_service = DatabaseService(db_path=settings.db_path)
    db_service.init_db()
    cookie_manager = CookieManager()

    # Rate limit status
    rate_limiter = RateLimiter(db_service, settings)
    rate_display = RateLimitDisplay(rate_limiter)
    console.print(rate_display.render_status())
    console.print()

    # Database statistics
    stats = get_database_stats(db_service)
    console.print(_render_database_stats_panel(stats))
    console.print()

    # Account status
    accounts = cookie_manager.list_accounts()
    validation_result: tuple[str, bool] | None = None

    if account:
        # Validate specific account
        cookies = cookie_manager.get_cookies(account)
        if cookies is None:
            console.print(f"[yellow]Account '{account}' not found. No cookies stored.[/yellow]")
        else:
            console.print(f"[dim]Validating session for '{account}'...[/dim]")
            try:
                client = LinkedInClient(cookies["li_at"], cookies.get("JSESSIONID"))
                is_valid = client.validate_session()
                validation_result = (account, is_valid)
                if is_valid:
                    console.print(f"[green]Session for '{account}' is valid and active.[/green]")
                else:
                    console.print(f"[red]Session for '{account}' is expired or not valid.[/red]")
            except LinkedInAuthError:
                validation_result = (account, False)
                console.print(f"[red]Session for '{account}' is expired or not valid.[/red]")
        console.print()

    console.print(_render_accounts_panel(accounts, validation_result))


if __name__ == "__main__":
    app()
