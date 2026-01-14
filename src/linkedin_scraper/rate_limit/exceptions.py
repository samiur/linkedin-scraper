# ABOUTME: Exception classes for rate limiting functionality.
# ABOUTME: Contains RateLimitExceeded exception raised when daily limits are reached.

from datetime import datetime


class RateLimitExceeded(Exception):
    """Exception raised when the rate limit has been exceeded.

    Attributes:
        reset_time: Optional datetime when the rate limit will reset.
    """

    def __init__(self, message: str, reset_time: datetime | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable description of the error.
            reset_time: Optional datetime when the rate limit will reset.
        """
        super().__init__(message)
        self.reset_time = reset_time
