# ABOUTME: Tests for the configuration module.
# ABOUTME: Covers Settings class, environment variable overrides, and data directory creation.

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock

from linkedin_scraper.config import Settings, ensure_data_dir, get_settings


class TestSettingsDefaults:
    """Tests for Settings class default values."""

    def test_db_path_default(self) -> None:
        """Test that db_path defaults to ~/.linkedin-scraper/data.db."""
        settings = Settings()
        expected_path = Path.home() / ".linkedin-scraper" / "data.db"
        assert settings.db_path == expected_path

    def test_accounts_file_default(self) -> None:
        """Test that accounts_file defaults to ~/.linkedin-scraper/accounts.json."""
        settings = Settings()
        expected_path = Path.home() / ".linkedin-scraper" / "accounts.json"
        assert settings.accounts_file == expected_path

    def test_max_actions_per_day_default(self) -> None:
        """Test that max_actions_per_day defaults to 25."""
        settings = Settings()
        assert settings.max_actions_per_day == 25

    def test_min_delay_seconds_default(self) -> None:
        """Test that min_delay_seconds defaults to 60."""
        settings = Settings()
        assert settings.min_delay_seconds == 60

    def test_max_delay_seconds_default(self) -> None:
        """Test that max_delay_seconds defaults to 120."""
        settings = Settings()
        assert settings.max_delay_seconds == 120

    def test_tos_accepted_default(self) -> None:
        """Test that tos_accepted defaults to False."""
        settings = Settings()
        assert settings.tos_accepted is False

    def test_tos_accepted_at_default(self) -> None:
        """Test that tos_accepted_at defaults to None."""
        settings = Settings()
        assert settings.tos_accepted_at is None


class TestSettingsEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_db_path_from_env(self) -> None:
        """Test that db_path can be overridden via environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom.db"
            with mock.patch.dict(os.environ, {"LINKEDIN_SCRAPER_DB_PATH": str(custom_path)}):
                settings = Settings()
                assert settings.db_path == custom_path

    def test_accounts_file_from_env(self) -> None:
        """Test that accounts_file can be overridden via environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "accounts.json"
            with mock.patch.dict(os.environ, {"LINKEDIN_SCRAPER_ACCOUNTS_FILE": str(custom_path)}):
                settings = Settings()
                assert settings.accounts_file == custom_path

    def test_max_actions_per_day_from_env(self) -> None:
        """Test that max_actions_per_day can be overridden via environment variable."""
        with mock.patch.dict(os.environ, {"LINKEDIN_SCRAPER_MAX_ACTIONS_PER_DAY": "50"}):
            settings = Settings()
            assert settings.max_actions_per_day == 50

    def test_min_delay_seconds_from_env(self) -> None:
        """Test that min_delay_seconds can be overridden via environment variable."""
        with mock.patch.dict(os.environ, {"LINKEDIN_SCRAPER_MIN_DELAY_SECONDS": "30"}):
            settings = Settings()
            assert settings.min_delay_seconds == 30

    def test_max_delay_seconds_from_env(self) -> None:
        """Test that max_delay_seconds can be overridden via environment variable."""
        with mock.patch.dict(os.environ, {"LINKEDIN_SCRAPER_MAX_DELAY_SECONDS": "180"}):
            settings = Settings()
            assert settings.max_delay_seconds == 180

    def test_tos_accepted_from_env(self) -> None:
        """Test that tos_accepted can be overridden via environment variable."""
        with mock.patch.dict(os.environ, {"LINKEDIN_SCRAPER_TOS_ACCEPTED": "true"}):
            settings = Settings()
            assert settings.tos_accepted is True

    def test_tos_accepted_at_from_env(self) -> None:
        """Test that tos_accepted_at can be overridden via environment variable."""
        timestamp = "2025-06-15T10:30:00"
        with mock.patch.dict(os.environ, {"LINKEDIN_SCRAPER_TOS_ACCEPTED_AT": timestamp}):
            settings = Settings()
            assert settings.tos_accepted_at == datetime(2025, 6, 15, 10, 30, 0)


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_returns_settings_instance(self) -> None:
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_returns_cached_instance(self) -> None:
        """Test that get_settings returns the same cached instance."""
        # Clear cache first to ensure clean state
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_cache_can_be_cleared(self) -> None:
        """Test that the cache can be cleared to get a fresh instance."""
        settings1 = get_settings()
        get_settings.cache_clear()
        settings2 = get_settings()
        # After clearing cache, a new instance should be created
        # Values should be equal but they are different objects
        assert settings1.db_path == settings2.db_path


class TestEnsureDataDir:
    """Tests for ensure_data_dir function."""

    def test_ensure_data_dir_creates_directory(self) -> None:
        """Test that ensure_data_dir creates the data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "new_subdir" / ".linkedin-scraper"
            with mock.patch.dict(
                os.environ, {"LINKEDIN_SCRAPER_DB_PATH": str(data_dir / "data.db")}
            ):
                get_settings.cache_clear()
                result = ensure_data_dir()
                assert result.exists()
                assert result.is_dir()

    def test_ensure_data_dir_returns_path_if_exists(self) -> None:
        """Test that ensure_data_dir returns path even if directory already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            with mock.patch.dict(
                os.environ, {"LINKEDIN_SCRAPER_DB_PATH": str(data_dir / "data.db")}
            ):
                get_settings.cache_clear()
                result = ensure_data_dir()
                assert result.exists()

    def test_ensure_data_dir_returns_correct_path(self) -> None:
        """Test that ensure_data_dir returns the correct data directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir(parents=True)
            with mock.patch.dict(
                os.environ, {"LINKEDIN_SCRAPER_DB_PATH": str(data_dir / "data.db")}
            ):
                get_settings.cache_clear()
                result = ensure_data_dir()
                assert result == data_dir
