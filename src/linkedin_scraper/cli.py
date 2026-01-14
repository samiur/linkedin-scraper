# ABOUTME: CLI skeleton for LinkedIn connection search tool using Typer.
# ABOUTME: Provides command stubs for login, search, export, and status with ToS acceptance flow.

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from linkedin_scraper.config import Settings, get_settings

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
def login() -> None:
    """Store LinkedIn li_at cookie for authentication.

    Securely stores your LinkedIn session cookie in the OS keyring
    for use with search operations.
    """
    if not _check_tos_acceptance():
        raise typer.Exit(code=1)

    console.print("[yellow]Login command not implemented yet.[/yellow]")


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
