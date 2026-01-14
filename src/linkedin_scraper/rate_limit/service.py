# ABOUTME: Rate limiter service that enforces API call limits.
# ABOUTME: Tracks actions using database persistence and resets daily at midnight UTC.

import random
import time
from datetime import UTC, datetime, timedelta

from linkedin_scraper.config import Settings
from linkedin_scraper.database import DatabaseService
from linkedin_scraper.models import ActionType, RateLimitEntry
from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded


class RateLimiter:
    """Service that enforces API call rate limits.

    Tracks actions in the database and enforces a daily limit that resets
    at midnight UTC.
    """

    def __init__(self, db_service: DatabaseService, settings: Settings) -> None:
        """Initialize the rate limiter.

        Args:
            db_service: Database service for persisting rate limit entries.
            settings: Application settings containing rate limit configuration.
        """
        self._db_service = db_service
        self._settings = settings

    def _get_today_start(self) -> datetime:
        """Get the start of today in UTC (midnight).

        Returns:
            Datetime representing midnight UTC of the current day.
        """
        now = datetime.now(UTC)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    def can_perform_action(self, action_type: ActionType) -> bool:
        """Check if an action can be performed without exceeding the daily limit.

        Args:
            action_type: The type of action to check.

        Returns:
            True if the action can be performed, False if the daily limit is reached.
        """
        actions_today = self.get_actions_today()
        return actions_today < self._settings.max_actions_per_day

    def record_action(self, action_type: ActionType) -> None:
        """Record an action in the database.

        Args:
            action_type: The type of action to record.
        """
        entry = RateLimitEntry(
            action_type=action_type,
            timestamp=datetime.now(UTC),
        )
        self._db_service.save_rate_limit_entry(entry)

    def get_actions_today(self, action_type: ActionType | None = None) -> int:
        """Get the count of actions performed today.

        Args:
            action_type: Optional action type to filter by. If None, counts all types.

        Returns:
            Number of actions performed today.
        """
        today_start = self._get_today_start()
        entries = self._db_service.get_rate_limit_entries_since(
            since=today_start,
            action_type=action_type,
        )
        return len(entries)

    def get_remaining_actions(self) -> int:
        """Get the number of remaining actions allowed today.

        Returns:
            Number of actions that can still be performed today.
        """
        actions_today = self.get_actions_today()
        remaining = self._settings.max_actions_per_day - actions_today
        return max(0, remaining)

    def get_last_action_time(self) -> datetime | None:
        """Get the timestamp of the most recent action.

        Returns:
            Datetime of the last action, or None if no actions have been recorded.
        """
        today_start = self._get_today_start()
        entries = self._db_service.get_rate_limit_entries_since(since=today_start)

        if not entries:
            return None

        return max(entry.timestamp for entry in entries)

    def seconds_until_next_allowed(self) -> int:
        """Calculate seconds to wait before the next action is allowed.

        Based on the minimum delay setting and time since the last action.

        Returns:
            Number of seconds to wait, or 0 if no waiting is needed.
        """
        last_action_time = self.get_last_action_time()

        if last_action_time is None:
            return 0

        now = datetime.now(UTC)
        # Handle both timezone-aware and timezone-naive timestamps
        if last_action_time.tzinfo is None:
            last_action_time = last_action_time.replace(tzinfo=UTC)
        elapsed = (now - last_action_time).total_seconds()
        remaining = self._settings.min_delay_seconds - elapsed

        return max(0, int(remaining))

    def calculate_delay(self) -> float:
        """Calculate a random delay between min and max delay settings.

        Returns a random value between min_delay_seconds and max_delay_seconds
        to add jitter to requests and appear more human-like.

        Returns:
            Delay in seconds as a float.
        """
        return random.uniform(
            self._settings.min_delay_seconds,
            self._settings.max_delay_seconds,
        )

    def wait_if_needed(self) -> None:
        """Sleep if the minimum delay hasn't passed since the last action.

        If no actions have been recorded, returns immediately.
        Otherwise, waits until min_delay_seconds have passed since the last action.
        """
        seconds_to_wait = self.seconds_until_next_allowed()
        if seconds_to_wait > 0:
            time.sleep(seconds_to_wait)

    def _get_tomorrow_start(self) -> datetime:
        """Get the start of tomorrow in UTC (midnight).

        Returns:
            Datetime representing midnight UTC of the next day.
        """
        today_start = self._get_today_start()
        return today_start + timedelta(days=1)

    def check_and_wait(self, action_type: ActionType) -> None:
        """Check rate limit, wait if needed, and record the action.

        This is the main method to call before performing any rate-limited action.
        It will:
        1. Raise RateLimitExceeded if the daily limit is reached
        2. Wait if the minimum delay hasn't passed since the last action
        3. Record the action after waiting

        Args:
            action_type: The type of action being performed.

        Raises:
            RateLimitExceeded: If the daily action limit has been reached.
        """
        if not self.can_perform_action(action_type):
            reset_time = self._get_tomorrow_start()
            raise RateLimitExceeded(
                f"Daily limit of {self._settings.max_actions_per_day} actions reached. "
                f"Try again after {reset_time.isoformat()}",
                reset_time=reset_time,
            )

        self.wait_if_needed()
        self.record_action(action_type)
