# ABOUTME: Tests for the SearchOrchestrator service.
# ABOUTME: Covers coordination between RateLimiter, LinkedInClient, and DatabaseService.

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import pytest

from linkedin_scraper.auth import CookieManager
from linkedin_scraper.config import Settings
from linkedin_scraper.database import DatabaseService
from linkedin_scraper.linkedin.client import LinkedInClient
from linkedin_scraper.linkedin.exceptions import LinkedInAuthError, LinkedInRateLimitError
from linkedin_scraper.models import ActionType, ConnectionProfile
from linkedin_scraper.rate_limit.exceptions import RateLimitExceeded
from linkedin_scraper.rate_limit.service import RateLimiter
from linkedin_scraper.search.filters import NetworkDepth, SearchFilter
from linkedin_scraper.search.orchestrator import SearchOrchestrator


@pytest.fixture
def temp_db_path() -> Path:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def mock_settings(temp_db_path: Path) -> Settings:
    """Create a mock Settings object with temp paths."""
    return Settings(
        db_path=temp_db_path,
        accounts_file=temp_db_path.parent / "accounts.json",
        max_actions_per_day=25,
        min_delay_seconds=0,  # No delay for tests
        max_delay_seconds=1,
        tos_accepted=True,
    )


@pytest.fixture
def db_service(temp_db_path: Path) -> DatabaseService:
    """Create a DatabaseService with a temporary database."""
    service = DatabaseService(db_path=temp_db_path)
    service.init_db()
    return service


@pytest.fixture
def rate_limiter(db_service: DatabaseService, mock_settings: Settings) -> RateLimiter:
    """Create a RateLimiter with the test database."""
    return RateLimiter(db_service, mock_settings)


@pytest.fixture
def mock_cookie_manager() -> mock.Mock:
    """Create a mock CookieManager."""
    manager = mock.Mock(spec=CookieManager)
    manager.get_cookie.return_value = "test-li-at-cookie"
    return manager


@pytest.fixture
def mock_linkedin_client() -> mock.Mock:
    """Create a mock LinkedInClient."""
    client = mock.Mock(spec=LinkedInClient)
    return client


@pytest.fixture
def sample_search_results() -> list[dict]:
    """Sample search results from LinkedIn API."""
    return [
        {
            "urn_id": "urn:li:member:12345",
            "public_id": "john-doe",
            "name": "John Doe",
            "jobtitle": "Software Engineer at TechCorp",
            "location": "San Francisco, CA",
            "distance": "DISTANCE_1",
        },
        {
            "urn_id": "urn:li:member:67890",
            "public_id": "jane-smith",
            "name": "Jane Smith",
            "jobtitle": "Product Manager",
            "location": "New York, NY",
            "distance": "DISTANCE_2",
        },
    ]


class TestSearchOrchestratorInit:
    """Tests for SearchOrchestrator initialization."""

    def test_init_with_all_dependencies(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
    ) -> None:
        """Test that SearchOrchestrator initializes with required dependencies."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        assert orchestrator is not None

    def test_init_stores_dependencies(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
    ) -> None:
        """Test that dependencies are stored correctly."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        assert orchestrator._db_service is db_service
        assert orchestrator._rate_limiter is rate_limiter
        assert orchestrator._cookie_manager is mock_cookie_manager


class TestExecuteSearch:
    """Tests for the execute_search method."""

    def test_execute_search_loads_cookie_from_account(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
        sample_search_results: list[dict],
    ) -> None:
        """Test that execute_search loads cookie for the specified account."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="engineer", limit=10)

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.search_people.return_value = sample_search_results
            mock_client_class.return_value = mock_client

            orchestrator.execute_search(search_filter, account="work")

            mock_cookie_manager.get_cookie.assert_called_once_with("work")

    def test_execute_search_raises_when_no_cookie_found(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
    ) -> None:
        """Test that execute_search raises error when no cookie is found."""
        mock_cookie_manager.get_cookie.return_value = None
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="engineer", limit=10)

        with pytest.raises(LinkedInAuthError, match="No cookie found"):
            orchestrator.execute_search(search_filter, account="default")

    def test_execute_search_checks_rate_limit(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
        sample_search_results: list[dict],
    ) -> None:
        """Test that execute_search checks rate limit before searching."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="engineer", limit=10)

        with (
            mock.patch.object(rate_limiter, "check_and_wait") as mock_check,
            mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class,
        ):
            mock_client = mock.Mock()
            mock_client.search_people.return_value = sample_search_results
            mock_client_class.return_value = mock_client

            orchestrator.execute_search(search_filter, account="default")

            mock_check.assert_called_once_with(ActionType.SEARCH)

    def test_execute_search_raises_rate_limit_exceeded(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
    ) -> None:
        """Test that execute_search raises RateLimitExceeded when limit reached."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="engineer", limit=10)
        reset_time = datetime.now(UTC)

        with (
            mock.patch.object(
                rate_limiter,
                "check_and_wait",
                side_effect=RateLimitExceeded("Limit reached", reset_time=reset_time),
            ),
            pytest.raises(RateLimitExceeded),
        ):
            orchestrator.execute_search(search_filter, account="default")

    def test_execute_search_performs_search(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
        sample_search_results: list[dict],
    ) -> None:
        """Test that execute_search performs the search with correct filter."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(
            keywords="engineer",
            network_depths=[NetworkDepth.FIRST, NetworkDepth.SECOND],
            limit=10,
        )

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.search_people.return_value = sample_search_results
            mock_client_class.return_value = mock_client

            orchestrator.execute_search(search_filter, account="default")

            mock_client.search_people.assert_called_once_with(search_filter)

    def test_execute_search_returns_connection_profiles(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
        sample_search_results: list[dict],
    ) -> None:
        """Test that execute_search returns mapped ConnectionProfile objects."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="engineer", limit=10)

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.search_people.return_value = sample_search_results
            mock_client_class.return_value = mock_client

            results = orchestrator.execute_search(search_filter, account="default")

            assert len(results) == 2
            assert all(isinstance(r, ConnectionProfile) for r in results)
            assert results[0].first_name == "John"
            assert results[0].last_name == "Doe"
            assert results[1].first_name == "Jane"
            assert results[1].last_name == "Smith"

    def test_execute_search_saves_results_to_database(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
        sample_search_results: list[dict],
    ) -> None:
        """Test that execute_search saves results to the database."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="engineer", limit=10)

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.search_people.return_value = sample_search_results
            mock_client_class.return_value = mock_client

            orchestrator.execute_search(search_filter, account="default")

            # Verify results were saved
            saved_profiles = db_service.get_connections(limit=10)
            assert len(saved_profiles) == 2
            public_ids = {p.public_id for p in saved_profiles}
            assert "john-doe" in public_ids
            assert "jane-smith" in public_ids

    def test_execute_search_sets_search_query_on_profiles(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
        sample_search_results: list[dict],
    ) -> None:
        """Test that search_query is set on saved profiles."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="engineer", limit=10)

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.search_people.return_value = sample_search_results
            mock_client_class.return_value = mock_client

            results = orchestrator.execute_search(search_filter, account="default")

            assert all(r.search_query == "engineer" for r in results)

    def test_execute_search_handles_empty_results(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
    ) -> None:
        """Test that execute_search handles empty results gracefully."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="nonexistent", limit=10)

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.search_people.return_value = []
            mock_client_class.return_value = mock_client

            results = orchestrator.execute_search(search_filter, account="default")

            assert results == []


class TestCompanyResolution:
    """Tests for company ID resolution in search."""

    def test_execute_search_with_company_name_resolves_to_id(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
        sample_search_results: list[dict],
    ) -> None:
        """Test that company name is resolved to ID before search."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.resolve_company_id.return_value = "1234"
            mock_client.search_people.return_value = sample_search_results
            mock_client_class.return_value = mock_client

            orchestrator.execute_search_with_company_name(
                keywords="engineer",
                company_name="TechCorp",
                account="default",
            )

            mock_client.resolve_company_id.assert_called_once_with("TechCorp")

    def test_execute_search_with_company_name_uses_resolved_id_in_filter(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
        sample_search_results: list[dict],
    ) -> None:
        """Test that resolved company ID is used in search filter."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.resolve_company_id.return_value = "1234"
            mock_client.search_people.return_value = sample_search_results
            mock_client_class.return_value = mock_client

            orchestrator.execute_search_with_company_name(
                keywords="engineer",
                company_name="TechCorp",
                account="default",
            )

            # Verify the filter passed to search_people has the company ID
            call_args = mock_client.search_people.call_args
            filter_used = call_args[0][0]
            assert filter_used.current_company_ids == ["1234"]

    def test_execute_search_with_company_name_handles_unknown_company(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
        sample_search_results: list[dict],
    ) -> None:
        """Test that search proceeds without company filter if company not found."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.resolve_company_id.return_value = None
            mock_client.search_people.return_value = sample_search_results
            mock_client_class.return_value = mock_client

            # Should not raise, but search without company filter
            results = orchestrator.execute_search_with_company_name(
                keywords="engineer",
                company_name="UnknownCorp",
                account="default",
            )

            # Verify the filter has no company IDs
            call_args = mock_client.search_people.call_args
            filter_used = call_args[0][0]
            assert filter_used.current_company_ids is None
            assert len(results) == 2


class TestErrorHandling:
    """Tests for error handling in SearchOrchestrator."""

    def test_execute_search_propagates_linkedin_auth_error(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
    ) -> None:
        """Test that LinkedInAuthError is propagated correctly."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="engineer", limit=10)

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client_class.side_effect = LinkedInAuthError("Invalid cookie")

            with pytest.raises(LinkedInAuthError, match="Invalid cookie"):
                orchestrator.execute_search(search_filter, account="default")

    def test_execute_search_propagates_linkedin_rate_limit_error(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
    ) -> None:
        """Test that LinkedInRateLimitError is propagated correctly."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="engineer", limit=10)

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.search_people.side_effect = LinkedInRateLimitError("Too many requests")
            mock_client_class.return_value = mock_client

            with pytest.raises(LinkedInRateLimitError, match="Too many requests"):
                orchestrator.execute_search(search_filter, account="default")


class TestGetRemainingActions:
    """Tests for get_remaining_actions helper method."""

    def test_get_remaining_actions_returns_remaining(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
    ) -> None:
        """Test that get_remaining_actions returns correct value."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )

        remaining = orchestrator.get_remaining_actions()
        assert remaining == 25  # Default max_actions_per_day

    def test_get_remaining_actions_after_search(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        mock_cookie_manager: mock.Mock,
        sample_search_results: list[dict],
    ) -> None:
        """Test that remaining actions decreases after search."""
        orchestrator = SearchOrchestrator(
            db_service=db_service,
            rate_limiter=rate_limiter,
            cookie_manager=mock_cookie_manager,
        )
        search_filter = SearchFilter(keywords="engineer", limit=10)

        with mock.patch("linkedin_scraper.search.orchestrator.LinkedInClient") as mock_client_class:
            mock_client = mock.Mock()
            mock_client.search_people.return_value = sample_search_results
            mock_client_class.return_value = mock_client

            orchestrator.execute_search(search_filter, account="default")

            remaining = orchestrator.get_remaining_actions()
            assert remaining == 24  # One action used
