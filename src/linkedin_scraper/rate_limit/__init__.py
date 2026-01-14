# ABOUTME: Rate limiting package for enforcing API call limits.
# ABOUTME: Exports RateLimiter service for tracking and limiting actions.

from linkedin_scraper.rate_limit.service import RateLimiter

__all__ = ["RateLimiter"]
