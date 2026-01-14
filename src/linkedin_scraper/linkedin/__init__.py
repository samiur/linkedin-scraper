# ABOUTME: LinkedIn integration package for authenticated API operations.
# ABOUTME: Exports LinkedInClient, mapper functions, and exception types for LinkedIn interactions.

from linkedin_scraper.linkedin.client import LinkedInClient
from linkedin_scraper.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInError,
    LinkedInRateLimitError,
)
from linkedin_scraper.linkedin.mapper import map_search_result_to_profile

__all__ = [
    "LinkedInClient",
    "LinkedInError",
    "LinkedInAuthError",
    "LinkedInRateLimitError",
    "map_search_result_to_profile",
]
