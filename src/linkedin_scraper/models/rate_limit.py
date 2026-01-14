# ABOUTME: SQLModel for tracking API calls to enforce rate limits.
# ABOUTME: Persists action history to survive application restarts.

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class ActionType(str, Enum):
    """Types of rate-limited actions."""

    SEARCH = "search"
    PROFILE_VIEW = "profile_view"


class RateLimitEntry(SQLModel, table=True):
    """Tracks API calls for rate limiting."""

    __tablename__ = "rate_limit_entries"

    id: int | None = Field(default=None, primary_key=True)
    action_type: ActionType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
