# ABOUTME: Status display functions for search summaries and rate limit warnings.
# ABOUTME: Provides Rich panels for displaying operation status and warnings to users.

from rich.panel import Panel
from rich.text import Text

WARNING_THRESHOLD = 5


def display_search_summary(
    count: int,
    query: str,
    duration_seconds: float,
) -> Panel:
    """Display a summary panel for search results.

    Args:
        count: Number of results found.
        query: The search query string.
        duration_seconds: Time taken to perform the search.

    Returns:
        Rich Panel containing the search summary.
    """
    if count == 0:
        result_text = "[yellow]No results found[/yellow]"
    elif count == 1:
        result_text = "[green]1 result found[/green]"
    else:
        result_text = f"[green]{count} results found[/green]"

    duration_formatted = f"{duration_seconds:.2f}s"

    content = Text()
    content.append("Query: ", style="dim")
    content.append(f"{query}\n", style="cyan")
    content.append("Results: ", style="dim")
    content.append_text(Text.from_markup(result_text))
    content.append("\n")
    content.append("Duration: ", style="dim")
    content.append(duration_formatted, style="blue")

    return Panel(
        content,
        title="Search Summary",
        border_style="green" if count > 0 else "yellow",
        padding=(1, 2),
    )


def display_rate_limit_warning(remaining: int) -> Panel | None:
    """Display a warning panel if rate limit is low.

    Args:
        remaining: Number of remaining actions for today.

    Returns:
        Rich Panel with warning if remaining < 5, None otherwise.
    """
    if remaining >= WARNING_THRESHOLD:
        return None

    if remaining == 0:
        message = (
            "[bold red]Daily rate limit reached![/bold red]\n"
            "You cannot perform more searches until tomorrow (midnight UTC)."
        )
        title = "Rate Limit Reached"
        border_style = "red"
    elif remaining == 1:
        message = (
            f"[yellow]Only {remaining} search remaining for today.[/yellow]\n"
            "Consider waiting until tomorrow to continue."
        )
        title = "Rate Limit Warning"
        border_style = "yellow"
    else:
        message = (
            f"[yellow]Only {remaining} searches remaining for today.[/yellow]\n"
            "Consider waiting until tomorrow to continue."
        )
        title = "Rate Limit Warning"
        border_style = "yellow"

    return Panel(
        Text.from_markup(message),
        title=title,
        border_style=border_style,
        padding=(1, 2),
    )
