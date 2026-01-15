# ABOUTME: Tests for database statistics functionality.
# ABOUTME: Covers get_database_stats function that provides connection statistics.

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from linkedin_scraper.database.service import DatabaseService
from linkedin_scraper.database.stats import get_database_stats
from linkedin_scraper.models import ConnectionProfile


@pytest.fixture
def temp_db_path() -> Path:
    """Create a temporary database path for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def db_service(temp_db_path: Path) -> DatabaseService:
    """Create a DatabaseService instance for testing."""
    service = DatabaseService(db_path=temp_db_path)
    service.init_db()
    return service


def _create_profile(
    urn_id: str,
    first_name: str = "Test",
    last_name: str = "User",
    company: str | None = None,
    location: str | None = None,
    search_query: str | None = None,
    found_at: datetime | None = None,
) -> ConnectionProfile:
    """Helper to create a ConnectionProfile for testing."""
    return ConnectionProfile(
        linkedin_urn_id=urn_id,
        public_id=urn_id.split(":")[-1],
        first_name=first_name,
        last_name=last_name,
        headline="Engineer",
        current_company=company,
        location=location,
        profile_url=f"https://linkedin.com/in/{urn_id.split(':')[-1]}",
        connection_degree=1,
        search_query=search_query,
        found_at=found_at or datetime.now(UTC),
    )


class TestGetDatabaseStats:
    """Tests for the get_database_stats function."""

    def test_returns_dict_with_required_keys(self, db_service: DatabaseService) -> None:
        """Test that get_database_stats returns a dict with all required keys."""
        stats = get_database_stats(db_service)

        assert "total_connections" in stats
        assert "unique_companies" in stats
        assert "unique_locations" in stats
        assert "recent_searches_count" in stats

    def test_returns_zero_for_empty_database(self, db_service: DatabaseService) -> None:
        """Test that stats return zeros for an empty database."""
        stats = get_database_stats(db_service)

        assert stats["total_connections"] == 0
        assert stats["unique_companies"] == 0
        assert stats["unique_locations"] == 0
        assert stats["recent_searches_count"] == 0

    def test_counts_total_connections(self, db_service: DatabaseService) -> None:
        """Test that total_connections counts all profiles."""
        for i in range(5):
            profile = _create_profile(f"urn:li:member:{i}")
            db_service.save_connection(profile)

        stats = get_database_stats(db_service)
        assert stats["total_connections"] == 5

    def test_counts_unique_companies(self, db_service: DatabaseService) -> None:
        """Test that unique_companies counts distinct non-null company names."""
        companies = ["TechCorp", "TechCorp", "StartupInc", "BigCo", None]
        for i, company in enumerate(companies):
            profile = _create_profile(f"urn:li:member:{i}", company=company)
            db_service.save_connection(profile)

        stats = get_database_stats(db_service)
        # Should be 3 unique companies (TechCorp, StartupInc, BigCo), None not counted
        assert stats["unique_companies"] == 3

    def test_counts_unique_locations(self, db_service: DatabaseService) -> None:
        """Test that unique_locations counts distinct non-null locations."""
        locations = ["San Francisco, CA", "New York, NY", "San Francisco, CA", None, "London, UK"]
        for i, location in enumerate(locations):
            profile = _create_profile(f"urn:li:member:{i}", location=location)
            db_service.save_connection(profile)

        stats = get_database_stats(db_service)
        # Should be 3 unique locations (SF, NY, London), None not counted
        assert stats["unique_locations"] == 3

    def test_counts_recent_searches(self, db_service: DatabaseService) -> None:
        """Test that recent_searches_count counts distinct search queries."""
        queries = ["engineer", "manager", "engineer", "designer", None]
        for i, query in enumerate(queries):
            profile = _create_profile(f"urn:li:member:{i}", search_query=query)
            db_service.save_connection(profile)

        stats = get_database_stats(db_service)
        # Should be 3 unique queries (engineer, manager, designer), None not counted
        assert stats["recent_searches_count"] == 3

    def test_handles_all_null_fields(self, db_service: DatabaseService) -> None:
        """Test that stats handle profiles with all null optional fields."""
        for i in range(3):
            profile = _create_profile(
                f"urn:li:member:{i}",
                company=None,
                location=None,
                search_query=None,
            )
            db_service.save_connection(profile)

        stats = get_database_stats(db_service)
        assert stats["total_connections"] == 3
        assert stats["unique_companies"] == 0
        assert stats["unique_locations"] == 0
        assert stats["recent_searches_count"] == 0

    def test_returns_search_queries_list(self, db_service: DatabaseService) -> None:
        """Test that stats include a list of search queries."""
        queries = ["engineer", "manager", "designer"]
        for i, query in enumerate(queries):
            profile = _create_profile(f"urn:li:member:{i}", search_query=query)
            db_service.save_connection(profile)

        stats = get_database_stats(db_service)
        assert "search_queries" in stats
        assert set(stats["search_queries"]) == set(queries)

    def test_returns_connection_degree_distribution(self, db_service: DatabaseService) -> None:
        """Test that stats include connection degree distribution."""
        # Create profiles with different degrees
        degrees = [1, 1, 1, 2, 2, 3]
        for i, degree in enumerate(degrees):
            profile = ConnectionProfile(
                linkedin_urn_id=f"urn:li:member:{i}",
                public_id=f"user-{i}",
                first_name="Test",
                last_name="User",
                headline="Engineer",
                profile_url=f"https://linkedin.com/in/user-{i}",
                connection_degree=degree,
                found_at=datetime.now(UTC),
            )
            db_service.save_connection(profile)

        stats = get_database_stats(db_service)
        assert "degree_distribution" in stats
        assert stats["degree_distribution"].get(1) == 3
        assert stats["degree_distribution"].get(2) == 2
        assert stats["degree_distribution"].get(3) == 1
