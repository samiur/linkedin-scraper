# ABOUTME: Tests for the CLI skeleton using Typer.
# ABOUTME: Covers command stubs, ToS acceptance flow, and basic CLI structure.

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from linkedin_scraper.cli import app
from linkedin_scraper.config import get_settings


@pytest.fixture
def runner() -> CliRunner:
    """Create a CliRunner instance for testing Typer commands."""
    return CliRunner()


@pytest.fixture
def temp_settings_env():
    """Create a temporary environment with fresh settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "data.db"
        accounts_file = Path(tmpdir) / "accounts.json"
        env_vars = {
            "LINKEDIN_SCRAPER_DB_PATH": str(db_path),
            "LINKEDIN_SCRAPER_ACCOUNTS_FILE": str(accounts_file),
            "LINKEDIN_SCRAPER_TOS_ACCEPTED": "true",
        }
        with mock.patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            yield tmpdir
        get_settings.cache_clear()


@pytest.fixture
def temp_settings_env_tos_not_accepted():
    """Create a temporary environment with ToS not accepted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "data.db"
        accounts_file = Path(tmpdir) / "accounts.json"
        env_vars = {
            "LINKEDIN_SCRAPER_DB_PATH": str(db_path),
            "LINKEDIN_SCRAPER_ACCOUNTS_FILE": str(accounts_file),
            "LINKEDIN_SCRAPER_TOS_ACCEPTED": "false",
        }
        with mock.patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            yield tmpdir
        get_settings.cache_clear()


class TestCLIBasics:
    """Tests for basic CLI structure and functionality."""

    def test_app_has_help(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that the app has help text."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "linkedin-scraper" in result.output.lower() or "Usage" in result.output

    def test_app_has_login_command(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that the login command exists."""
        result = runner.invoke(app, ["login", "--help"])
        assert result.exit_code == 0
        assert "login" in result.output.lower() or "cookie" in result.output.lower()

    def test_app_has_search_command(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that the search command exists."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output.lower()

    def test_app_has_export_command(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that the export command exists."""
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0
        assert "export" in result.output.lower() or "csv" in result.output.lower()

    def test_app_has_status_command(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that the status command exists."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()


class TestLoginCommand:
    """Tests for the login command stub."""

    def test_login_prints_not_implemented(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that login command prints not implemented message."""
        result = runner.invoke(app, ["login"])
        assert "not implemented" in result.output.lower()


class TestSearchCommand:
    """Tests for the search command stub."""

    def test_search_prints_not_implemented(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that search command prints not implemented message."""
        result = runner.invoke(app, ["search"])
        assert "not implemented" in result.output.lower()


class TestExportCommand:
    """Tests for the export command stub."""

    def test_export_prints_not_implemented(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that export command prints not implemented message."""
        result = runner.invoke(app, ["export"])
        assert "not implemented" in result.output.lower()


class TestStatusCommand:
    """Tests for the status command stub."""

    def test_status_prints_not_implemented(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that status command prints not implemented message."""
        result = runner.invoke(app, ["status"])
        assert "not implemented" in result.output.lower()


class TestToSAcceptance:
    """Tests for Terms of Service acceptance flow."""

    def test_shows_tos_warning_when_not_accepted(
        self, runner: CliRunner, temp_settings_env_tos_not_accepted: str
    ) -> None:
        """Test that ToS warning is shown when not accepted."""
        result = runner.invoke(app, ["status"], input="n\n")
        # Should show ToS warning
        assert (
            "terms" in result.output.lower()
            or "unofficial" in result.output.lower()
            or "accept" in result.output.lower()
        )

    def test_exits_if_tos_not_accepted(
        self, runner: CliRunner, temp_settings_env_tos_not_accepted: str
    ) -> None:
        """Test that app exits if user declines ToS."""
        result = runner.invoke(app, ["status"], input="n\n")
        # Should exit with non-zero code or show declined message
        assert result.exit_code != 0 or "decline" in result.output.lower()

    def test_proceeds_if_tos_accepted_interactively(
        self, runner: CliRunner, temp_settings_env_tos_not_accepted: str
    ) -> None:
        """Test that app proceeds if user accepts ToS interactively."""
        result = runner.invoke(app, ["status"], input="y\n")
        # Should proceed to command (showing not implemented)
        assert "not implemented" in result.output.lower()

    def test_skips_tos_when_already_accepted(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that ToS prompt is skipped when already accepted."""
        result = runner.invoke(app, ["status"])
        # Should not show ToS prompt, just the command output
        assert "not implemented" in result.output.lower()
        # Should not ask about acceptance
        assert "do you accept" not in result.output.lower()
