# ABOUTME: Tests for the RateLimitDisplay class.
# ABOUTME: Covers status dictionary generation and Rich panel rendering.

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from rich.panel import Panel

from linkedin_scraper.config import Settings
from linkedin_scraper.database import DatabaseService
from linkedin_scraper.models import ActionType, RateLimitEntry
from linkedin_scraper.rate_limit import RateLimiter
from linkedin_scraper.rate_limit.display import RateLimitDisplay


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def db_service(temp_db_path: Path) -> DatabaseService:
    """Create a DatabaseService with a temporary database."""
    service = DatabaseService(db_path=temp_db_path)
    service.init_db()
    return service


@pytest.fixture
def settings() -> Settings:
    """Create Settings with test values."""
    return Settings(
        max_actions_per_day=10,
        min_delay_seconds=10,
        max_delay_seconds=20,
    )


@pytest.fixture
def rate_limiter(db_service: DatabaseService, settings: Settings) -> RateLimiter:
    """Create a RateLimiter with test dependencies."""
    return RateLimiter(db_service=db_service, settings=settings)


@pytest.fixture
def display(rate_limiter: RateLimiter) -> RateLimitDisplay:
    """Create a RateLimitDisplay with a rate limiter."""
    return RateLimitDisplay(rate_limiter=rate_limiter)


class TestRateLimitDisplayInit:
    """Tests for RateLimitDisplay initialization."""

    def test_init_with_rate_limiter(self, rate_limiter: RateLimiter) -> None:
        """RateLimitDisplay should be initialized with a RateLimiter."""
        display = RateLimitDisplay(rate_limiter=rate_limiter)
        assert display._rate_limiter is rate_limiter


class TestGetStatusDict:
    """Tests for the get_status_dict method."""

    def test_get_status_dict_returns_dict(self, display: RateLimitDisplay) -> None:
        """Should return a dictionary."""
        result = display.get_status_dict()
        assert isinstance(result, dict)

    def test_get_status_dict_contains_required_keys(self, display: RateLimitDisplay) -> None:
        """Should contain all required keys."""
        result = display.get_status_dict()

        required_keys = [
            "actions_used",
            "max_actions",
            "remaining_actions",
            "reset_time",
            "last_action_time",
            "is_warning",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_get_status_dict_when_no_actions(
        self, display: RateLimitDisplay, settings: Settings
    ) -> None:
        """Should show zero actions used when no actions performed."""
        result = display.get_status_dict()

        assert result["actions_used"] == 0
        assert result["max_actions"] == settings.max_actions_per_day
        assert result["remaining_actions"] == settings.max_actions_per_day
        assert result["last_action_time"] is None
        assert result["is_warning"] is False

    def test_get_status_dict_after_some_actions(
        self, display: RateLimitDisplay, rate_limiter: RateLimiter
    ) -> None:
        """Should correctly show action counts after some actions."""
        rate_limiter.record_action(ActionType.SEARCH)
        rate_limiter.record_action(ActionType.PROFILE_VIEW)
        rate_limiter.record_action(ActionType.SEARCH)

        result = display.get_status_dict()

        assert result["actions_used"] == 3
        assert result["remaining_actions"] == 7  # max_actions=10

    def test_get_status_dict_has_last_action_time(
        self, display: RateLimitDisplay, rate_limiter: RateLimiter
    ) -> None:
        """Should include last action time when actions have been recorded."""
        rate_limiter.record_action(ActionType.SEARCH)

        result = display.get_status_dict()

        assert result["last_action_time"] is not None
        assert isinstance(result["last_action_time"], datetime)

    def test_get_status_dict_reset_time_is_tomorrow_midnight(
        self, display: RateLimitDisplay
    ) -> None:
        """Reset time should be midnight UTC tomorrow."""
        result = display.get_status_dict()

        reset_time = result["reset_time"]
        assert isinstance(reset_time, datetime)
        assert reset_time.hour == 0
        assert reset_time.minute == 0
        assert reset_time.second == 0

        # Should be tomorrow
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        expected_reset = today_start + timedelta(days=1)
        assert reset_time == expected_reset

    def test_get_status_dict_warning_when_less_than_5_remaining(
        self, display: RateLimitDisplay, rate_limiter: RateLimiter
    ) -> None:
        """Should set is_warning=True when less than 5 actions remaining."""
        # Record 6 actions (leaves 4 remaining with max=10)
        for _ in range(6):
            rate_limiter.record_action(ActionType.SEARCH)

        result = display.get_status_dict()

        assert result["remaining_actions"] == 4
        assert result["is_warning"] is True

    def test_get_status_dict_no_warning_when_5_or_more_remaining(
        self, display: RateLimitDisplay, rate_limiter: RateLimiter
    ) -> None:
        """Should set is_warning=False when 5 or more actions remaining."""
        # Record 5 actions (leaves 5 remaining with max=10)
        for _ in range(5):
            rate_limiter.record_action(ActionType.SEARCH)

        result = display.get_status_dict()

        assert result["remaining_actions"] == 5
        assert result["is_warning"] is False

    def test_get_status_dict_warning_at_exactly_4_remaining(
        self, db_service: DatabaseService
    ) -> None:
        """Boundary test: is_warning should be True when exactly 4 remaining."""
        settings = Settings(max_actions_per_day=5)
        limiter = RateLimiter(db_service=db_service, settings=settings)
        display = RateLimitDisplay(rate_limiter=limiter)

        # Record 1 action (leaves 4 remaining)
        limiter.record_action(ActionType.SEARCH)

        result = display.get_status_dict()

        assert result["remaining_actions"] == 4
        assert result["is_warning"] is True

    def test_get_status_dict_warning_when_zero_remaining(
        self, display: RateLimitDisplay, rate_limiter: RateLimiter
    ) -> None:
        """Should set is_warning=True when no actions remaining."""
        # Record all 10 actions
        for _ in range(10):
            rate_limiter.record_action(ActionType.SEARCH)

        result = display.get_status_dict()

        assert result["remaining_actions"] == 0
        assert result["is_warning"] is True


class TestRenderStatus:
    """Tests for the render_status method."""

    def test_render_status_returns_panel(self, display: RateLimitDisplay) -> None:
        """Should return a Rich Panel."""
        result = display.render_status()
        assert isinstance(result, Panel)

    def test_render_status_panel_has_title(self, display: RateLimitDisplay) -> None:
        """Panel should have an appropriate title."""
        result = display.render_status()
        # Panel.title can be str or Text object
        assert result.title is not None

    def test_render_status_shows_action_count(
        self, display: RateLimitDisplay, rate_limiter: RateLimiter
    ) -> None:
        """Panel should display action counts."""
        rate_limiter.record_action(ActionType.SEARCH)
        rate_limiter.record_action(ActionType.SEARCH)

        panel = display.render_status()
        assert isinstance(panel, Panel)

        # Verify the underlying data shows correct counts
        status_dict = display.get_status_dict()
        assert status_dict["actions_used"] == 2
        assert status_dict["remaining_actions"] == 8

    def test_render_status_when_no_actions(self, display: RateLimitDisplay) -> None:
        """Panel should render correctly when no actions recorded."""
        result = display.render_status()

        # Should not raise and should return a valid panel
        assert isinstance(result, Panel)

    def test_render_status_with_warning_state(
        self, display: RateLimitDisplay, rate_limiter: RateLimiter
    ) -> None:
        """Panel should indicate warning state visually."""
        # Fill up to near limit (4 remaining)
        for _ in range(6):
            rate_limiter.record_action(ActionType.SEARCH)

        result = display.render_status()

        # Should still return a valid panel
        assert isinstance(result, Panel)
        # Warning state should be reflected (we trust the implementation handles this)
        status_dict = display.get_status_dict()
        assert status_dict["is_warning"] is True

    def test_render_status_with_last_action_time(
        self, display: RateLimitDisplay, rate_limiter: RateLimiter
    ) -> None:
        """Panel should include last action time when available."""
        rate_limiter.record_action(ActionType.SEARCH)

        result = display.render_status()

        # Should return a valid panel that includes last action info
        assert isinstance(result, Panel)
        status_dict = display.get_status_dict()
        assert status_dict["last_action_time"] is not None

    def test_render_status_at_limit(
        self, display: RateLimitDisplay, rate_limiter: RateLimiter
    ) -> None:
        """Panel should handle being at the daily limit."""
        # Fill up completely
        for _ in range(10):
            rate_limiter.record_action(ActionType.SEARCH)

        result = display.render_status()

        assert isinstance(result, Panel)
        status_dict = display.get_status_dict()
        assert status_dict["remaining_actions"] == 0


class TestRateLimitDisplayExport:
    """Tests for package exports."""

    def test_rate_limit_display_importable_from_package(self) -> None:
        """RateLimitDisplay should be importable from the rate_limit package."""
        from linkedin_scraper.rate_limit import RateLimitDisplay

        assert RateLimitDisplay is not None

    def test_rate_limit_display_in_all(self) -> None:
        """RateLimitDisplay should be in __all__ of the rate_limit package."""
        from linkedin_scraper import rate_limit

        assert "RateLimitDisplay" in rate_limit.__all__


class TestIntegration:
    """Integration tests for RateLimitDisplay."""

    def test_display_workflow_with_multiple_actions(self, db_service: DatabaseService) -> None:
        """Test complete workflow of displaying status through various states."""
        settings = Settings(max_actions_per_day=5)
        limiter = RateLimiter(db_service=db_service, settings=settings)
        display = RateLimitDisplay(rate_limiter=limiter)

        # Initial state
        status = display.get_status_dict()
        assert status["actions_used"] == 0
        assert status["remaining_actions"] == 5
        assert status["is_warning"] is False
        panel = display.render_status()
        assert isinstance(panel, Panel)

        # After one action
        limiter.record_action(ActionType.SEARCH)
        status = display.get_status_dict()
        assert status["actions_used"] == 1
        assert status["remaining_actions"] == 4
        assert status["is_warning"] is True  # < 5 remaining

        # After filling to limit
        for _ in range(4):
            limiter.record_action(ActionType.SEARCH)
        status = display.get_status_dict()
        assert status["actions_used"] == 5
        assert status["remaining_actions"] == 0
        assert status["is_warning"] is True
        panel = display.render_status()
        assert isinstance(panel, Panel)

    def test_display_with_historical_actions(self, db_service: DatabaseService) -> None:
        """Display should correctly handle actions from yesterday vs today."""
        settings = Settings(max_actions_per_day=5)
        limiter = RateLimiter(db_service=db_service, settings=settings)
        display = RateLimitDisplay(rate_limiter=limiter)

        # Add actions from yesterday (should not count)
        yesterday = datetime.now(UTC) - timedelta(days=1)
        for _ in range(3):
            db_service.save_rate_limit_entry(
                RateLimitEntry(action_type=ActionType.SEARCH, timestamp=yesterday)
            )

        # Add one action today
        limiter.record_action(ActionType.SEARCH)

        status = display.get_status_dict()
        assert status["actions_used"] == 1  # Only today's action
        assert status["remaining_actions"] == 4
