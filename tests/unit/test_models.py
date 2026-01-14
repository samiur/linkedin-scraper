# ABOUTME: Unit tests for data models (ConnectionProfile, SearchFilter, RateLimitEntry).
# ABOUTME: Tests validation, defaults, and serialization behavior.

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from linkedin_scraper.models.connection import ConnectionProfile
from linkedin_scraper.models.rate_limit import ActionType, RateLimitEntry
from linkedin_scraper.search.filters import NetworkDepth, SearchFilter


class TestConnectionProfile:
    """Tests for ConnectionProfile SQLModel."""

    def test_create_connection_profile_with_required_fields(self):
        """Test creating a profile with only required fields."""
        profile = ConnectionProfile(
            linkedin_urn_id="urn:li:fs_miniProfile:ABC123",
            public_id="john-doe-123",
            first_name="John",
            last_name="Doe",
            profile_url="https://www.linkedin.com/in/john-doe-123",
            connection_degree=1,
        )

        assert profile.first_name == "John"
        assert profile.last_name == "Doe"
        assert profile.connection_degree == 1
        assert isinstance(profile.id, UUID)
        assert profile.full_name == "John Doe"

    def test_create_connection_profile_with_all_fields(self):
        """Test creating a profile with all fields populated."""
        profile = ConnectionProfile(
            linkedin_urn_id="urn:li:fs_miniProfile:ABC123",
            public_id="jane-smith-456",
            first_name="Jane",
            last_name="Smith",
            headline="Software Engineer at Google",
            location="San Francisco, CA",
            current_company="Google",
            current_title="Software Engineer",
            profile_url="https://www.linkedin.com/in/jane-smith-456",
            connection_degree=2,
            search_query="Software Engineer",
        )

        assert profile.headline == "Software Engineer at Google"
        assert profile.current_company == "Google"
        assert profile.search_query == "Software Engineer"
        assert isinstance(profile.found_at, datetime)

    def test_connection_degree_validation_rejects_invalid(self):
        """Test that connection degree must be 1, 2, or 3."""
        with pytest.raises(ValidationError):
            ConnectionProfile(
                linkedin_urn_id="urn:li:fs_miniProfile:ABC123",
                public_id="test",
                first_name="Test",
                last_name="User",
                profile_url="https://linkedin.com/in/test",
                connection_degree=0,
            )

        with pytest.raises(ValidationError):
            ConnectionProfile(
                linkedin_urn_id="urn:li:fs_miniProfile:ABC123",
                public_id="test",
                first_name="Test",
                last_name="User",
                profile_url="https://linkedin.com/in/test",
                connection_degree=4,
            )


class TestSearchFilter:
    """Tests for SearchFilter Pydantic model."""

    def test_search_filter_defaults(self):
        """Test that SearchFilter has sensible defaults."""
        filter = SearchFilter()

        assert filter.keywords is None
        assert filter.network_depths == [NetworkDepth.FIRST, NetworkDepth.SECOND]
        assert filter.current_company_ids is None
        assert filter.regions is None
        assert filter.limit == 100

    def test_search_filter_with_keywords(self):
        """Test creating a filter with keyword search."""
        filter = SearchFilter(keywords="Software Engineer")

        assert filter.keywords == "Software Engineer"

    def test_search_filter_with_network_depth(self):
        """Test specifying network depth filter."""
        filter = SearchFilter(network_depths=[NetworkDepth.FIRST])

        assert filter.network_depths == [NetworkDepth.FIRST]

    def test_search_filter_with_company_and_region(self):
        """Test filter with company and region."""
        filter = SearchFilter(
            keywords="HR Manager",
            current_company_ids=["12345", "67890"],
            regions=["us:0"],
        )

        assert filter.current_company_ids == ["12345", "67890"]
        assert filter.regions == ["us:0"]

    def test_search_filter_limit_validation(self):
        """Test that limit must be within bounds."""
        filter = SearchFilter(limit=500)
        assert filter.limit == 500

        with pytest.raises(ValidationError):
            SearchFilter(limit=0)

        with pytest.raises(ValidationError):
            SearchFilter(limit=1001)


class TestNetworkDepth:
    """Tests for NetworkDepth enum."""

    def test_network_depth_values(self):
        """Test that NetworkDepth has correct API values."""
        assert NetworkDepth.FIRST.value == "F"
        assert NetworkDepth.SECOND.value == "S"
        assert NetworkDepth.THIRD.value == "O"


class TestRateLimitEntry:
    """Tests for RateLimitEntry SQLModel."""

    def test_create_rate_limit_entry(self):
        """Test creating a rate limit entry."""
        entry = RateLimitEntry(action_type=ActionType.SEARCH)

        assert entry.action_type == ActionType.SEARCH
        assert isinstance(entry.timestamp, datetime)

    def test_action_type_values(self):
        """Test that ActionType has correct values."""
        assert ActionType.SEARCH.value == "search"
        assert ActionType.PROFILE_VIEW.value == "profile_view"
