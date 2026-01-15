# ABOUTME: Error display helpers for formatting error messages with Rich.
# ABOUTME: Provides user-friendly error panels for auth failures, rate limits, and generic errors.

import traceback
from datetime import datetime

from rich.panel import Panel
from rich.text import Text


def display_error(error: Exception, verbose: bool = False) -> Panel:
    """Format an error as a Rich Panel.

    Args:
        error: The exception to display.
        verbose: If True, include full traceback information.

    Returns:
        A Rich Panel containing formatted error information.
    """
    error_type = type(error).__name__
    error_message = str(error)

    content = Text()
    content.append(f"{error_type}: ", style="bold red")
    content.append(error_message, style="red")

    if verbose:
        content.append("\n\n")
        content.append("Traceback:", style="dim")
        content.append("\n")
        tb_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        content.append(tb_text, style="dim")

    return Panel(
        content,
        title="Error",
        border_style="red",
        padding=(1, 2),
    )


def display_cookie_help() -> Panel:
    """Display help information for obtaining the LinkedIn li_at cookie.

    Returns:
        A Rich Panel containing step-by-step instructions for getting
        the LinkedIn session cookie from a browser.
    """
    help_text = """[bold cyan]How to get your LinkedIn li_at cookie:[/bold cyan]

1. Open your browser and log in to [link=https://www.linkedin.com]LinkedIn[/link]
2. Open DevTools (F12 or right-click → Inspect)
3. Go to the [bold]Application[/bold] tab (Chrome) or [bold]Storage[/bold] tab (Firefox)
4. In the left sidebar, expand [bold]Cookies[/bold] → [bold]https://www.linkedin.com[/bold]
5. Find the cookie named [bold yellow]li_at[/bold yellow]
6. Copy the entire [bold]Value[/bold] (it's a long string starting with "AQ...")

[dim]Note: The cookie expires periodically. If authentication fails, get a fresh cookie.[/dim]

[bold]Then run:[/bold]
  linkedin-scraper login"""

    return Panel(
        Text.from_markup(help_text),
        title="Cookie Help",
        border_style="cyan",
        padding=(1, 2),
    )


def display_rate_limit_exceeded(reset_time: datetime) -> Panel:
    """Display information about rate limit being exceeded.

    Args:
        reset_time: The datetime when the rate limit will reset.

    Returns:
        A Rich Panel showing when the user can try again.
    """
    message = Text()
    message.append("Daily rate limit reached!\n\n", style="bold red")
    message.append(
        "You have exceeded the maximum number of searches allowed for today.\n",
        style="yellow",
    )
    message.append("The limit will reset at ", style="dim")
    message.append("midnight UTC", style="bold cyan")
    message.append(".\n\n", style="dim")
    message.append("Please try again tomorrow.", style="dim")

    return Panel(
        message,
        title="Rate Limit Exceeded",
        border_style="yellow",
        padding=(1, 2),
    )


def display_network_error(error: Exception) -> Panel:
    """Display a user-friendly message for network errors.

    Args:
        error: The network-related exception.

    Returns:
        A Rich Panel with retry suggestions.
    """
    message = Text()
    message.append("Network Error\n\n", style="bold red")
    message.append(f"{error}\n\n", style="red")
    message.append("Suggestions:\n", style="bold")
    message.append("• Check your internet connection\n", style="dim")
    message.append("• Try again in a few moments\n", style="dim")
    message.append("• LinkedIn may be temporarily unavailable", style="dim")

    return Panel(
        message,
        title="Connection Error",
        border_style="red",
        padding=(1, 2),
    )
