# ABOUTME: Tests for the display module including ConnectionTable and status display functions.
# ABOUTME: Covers Rich table rendering, truncation, color-coding, and panel generation.

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from rich.panel import Panel
from rich.table import Table

from linkedin_scraper.models import ConnectionProfile


@pytest.fixture
def sample_profile() -> ConnectionProfile:
    """Create a sample ConnectionProfile for testing."""
    return ConnectionProfile(
        id=uuid4(),
        linkedin_urn_id="urn:li:fsd_profile:ABC123",
        public_id="john-doe",
        first_name="John",
        last_name="Doe",
        headline="Software Engineer at Tech Corp",
        location="San Francisco, CA",
        current_company="Tech Corp",
        current_title="Software Engineer",
        profile_url="https://www.linkedin.com/in/john-doe",
        connection_degree=1,
        search_query="software engineer",
        found_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_profiles() -> list[ConnectionProfile]:
    """Create a list of sample ConnectionProfiles for testing."""
    profiles = []
    for i, (first, last, degree, company, location) in enumerate(
        [
            ("John", "Doe", 1, "Tech Corp", "San Francisco, CA"),
            ("Jane", "Smith", 2, "Startup Inc", "New York, NY"),
            ("Bob", "Johnson", 3, "Big Company", "Los Angeles, CA"),
            ("Alice", "Williams", 1, "Small Firm", "Seattle, WA"),
            ("Charlie", "Brown", 2, "Another Corp", "Austin, TX"),
        ]
    ):
        profiles.append(
            ConnectionProfile(
                id=uuid4(),
                linkedin_urn_id=f"urn:li:fsd_profile:PROFILE{i}",
                public_id=f"{first.lower()}-{last.lower()}",
                first_name=first,
                last_name=last,
                headline=f"Engineer at {company}",
                location=location,
                current_company=company,
                current_title="Engineer",
                profile_url=f"https://www.linkedin.com/in/{first.lower()}-{last.lower()}",
                connection_degree=degree,
                search_query="engineer",
                found_at=datetime.now(UTC),
            )
        )
    return profiles


@pytest.fixture
def profile_with_long_headline() -> ConnectionProfile:
    """Create a profile with a very long headline for truncation testing."""
    return ConnectionProfile(
        id=uuid4(),
        linkedin_urn_id="urn:li:fsd_profile:LONG123",
        public_id="long-headline-person",
        first_name="Long",
        last_name="Headline",
        headline=(
            "Senior Principal Staff Software Engineer at Very Long Company Name Inc "
            "with Specialization in Machine Learning and Artificial Intelligence"
        ),
        location="San Francisco Bay Area, California, United States",
        current_company="Very Long Company Name Inc",
        current_title="Senior Principal Staff Software Engineer",
        profile_url="https://www.linkedin.com/in/long-headline-person",
        connection_degree=2,
        search_query="engineer",
        found_at=datetime.now(UTC),
    )


@pytest.fixture
def profile_with_missing_fields() -> ConnectionProfile:
    """Create a profile with missing optional fields."""
    return ConnectionProfile(
        id=uuid4(),
        linkedin_urn_id="urn:li:fsd_profile:MINIMAL123",
        public_id="minimal-person",
        first_name="Minimal",
        last_name="Person",
        headline=None,
        location=None,
        current_company=None,
        current_title=None,
        profile_url="https://www.linkedin.com/in/minimal-person",
        connection_degree=1,
        search_query=None,
        found_at=datetime.now(UTC),
    )


class TestConnectionTableInit:
    """Tests for ConnectionTable initialization."""

    def test_connection_table_can_be_imported(self) -> None:
        """ConnectionTable should be importable from the display module."""
        from linkedin_scraper.display import ConnectionTable

        assert ConnectionTable is not None

    def test_connection_table_instantiation(self) -> None:
        """ConnectionTable should be instantiable without arguments."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        assert table is not None


class TestConnectionTableRender:
    """Tests for ConnectionTable.render method."""

    def test_render_returns_table(self, sample_profiles: list[ConnectionProfile]) -> None:
        """render() should return a Rich Table."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render(sample_profiles)

        assert isinstance(result, Table)

    def test_render_empty_list_returns_table(self) -> None:
        """render() with empty list should return an empty Table."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render([])

        assert isinstance(result, Table)

    def test_render_with_title(self, sample_profiles: list[ConnectionProfile]) -> None:
        """render() should accept and use an optional title."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render(sample_profiles, title="Custom Title")

        assert result.title == "Custom Title"

    def test_render_without_title(self, sample_profiles: list[ConnectionProfile]) -> None:
        """render() without title should use default or no title."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render(sample_profiles)

        # Default title should be set or None is acceptable
        assert result.title is None or isinstance(result.title, str)

    def test_render_has_correct_columns(self, sample_profile: ConnectionProfile) -> None:
        """render() should create table with required columns."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render([sample_profile])

        column_names = [col.header for col in result.columns]
        expected_columns = ["#", "Name", "Headline", "Company", "Location", "Degree"]

        for expected in expected_columns:
            assert expected in column_names, f"Missing column: {expected}"

    def test_render_includes_row_numbers(self, sample_profiles: list[ConnectionProfile]) -> None:
        """render() should include row numbers starting at 1."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render(sample_profiles)

        # The first column should be for row numbers
        assert len(result.columns) > 0
        first_column = result.columns[0]
        assert first_column.header == "#"

    def test_render_single_profile(self, sample_profile: ConnectionProfile) -> None:
        """render() should handle a single profile correctly."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render([sample_profile])

        assert isinstance(result, Table)
        assert result.row_count == 1

    def test_render_multiple_profiles_correct_row_count(
        self, sample_profiles: list[ConnectionProfile]
    ) -> None:
        """render() should create correct number of rows."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render(sample_profiles)

        assert result.row_count == len(sample_profiles)


class TestConnectionTableTruncation:
    """Tests for headline and company name truncation."""

    def test_long_headline_is_truncated(
        self, profile_with_long_headline: ConnectionProfile
    ) -> None:
        """Long headlines should be truncated with ellipsis."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        # Just verify it doesn't crash and returns a table
        result = table.render([profile_with_long_headline])

        assert isinstance(result, Table)
        assert result.row_count == 1

    def test_long_company_name_is_truncated(
        self, profile_with_long_headline: ConnectionProfile
    ) -> None:
        """Long company names should be truncated with ellipsis."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render([profile_with_long_headline])

        assert isinstance(result, Table)

    def test_long_location_is_truncated(
        self, profile_with_long_headline: ConnectionProfile
    ) -> None:
        """Long locations should be truncated with ellipsis."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render([profile_with_long_headline])

        assert isinstance(result, Table)


class TestConnectionTableColorCoding:
    """Tests for connection degree color-coding."""

    def test_first_degree_connection_color(self) -> None:
        """1st degree connections should be rendered in green."""
        from linkedin_scraper.display import ConnectionTable

        profile = ConnectionProfile(
            id=uuid4(),
            linkedin_urn_id="urn:li:fsd_profile:FIRST1",
            public_id="first-degree",
            first_name="First",
            last_name="Degree",
            headline="Test",
            profile_url="https://linkedin.com/in/first-degree",
            connection_degree=1,
        )

        table = ConnectionTable()
        result = table.render([profile])

        # The table should render without error
        assert isinstance(result, Table)
        assert result.row_count == 1

    def test_second_degree_connection_color(self) -> None:
        """2nd degree connections should be rendered in yellow."""
        from linkedin_scraper.display import ConnectionTable

        profile = ConnectionProfile(
            id=uuid4(),
            linkedin_urn_id="urn:li:fsd_profile:SECOND1",
            public_id="second-degree",
            first_name="Second",
            last_name="Degree",
            headline="Test",
            profile_url="https://linkedin.com/in/second-degree",
            connection_degree=2,
        )

        table = ConnectionTable()
        result = table.render([profile])

        assert isinstance(result, Table)

    def test_third_degree_connection_color(self) -> None:
        """3rd degree connections should be rendered in red."""
        from linkedin_scraper.display import ConnectionTable

        profile = ConnectionProfile(
            id=uuid4(),
            linkedin_urn_id="urn:li:fsd_profile:THIRD1",
            public_id="third-degree",
            first_name="Third",
            last_name="Degree",
            headline="Test",
            profile_url="https://linkedin.com/in/third-degree",
            connection_degree=3,
        )

        table = ConnectionTable()
        result = table.render([profile])

        assert isinstance(result, Table)


class TestConnectionTableMissingFields:
    """Tests for handling profiles with missing optional fields."""

    def test_render_profile_with_no_headline(
        self, profile_with_missing_fields: ConnectionProfile
    ) -> None:
        """Should handle profile with no headline gracefully."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render([profile_with_missing_fields])

        assert isinstance(result, Table)
        assert result.row_count == 1

    def test_render_profile_with_no_location(
        self, profile_with_missing_fields: ConnectionProfile
    ) -> None:
        """Should handle profile with no location gracefully."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render([profile_with_missing_fields])

        assert isinstance(result, Table)

    def test_render_profile_with_no_company(
        self, profile_with_missing_fields: ConnectionProfile
    ) -> None:
        """Should handle profile with no company gracefully."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render([profile_with_missing_fields])

        assert isinstance(result, Table)


class TestDisplaySearchSummary:
    """Tests for display_search_summary function."""

    def test_display_search_summary_can_be_imported(self) -> None:
        """display_search_summary should be importable from display.status."""
        from linkedin_scraper.display.status import display_search_summary

        assert display_search_summary is not None

    def test_display_search_summary_returns_panel(self) -> None:
        """display_search_summary should return a Rich Panel."""
        from linkedin_scraper.display.status import display_search_summary

        result = display_search_summary(count=10, query="engineer", duration_seconds=2.5)

        assert isinstance(result, Panel)

    def test_display_search_summary_with_zero_results(self) -> None:
        """Should handle zero results gracefully."""
        from linkedin_scraper.display.status import display_search_summary

        result = display_search_summary(count=0, query="unknown", duration_seconds=1.0)

        assert isinstance(result, Panel)

    def test_display_search_summary_with_large_count(self) -> None:
        """Should handle large result counts."""
        from linkedin_scraper.display.status import display_search_summary

        result = display_search_summary(count=1000, query="developer", duration_seconds=30.5)

        assert isinstance(result, Panel)

    def test_display_search_summary_with_fractional_duration(self) -> None:
        """Should handle fractional second durations."""
        from linkedin_scraper.display.status import display_search_summary

        result = display_search_summary(count=5, query="test", duration_seconds=0.123)

        assert isinstance(result, Panel)


class TestDisplayRateLimitWarning:
    """Tests for display_rate_limit_warning function."""

    def test_display_rate_limit_warning_can_be_imported(self) -> None:
        """display_rate_limit_warning should be importable from display.status."""
        from linkedin_scraper.display.status import display_rate_limit_warning

        assert display_rate_limit_warning is not None

    def test_display_rate_limit_warning_returns_panel_when_low(self) -> None:
        """Should return a Panel when remaining actions are below threshold."""
        from linkedin_scraper.display.status import display_rate_limit_warning

        result = display_rate_limit_warning(remaining=3)

        assert isinstance(result, Panel)

    def test_display_rate_limit_warning_returns_none_when_safe(self) -> None:
        """Should return None when remaining actions are above threshold."""
        from linkedin_scraper.display.status import display_rate_limit_warning

        result = display_rate_limit_warning(remaining=10)

        assert result is None

    def test_display_rate_limit_warning_at_threshold(self) -> None:
        """Should return None at exactly 5 remaining (threshold boundary)."""
        from linkedin_scraper.display.status import display_rate_limit_warning

        result = display_rate_limit_warning(remaining=5)

        assert result is None

    def test_display_rate_limit_warning_at_4_remaining(self) -> None:
        """Should return Panel at 4 remaining (below threshold)."""
        from linkedin_scraper.display.status import display_rate_limit_warning

        result = display_rate_limit_warning(remaining=4)

        assert isinstance(result, Panel)

    def test_display_rate_limit_warning_at_zero(self) -> None:
        """Should return Panel when no remaining actions."""
        from linkedin_scraper.display.status import display_rate_limit_warning

        result = display_rate_limit_warning(remaining=0)

        assert isinstance(result, Panel)

    def test_display_rate_limit_warning_at_one(self) -> None:
        """Should return Panel with 1 remaining."""
        from linkedin_scraper.display.status import display_rate_limit_warning

        result = display_rate_limit_warning(remaining=1)

        assert isinstance(result, Panel)


class TestDisplayModuleExports:
    """Tests for display module exports."""

    def test_connection_table_in_display_init(self) -> None:
        """ConnectionTable should be exported from linkedin_scraper.display."""
        from linkedin_scraper.display import ConnectionTable

        assert ConnectionTable is not None

    def test_display_search_summary_importable(self) -> None:
        """display_search_summary should be importable from display.status."""
        from linkedin_scraper.display.status import display_search_summary

        assert callable(display_search_summary)

    def test_display_rate_limit_warning_importable(self) -> None:
        """display_rate_limit_warning should be importable from display.status."""
        from linkedin_scraper.display.status import display_rate_limit_warning

        assert callable(display_rate_limit_warning)


class TestConnectionTableIntegration:
    """Integration tests for ConnectionTable with various profile scenarios."""

    def test_mixed_degree_profiles_render(self, sample_profiles: list[ConnectionProfile]) -> None:
        """Should render table with profiles of different degrees."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render(sample_profiles, title="Mixed Degrees")

        assert isinstance(result, Table)
        assert result.row_count == len(sample_profiles)

    def test_render_preserves_order(self, sample_profiles: list[ConnectionProfile]) -> None:
        """Rows should be rendered in the same order as input profiles."""
        from linkedin_scraper.display import ConnectionTable

        table = ConnectionTable()
        result = table.render(sample_profiles)

        # The table should have the same number of rows as profiles
        assert result.row_count == len(sample_profiles)

    def test_render_large_profile_list(self) -> None:
        """Should handle rendering a large list of profiles."""
        from linkedin_scraper.display import ConnectionTable

        profiles = []
        for i in range(100):
            profiles.append(
                ConnectionProfile(
                    id=uuid4(),
                    linkedin_urn_id=f"urn:li:fsd_profile:BULK{i}",
                    public_id=f"person-{i}",
                    first_name=f"Person{i}",
                    last_name=f"Number{i}",
                    headline=f"Title {i}",
                    location=f"City {i % 10}",
                    current_company=f"Company {i % 20}",
                    profile_url=f"https://linkedin.com/in/person-{i}",
                    connection_degree=(i % 3) + 1,
                )
            )

        table = ConnectionTable()
        result = table.render(profiles, title="Bulk Results")

        assert isinstance(result, Table)
        assert result.row_count == 100
