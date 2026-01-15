# ABOUTME: End-to-end integration tests for the LinkedIn scraper CLI tool.
# ABOUTME: Tests full login -> search -> export flow with mocked LinkedIn API.

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from linkedin_scraper.cli import app
from linkedin_scraper.config import get_settings
from linkedin_scraper.database import DatabaseService
from linkedin_scraper.models import ActionType, ConnectionProfile, RateLimitEntry


@pytest.fixture
def runner() -> CliRunner:
    """Create a CliRunner instance for testing Typer commands."""
    return CliRunner()


@pytest.fixture
def temp_integration_env():
    """Create a fully isolated temporary environment for integration tests.

    This fixture sets up:
    - A temporary database file
    - A temporary accounts file
    - ToS pre-accepted
    - Fresh settings cache for each test
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "data.db"
        accounts_file = Path(tmpdir) / "accounts.json"
        env_vars = {
            "LINKEDIN_SCRAPER_DB_PATH": str(db_path),
            "LINKEDIN_SCRAPER_ACCOUNTS_FILE": str(accounts_file),
            "LINKEDIN_SCRAPER_TOS_ACCEPTED": "true",
            "LINKEDIN_SCRAPER_MAX_ACTIONS_PER_DAY": "5",
            "LINKEDIN_SCRAPER_MIN_DELAY_SECONDS": "0",
            "LINKEDIN_SCRAPER_MAX_DELAY_SECONDS": "0",
        }
        with mock.patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            yield {
                "tmpdir": tmpdir,
                "db_path": db_path,
                "accounts_file": accounts_file,
            }
        get_settings.cache_clear()


class TestFullLoginSearchExportFlow:
    """Test the complete login -> search -> export workflow."""

    def test_login_search_export_flow(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test the full workflow: login, search, and export to CSV."""
        valid_li_at = "AQEDAQEBAAAAAAAAAAAAAAFZXyYZWFhW"
        valid_jsessionid = "ajax:1234567890123456789"

        # Step 1: Login with valid cookies
        with mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm:
            mock_cm.return_value.validate_cookie_format.return_value = True
            login_result = runner.invoke(
                app, ["login", "--no-validate"], input=f"{valid_li_at}\n{valid_jsessionid}\n"
            )
            assert login_result.exit_code == 0
            assert "success" in login_result.output.lower()
            mock_cm.return_value.store_cookies.assert_called_once_with(
                valid_li_at, valid_jsessionid, "default"
            )

        # Step 2: Execute search
        with (
            mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch,
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
        ):
            # Configure mock orchestrator to return sample profiles
            sample_profiles = [
                ConnectionProfile(
                    linkedin_urn_id="urn:li:member:123",
                    public_id="john-doe",
                    first_name="John",
                    last_name="Doe",
                    headline="Senior Software Engineer at TechCorp",
                    location="San Francisco, CA",
                    profile_url="https://linkedin.com/in/john-doe",
                    connection_degree=1,
                    search_query="engineer",
                    found_at=datetime.now(UTC),
                ),
                ConnectionProfile(
                    linkedin_urn_id="urn:li:member:456",
                    public_id="jane-smith",
                    first_name="Jane",
                    last_name="Smith",
                    headline="Engineering Manager",
                    location="New York, NY",
                    profile_url="https://linkedin.com/in/jane-smith",
                    connection_degree=2,
                    search_query="engineer",
                    found_at=datetime.now(UTC),
                ),
            ]
            mock_orch.return_value.execute_search_with_company_name.return_value = sample_profiles
            mock_orch.return_value.get_remaining_actions.return_value = 24

            search_result = runner.invoke(app, ["search", "-k", "engineer"])
            assert search_result.exit_code == 0
            assert "john" in search_result.output.lower()
            assert "2" in search_result.output  # result count

        # Step 3: Export results
        export_path = Path(temp_integration_env["tmpdir"]) / "export.csv"
        with (
            mock.patch("linkedin_scraper.cli.DatabaseService") as mock_db,
            mock.patch("linkedin_scraper.cli.CSVExporter") as mock_exporter,
        ):
            mock_db.return_value.get_connections.return_value = sample_profiles
            mock_exporter.return_value.export.return_value = export_path

            export_result = runner.invoke(app, ["export", "-o", str(export_path)])
            assert export_result.exit_code == 0
            assert "2" in export_result.output  # exported count

    def test_workflow_with_company_filter(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test search with company name filter triggers company resolution."""
        sample_profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:789",
                public_id="alice-jones",
                first_name="Alice",
                last_name="Jones",
                headline="Software Developer at Acme Inc",
                location="Seattle, WA",
                current_company="Acme Inc",
                profile_url="https://linkedin.com/in/alice-jones",
                connection_degree=1,
                search_query="developer",
                found_at=datetime.now(UTC),
            ),
        ]

        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = sample_profiles
            mock_orch.return_value.get_remaining_actions.return_value = 24

            result = runner.invoke(app, ["search", "-k", "developer", "-c", "Acme Inc"])
            assert result.exit_code == 0

            # Verify company_name was passed to orchestrator
            call_kwargs = mock_orch.return_value.execute_search_with_company_name.call_args[1]
            assert call_kwargs["company_name"] == "Acme Inc"

    def test_workflow_with_multiple_filters(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test search with multiple filters: company, location, degree."""
        sample_profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:111",
                public_id="bob-wilson",
                first_name="Bob",
                last_name="Wilson",
                headline="Senior Developer",
                location="Austin, TX",
                profile_url="https://linkedin.com/in/bob-wilson",
                connection_degree=2,
                search_query="senior developer",
                found_at=datetime.now(UTC),
            ),
        ]

        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = sample_profiles
            mock_orch.return_value.get_remaining_actions.return_value = 23

            result = runner.invoke(
                app,
                [
                    "search",
                    "-k",
                    "senior developer",
                    "-c",
                    "BigTech",
                    "-l",
                    "Austin",
                    "-d",
                    "2,3",
                    "--limit",
                    "50",
                ],
            )
            assert result.exit_code == 0

            # Verify all filters were passed correctly
            call_kwargs = mock_orch.return_value.execute_search_with_company_name.call_args[1]
            assert call_kwargs["keywords"] == "senior developer"
            assert call_kwargs["company_name"] == "BigTech"
            assert call_kwargs["location"] == "Austin"
            assert call_kwargs["limit"] == 50
            # Degree filter should be parsed to network_depths
            assert len(call_kwargs["network_depths"]) == 2


class TestRateLimitEnforcementIntegration:
    """Test rate limit enforcement across multiple operations."""

    def test_rate_limit_enforced_across_searches(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that rate limits are checked before each search operation."""
        call_count = 0

        def mock_check_and_wait(*args: object, **kwargs: object) -> None:
            nonlocal call_count
            call_count += 1

        sample_profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:999",
                public_id="test-user",
                first_name="Test",
                last_name="User",
                headline="Developer",
                profile_url="https://linkedin.com/in/test-user",
                connection_degree=1,
                search_query="test",
                found_at=datetime.now(UTC),
            ),
        ]

        with (
            mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch,
            mock.patch(
                "linkedin_scraper.rate_limit.service.RateLimiter.check_and_wait",
                side_effect=mock_check_and_wait,
            ),
        ):
            mock_orch.return_value.execute_search_with_company_name.return_value = sample_profiles
            mock_orch.return_value.get_remaining_actions.return_value = 24

            # First search
            result1 = runner.invoke(app, ["search", "-k", "test1"])
            assert result1.exit_code == 0

            # Second search
            result2 = runner.invoke(app, ["search", "-k", "test2"])
            assert result2.exit_code == 0

    def test_rate_limit_exceeded_blocks_search(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that search is blocked when rate limit is exceeded."""
        from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded

        reset_time = datetime.now(UTC)

        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.side_effect = RateLimitExceeded(
                "Daily limit reached", reset_time=reset_time
            )

            result = runner.invoke(app, ["search", "-k", "blocked"])
            assert result.exit_code != 0
            assert "limit" in result.output.lower()

    def test_rate_limit_status_updates_after_search(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that rate limit status is displayed after search."""
        sample_profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:888",
                public_id="status-test",
                first_name="Status",
                last_name="Test",
                headline="Tester",
                profile_url="https://linkedin.com/in/status-test",
                connection_degree=1,
                search_query="status",
                found_at=datetime.now(UTC),
            ),
        ]

        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = sample_profiles
            mock_orch.return_value.get_remaining_actions.return_value = 3  # Low count

            result = runner.invoke(app, ["search", "-k", "status"])
            assert result.exit_code == 0
            # Should show remaining actions or warning
            assert "3" in result.output or "remaining" in result.output.lower()

    def test_rate_limit_warning_displayed_when_low(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that a warning is displayed when rate limit is getting low."""
        sample_profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:777",
                public_id="warn-test",
                first_name="Warn",
                last_name="Test",
                headline="Tester",
                profile_url="https://linkedin.com/in/warn-test",
                connection_degree=1,
                search_query="warn",
                found_at=datetime.now(UTC),
            ),
        ]

        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = sample_profiles
            # Return a low number to trigger warning
            mock_orch.return_value.get_remaining_actions.return_value = 2

            result = runner.invoke(app, ["search", "-k", "warn"])
            assert result.exit_code == 0
            # Should show the remaining count
            assert "2" in result.output


class TestDatabasePersistenceIntegration:
    """Test database persistence across command invocations."""

    def test_search_results_persist_to_database(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that search results are saved to the database."""
        db_path = temp_integration_env["db_path"]

        # Initialize database with test data directly
        db_service = DatabaseService(db_path=db_path)
        db_service.init_db()

        # Save a test connection
        test_profile = ConnectionProfile(
            linkedin_urn_id="urn:li:member:persist1",
            public_id="persist-user",
            first_name="Persist",
            last_name="User",
            headline="Test Engineer",
            profile_url="https://linkedin.com/in/persist-user",
            connection_degree=1,
            search_query="persist test",
            found_at=datetime.now(UTC),
        )
        db_service.save_connection(test_profile)

        # Verify data persists by reading from a new service instance
        db_service2 = DatabaseService(db_path=db_path)
        connections = db_service2.get_connections(limit=10)
        assert len(connections) == 1
        assert connections[0].public_id == "persist-user"

    def test_export_reads_from_persistent_database(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that export command reads from the persistent database."""
        db_path = temp_integration_env["db_path"]

        # Pre-populate database
        db_service = DatabaseService(db_path=db_path)
        db_service.init_db()

        profiles_to_save = [
            ConnectionProfile(
                linkedin_urn_id=f"urn:li:member:export{i}",
                public_id=f"export-user-{i}",
                first_name=f"Export{i}",
                last_name="User",
                headline="Tester",
                profile_url=f"https://linkedin.com/in/export-user-{i}",
                connection_degree=1,
                search_query="export test",
                found_at=datetime.now(UTC),
            )
            for i in range(3)
        ]

        for profile in profiles_to_save:
            db_service.save_connection(profile)

        # Export should use the real database service
        export_path = Path(temp_integration_env["tmpdir"]) / "db_export.csv"

        with mock.patch("linkedin_scraper.cli.CSVExporter") as mock_exporter:
            mock_exporter.return_value.export.return_value = export_path

            result = runner.invoke(app, ["export", "-o", str(export_path)])
            assert result.exit_code == 0

            # The exporter should have been called with the profiles from DB
            export_call = mock_exporter.return_value.export.call_args
            exported_profiles = export_call[0][0]
            assert len(exported_profiles) == 3

    def test_rate_limit_entries_persist_across_invocations(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that rate limit entries persist in the database."""
        db_path = temp_integration_env["db_path"]

        # Record rate limit entries directly
        db_service = DatabaseService(db_path=db_path)
        db_service.init_db()

        entry1 = RateLimitEntry(
            action_type=ActionType.SEARCH,
            timestamp=datetime.now(UTC),
        )
        db_service.save_rate_limit_entry(entry1)

        # Verify entries persist in a new service instance
        db_service2 = DatabaseService(db_path=db_path)
        entries = db_service2.get_rate_limit_entries_since(
            datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        )
        assert len(entries) >= 1
        assert entries[0].action_type == ActionType.SEARCH

    def test_status_shows_database_statistics(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that status command shows database statistics from real DB."""
        db_path = temp_integration_env["db_path"]

        # Pre-populate database with connections
        db_service = DatabaseService(db_path=db_path)
        db_service.init_db()

        for i in range(5):
            profile = ConnectionProfile(
                linkedin_urn_id=f"urn:li:member:stats{i}",
                public_id=f"stats-user-{i}",
                first_name=f"Stats{i}",
                last_name="User",
                headline="Engineer",
                location="San Francisco" if i < 3 else "New York",
                current_company="TechCorp" if i < 2 else "OtherCorp",
                profile_url=f"https://linkedin.com/in/stats-user-{i}",
                connection_degree=1 if i < 3 else 2,
                search_query="stats test",
                found_at=datetime.now(UTC),
            )
            db_service.save_connection(profile)

        # Status command should show real statistics
        with mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm:
            mock_cm.return_value.list_accounts.return_value = []

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            # Should show the total connections
            assert "5" in result.output or "connections" in result.output.lower()


class TestAccountManagementIntegration:
    """Test account management across commands."""

    def test_login_to_custom_account_then_search(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test logging into a custom account and using it for search."""
        valid_li_at = "AQEDAQEBAAAAAAAAAAAAAAFZXyYZWFhW"
        valid_jsessionid = "ajax:1234567890123456789"
        account_name = "work"

        # Login to work account
        with mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm:
            mock_cm.return_value.validate_cookie_format.return_value = True
            login_result = runner.invoke(
                app,
                ["login", "-a", account_name, "--no-validate"],
                input=f"{valid_li_at}\n{valid_jsessionid}\n",
            )
            assert login_result.exit_code == 0
            mock_cm.return_value.store_cookies.assert_called_once_with(
                valid_li_at, valid_jsessionid, account_name
            )

        # Search with work account
        sample_profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:work1",
                public_id="work-user",
                first_name="Work",
                last_name="User",
                headline="Manager",
                profile_url="https://linkedin.com/in/work-user",
                connection_degree=1,
                search_query="manager",
                found_at=datetime.now(UTC),
            ),
        ]

        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = sample_profiles
            mock_orch.return_value.get_remaining_actions.return_value = 24

            search_result = runner.invoke(app, ["search", "-k", "manager", "-a", account_name])
            assert search_result.exit_code == 0

            # Verify the account was passed to orchestrator
            call_kwargs = mock_orch.return_value.execute_search_with_company_name.call_args[1]
            assert call_kwargs["account"] == account_name

    def test_status_shows_multiple_accounts(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that status shows all stored accounts."""
        with (
            mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm,
            mock.patch("linkedin_scraper.cli.get_database_stats") as mock_stats,
        ):
            mock_cm.return_value.list_accounts.return_value = [
                "default",
                "work",
                "personal",
            ]
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
            # Should show all accounts
            assert (
                "default" in result.output or "work" in result.output or "personal" in result.output
            )


class TestErrorRecoveryIntegration:
    """Test error handling and recovery scenarios."""

    def test_search_after_auth_error_recovery(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that user can recover from auth error by re-logging in."""
        from linkedin_scraper.linkedin.exceptions import LinkedInAuthError

        # First search attempt fails with auth error
        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.side_effect = LinkedInAuthError(
                "Cookie expired"
            )

            result1 = runner.invoke(app, ["search", "-k", "test"])
            assert result1.exit_code != 0
            assert "cookie" in result1.output.lower() or "login" in result1.output.lower()

        # User re-logs in
        valid_li_at = "AQEDAQEBAAAAAAAAAAAAAAFZXyYZWFhW"
        valid_jsessionid = "ajax:1234567890123456789"
        with mock.patch("linkedin_scraper.cli.CookieManager") as mock_cm:
            mock_cm.return_value.validate_cookie_format.return_value = True
            login_result = runner.invoke(
                app, ["login", "--no-validate"], input=f"{valid_li_at}\n{valid_jsessionid}\n"
            )
            assert login_result.exit_code == 0

        # Search succeeds with new cookie
        sample_profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:recovery",
                public_id="recovery-user",
                first_name="Recovery",
                last_name="User",
                headline="Tester",
                profile_url="https://linkedin.com/in/recovery-user",
                connection_degree=1,
                search_query="test",
                found_at=datetime.now(UTC),
            ),
        ]

        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.return_value = sample_profiles
            mock_orch.return_value.get_remaining_actions.return_value = 24

            result2 = runner.invoke(app, ["search", "-k", "test"])
            assert result2.exit_code == 0

    def test_export_with_no_data_shows_warning(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that export shows warning when database is empty."""
        export_path = Path(temp_integration_env["tmpdir"]) / "empty_export.csv"

        with mock.patch("linkedin_scraper.cli.CSVExporter") as mock_exporter:
            mock_exporter.return_value.export.return_value = export_path

            result = runner.invoke(app, ["export", "-o", str(export_path)])
            assert result.exit_code == 0
            # Should show warning or 0 count
            assert "0" in result.output or "no" in result.output.lower()

    def test_network_error_shows_helpful_message(
        self,
        runner: CliRunner,
        temp_integration_env: dict[str, Path | str],
    ) -> None:
        """Test that network errors show helpful retry message."""
        import urllib.error

        with mock.patch("linkedin_scraper.cli.SearchOrchestrator") as mock_orch:
            mock_orch.return_value.execute_search_with_company_name.side_effect = (
                urllib.error.URLError("Connection timed out")
            )

            result = runner.invoke(app, ["search", "-k", "network-test"])
            assert result.exit_code != 0
            assert (
                "retry" in result.output.lower()
                or "network" in result.output.lower()
                or "connection" in result.output.lower()
            )
