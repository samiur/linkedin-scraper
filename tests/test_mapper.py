# ABOUTME: Tests for LinkedIn search result to ConnectionProfile mapping.
# ABOUTME: Verifies correct extraction and transformation of LinkedIn API responses.

from datetime import UTC, datetime

from linkedin_scraper.linkedin.mapper import map_search_result_to_profile
from linkedin_scraper.models.connection import ConnectionProfile


class TestMapSearchResultToProfile:
    """Tests for the map_search_result_to_profile function."""

    def test_maps_basic_profile_fields(self) -> None:
        """Should map basic fields from search result to ConnectionProfile."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "john-doe",
            "name": "John Doe",
            "jobtitle": "Senior Software Engineer",
            "location": "San Francisco Bay Area",
        }

        profile = map_search_result_to_profile(result)

        assert profile.linkedin_urn_id == "ACoAABCDEFGHIJ"
        assert profile.public_id == "john-doe"
        assert profile.first_name == "John"
        assert profile.last_name == "Doe"
        assert profile.headline == "Senior Software Engineer"
        assert profile.location == "San Francisco Bay Area"

    def test_maps_profile_url(self) -> None:
        """Should construct LinkedIn profile URL from public_id."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "jane-smith-123",
            "name": "Jane Smith",
        }

        profile = map_search_result_to_profile(result)

        assert profile.profile_url == "https://www.linkedin.com/in/jane-smith-123"

    def test_maps_first_degree_connection(self) -> None:
        """Should map DISTANCE_1 to connection_degree 1."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
            "distance": "DISTANCE_1",
        }

        profile = map_search_result_to_profile(result)

        assert profile.connection_degree == 1

    def test_maps_second_degree_connection(self) -> None:
        """Should map DISTANCE_2 to connection_degree 2."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
            "distance": "DISTANCE_2",
        }

        profile = map_search_result_to_profile(result)

        assert profile.connection_degree == 2

    def test_maps_third_degree_connection(self) -> None:
        """Should map DISTANCE_3 or OUT_OF_NETWORK to connection_degree 3."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
            "distance": "DISTANCE_3",
        }

        profile = map_search_result_to_profile(result)

        assert profile.connection_degree == 3

    def test_maps_out_of_network_to_third_degree(self) -> None:
        """Should map OUT_OF_NETWORK distance to connection_degree 3."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
            "distance": "OUT_OF_NETWORK",
        }

        profile = map_search_result_to_profile(result)

        assert profile.connection_degree == 3

    def test_defaults_missing_distance_to_third_degree(self) -> None:
        """Should default to connection_degree 3 when distance is missing."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
        }

        profile = map_search_result_to_profile(result)

        assert profile.connection_degree == 3

    def test_sets_search_query_when_provided(self) -> None:
        """Should set search_query when provided."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
        }

        profile = map_search_result_to_profile(result, search_query="software engineer")

        assert profile.search_query == "software engineer"

    def test_search_query_defaults_to_none(self) -> None:
        """Should default search_query to None when not provided."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
        }

        profile = map_search_result_to_profile(result)

        assert profile.search_query is None

    def test_sets_found_at_timestamp(self) -> None:
        """Should set found_at to current timestamp."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
        }

        before = datetime.now(UTC)
        profile = map_search_result_to_profile(result)
        after = datetime.now(UTC)

        assert before <= profile.found_at <= after

    def test_handles_single_name(self) -> None:
        """Should handle single-word names gracefully."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "madonna",
            "name": "Madonna",
        }

        profile = map_search_result_to_profile(result)

        assert profile.first_name == "Madonna"
        assert profile.last_name == ""

    def test_handles_multi_part_names(self) -> None:
        """Should handle names with multiple parts."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "jose-garcia",
            "name": "Jose Maria Garcia Lopez",
        }

        profile = map_search_result_to_profile(result)

        assert profile.first_name == "Jose"
        assert profile.last_name == "Maria Garcia Lopez"

    def test_handles_missing_headline(self) -> None:
        """Should handle missing headline/jobtitle gracefully."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
        }

        profile = map_search_result_to_profile(result)

        assert profile.headline is None

    def test_handles_missing_location(self) -> None:
        """Should handle missing location gracefully."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
        }

        profile = map_search_result_to_profile(result)

        assert profile.location is None

    def test_returns_connection_profile_instance(self) -> None:
        """Should return a ConnectionProfile model instance."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "Test User",
        }

        profile = map_search_result_to_profile(result)

        assert isinstance(profile, ConnectionProfile)

    def test_maps_complete_profile_with_all_fields(self) -> None:
        """Should correctly map a complete search result with all fields."""
        result = {
            "urn_id": "ACoAAB123456XYZ",
            "public_id": "alice-johnson-eng",
            "name": "Alice Johnson",
            "jobtitle": "Staff Engineer at TechCorp",
            "location": "New York City Metropolitan Area",
            "distance": "DISTANCE_2",
        }

        profile = map_search_result_to_profile(result, search_query="staff engineer")

        assert profile.linkedin_urn_id == "ACoAAB123456XYZ"
        assert profile.public_id == "alice-johnson-eng"
        assert profile.first_name == "Alice"
        assert profile.last_name == "Johnson"
        assert profile.headline == "Staff Engineer at TechCorp"
        assert profile.location == "New York City Metropolitan Area"
        assert profile.profile_url == "https://www.linkedin.com/in/alice-johnson-eng"
        assert profile.connection_degree == 2
        assert profile.search_query == "staff engineer"

    def test_handles_empty_name(self) -> None:
        """Should handle empty name field gracefully."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "",
        }

        profile = map_search_result_to_profile(result)

        assert profile.first_name == ""
        assert profile.last_name == ""

    def test_strips_whitespace_from_names(self) -> None:
        """Should strip leading/trailing whitespace from name parts."""
        result = {
            "urn_id": "ACoAABCDEFGHIJ",
            "public_id": "test-user",
            "name": "  John   Doe  ",
        }

        profile = map_search_result_to_profile(result)

        assert profile.first_name == "John"
        assert profile.last_name == "Doe"


class TestMapCompanyResult:
    """Tests for the map_company_result function."""

    def test_maps_basic_company_fields(self) -> None:
        """Should map basic fields from company search result."""
        from linkedin_scraper.linkedin.mapper import map_company_result

        result = {
            "urn_id": "urn:li:company:1441",
            "name": "Google",
            "industry": "Internet",
            "staff_count": 150000,
        }

        mapped = map_company_result(result)

        assert mapped["company_id"] == "1441"
        assert mapped["name"] == "Google"
        assert mapped["industry"] == "Internet"
        assert mapped["employee_count"] == 150000

    def test_extracts_company_id_from_urn(self) -> None:
        """Should extract numeric company ID from URN format."""
        from linkedin_scraper.linkedin.mapper import map_company_result

        result = {
            "urn_id": "urn:li:company:28627158",
            "name": "Anthropic",
        }

        mapped = map_company_result(result)

        assert mapped["company_id"] == "28627158"

    def test_handles_plain_numeric_id(self) -> None:
        """Should handle plain numeric company IDs."""
        from linkedin_scraper.linkedin.mapper import map_company_result

        result = {
            "urn_id": "10667",
            "name": "Meta",
        }

        mapped = map_company_result(result)

        assert mapped["company_id"] == "10667"

    def test_handles_missing_industry(self) -> None:
        """Should handle missing industry gracefully."""
        from linkedin_scraper.linkedin.mapper import map_company_result

        result = {
            "urn_id": "urn:li:company:12345",
            "name": "Startup Inc",
        }

        mapped = map_company_result(result)

        assert mapped["company_id"] == "12345"
        assert mapped["name"] == "Startup Inc"
        assert mapped["industry"] is None

    def test_handles_missing_employee_count(self) -> None:
        """Should handle missing employee count gracefully."""
        from linkedin_scraper.linkedin.mapper import map_company_result

        result = {
            "urn_id": "urn:li:company:12345",
            "name": "Small Co",
        }

        mapped = map_company_result(result)

        assert mapped["employee_count"] is None

    def test_handles_missing_urn_id(self) -> None:
        """Should handle missing urn_id and return None for company_id."""
        from linkedin_scraper.linkedin.mapper import map_company_result

        result = {
            "name": "Unknown Company",
        }

        mapped = map_company_result(result)

        assert mapped["company_id"] is None
        assert mapped["name"] == "Unknown Company"

    def test_handles_empty_urn_id(self) -> None:
        """Should handle empty urn_id string."""
        from linkedin_scraper.linkedin.mapper import map_company_result

        result = {
            "urn_id": "",
            "name": "Company",
        }

        mapped = map_company_result(result)

        assert mapped["company_id"] is None

    def test_maps_complete_company_result(self) -> None:
        """Should correctly map a complete company search result."""
        from linkedin_scraper.linkedin.mapper import map_company_result

        result = {
            "urn_id": "urn:li:company:162479",
            "name": "Apple Inc.",
            "industry": "Consumer Electronics",
            "staff_count": 164000,
        }

        mapped = map_company_result(result)

        assert mapped["company_id"] == "162479"
        assert mapped["name"] == "Apple Inc."
        assert mapped["industry"] == "Consumer Electronics"
        assert mapped["employee_count"] == 164000
