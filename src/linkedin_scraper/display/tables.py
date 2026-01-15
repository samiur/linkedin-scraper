# ABOUTME: Rich table rendering for connection profiles.
# ABOUTME: Provides ConnectionTable class for displaying search results in formatted tables.

from rich.table import Table

from linkedin_scraper.models import ConnectionProfile


class ConnectionTable:
    """Renders ConnectionProfile data as Rich tables.

    Creates formatted tables with color-coded connection degrees,
    truncated long text, and row numbers.
    """

    MAX_HEADLINE_LENGTH = 40
    MAX_COMPANY_LENGTH = 25
    MAX_LOCATION_LENGTH = 20

    DEGREE_COLORS: dict[int, str] = {
        1: "green",
        2: "yellow",
        3: "red",
    }

    def __init__(self) -> None:
        """Initialize the ConnectionTable renderer."""
        pass

    def _truncate(self, text: str | None, max_length: int) -> str:
        """Truncate text to max length with ellipsis.

        Args:
            text: The text to truncate, or None.
            max_length: Maximum length before truncation.

        Returns:
            Truncated text with ellipsis, or empty string if None.
        """
        if text is None:
            return ""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _get_degree_styled(self, degree: int) -> str:
        """Get the connection degree with color styling.

        Args:
            degree: The connection degree (1, 2, or 3).

        Returns:
            Rich-formatted string with appropriate color.
        """
        color = self.DEGREE_COLORS.get(degree, "white")
        return f"[{color}]{degree}[/{color}]"

    def render(
        self,
        profiles: list[ConnectionProfile],
        title: str | None = None,
    ) -> Table:
        """Render connection profiles as a Rich Table.

        Args:
            profiles: List of ConnectionProfile objects to display.
            title: Optional title for the table.

        Returns:
            Rich Table with formatted connection data.
        """
        table = Table(title=title, show_lines=False)

        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Headline", style="white", max_width=self.MAX_HEADLINE_LENGTH)
        table.add_column("Company", style="magenta", max_width=self.MAX_COMPANY_LENGTH)
        table.add_column("Location", style="green", max_width=self.MAX_LOCATION_LENGTH)
        table.add_column("Degree", style="yellow", width=6)

        for idx, profile in enumerate(profiles, 1):
            name = f"{profile.first_name} {profile.last_name}"
            headline = self._truncate(profile.headline, self.MAX_HEADLINE_LENGTH)
            company = self._truncate(profile.current_company, self.MAX_COMPANY_LENGTH)
            location = self._truncate(profile.location, self.MAX_LOCATION_LENGTH)
            degree_styled = self._get_degree_styled(profile.connection_degree)

            table.add_row(
                str(idx),
                name,
                headline,
                company,
                location,
                degree_styled,
            )

        return table
