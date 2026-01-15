# ABOUTME: Base exception class for LinkedIn Scraper application errors.
# ABOUTME: Provides a common base for all custom exceptions in the application.


class LinkedInScraperError(Exception):
    """Base exception for all LinkedIn Scraper errors.

    This is the root exception class for the application. All custom
    exceptions should inherit from this class to enable unified
    error handling throughout the CLI.
    """

    pass
