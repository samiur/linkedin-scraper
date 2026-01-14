# ABOUTME: Shared pytest fixtures for linkedin-scraper tests.
# ABOUTME: Provides database, mock clients, and sample data fixtures.

import pytest
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a database session for testing."""
    with Session(test_engine) as session:
        yield session
