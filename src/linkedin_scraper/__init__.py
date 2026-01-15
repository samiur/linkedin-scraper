# ABOUTME: Main package initialization for the LinkedIn scraper CLI tool.
# ABOUTME: Exports version information from pyproject.toml.

from importlib.metadata import version

__version__ = version("linkedin-scraper")


def hello() -> str:
    """Return a greeting message.

    Returns:
        A greeting string for the package.
    """
    return "Hello from linkedin-scraper!"
