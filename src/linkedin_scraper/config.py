# ABOUTME: Configuration module for application settings.
# ABOUTME: Uses pydantic-settings for environment variable overrides and provides cached access.

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support.

    All settings can be overridden via environment variables with the
    LINKEDIN_SCRAPER_ prefix (e.g., LINKEDIN_SCRAPER_DB_PATH).
    """

    model_config = SettingsConfigDict(
        env_prefix="LINKEDIN_SCRAPER_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    db_path: Annotated[Path, Field(description="Path to SQLite database file")] = (
        Path.home() / ".linkedin-scraper" / "data.db"
    )

    accounts_file: Annotated[Path, Field(description="Path to accounts JSON file")] = (
        Path.home() / ".linkedin-scraper" / "accounts.json"
    )

    max_actions_per_day: Annotated[int, Field(description="Maximum API actions per day", ge=1)] = 25

    min_delay_seconds: Annotated[
        int, Field(description="Minimum delay between actions in seconds", ge=0)
    ] = 60

    max_delay_seconds: Annotated[
        int, Field(description="Maximum delay between actions in seconds", ge=0)
    ] = 120

    tos_accepted: Annotated[bool, Field(description="Whether Terms of Service was accepted")] = (
        False
    )

    tos_accepted_at: Annotated[
        datetime | None, Field(description="Timestamp when ToS was accepted")
    ] = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get the application settings.

    Returns a cached Settings instance. Use get_settings.cache_clear()
    to clear the cache if needed.

    Returns:
        Cached Settings instance.
    """
    return Settings()


def ensure_data_dir() -> Path:
    """Ensure the data directory exists.

    Creates the directory containing the database file if it doesn't exist.

    Returns:
        Path to the data directory.
    """
    settings = get_settings()
    data_dir = settings.db_path.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
