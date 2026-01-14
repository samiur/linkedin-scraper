# ABOUTME: CLI skeleton for LinkedIn connection search tool using Typer.
# ABOUTME: Provides login, search, export, and status commands with ToS acceptance flow.

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from linkedin_scraper.auth import CookieManager
from linkedin_scraper.config import Settings, get_settings
from linkedin_scraper.linkedin.client import LinkedInClient
from linkedin_scraper.linkedin.exceptions import LinkedInAuthError

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


@app.command()
def search() -> None:
    """Search LinkedIn connections with filters.

    Search for connections by keywords, company, location, and connection degree.
    Results are saved to the database and displayed in a formatted table.
    """
    if not _check_tos_acceptance():
        raise typer.Exit(code=1)

    console.print("[yellow]Search command not implemented yet.[/yellow]")


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
