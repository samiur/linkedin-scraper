# ABOUTME: SQLModel for persisting LinkedIn connection profile data.
# ABOUTME: Stores search results with metadata for later export and analysis.

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ConnectionProfile(SQLModel, table=True):
    """Represents a LinkedIn connection profile."""

    __tablename__ = "connection_profiles"
    model_config = {"validate_assignment": True}

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    linkedin_urn_id: Annotated[str, Field(index=True, description="LinkedIn URN ID")]
    public_id: Annotated[str, Field(index=True, description="URL-friendly identifier")]

    first_name: str
    last_name: str
    headline: str | None = None
    location: str | None = None

    current_company: str | None = None
    current_title: str | None = None

    profile_url: str
    connection_degree: Annotated[int, Field(ge=1, le=3, description="1st, 2nd, or 3rd degree")]

    search_query: Annotated[
        str | None, Field(default=None, description="The search query that found this profile")
    ]
    found_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def full_name(self) -> str:
        """Return the full name of the connection."""
        return f"{self.first_name} {self.last_name}"
