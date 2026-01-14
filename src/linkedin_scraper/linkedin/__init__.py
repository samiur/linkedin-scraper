# ABOUTME: LinkedIn integration package for authenticated API operations.
# ABOUTME: Exports LinkedInClient and exception types for LinkedIn interactions.

from linkedin_scraper.linkedin.client import LinkedInClient
from linkedin_scraper.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInError,
    LinkedInRateLimitError,
)

__all__ = [
    "LinkedInClient",
    "LinkedInError",
    "LinkedInAuthError",
    "LinkedInRateLimitError",
]
