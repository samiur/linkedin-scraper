# ABOUTME: Models package for LinkedIn scraper data structures.
# ABOUTME: Exports ConnectionProfile and RateLimitEntry SQLModels.

from linkedin_scraper.models.connection import ConnectionProfile
from linkedin_scraper.models.rate_limit import ActionType, RateLimitEntry

__all__ = ["ConnectionProfile", "RateLimitEntry", "ActionType"]
