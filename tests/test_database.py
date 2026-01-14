# ABOUTME: Tests for the database service module.
# ABOUTME: Covers CRUD operations and session management for SQLModel entities.

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from linkedin_scraper.database import DatabaseService
from linkedin_scraper.models import ActionType, ConnectionProfile, RateLimitEntry


@pytest.fixture
def temp_db_path() -> Path:
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return Path(f.name)


@pytest.fixture
def db_service(temp_db_path: Path) -> DatabaseService:
    """Create a DatabaseService instance with a temporary database."""
    service = DatabaseService(db_path=temp_db_path)
    service.init_db()
    return service


class TestDatabaseServiceInit:
    """Tests for DatabaseService initialization."""

    def test_init_with_custom_path(self, temp_db_path: Path) -> None:
        """Test that DatabaseService accepts a custom database path."""
        service = DatabaseService(db_path=temp_db_path)
        assert service.db_path == temp_db_path

    def test_init_with_default_path(self) -> None:
        """Test that DatabaseService uses default path when none provided."""
        service = DatabaseService()
        expected_path = Path.home() / ".linkedin-scraper" / "data.db"
        assert service.db_path == expected_path

    def test_init_db_creates_tables(self, temp_db_path: Path) -> None:
        """Test that init_db creates the required tables."""
        service = DatabaseService(db_path=temp_db_path)
        service.init_db()
        # If no exception raised, tables were created successfully
        # Verify by attempting to query
        connections = service.get_connections()
        assert connections == []

    def test_init_db_creates_parent_directory(self) -> None:
        """Test that init_db creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "subdir" / "nested" / "data.db"
            service = DatabaseService(db_path=db_path)
            service.init_db()
            assert db_path.parent.exists()


class TestDatabaseServiceSession:
    """Tests for session management."""

    def test_get_session_returns_context_manager(self, db_service: DatabaseService) -> None:
        """Test that get_session returns a usable context manager."""
        with db_service.get_session() as session:
            assert session is not None


class TestConnectionProfileOperations:
    """Tests for ConnectionProfile CRUD operations."""

    def test_save_connection_creates_new_profile(self, db_service: DatabaseService) -> None:
        """Test saving a new connection profile."""
        profile = ConnectionProfile(
            linkedin_urn_id="urn:li:member:123456",
            public_id="john-doe",
            first_name="John",
            last_name="Doe",
            headline="Software Engineer",
            location="San Francisco, CA",
            current_company="Acme Corp",
            current_title="Senior Engineer",
            profile_url="https://linkedin.com/in/john-doe",
            connection_degree=1,
            search_query="software engineer",
        )

        saved = db_service.save_connection(profile)

        assert saved.id is not None
        assert saved.linkedin_urn_id == "urn:li:member:123456"
        assert saved.first_name == "John"

    def test_save_connection_persists_to_database(self, db_service: DatabaseService) -> None:
        """Test that saved connection can be retrieved."""
        profile = ConnectionProfile(
            linkedin_urn_id="urn:li:member:789",
            public_id="jane-smith",
            first_name="Jane",
            last_name="Smith",
            profile_url="https://linkedin.com/in/jane-smith",
            connection_degree=2,
        )

        db_service.save_connection(profile)
        connections = db_service.get_connections()

        assert len(connections) == 1
        assert connections[0].public_id == "jane-smith"

    def test_get_connections_returns_empty_list_when_no_data(
        self, db_service: DatabaseService
    ) -> None:
        """Test that get_connections returns empty list for empty database."""
        connections = db_service.get_connections()
        assert connections == []

    def test_get_connections_with_limit(self, db_service: DatabaseService) -> None:
        """Test that get_connections respects limit parameter."""
        for i in range(5):
            profile = ConnectionProfile(
                linkedin_urn_id=f"urn:li:member:{i}",
                public_id=f"user-{i}",
                first_name=f"User{i}",
                last_name="Test",
                profile_url=f"https://linkedin.com/in/user-{i}",
                connection_degree=1,
            )
            db_service.save_connection(profile)

        connections = db_service.get_connections(limit=3)
        assert len(connections) == 3

    def test_get_connections_with_offset(self, db_service: DatabaseService) -> None:
        """Test that get_connections respects offset parameter."""
        for i in range(5):
            profile = ConnectionProfile(
                linkedin_urn_id=f"urn:li:member:{i}",
                public_id=f"user-{i}",
                first_name=f"User{i}",
                last_name="Test",
                profile_url=f"https://linkedin.com/in/user-{i}",
                connection_degree=1,
            )
            db_service.save_connection(profile)

        connections = db_service.get_connections(limit=2, offset=2)
        assert len(connections) == 2

    def test_get_connection_by_urn_returns_profile(self, db_service: DatabaseService) -> None:
        """Test retrieving a connection by URN ID."""
        profile = ConnectionProfile(
            linkedin_urn_id="urn:li:member:unique123",
            public_id="unique-user",
            first_name="Unique",
            last_name="User",
            profile_url="https://linkedin.com/in/unique-user",
            connection_degree=1,
        )
        db_service.save_connection(profile)

        found = db_service.get_connection_by_urn("urn:li:member:unique123")

        assert found is not None
        assert found.public_id == "unique-user"

    def test_get_connection_by_urn_returns_none_when_not_found(
        self, db_service: DatabaseService
    ) -> None:
        """Test that get_connection_by_urn returns None for non-existent URN."""
        found = db_service.get_connection_by_urn("urn:li:member:nonexistent")
        assert found is None


class TestRateLimitEntryOperations:
    """Tests for RateLimitEntry operations."""

    def test_save_rate_limit_entry(self, db_service: DatabaseService) -> None:
        """Test saving a rate limit entry."""
        entry = RateLimitEntry(
            action_type=ActionType.SEARCH,
            timestamp=datetime.now(),
        )

        saved = db_service.save_rate_limit_entry(entry)

        assert saved.id is not None
        assert saved.action_type == ActionType.SEARCH

    def test_get_rate_limit_entries_since(self, db_service: DatabaseService) -> None:
        """Test retrieving rate limit entries since a given time."""
        # Create entries with different timestamps
        # Use naive datetimes since SQLite doesn't preserve timezone info
        old_time = datetime(2020, 1, 1)
        recent_time = datetime(2025, 6, 15, 12, 30, 0)

        old_entry = RateLimitEntry(
            action_type=ActionType.SEARCH,
            timestamp=old_time,
        )
        recent_entry = RateLimitEntry(
            action_type=ActionType.SEARCH,
            timestamp=recent_time,
        )

        db_service.save_rate_limit_entry(old_entry)
        db_service.save_rate_limit_entry(recent_entry)

        # Query for entries since 2023
        since = datetime(2023, 1, 1)
        entries = db_service.get_rate_limit_entries_since(since)

        assert len(entries) == 1
        assert entries[0].timestamp == recent_time

    def test_get_rate_limit_entries_by_action_type(self, db_service: DatabaseService) -> None:
        """Test filtering rate limit entries by action type."""
        search_entry = RateLimitEntry(action_type=ActionType.SEARCH)
        view_entry = RateLimitEntry(action_type=ActionType.PROFILE_VIEW)

        db_service.save_rate_limit_entry(search_entry)
        db_service.save_rate_limit_entry(view_entry)

        since = datetime(2020, 1, 1)
        search_entries = db_service.get_rate_limit_entries_since(
            since, action_type=ActionType.SEARCH
        )

        assert len(search_entries) == 1
        assert search_entries[0].action_type == ActionType.SEARCH
