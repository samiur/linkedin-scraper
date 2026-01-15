# ABOUTME: Tests for the CLI skeleton using Typer.
# ABOUTME: Covers command stubs, ToS acceptance flow, and basic CLI structure.

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from linkedin_scraper.cli import app, get_cookie_instructions
from linkedin_scraper.config import get_settings
from linkedin_scraper.linkedin.exceptions import LinkedInAuthError, LinkedInRateLimitError
from linkedin_scraper.models import ConnectionProfile
from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded


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
    """Tests for the search command."""

    def test_search_help_shows_options(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search command help shows all required options."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "--keywords" in result.output or "-k" in result.output
        assert "--company" in result.output or "-c" in result.output
        assert "--location" in result.output or "-l" in result.output
        assert "--degree" in result.output or "-d" in result.output
        assert "--limit" in result.output
        assert "--account" in result.output or "-a" in result.output

    def test_search_requires_keywords(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search command requires --keywords option."""
        result = runner.invoke(app, ["search"])
        # Should show error about missing keywords
        assert result.exit_code != 0

    def test_search_successful_displays_results(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that search displays results in a table."""
        sample_profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:123",
                public_id="john-doe",
                first_name="John",
                last_name="Doe",
                headline="Software Engineer",
                location="San Francisco, CA",
                profile_url="https://linkedin.com/in/john-doe",
                connection_degree=1,
                search_query="engineer",
                found_at=datetime.now(UTC),
            ),
        ]
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = sample_profiles
            mock_orch.return_value.get_remaining_actions.return_value = 24
            result = runner.invoke(app, ["search", "-k", "engineer"])
            # Should display results
            assert "john" in result.output.lower() or "doe" in result.output.lower()

    def test_search_uses_default_account(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search uses 'default' account when not specified."""
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = []
            mock_orch.return_value.get_remaining_actions.return_value = 25
            runner.invoke(app, ["search", "-k", "engineer"])
            call_kwargs = mock_orch.return_value.execute_search_with_company_name.call_args[1]
            assert call_kwargs["account"] == "default"

    def test_search_with_custom_account(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search respects --account option."""
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = []
            mock_orch.return_value.get_remaining_actions.return_value = 25
            runner.invoke(app, ["search", "-k", "engineer", "-a", "work"])
            call_kwargs = mock_orch.return_value.execute_search_with_company_name.call_args[1]
            assert call_kwargs["account"] == "work"

    def test_search_with_company_filter(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search passes company name to orchestrator."""
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = []
            mock_orch.return_value.get_remaining_actions.return_value = 25
            runner.invoke(app, ["search", "-k", "engineer", "-c", "TechCorp"])
            call_kwargs = mock_orch.return_value.execute_search_with_company_name.call_args[1]
            assert call_kwargs["company_name"] == "TechCorp"

    def test_search_with_location_filter(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search passes location to orchestrator."""
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = []
            mock_orch.return_value.get_remaining_actions.return_value = 25
            runner.invoke(app, ["search", "-k", "engineer", "-l", "San Francisco"])
            call_kwargs = mock_orch.return_value.execute_search_with_company_name.call_args[1]
            assert call_kwargs["location"] == "San Francisco"

    def test_search_with_degree_filter(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search parses and passes degree filter."""
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = []
            mock_orch.return_value.get_remaining_actions.return_value = 25
            runner.invoke(app, ["search", "-k", "engineer", "-d", "1,2,3"])
            call_kwargs = mock_orch.return_value.execute_search_with_company_name.call_args[1]
            # Should have 3 network depths
            assert len(call_kwargs["network_depths"]) == 3

    def test_search_with_limit(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search respects --limit option."""
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = []
            mock_orch.return_value.get_remaining_actions.return_value = 25
            runner.invoke(app, ["search", "-k", "engineer", "--limit", "50"])
            call_kwargs = mock_orch.return_value.execute_search_with_company_name.call_args[1]
            assert call_kwargs["limit"] == 50

    def test_search_shows_rate_limit_status(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that search shows rate limit status after search."""
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = []
            mock_orch.return_value.get_remaining_actions.return_value = 20
            result = runner.invoke(app, ["search", "-k", "engineer"])
            # Should show remaining actions or rate limit info
            assert "20" in result.output or "remaining" in result.output.lower()

    def test_search_handles_auth_error(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search shows helpful error on auth failure."""
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.side_effect = LinkedInAuthError(
                "No cookie found"
            )
            result = runner.invoke(app, ["search", "-k", "engineer"])
            # Should show auth error and instructions
            assert result.exit_code != 0
            assert "cookie" in result.output.lower() or "login" in result.output.lower()

    def test_search_handles_rate_limit_exceeded(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that search shows helpful error when rate limit exceeded."""
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.side_effect = RateLimitExceeded(
                "Daily limit reached", reset_time=datetime.now(UTC)
            )
            result = runner.invoke(app, ["search", "-k", "engineer"])
            # Should show rate limit error
            assert result.exit_code != 0
            assert "limit" in result.output.lower()

    def test_search_handles_linkedin_rate_limit_error(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that search handles LinkedIn's rate limit error."""
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.side_effect = (
                LinkedInRateLimitError("Too many requests")
            )
            result = runner.invoke(app, ["search", "-k", "engineer"])
            # Should show error
            assert result.exit_code != 0

    def test_search_displays_result_count(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that search displays the number of results found."""
        sample_profiles = [
            ConnectionProfile(
                linkedin_urn_id=f"urn:li:member:{i}",
                public_id=f"user-{i}",
                first_name=f"User{i}",
                last_name="Test",
                headline="Engineer",
                profile_url=f"https://linkedin.com/in/user-{i}",
                connection_degree=1,
                search_query="engineer",
                found_at=datetime.now(UTC),
            )
            for i in range(5)
        ]
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = sample_profiles
            mock_orch.return_value.get_remaining_actions.return_value = 24
            result = runner.invoke(app, ["search", "-k", "engineer"])
            # Should show count of 5
            assert "5" in result.output


class TestExportCommand:
    """Tests for the export command stub."""

    def test_export_prints_not_implemented(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that export command prints not implemented message."""
        result = runner.invoke(app, ["export"])
        assert "not implemented" in result.output.lower()


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_displays_rate_limit_panel(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that status command displays rate limit information."""
        with mock.patch("linkedin_scraper.cli.RateLimitDisplay") as mock_display:
            # Create a mock panel
            from rich.panel import Panel

            mock_panel = Panel("Rate Limit Info", title="Rate Limit Status")
            mock_display.return_value.render_status.return_value = mock_panel

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            # Should call render_status
            mock_display.return_value.render_status.assert_called_once()

    def test_status_displays_database_statistics(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that status command displays database statistics."""
        with mock.patch("linkedin_scraper.cli.get_database_stats") as mock_stats:
            mock_stats.return_value = {
                "total_connections": 150,
                "unique_companies": 25,
                "unique_locations": 10,
                "recent_searches_count": 5,
                "search_queries": ["engineer", "manager"],
                "degree_distribution": {1: 100, 2: 40, 3: 10},
            }
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            # Should display connection stats
            assert "150" in result.output or "connections" in result.output.lower()

    def test_status_displays_account_list(self, runner: CliRunner, temp_settings_env: str) -> None:
        """Test that status command displays stored accounts."""
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.get_database_stats") as mock_stats,
        ):
            mock_cm.return_value.list_accounts.return_value = ["default", "work"]
            mock_stats.return_value = {
                "total_connections": 0,
                "unique_companies": 0,
                "unique_locations": 0,
                "recent_searches_count": 0,
                "search_queries": [],
                "degree_distribution": {},
            }
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            # Should display accounts
            assert "default" in result.output or "work" in result.output

    def test_status_shows_no_accounts_message(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that status shows message when no accounts are stored."""
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.get_database_stats") as mock_stats,
        ):
            mock_cm.return_value.list_accounts.return_value = []
            mock_stats.return_value = {
                "total_connections": 0,
                "unique_companies": 0,
                "unique_locations": 0,
                "recent_searches_count": 0,
                "search_queries": [],
                "degree_distribution": {},
            }
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            # Should indicate no accounts or show login instruction
            assert (
                "no account" in result.output.lower()
                or "login" in result.output.lower()
                or "none" in result.output.lower()
            )

    def test_status_with_account_option_validates_cookie(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that --account option validates the specific account's cookie."""
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.LinkedInClient") as mock_li,
            mock.patch("linkedin_scraper.cli.get_database_stats") as mock_stats,
        ):
            mock_cm.return_value.list_accounts.return_value = ["work"]
            mock_cm.return_value.get_cookie.return_value = "valid_cookie"
            mock_li.return_value.validate_session.return_value = True
            mock_stats.return_value = {
                "total_connections": 0,
                "unique_companies": 0,
                "unique_locations": 0,
                "recent_searches_count": 0,
                "search_queries": [],
                "degree_distribution": {},
            }
            result = runner.invoke(app, ["status", "--account", "work"])
            assert result.exit_code == 0
            # Should get cookie for the specified account
            mock_cm.return_value.get_cookie.assert_called_with("work")
            # Should validate session
            mock_li.return_value.validate_session.assert_called_once()

    def test_status_shows_valid_session_message(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that status shows valid session message when cookie is valid."""
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.LinkedInClient") as mock_li,
            mock.patch("linkedin_scraper.cli.get_database_stats") as mock_stats,
        ):
            mock_cm.return_value.list_accounts.return_value = ["default"]
            mock_cm.return_value.get_cookie.return_value = "valid_cookie"
            mock_li.return_value.validate_session.return_value = True
            mock_stats.return_value = {
                "total_connections": 0,
                "unique_companies": 0,
                "unique_locations": 0,
                "recent_searches_count": 0,
                "search_queries": [],
                "degree_distribution": {},
            }
            result = runner.invoke(app, ["status", "-a", "default"])
            assert result.exit_code == 0
            # Should show valid/active status
            assert "valid" in result.output.lower() or "active" in result.output.lower()

    def test_status_shows_invalid_session_message(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that status shows invalid session message when cookie is expired."""
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.LinkedInClient") as mock_li,
            mock.patch("linkedin_scraper.cli.get_database_stats") as mock_stats,
        ):
            mock_cm.return_value.list_accounts.return_value = ["default"]
            mock_cm.return_value.get_cookie.return_value = "expired_cookie"
            mock_li.return_value.validate_session.return_value = False
            mock_stats.return_value = {
                "total_connections": 0,
                "unique_companies": 0,
                "unique_locations": 0,
                "recent_searches_count": 0,
                "search_queries": [],
                "degree_distribution": {},
            }
            result = runner.invoke(app, ["status", "-a", "default"])
            assert result.exit_code == 0
            # Should show invalid/expired status
            assert (
                "invalid" in result.output.lower()
                or "expired" in result.output.lower()
                or "not valid" in result.output.lower()
            )

    def test_status_shows_account_not_found_message(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that status shows message when specified account is not found."""
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.get_database_stats") as mock_stats,
        ):
            mock_cm.return_value.list_accounts.return_value = []
            mock_cm.return_value.get_cookie.return_value = None
            mock_stats.return_value = {
                "total_connections": 0,
                "unique_companies": 0,
                "unique_locations": 0,
                "recent_searches_count": 0,
                "search_queries": [],
                "degree_distribution": {},
            }
            result = runner.invoke(app, ["status", "-a", "nonexistent"])
            assert result.exit_code == 0
            # Should show not found message
            assert "not found" in result.output.lower() or "no cookie" in result.output.lower()

    def test_status_help_shows_account_option(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that status help shows --account option."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "--account" in result.output or "-a" in result.output

    def test_status_displays_degree_distribution(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that status displays connection degree distribution."""
        with mock.patch("linkedin_scraper.cli.get_database_stats") as mock_stats:
            mock_stats.return_value = {
                "total_connections": 150,
                "unique_companies": 25,
                "unique_locations": 10,
                "recent_searches_count": 5,
                "search_queries": ["engineer"],
                "degree_distribution": {1: 100, 2: 40, 3: 10},
            }
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            # Should display degree info (showing counts or degree labels)
            assert (
                "1st" in result.output
                or "2nd" in result.output
                or "100" in result.output
                or "degree" in result.output.lower()
            )


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
        # Should proceed to command (showing rate limit or database stats)
        assert (
            "rate limit" in result.output.lower()
            or "connections" in result.output.lower()
            or "database" in result.output.lower()
            or "accounts" in result.output.lower()
        )

    def test_skips_tos_when_already_accepted(
        self, runner: CliRunner, temp_settings_env: str
    ) -> None:
        """Test that ToS prompt is skipped when already accepted."""
        result = runner.invoke(app, ["status"])
        # Should not show ToS prompt, just the command output
        assert (
            "rate limit" in result.output.lower()
            or "connections" in result.output.lower()
            or "database" in result.output.lower()
            or "accounts" in result.output.lower()
        )
        # Should not ask about acceptance
        assert "do you accept" not in result.output.lower()
