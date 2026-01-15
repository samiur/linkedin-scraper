# ABOUTME: CLI skeleton for LinkedIn connection search tool using Typer.
# ABOUTME: Provides login, search, export, and status commands with ToS acceptance flow.

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from linkedin_scraper.auth import CookieManager
from linkedin_scraper.config import Settings, get_settings
from linkedin_scraper.database import DatabaseService
from linkedin_scraper.linkedin.client import LinkedInClient
from linkedin_scraper.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInRateLimitError,
)
from linkedin_scraper.models import ConnectionProfile
from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded
from linkedin_scraper.rate_limit.service import RateLimiter
from linkedin_scraper.search.filters import NetworkDepth
from linkedin_scraper.search.orchestrator import SearchOrchestrator

app = typer.Typer(
    name="linkedin-scraper",
    help="CLI tool to search LinkedIn connections using cookies.",
    add_completion=False,
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
    """Return instructions for extracting the li_at cookie from a browser.

    Returns:
        A formatted string with step-by-step instructions for getting
        the LinkedIn li_at cookie from browser DevTools.
    """
    return """[bold cyan]How to get your LinkedIn li_at cookie:[/bold cyan]

1. Open your browser and log in to [link=https://www.linkedin.com]LinkedIn[/link]
2. Open DevTools (F12 or right-click → Inspect)
3. Go to the [bold]Application[/bold] tab (Chrome) or [bold]Storage[/bold] tab (Firefox)
4. In the left sidebar, expand [bold]Cookies[/bold] → [bold]https://www.linkedin.com[/bold]
5. Find the cookie named [bold yellow]li_at[/bold yellow]
6. Copy the entire [bold]Value[/bold] (it's a long string starting with "AQ...")

[dim]Note: The cookie expires periodically. If authentication fails, get a fresh cookie.[/dim]"""


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


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """LinkedIn connection search CLI tool.

    Search for LinkedIn connections by keywords, company, location, and more.
    Results can be exported to CSV for further analysis.
    """
    if ctx.invoked_subcommand is None:
        console.print("[dim]Use --help to see available commands.[/dim]")


@app.command()
def login(
    account: Annotated[
        str,
        typer.Option(
            "--account",
            "-a",
            help="Account name to store the cookie under.",
        ),
    ] = "default",
    validate: Annotated[
        bool,
        typer.Option(
            "--validate/--no-validate",
            help="Validate the cookie with LinkedIn before storing.",
        ),
    ] = True,
) -> None:
    """Store LinkedIn li_at cookie for authentication.

    Securely stores your LinkedIn session cookie in the OS keyring
    for use with search operations.
    """
    if not _check_tos_acceptance():
        raise typer.Exit(code=1)

    cookie_manager = CookieManager()

    console.print()
    console.print(
        Panel(get_cookie_instructions(), title="Cookie Instructions", border_style="cyan")
    )
    console.print()

    cookie = Prompt.ask("[bold]Paste your li_at cookie value[/bold]", password=True)

    if not cookie_manager.validate_cookie_format(cookie):
        console.print("[red]Error: Invalid cookie format.[/red]")
        console.print("[dim]The cookie should be at least 10 characters long.[/dim]")
        raise typer.Exit(code=1)

    if validate:
        console.print("[dim]Validating cookie with LinkedIn...[/dim]")
        try:
            client = LinkedInClient(cookie)
            if not client.validate_session():
                console.print("[red]Error: Cookie validation failed.[/red]")
                console.print("[yellow]The cookie may be expired or invalid.[/yellow]")
                console.print()
                console.print(
                    Panel(
                        get_cookie_instructions(),
                        title="How to Get a Fresh Cookie",
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
                    title="How to Get a Fresh Cookie",
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=1) from None

    cookie_manager.store_cookie(cookie, account)
    console.print(f"[green]Success! Cookie stored for account '[bold]{account}[/bold]'.[/green]")


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


def _render_results_table(profiles: list[ConnectionProfile]) -> Table:
    """Render search results as a Rich table.

    Args:
        profiles: List of ConnectionProfile objects to display.

    Returns:
        Rich Table with formatted results.
    """
    table = Table(title="Search Results", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Headline", style="white", max_width=40)
    table.add_column("Location", style="green", max_width=20)
    table.add_column("Degree", style="yellow", width=6)

    for idx, profile in enumerate(profiles, 1):
        name = f"{profile.first_name} {profile.last_name}"
        headline = profile.headline or ""
        if len(headline) > 40:
            headline = headline[:37] + "..."
        location = profile.location or ""
        if len(location) > 20:
            location = location[:17] + "..."

        degree_colors = {1: "green", 2: "yellow", 3: "red"}
        degree_style = degree_colors.get(profile.connection_degree, "white")
        degree_text = f"[{degree_style}]{profile.connection_degree}[/{degree_style}]"

        table.add_row(str(idx), name, headline, location, degree_text)

    return table


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
    except LinkedInAuthError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print()
        console.print("[yellow]Please run 'linkedin-scraper login' first.[/yellow]")
        console.print()
        console.print(
            Panel(
                get_cookie_instructions(),
                title="How to Get a Cookie",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=1) from None
    except RateLimitExceeded as e:
        console.print("[red]Error: Rate limit exceeded.[/red]")
        console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(code=1) from None
    except LinkedInRateLimitError as e:
        console.print("[red]Error: LinkedIn rate limit triggered.[/red]")
        console.print(f"[yellow]{e}[/yellow]")
        console.print("[dim]Wait a few minutes and try again.[/dim]")
        raise typer.Exit(code=1) from None

    # Display results
    if profiles:
        table = _render_results_table(profiles)
        console.print(table)
        console.print()
        console.print(f"[green]Found {len(profiles)} result(s).[/green]")
    else:
        console.print("[yellow]No results found.[/yellow]")

    # Show rate limit status
    remaining = orchestrator.get_remaining_actions()
    remaining_style = "red" if remaining < 5 else "green"
    console.print(
        f"[dim]Remaining searches today: [{remaining_style}]{remaining}[/{remaining_style}][/dim]"
    )


@app.command()
def export() -> None:
    """Export search results to CSV.

    Export stored connection profiles to a CSV file for
    further analysis or import into other tools.
    """
    if not _check_tos_acceptance():
        raise typer.Exit(code=1)

    console.print("[yellow]Export command not implemented yet.[/yellow]")


@app.command()
def status() -> None:
    """Show rate limits and account status.

    Display current rate limit usage, stored accounts,
    and database statistics.
    """
    if not _check_tos_acceptance():
        raise typer.Exit(code=1)

    console.print("[yellow]Status command not implemented yet.[/yellow]")


if __name__ == "__main__":
    app()
