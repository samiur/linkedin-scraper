# ABOUTME: Custom exceptions for LinkedIn API operations.
# ABOUTME: Provides specific error types for auth failures, rate limits, and general errors.


class LinkedInError(Exception):
    """Base exception for all LinkedIn API errors."""

    pass


class LinkedInAuthError(LinkedInError):
    """Exception raised when authentication fails or cookie is invalid/expired."""

    pass


class LinkedInRateLimitError(LinkedInError):
    """Exception raised when LinkedIn's rate limiting is triggered."""

    pass
