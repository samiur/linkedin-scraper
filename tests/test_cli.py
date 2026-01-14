# ABOUTME: Tests for the CLI skeleton using Typer.
# ABOUTME: Covers command stubs, ToS acceptance flow, and basic CLI structure.

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from linkedin_scraper.cli import app, get_cookie_instructions
from linkedin_scraper.config import get_settings
from linkedin_scraper.linkedin.exceptions import LinkedInAuthError


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
    """Tests for the login command."""

    def test_login_help_shows_options(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that login command help shows --account and --validate options."""
        result = runner.invoke(app, ["login", "--help"])
        assert result.exit_code == 0
        assert "--account" in result.output or "-a" in result.output
        assert "--validate" in result.output or "--no-validate" in result.output

    def test_login_prompts_for_cookie(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that login command prompts for cookie input."""
        with mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm:
            mock_cm.return_value.validate_cookie_format.return_value = False
            result = runner.invoke(app, ["login", "--no-validate"], input="short\n")
            # Should prompt for cookie
            assert "cookie" in result.output.lower() or "li_at" in result.output.lower()

    def test_login_validates_cookie_format(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that login rejects invalid cookie format."""
        with mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm:
            mock_cm.return_value.validate_cookie_format.return_value = False
            result = runner.invoke(app, ["login", "--no-validate"], input="bad\n")
            # Should show error about invalid format
            assert result.exit_code != 0 or "invalid" in result.output.lower()

    def test_login_successful_stores_cookie(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that login stores cookie on success."""
        valid_cookie = "AQEDAQEBAAAAAAAAAAAAAAFZXyYZWFhW"
        with mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm:
            mock_cm.return_value.validate_cookie_format.return_value = True
            result = runner.invoke(app, ["login", "--no-validate"], input=f"{valid_cookie}\n")
            # Should store the cookie
            mock_cm.return_value.store_cookie.assert_called_once_with(valid_cookie, "default")
            # Should show success
            assert "success" in result.output.lower() or "stored" in result.output.lower()

    def test_login_with_custom_account_name(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that login respects --account option."""
        valid_cookie = "AQEDAQEBAAAAAAAAAAAAAAFZXyYZWFhW"
        with mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm:
            mock_cm.return_value.validate_cookie_format.return_value = True
            runner.invoke(
                app,
                ["login", "--account", "work", "--no-validate"],
                input=f"{valid_cookie}\n",
            )
            # Should store with custom account name
            mock_cm.return_value.store_cookie.assert_called_once_with(valid_cookie, "work")

    def test_login_validates_cookie_online_by_default(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that login validates cookie with LinkedIn by default."""
        valid_cookie = "AQEDAQEBAAAAAAAAAAAAAAFZXyYZWFhW"
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.LinkedInClient") as mock_li,
        ):
            mock_cm.return_value.validate_cookie_format.return_value = True
            mock_li.return_value.validate_session.return_value = True
            runner.invoke(app, ["login"], input=f"{valid_cookie}\n")
            # Should create LinkedInClient and validate session
            mock_li.assert_called_once_with(valid_cookie)
            mock_li.return_value.validate_session.assert_called_once()

    def test_login_skips_validation_with_no_validate_flag(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that --no-validate skips online validation."""
        valid_cookie = "AQEDAQEBAAAAAAAAAAAAAAFZXyYZWFhW"
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.LinkedInClient") as mock_li,
        ):
            mock_cm.return_value.validate_cookie_format.return_value = True
            runner.invoke(app, ["login", "--no-validate"], input=f"{valid_cookie}\n")
            # Should NOT create LinkedInClient
            mock_li.assert_not_called()
            # Cookie should still be stored
            mock_cm.return_value.store_cookie.assert_called_once()

    def test_login_fails_on_invalid_session(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that login fails if session validation fails."""
        invalid_cookie = "AQEDAQEBAAAAAAAAAAAAAAFZXyYZWFhW"
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.LinkedInClient") as mock_li,
        ):
            mock_cm.return_value.validate_cookie_format.return_value = True
            mock_li.return_value.validate_session.return_value = False
            result = runner.invoke(app, ["login"], input=f"{invalid_cookie}\n")
            # Should show error about invalid session
            assert result.exit_code != 0 or "invalid" in result.output.lower()
            # Should NOT store the cookie
            mock_cm.return_value.store_cookie.assert_not_called()

    def test_login_shows_instructions_on_auth_error(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that login shows cookie instructions on auth error."""
        invalid_cookie = "AQEDAQEBAAAAAAAAAAAAAAFZXyYZWFhW"
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.LinkedInClient") as mock_li,
        ):
            mock_cm.return_value.validate_cookie_format.return_value = True
            mock_li.side_effect = LinkedInAuthError("Auth failed")
            result = runner.invoke(app, ["login"], input=f"{invalid_cookie}\n")
            # Should show instructions about getting cookie
            assert (
                "instructions" in result.output.lower()
                or "browser" in result.output.lower()
                or "devtools" in result.output.lower()
                or "how to" in result.output.lower()
            )


class TestGetCookieInstructions:
    """Tests for the get_cookie_instructions helper function."""

    def test_instructions_contain_browser_steps(self) -> None:
        """Test that instructions explain how to get cookie from browser."""
        instructions = get_cookie_instructions()
        # Should mention browser/DevTools
        assert "browser" in instructions.lower() or "devtools" in instructions.lower()
        # Should mention cookies or li_at
        assert "cookie" in instructions.lower() or "li_at" in instructions.lower()

    def test_instructions_mention_linkedin(self) -> None:
        """Test that instructions mention LinkedIn."""
        instructions = get_cookie_instructions()
        assert "linkedin" in instructions.lower()


class TestSearchCommand:
    """Tests for the search command stub."""

    def test_search_prints_not_implemented(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search command prints not implemented message."""
        result = runner.invoke(app, ["search"])
        assert "not implemented" in result.output.lower()


class TestExportCommand:
    """Tests for the export command stub."""

    def test_export_prints_not_implemented(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that export command prints not implemented message."""
        result = runner.invoke(app, ["export"])
        assert "not implemented" in result.output.lower()


class TestStatusCommand:
    """Tests for the status command stub."""

    def test_status_prints_not_implemented(self, runner: CliRunner, temp_settings_env: str) -> None:
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
