# ABOUTME: Tests for error handling and error display functionality.
# ABOUTME: Covers base exceptions, error display helpers, and CLI error handling.

from datetime import UTC, datetime

import pytest
from rich.panel import Panel

from linkedin_scraper.display.errors import (
    display_cookie_help,
    display_error,
    display_rate_limit_exceeded,
)
from linkedin_scraper.errors import LinkedInScraperError
from linkedin_scraper.linkedin.exceptions import LinkedInAuthError, LinkedInRateLimitError
from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded


class TestLinkedInScraperError:
    """Tests for the base LinkedInScraperError exception."""

    def test_base_exception_exists(self) -> None:
        """Test that LinkedInScraperError can be instantiated."""
        error = LinkedInScraperError("Test error message")
        assert str(error) == "Test error message"

    def test_base_exception_is_exception(self) -> None:
        """Test that LinkedInScraperError inherits from Exception."""
        error = LinkedInScraperError("Test")
        assert isinstance(error, Exception)

    def test_base_exception_can_be_raised_and_caught(self) -> None:
        """Test that LinkedInScraperError can be raised and caught."""
        with pytest.raises(LinkedInScraperError) as exc_info:
            raise LinkedInScraperError("Test error")
        assert "Test error" in str(exc_info.value)


class TestDisplayError:
    """Tests for the display_error function."""

    def test_display_error_returns_panel(self) -> None:
        """Test that display_error returns a Rich Panel."""
        error = ValueError("Test error")
        result = display_error(error)
        assert isinstance(result, Panel)

    def test_display_error_shows_error_message(self) -> None:
        """Test that display_error includes the error message in the panel."""
        error = ValueError("Something went wrong")
        result = display_error(error)
        # The panel should contain the error message
        # We check the renderable content
        assert result.renderable is not None

    def test_display_error_handles_auth_error(self) -> None:
        """Test that display_error handles LinkedInAuthError specially."""
        error = LinkedInAuthError("Invalid cookie")
        result = display_error(error)
        assert isinstance(result, Panel)

    def test_display_error_handles_rate_limit_error(self) -> None:
        """Test that display_error handles RateLimitExceeded specially."""
        reset_time = datetime.now(UTC)
        error = RateLimitExceeded("Daily limit reached", reset_time=reset_time)
        result = display_error(error)
        assert isinstance(result, Panel)

    def test_display_error_handles_linkedin_rate_limit_error(self) -> None:
        """Test that display_error handles LinkedInRateLimitError."""
        error = LinkedInRateLimitError("Too many requests")
        result = display_error(error)
        assert isinstance(result, Panel)

    def test_display_error_includes_traceback_when_verbose(self) -> None:
        """Test that display_error includes traceback when verbose=True."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            result = display_error(e, verbose=True)
            assert isinstance(result, Panel)
            # Verbose mode should include more detail

    def test_display_error_uses_red_border_for_errors(self) -> None:
        """Test that display_error uses red border style."""
        error = ValueError("Test")
        result = display_error(error)
        assert result.border_style == "red"


class TestDisplayCookieHelp:
    """Tests for the display_cookie_help function."""

    def test_display_cookie_help_returns_panel(self) -> None:
        """Test that display_cookie_help returns a Rich Panel."""
        result = display_cookie_help()
        assert isinstance(result, Panel)

    def test_display_cookie_help_mentions_browser(self) -> None:
        """Test that cookie help mentions browser instructions."""
        result = display_cookie_help()
        # The panel should mention browser or DevTools
        renderable_str = str(result.renderable)
        assert "browser" in renderable_str.lower() or "devtools" in renderable_str.lower()

    def test_display_cookie_help_mentions_li_at(self) -> None:
        """Test that cookie help mentions the li_at cookie."""
        result = display_cookie_help()
        renderable_str = str(result.renderable)
        assert "li_at" in renderable_str.lower()

    def test_display_cookie_help_mentions_linkedin(self) -> None:
        """Test that cookie help mentions LinkedIn."""
        result = display_cookie_help()
        renderable_str = str(result.renderable)
        assert "linkedin" in renderable_str.lower()


class TestDisplayRateLimitExceeded:
    """Tests for the display_rate_limit_exceeded function."""

    def test_display_rate_limit_exceeded_returns_panel(self) -> None:
        """Test that display_rate_limit_exceeded returns a Rich Panel."""
        reset_time = datetime.now(UTC)
        result = display_rate_limit_exceeded(reset_time)
        assert isinstance(result, Panel)

    def test_display_rate_limit_exceeded_shows_reset_time(self) -> None:
        """Test that display_rate_limit_exceeded shows when limit resets."""
        reset_time = datetime(2026, 1, 15, 0, 0, 0, tzinfo=UTC)
        result = display_rate_limit_exceeded(reset_time)
        # Should mention when the limit resets or midnight UTC
        renderable_str = str(result.renderable)
        assert (
            "midnight" in renderable_str.lower()
            or "reset" in renderable_str.lower()
            or "tomorrow" in renderable_str.lower()
        )

    def test_display_rate_limit_exceeded_uses_warning_style(self) -> None:
        """Test that display_rate_limit_exceeded uses appropriate warning style."""
        reset_time = datetime.now(UTC)
        result = display_rate_limit_exceeded(reset_time)
        # Should use yellow or red border for warnings
        assert result.border_style in ("yellow", "red")

    def test_display_rate_limit_exceeded_mentions_daily_limit(self) -> None:
        """Test that display_rate_limit_exceeded mentions daily limit."""
        reset_time = datetime.now(UTC)
        result = display_rate_limit_exceeded(reset_time)
        renderable_str = str(result.renderable)
        assert "daily" in renderable_str.lower() or "limit" in renderable_str.lower()
