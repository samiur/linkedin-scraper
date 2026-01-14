# ABOUTME: Display helper for rate limiter status using Rich formatting.
# ABOUTME: Provides methods to render rate limit status as dictionaries and Rich panels.

from datetime import UTC, datetime, timedelta
from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from linkedin_scraper.rate_limit.service import RateLimiter


class RateLimitDisplay:
    """Display helper for rate limiter status.

    Provides methods to format and render rate limit information
    for display in the CLI using Rich formatting.
    """

    WARNING_THRESHOLD = 5

    def __init__(self, rate_limiter: RateLimiter) -> None:
        """Initialize the display helper.

        Args:
            rate_limiter: The RateLimiter instance to get status from.
        """
        self._rate_limiter = rate_limiter

    def _get_reset_time(self) -> datetime:
        """Get the time when the daily limit resets (midnight UTC tomorrow).

        Returns:
            Datetime representing midnight UTC of the next day.
        """
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return today_start + timedelta(days=1)

    def _format_time_until_reset(self, reset_time: datetime) -> str:
        """Format the time remaining until reset as a human-readable string.

        Args:
            reset_time: The datetime when the limit resets.

        Returns:
            Human-readable string like "5h 23m" or "45m".
        """
        now = datetime.now(UTC)
        delta = reset_time - now
        total_seconds = int(delta.total_seconds())

        if total_seconds <= 0:
            return "resetting soon"

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def get_status_dict(self) -> dict[str, Any]:
        """Get the current rate limit status as a dictionary.

        Returns:
            Dictionary containing:
                - actions_used: Number of actions performed today
                - max_actions: Maximum allowed actions per day
                - remaining_actions: Number of actions remaining today
                - reset_time: Datetime when the daily limit resets
                - last_action_time: Datetime of the most recent action (or None)
                - is_warning: True if remaining actions are below warning threshold
        """
        actions_used = self._rate_limiter.get_actions_today()
        remaining = self._rate_limiter.get_remaining_actions()
        max_actions = self._rate_limiter._settings.max_actions_per_day
        last_action = self._rate_limiter.get_last_action_time()
        reset_time = self._get_reset_time()

        return {
            "actions_used": actions_used,
            "max_actions": max_actions,
            "remaining_actions": remaining,
            "reset_time": reset_time,
            "last_action_time": last_action,
            "is_warning": remaining < self.WARNING_THRESHOLD,
        }

    def render_status(self) -> Panel:
        """Render the rate limit status as a Rich Panel.

        The panel displays:
        - Actions used today / max actions
        - Remaining actions
        - Time until daily reset
        - Last action timestamp
        - Warning if approaching limit (< 5 remaining)

        Returns:
            A Rich Panel containing the formatted status information.
        """
        status = self.get_status_dict()

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="dim")
        table.add_column("Value")

        # Actions used
        used_color = "red" if status["is_warning"] else "green"
        used_text = Text(
            f"{status['actions_used']} / {status['max_actions']}",
            style=used_color,
        )
        table.add_row("Actions Today:", used_text)

        # Remaining actions
        remaining_style = "red bold" if status["is_warning"] else "green"
        remaining_text = Text(str(status["remaining_actions"]), style=remaining_style)
        table.add_row("Remaining:", remaining_text)

        # Time until reset
        time_until = self._format_time_until_reset(status["reset_time"])
        table.add_row("Resets In:", Text(time_until, style="cyan"))

        # Last action time
        if status["last_action_time"]:
            last_time = status["last_action_time"]
            # Handle timezone-naive timestamps
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=UTC)
            last_action_str = last_time.strftime("%H:%M:%S UTC")
        else:
            last_action_str = "No actions today"
        table.add_row("Last Action:", Text(last_action_str, style="dim"))

        # Build the panel
        border_style = "red" if status["is_warning"] else "green"
        title = "Rate Limit Status"

        if status["is_warning"]:
            if status["remaining_actions"] == 0:
                title = "⚠️  Rate Limit Reached"
            else:
                title = f"⚠️  Rate Limit Warning ({status['remaining_actions']} left)"

        return Panel(
            table,
            title=title,
            border_style=border_style,
            padding=(1, 2),
        )
