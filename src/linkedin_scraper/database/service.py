# ABOUTME: Database service for managing SQLite connections and CRUD operations.
# ABOUTME: Provides session management and persistence for ConnectionProfile and RateLimitEntry.

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from linkedin_scraper.models import ActionType, ConnectionProfile, RateLimitEntry


class DatabaseService:
    """Service for managing database connections and operations."""

    DEFAULT_DB_PATH = Path.home() / ".linkedin-scraper" / "data.db"

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize the database service.

        Args:
            db_path: Path to the SQLite database file. Defaults to ~/.linkedin-scraper/data.db
        """
        self.db_path = db_path if db_path is not None else self.DEFAULT_DB_PATH
        self._engine = create_engine(f"sqlite:///{self.db_path}", echo=False)

    def init_db(self) -> None:
        """Initialize the database by creating tables and parent directories."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        SQLModel.metadata.create_all(self._engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session as a context manager.

        Yields:
            SQLModel Session for database operations.
        """
        with Session(self._engine) as session:
            yield session

    def save_connection(self, profile: ConnectionProfile) -> ConnectionProfile:
        """Save a connection profile to the database.

        Args:
            profile: The ConnectionProfile to save.

        Returns:
            The saved ConnectionProfile with ID populated.
        """
        with self.get_session() as session:
            session.add(profile)
            session.commit()
            session.refresh(profile)
            return profile

    def get_connections(self, limit: int = 100, offset: int = 0) -> list[ConnectionProfile]:
        """Retrieve connection profiles from the database.

        Args:
            limit: Maximum number of profiles to return.
            offset: Number of profiles to skip.

        Returns:
            List of ConnectionProfile objects.
        """
        with self.get_session() as session:
            statement = select(ConnectionProfile).offset(offset).limit(limit)
            results = session.exec(statement)
            return list(results.all())

    def get_connection_by_urn(self, urn_id: str) -> ConnectionProfile | None:
        """Retrieve a connection profile by its LinkedIn URN ID.

        Args:
            urn_id: The LinkedIn URN ID to search for.

        Returns:
            The ConnectionProfile if found, None otherwise.
        """
        with self.get_session() as session:
            statement = select(ConnectionProfile).where(ConnectionProfile.linkedin_urn_id == urn_id)
            result = session.exec(statement)
            return result.first()

    def get_connections_by_query(
        self, query: str, limit: int | None = None
    ) -> list[ConnectionProfile]:
        """Retrieve connection profiles filtered by search query.

        Args:
            query: The search query string to filter by.
            limit: Maximum number of profiles to return. None for no limit.

        Returns:
            List of ConnectionProfile objects matching the query.
        """
        with self.get_session() as session:
            statement = select(ConnectionProfile).where(ConnectionProfile.search_query == query)
            if limit is not None:
                statement = statement.limit(limit)
            results = session.exec(statement)
            return list(results.all())

    def save_rate_limit_entry(self, entry: RateLimitEntry) -> RateLimitEntry:
        """Save a rate limit entry to the database.

        Args:
            entry: The RateLimitEntry to save.

        Returns:
            The saved RateLimitEntry with ID populated.
        """
        with self.get_session() as session:
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry

    def get_rate_limit_entries_since(
        self,
        since: datetime,
        action_type: ActionType | None = None,
    ) -> list[RateLimitEntry]:
        """Retrieve rate limit entries since a given time.

        Args:
            since: Datetime to filter entries from.
            action_type: Optional action type to filter by.

        Returns:
            List of RateLimitEntry objects.
        """
        with self.get_session() as session:
            statement = select(RateLimitEntry).where(RateLimitEntry.timestamp >= since)
            if action_type is not None:
                statement = statement.where(RateLimitEntry.action_type == action_type)
            results = session.exec(statement)
            return list(results.all())
