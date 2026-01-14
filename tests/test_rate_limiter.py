# ABOUTME: Tests for the RateLimiter service.
# ABOUTME: Covers action tracking, daily limits, and time-based queries.

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from linkedin_scraper.config import Settings
from linkedin_scraper.database import DatabaseService
from linkedin_scraper.models import ActionType, RateLimitEntry
from linkedin_scraper.rate_limit import RateLimiter


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
        max_actions_per_day=5,
        min_delay_seconds=10,
        max_delay_seconds=20,
    )


@pytest.fixture
def rate_limiter(db_service: DatabaseService, settings: Settings) -> RateLimiter:
    """Create a RateLimiter with test dependencies."""
    return RateLimiter(db_service=db_service, settings=settings)


class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    def test_init_with_dependencies(self, db_service: DatabaseService, settings: Settings) -> None:
        """RateLimiter should be initialized with db_service and settings."""
        limiter = RateLimiter(db_service=db_service, settings=settings)
        assert limiter._db_service is db_service
        assert limiter._settings is settings


class TestCanPerformAction:
    """Tests for the can_perform_action method."""

    def test_can_perform_action_when_no_actions_today(self, rate_limiter: RateLimiter) -> None:
        """Should return True when no actions have been performed today."""
        assert rate_limiter.can_perform_action(ActionType.SEARCH) is True

    def test_can_perform_action_when_under_limit(
        self, rate_limiter: RateLimiter, db_service: DatabaseService
    ) -> None:
        """Should return True when actions are under the daily limit."""
        # Record 3 actions (limit is 5)
        for _ in range(3):
            db_service.save_rate_limit_entry(RateLimitEntry(action_type=ActionType.SEARCH))

        assert rate_limiter.can_perform_action(ActionType.SEARCH) is True

    def test_cannot_perform_action_when_at_limit(
        self, rate_limiter: RateLimiter, db_service: DatabaseService
    ) -> None:
        """Should return False when daily limit is reached."""
        # Record 5 actions (limit is 5)
        for _ in range(5):
            db_service.save_rate_limit_entry(RateLimitEntry(action_type=ActionType.SEARCH))

        assert rate_limiter.can_perform_action(ActionType.SEARCH) is False

    def test_can_perform_action_ignores_yesterday_actions(
        self, rate_limiter: RateLimiter, db_service: DatabaseService
    ) -> None:
        """Should not count actions from previous days."""
        yesterday = datetime.now(UTC) - timedelta(days=1)

        # Record 5 actions from yesterday
        for _ in range(5):
            entry = RateLimitEntry(action_type=ActionType.SEARCH, timestamp=yesterday)
            db_service.save_rate_limit_entry(entry)

        assert rate_limiter.can_perform_action(ActionType.SEARCH) is True


class TestRecordAction:
    """Tests for the record_action method."""

    def test_record_action_creates_entry(
        self, rate_limiter: RateLimiter, db_service: DatabaseService
    ) -> None:
        """Should create a RateLimitEntry in the database."""
        rate_limiter.record_action(ActionType.SEARCH)

        # Get today's start in UTC
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        entries = db_service.get_rate_limit_entries_since(today_start)

        assert len(entries) == 1
        assert entries[0].action_type == ActionType.SEARCH

    def test_record_action_with_different_types(
        self, rate_limiter: RateLimiter, db_service: DatabaseService
    ) -> None:
        """Should record different action types correctly."""
        rate_limiter.record_action(ActionType.SEARCH)
        rate_limiter.record_action(ActionType.PROFILE_VIEW)

        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        entries = db_service.get_rate_limit_entries_since(today_start)

        assert len(entries) == 2
        action_types = {entry.action_type for entry in entries}
        assert action_types == {ActionType.SEARCH, ActionType.PROFILE_VIEW}


class TestGetActionsToday:
    """Tests for the get_actions_today method."""

    def test_get_actions_today_returns_zero_when_empty(self, rate_limiter: RateLimiter) -> None:
        """Should return 0 when no actions have been performed today."""
        assert rate_limiter.get_actions_today() == 0

    def test_get_actions_today_counts_all_action_types(self, rate_limiter: RateLimiter) -> None:
        """Should count all action types when no filter is provided."""
        rate_limiter.record_action(ActionType.SEARCH)
        rate_limiter.record_action(ActionType.PROFILE_VIEW)
        rate_limiter.record_action(ActionType.SEARCH)

        assert rate_limiter.get_actions_today() == 3

    def test_get_actions_today_filters_by_action_type(self, rate_limiter: RateLimiter) -> None:
        """Should filter by action type when provided."""
        rate_limiter.record_action(ActionType.SEARCH)
        rate_limiter.record_action(ActionType.PROFILE_VIEW)
        rate_limiter.record_action(ActionType.SEARCH)

        assert rate_limiter.get_actions_today(ActionType.SEARCH) == 2
        assert rate_limiter.get_actions_today(ActionType.PROFILE_VIEW) == 1

    def test_get_actions_today_ignores_yesterday(
        self, rate_limiter: RateLimiter, db_service: DatabaseService
    ) -> None:
        """Should not count actions from previous days."""
        yesterday = datetime.now(UTC) - timedelta(days=1)
        db_service.save_rate_limit_entry(
            RateLimitEntry(action_type=ActionType.SEARCH, timestamp=yesterday)
        )
        rate_limiter.record_action(ActionType.SEARCH)

        assert rate_limiter.get_actions_today() == 1


class TestGetRemainingActions:
    """Tests for the get_remaining_actions method."""

    def test_get_remaining_actions_when_empty(self, rate_limiter: RateLimiter) -> None:
        """Should return max_actions_per_day when no actions performed."""
        assert rate_limiter.get_remaining_actions() == 5

    def test_get_remaining_actions_after_some_actions(self, rate_limiter: RateLimiter) -> None:
        """Should return correct remaining count."""
        rate_limiter.record_action(ActionType.SEARCH)
        rate_limiter.record_action(ActionType.SEARCH)

        assert rate_limiter.get_remaining_actions() == 3

    def test_get_remaining_actions_when_at_limit(self, rate_limiter: RateLimiter) -> None:
        """Should return 0 when at limit."""
        for _ in range(5):
            rate_limiter.record_action(ActionType.SEARCH)

        assert rate_limiter.get_remaining_actions() == 0

    def test_get_remaining_actions_never_negative(self, rate_limiter: RateLimiter) -> None:
        """Should never return negative (edge case if data is corrupted)."""
        # Record more than limit (shouldn't happen in practice)
        for _ in range(7):
            rate_limiter.record_action(ActionType.SEARCH)

        assert rate_limiter.get_remaining_actions() == 0


class TestGetLastActionTime:
    """Tests for the get_last_action_time method."""

    def test_get_last_action_time_when_empty(self, rate_limiter: RateLimiter) -> None:
        """Should return None when no actions have been performed."""
        assert rate_limiter.get_last_action_time() is None

    def test_get_last_action_time_returns_most_recent(self, rate_limiter: RateLimiter) -> None:
        """Should return the timestamp of the most recent action."""
        rate_limiter.record_action(ActionType.SEARCH)
        first_time = rate_limiter.get_last_action_time()
        assert first_time is not None

        # Small delay to ensure different timestamps
        rate_limiter.record_action(ActionType.PROFILE_VIEW)
        second_time = rate_limiter.get_last_action_time()

        assert second_time is not None
        assert second_time >= first_time


class TestSecondsUntilNextAllowed:
    """Tests for the seconds_until_next_allowed method."""

    def test_seconds_until_next_allowed_when_empty(self, rate_limiter: RateLimiter) -> None:
        """Should return 0 when no actions have been performed."""
        assert rate_limiter.seconds_until_next_allowed() == 0

    def test_seconds_until_next_allowed_within_min_delay(self, rate_limiter: RateLimiter) -> None:
        """Should return remaining seconds when within minimum delay period."""
        rate_limiter.record_action(ActionType.SEARCH)

        # Should need to wait some time (min_delay is 10 seconds)
        wait_time = rate_limiter.seconds_until_next_allowed()
        assert 0 < wait_time <= 10

    def test_seconds_until_next_allowed_after_min_delay(
        self, rate_limiter: RateLimiter, db_service: DatabaseService
    ) -> None:
        """Should return 0 when minimum delay has passed."""
        # Create an entry from 15 seconds ago (min_delay is 10)
        past_time = datetime.now(UTC) - timedelta(seconds=15)
        db_service.save_rate_limit_entry(
            RateLimitEntry(action_type=ActionType.SEARCH, timestamp=past_time)
        )

        assert rate_limiter.seconds_until_next_allowed() == 0


class TestDayBoundary:
    """Tests for day boundary behavior (midnight UTC reset)."""

    def test_actions_reset_at_midnight_utc(
        self, db_service: DatabaseService, settings: Settings
    ) -> None:
        """Actions should reset at midnight UTC."""
        rate_limiter = RateLimiter(db_service=db_service, settings=settings)

        # Record actions at 23:59 UTC yesterday
        yesterday_2359 = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(minutes=1)

        for _ in range(5):
            db_service.save_rate_limit_entry(
                RateLimitEntry(action_type=ActionType.SEARCH, timestamp=yesterday_2359)
            )

        # Should be able to perform actions today
        assert rate_limiter.can_perform_action(ActionType.SEARCH) is True
        assert rate_limiter.get_actions_today() == 0

    def test_midnight_utc_boundary_calculation(self, rate_limiter: RateLimiter) -> None:
        """Today's start should be midnight UTC."""
        today_start = rate_limiter._get_today_start()

        assert today_start.hour == 0
        assert today_start.minute == 0
        assert today_start.second == 0
        assert today_start.microsecond == 0
        assert today_start.tzinfo == UTC


class TestIntegration:
    """Integration tests for RateLimiter."""

    def test_full_workflow(self, rate_limiter: RateLimiter) -> None:
        """Test a complete workflow of recording and checking actions."""
        # Initial state
        assert rate_limiter.can_perform_action(ActionType.SEARCH) is True
        assert rate_limiter.get_remaining_actions() == 5
        assert rate_limiter.get_actions_today() == 0

        # Record some actions
        for _ in range(3):
            rate_limiter.record_action(ActionType.SEARCH)

        assert rate_limiter.get_actions_today() == 3
        assert rate_limiter.get_remaining_actions() == 2
        assert rate_limiter.can_perform_action(ActionType.SEARCH) is True

        # Fill up to limit
        rate_limiter.record_action(ActionType.SEARCH)
        rate_limiter.record_action(ActionType.SEARCH)

        assert rate_limiter.get_actions_today() == 5
        assert rate_limiter.get_remaining_actions() == 0
        assert rate_limiter.can_perform_action(ActionType.SEARCH) is False

    def test_different_action_types_share_limit(self, rate_limiter: RateLimiter) -> None:
        """All action types should count against the same daily limit."""
        rate_limiter.record_action(ActionType.SEARCH)
        rate_limiter.record_action(ActionType.SEARCH)
        rate_limiter.record_action(ActionType.PROFILE_VIEW)
        rate_limiter.record_action(ActionType.PROFILE_VIEW)
        rate_limiter.record_action(ActionType.SEARCH)

        assert rate_limiter.get_actions_today() == 5
        assert rate_limiter.get_remaining_actions() == 0
        assert rate_limiter.can_perform_action(ActionType.SEARCH) is False
        assert rate_limiter.can_perform_action(ActionType.PROFILE_VIEW) is False


class TestCalculateDelay:
    """Tests for the calculate_delay method."""

    def test_calculate_delay_returns_float(self, rate_limiter: RateLimiter) -> None:
        """Should return a float representing delay in seconds."""
        delay = rate_limiter.calculate_delay()
        assert isinstance(delay, float)

    def test_calculate_delay_within_bounds(self, rate_limiter: RateLimiter) -> None:
        """Should return a delay between min and max delay settings."""
        # settings has min_delay=10, max_delay=20
        for _ in range(10):
            delay = rate_limiter.calculate_delay()
            assert 10 <= delay <= 20

    def test_calculate_delay_with_mocked_random(
        self, db_service: DatabaseService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should use random.uniform for jitter."""
        import random

        settings = Settings(min_delay_seconds=60, max_delay_seconds=120)
        limiter = RateLimiter(db_service=db_service, settings=settings)

        # Mock random.uniform to return a predictable value
        monkeypatch.setattr(random, "uniform", lambda a, b: 90.5)

        delay = limiter.calculate_delay()
        assert delay == 90.5


class TestWaitIfNeeded:
    """Tests for the wait_if_needed method."""

    def test_wait_if_needed_no_wait_when_no_actions(
        self, rate_limiter: RateLimiter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should not wait when no previous actions."""
        import time

        sleep_called = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_called.append(s))

        rate_limiter.wait_if_needed()

        assert len(sleep_called) == 0

    def test_wait_if_needed_sleeps_when_needed(
        self, rate_limiter: RateLimiter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should sleep for the remaining time until min_delay has passed."""
        import time

        sleep_called = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_called.append(s))

        # Record an action just now
        rate_limiter.record_action(ActionType.SEARCH)

        rate_limiter.wait_if_needed()

        # Should have called sleep since action was just recorded
        assert len(sleep_called) == 1
        assert sleep_called[0] > 0

    def test_wait_if_needed_no_wait_after_min_delay_passed(
        self, db_service: DatabaseService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should not wait when min_delay has already passed."""
        import time

        settings = Settings(min_delay_seconds=10, max_delay_seconds=20)
        limiter = RateLimiter(db_service=db_service, settings=settings)

        # Record an action from 15 seconds ago
        past_time = datetime.now(UTC) - timedelta(seconds=15)
        db_service.save_rate_limit_entry(
            RateLimitEntry(action_type=ActionType.SEARCH, timestamp=past_time)
        )

        sleep_called = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_called.append(s))

        limiter.wait_if_needed()

        assert len(sleep_called) == 0


class TestRateLimitExceededException:
    """Tests for the RateLimitExceeded exception."""

    def test_rate_limit_exceeded_exception_exists(self) -> None:
        """RateLimitExceeded exception should be importable."""
        from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded

        assert issubclass(RateLimitExceeded, Exception)

    def test_rate_limit_exceeded_has_message(self) -> None:
        """RateLimitExceeded should have a message attribute."""
        from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded

        exc = RateLimitExceeded("Daily limit reached")
        assert str(exc) == "Daily limit reached"

    def test_rate_limit_exceeded_can_have_reset_time(self) -> None:
        """RateLimitExceeded should be able to store reset time."""
        from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded

        reset_time = datetime.now(UTC) + timedelta(hours=5)
        exc = RateLimitExceeded("Daily limit reached", reset_time=reset_time)
        assert exc.reset_time == reset_time


class TestCheckAndWait:
    """Tests for the check_and_wait method."""

    def test_check_and_wait_raises_when_limit_exceeded(self, rate_limiter: RateLimiter) -> None:
        """Should raise RateLimitExceeded when daily limit is reached."""
        from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded

        # Fill up the limit (5 actions)
        for _ in range(5):
            rate_limiter.record_action(ActionType.SEARCH)

        with pytest.raises(RateLimitExceeded):
            rate_limiter.check_and_wait(ActionType.SEARCH)

    def test_check_and_wait_waits_and_records(
        self, rate_limiter: RateLimiter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should wait if needed and then record the action."""
        import time

        sleep_called = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_called.append(s))

        # No previous actions, should not need to wait much
        initial_count = rate_limiter.get_actions_today()

        rate_limiter.check_and_wait(ActionType.SEARCH)

        # Should have recorded the action
        assert rate_limiter.get_actions_today() == initial_count + 1

    def test_check_and_wait_respects_delay_after_previous_action(
        self, rate_limiter: RateLimiter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should wait appropriately after a previous action."""
        import time

        sleep_called = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_called.append(s))

        # First action
        rate_limiter.check_and_wait(ActionType.SEARCH)

        # Second action should need to wait
        rate_limiter.check_and_wait(ActionType.SEARCH)

        # Should have waited on the second call
        assert len(sleep_called) >= 1

    def test_check_and_wait_reset_time_in_exception(self, rate_limiter: RateLimiter) -> None:
        """RateLimitExceeded should include the reset time."""
        from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded

        # Fill up the limit
        for _ in range(5):
            rate_limiter.record_action(ActionType.SEARCH)

        with pytest.raises(RateLimitExceeded) as exc_info:
            rate_limiter.check_and_wait(ActionType.SEARCH)

        # Reset time should be tomorrow at midnight UTC
        assert exc_info.value.reset_time is not None
        assert exc_info.value.reset_time > datetime.now(UTC)
