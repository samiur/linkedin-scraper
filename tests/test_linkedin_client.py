# ABOUTME: Tests for the LinkedIn client wrapper.
# ABOUTME: Tests authentication, session validation, and profile retrieval with mocked API.

from unittest.mock import MagicMock, patch

import pytest

from linkedin_scraper.linkedin.client import LinkedInClient
from linkedin_scraper.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInError,
    LinkedInRateLimitError,
)


class TestLinkedInClient:
    """Tests for the LinkedInClient class."""

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_init_creates_client_with_cookie(self, mock_linkedin_class: MagicMock) -> None:
        """LinkedInClient should create underlying client and set cookies manually."""
        mock_instance = MagicMock()
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie_value", jsessionid="ajax:123")

        # Should create client with authenticate=False (cookies set manually)
        mock_linkedin_class.assert_called_once()
        call_kwargs = mock_linkedin_class.call_args.kwargs
        assert call_kwargs.get("authenticate") is False
        assert call_kwargs.get("refresh_cookies") is False
        assert client._client == mock_instance

        # Verify cookies were set on the session
        session_cookies = mock_instance.client.session.cookies
        session_cookies.set.assert_any_call("li_at", "test_cookie_value", domain=".linkedin.com")
        session_cookies.set.assert_any_call("JSESSIONID", '"ajax:123"', domain=".linkedin.com")

        # Verify csrf-token header was set
        mock_instance.client.session.headers.__setitem__.assert_called_with(
            "csrf-token", "ajax:123"
        )

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_init_raises_auth_error_on_invalid_cookie(self, mock_linkedin_class: MagicMock) -> None:
        """LinkedInClient should raise LinkedInAuthError if cookie is invalid during init."""
        mock_linkedin_class.side_effect = Exception("CHALLENGE")

        with pytest.raises(LinkedInAuthError) as exc_info:
            LinkedInClient(li_at="invalid_cookie")

        assert "CHALLENGE" in str(exc_info.value) or "authentication" in str(exc_info.value).lower()

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_validate_session_returns_true_for_valid_session(
        self, mock_linkedin_class: MagicMock
    ) -> None:
        """validate_session should return True when session is valid."""
        mock_instance = MagicMock()
        mock_instance.get_user_profile.return_value = {
            "miniProfile": {"publicIdentifier": "johndoe"}
        }
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="valid_cookie")
        result = client.validate_session()

        assert result is True
        mock_instance.get_user_profile.assert_called_once()

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_validate_session_returns_false_when_api_fails(
        self, mock_linkedin_class: MagicMock
    ) -> None:
        """validate_session should return False when API call fails."""
        mock_instance = MagicMock()
        mock_instance.get_user_profile.side_effect = Exception("Session invalid")
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="expired_cookie")
        result = client.validate_session()

        assert result is False

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_validate_session_returns_false_when_profile_empty(
        self, mock_linkedin_class: MagicMock
    ) -> None:
        """validate_session should return False when profile response is empty."""
        mock_instance = MagicMock()
        mock_instance.get_user_profile.return_value = None
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="some_cookie")
        result = client.validate_session()

        assert result is False

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_get_profile_id_returns_public_identifier(self, mock_linkedin_class: MagicMock) -> None:
        """get_profile_id should return the logged-in user's public identifier."""
        mock_instance = MagicMock()
        mock_instance.get_user_profile.return_value = {
            "miniProfile": {"publicIdentifier": "john-doe-123"}
        }
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="valid_cookie")
        profile_id = client.get_profile_id()

        assert profile_id == "john-doe-123"

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_get_profile_id_returns_none_when_not_found(
        self, mock_linkedin_class: MagicMock
    ) -> None:
        """get_profile_id should return None when profile ID cannot be found."""
        mock_instance = MagicMock()
        mock_instance.get_user_profile.return_value = {}
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="valid_cookie")
        profile_id = client.get_profile_id()

        assert profile_id is None

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_get_profile_id_returns_none_on_api_error(self, mock_linkedin_class: MagicMock) -> None:
        """get_profile_id should return None when API call fails."""
        mock_instance = MagicMock()
        mock_instance.get_user_profile.side_effect = Exception("API Error")
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="valid_cookie")
        profile_id = client.get_profile_id()

        assert profile_id is None

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_get_profile_id_handles_nested_profile_structure(
        self, mock_linkedin_class: MagicMock
    ) -> None:
        """get_profile_id should handle different profile response structures."""
        mock_instance = MagicMock()
        mock_instance.get_user_profile.return_value = {
            "plainId": "plain-id-value",
            "miniProfile": {"publicIdentifier": "mini-profile-id"},
        }
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="valid_cookie")
        profile_id = client.get_profile_id()

        # Should prefer miniProfile.publicIdentifier
        assert profile_id == "mini-profile-id"


class TestLinkedInExceptions:
    """Tests for LinkedIn exception classes."""

    def test_linkedin_error_is_base_exception(self) -> None:
        """LinkedInError should be the base exception for all LinkedIn errors."""
        error = LinkedInError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_linkedin_auth_error_inherits_from_linkedin_error(self) -> None:
        """LinkedInAuthError should inherit from LinkedInError."""
        error = LinkedInAuthError("Authentication failed")
        assert isinstance(error, LinkedInError)
        assert str(error) == "Authentication failed"

    def test_linkedin_rate_limit_error_inherits_from_linkedin_error(self) -> None:
        """LinkedInRateLimitError should inherit from LinkedInError."""
        error = LinkedInRateLimitError("Rate limited by LinkedIn")
        assert isinstance(error, LinkedInError)
        assert str(error) == "Rate limited by LinkedIn"


class TestLinkedInClientErrorHandling:
    """Tests for error handling in LinkedInClient."""

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_init_raises_rate_limit_error_on_429(self, mock_linkedin_class: MagicMock) -> None:
        """LinkedInClient should raise LinkedInRateLimitError on rate limit responses."""
        # Simulate a rate limit response from LinkedIn
        mock_linkedin_class.side_effect = Exception("429 Too Many Requests")

        with pytest.raises(LinkedInRateLimitError):
            LinkedInClient(li_at="test_cookie")

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_init_raises_auth_error_on_401(self, mock_linkedin_class: MagicMock) -> None:
        """LinkedInClient should raise LinkedInAuthError on authentication failures."""
        mock_linkedin_class.side_effect = Exception("401 Unauthorized")

        with pytest.raises(LinkedInAuthError):
            LinkedInClient(li_at="test_cookie")

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_init_wraps_unknown_errors_in_linkedin_error(
        self, mock_linkedin_class: MagicMock
    ) -> None:
        """LinkedInClient should wrap unknown exceptions in LinkedInError."""
        mock_linkedin_class.side_effect = Exception("Unknown network error")

        with pytest.raises(LinkedInError):
            LinkedInClient(li_at="test_cookie")


class TestLinkedInClientSearchPeople:
    """Tests for LinkedInClient.search_people method."""

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_people_with_keywords_only(self, mock_linkedin_class: MagicMock) -> None:
        """search_people should call underlying API with keywords."""
        mock_instance = MagicMock()
        mock_instance.search_people.return_value = [
            {"urn_id": "abc123", "name": "John Doe"},
            {"urn_id": "def456", "name": "Jane Smith"},
        ]
        mock_linkedin_class.return_value = mock_instance

        from linkedin_scraper.search.filters import SearchFilter

        client = LinkedInClient(li_at="test_cookie")
        search_filter = SearchFilter(keywords="software engineer")
        results = client.search_people(search_filter)

        assert len(results) == 2
        mock_instance.search_people.assert_called_once()
        call_kwargs = mock_instance.search_people.call_args.kwargs
        assert call_kwargs["keywords"] == "software engineer"
        assert call_kwargs["limit"] == 100

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_people_with_company_ids(self, mock_linkedin_class: MagicMock) -> None:
        """search_people should pass company IDs to underlying API."""
        mock_instance = MagicMock()
        mock_instance.search_people.return_value = []
        mock_linkedin_class.return_value = mock_instance

        from linkedin_scraper.search.filters import SearchFilter

        client = LinkedInClient(li_at="test_cookie")
        search_filter = SearchFilter(
            keywords="engineer",
            current_company_ids=["12345", "67890"],
        )
        client.search_people(search_filter)

        call_kwargs = mock_instance.search_people.call_args.kwargs
        assert call_kwargs["current_company"] == ["12345", "67890"]

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_people_with_network_depths(self, mock_linkedin_class: MagicMock) -> None:
        """search_people should convert NetworkDepth enums to API format."""
        mock_instance = MagicMock()
        mock_instance.search_people.return_value = []
        mock_linkedin_class.return_value = mock_instance

        from linkedin_scraper.search.filters import NetworkDepth, SearchFilter

        client = LinkedInClient(li_at="test_cookie")
        search_filter = SearchFilter(
            keywords="manager",
            network_depths=[NetworkDepth.FIRST, NetworkDepth.SECOND],
        )
        client.search_people(search_filter)

        call_kwargs = mock_instance.search_people.call_args.kwargs
        assert call_kwargs["network_depths"] == ["F", "S"]

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_people_with_regions(self, mock_linkedin_class: MagicMock) -> None:
        """search_people should pass region filters to underlying API."""
        mock_instance = MagicMock()
        mock_instance.search_people.return_value = []
        mock_linkedin_class.return_value = mock_instance

        from linkedin_scraper.search.filters import SearchFilter

        client = LinkedInClient(li_at="test_cookie")
        search_filter = SearchFilter(
            keywords="developer",
            regions=["us:0", "uk:0"],
        )
        client.search_people(search_filter)

        call_kwargs = mock_instance.search_people.call_args.kwargs
        assert call_kwargs["regions"] == ["us:0", "uk:0"]

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_people_with_custom_limit(self, mock_linkedin_class: MagicMock) -> None:
        """search_people should respect custom result limit."""
        mock_instance = MagicMock()
        mock_instance.search_people.return_value = []
        mock_linkedin_class.return_value = mock_instance

        from linkedin_scraper.search.filters import SearchFilter

        client = LinkedInClient(li_at="test_cookie")
        search_filter = SearchFilter(keywords="analyst", limit=50)
        client.search_people(search_filter)

        call_kwargs = mock_instance.search_people.call_args.kwargs
        assert call_kwargs["limit"] == 50

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_people_returns_raw_dicts(self, mock_linkedin_class: MagicMock) -> None:
        """search_people should return raw result dictionaries."""
        expected_results = [
            {
                "urn_id": "ACoAABCDEFG",
                "public_id": "johndoe",
                "distance": "DISTANCE_1",
                "jobtitle": "Senior Engineer",
                "location": "San Francisco, CA",
                "name": "John Doe",
            },
        ]
        mock_instance = MagicMock()
        mock_instance.search_people.return_value = expected_results
        mock_linkedin_class.return_value = mock_instance

        from linkedin_scraper.search.filters import SearchFilter

        client = LinkedInClient(li_at="test_cookie")
        search_filter = SearchFilter(keywords="engineer")
        results = client.search_people(search_filter)

        assert results == expected_results
        assert results[0]["urn_id"] == "ACoAABCDEFG"

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_people_handles_api_error(self, mock_linkedin_class: MagicMock) -> None:
        """search_people should wrap API errors appropriately."""
        mock_instance = MagicMock()
        mock_instance.search_people.side_effect = Exception("429 Rate limited")
        mock_linkedin_class.return_value = mock_instance

        from linkedin_scraper.search.filters import SearchFilter

        client = LinkedInClient(li_at="test_cookie")
        search_filter = SearchFilter(keywords="engineer")

        with pytest.raises(LinkedInRateLimitError):
            client.search_people(search_filter)

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_people_with_all_filters(self, mock_linkedin_class: MagicMock) -> None:
        """search_people should pass all filter parameters correctly."""
        mock_instance = MagicMock()
        mock_instance.search_people.return_value = []
        mock_linkedin_class.return_value = mock_instance

        from linkedin_scraper.search.filters import NetworkDepth, SearchFilter

        client = LinkedInClient(li_at="test_cookie")
        search_filter = SearchFilter(
            keywords="product manager",
            network_depths=[NetworkDepth.FIRST, NetworkDepth.SECOND, NetworkDepth.THIRD],
            current_company_ids=["111", "222"],
            regions=["us:0"],
            limit=200,
        )
        client.search_people(search_filter)

        call_kwargs = mock_instance.search_people.call_args.kwargs
        assert call_kwargs["keywords"] == "product manager"
        assert call_kwargs["network_depths"] == ["F", "S", "O"]
        assert call_kwargs["current_company"] == ["111", "222"]
        assert call_kwargs["regions"] == ["us:0"]
        assert call_kwargs["limit"] == 200


class TestLinkedInClientSearchCompanies:
    """Tests for LinkedInClient.search_companies method."""

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_companies_with_name(self, mock_linkedin_class: MagicMock) -> None:
        """search_companies should call underlying API with company name."""
        mock_instance = MagicMock()
        mock_instance.search_companies.return_value = [
            {"name": "Google", "urn_id": "urn:li:company:1441"},
            {"name": "Google Cloud", "urn_id": "urn:li:company:2374003"},
        ]
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")
        results = client.search_companies("Google")

        assert len(results) == 2
        mock_instance.search_companies.assert_called_once()
        call_kwargs = mock_instance.search_companies.call_args.kwargs
        assert call_kwargs["keywords"] == "Google"

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_companies_with_custom_limit(self, mock_linkedin_class: MagicMock) -> None:
        """search_companies should respect custom result limit."""
        mock_instance = MagicMock()
        mock_instance.search_companies.return_value = []
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")
        client.search_companies("Acme", limit=3)

        call_kwargs = mock_instance.search_companies.call_args.kwargs
        assert call_kwargs["limit"] == 3

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_companies_default_limit(self, mock_linkedin_class: MagicMock) -> None:
        """search_companies should use default limit of 5."""
        mock_instance = MagicMock()
        mock_instance.search_companies.return_value = []
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")
        client.search_companies("Microsoft")

        call_kwargs = mock_instance.search_companies.call_args.kwargs
        assert call_kwargs["limit"] == 5

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_companies_returns_raw_dicts(self, mock_linkedin_class: MagicMock) -> None:
        """search_companies should return raw result dictionaries."""
        expected_results = [
            {
                "name": "Apple Inc.",
                "urn_id": "urn:li:company:162479",
                "industry": "Consumer Electronics",
                "staff_count": 150000,
            },
        ]
        mock_instance = MagicMock()
        mock_instance.search_companies.return_value = expected_results
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")
        results = client.search_companies("Apple")

        assert results == expected_results
        assert results[0]["name"] == "Apple Inc."

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_companies_handles_api_error(self, mock_linkedin_class: MagicMock) -> None:
        """search_companies should wrap API errors appropriately."""
        mock_instance = MagicMock()
        mock_instance.search_companies.side_effect = Exception("429 Rate limited")
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")

        with pytest.raises(LinkedInRateLimitError):
            client.search_companies("Test Company")

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_search_companies_handles_auth_error(self, mock_linkedin_class: MagicMock) -> None:
        """search_companies should raise LinkedInAuthError on auth failures."""
        mock_instance = MagicMock()
        mock_instance.search_companies.side_effect = Exception("401 Unauthorized")
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")

        with pytest.raises(LinkedInAuthError):
            client.search_companies("Test Company")


class TestLinkedInClientResolveCompanyId:
    """Tests for LinkedInClient.resolve_company_id method."""

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_resolve_company_id_returns_best_match(self, mock_linkedin_class: MagicMock) -> None:
        """resolve_company_id should return the ID of the first match."""
        mock_instance = MagicMock()
        mock_instance.search_companies.return_value = [
            {"name": "Google", "urn_id": "urn:li:company:1441"},
            {"name": "Google Cloud", "urn_id": "urn:li:company:2374003"},
        ]
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")
        company_id = client.resolve_company_id("Google")

        assert company_id == "1441"

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_resolve_company_id_returns_none_when_no_match(
        self, mock_linkedin_class: MagicMock
    ) -> None:
        """resolve_company_id should return None when no companies found."""
        mock_instance = MagicMock()
        mock_instance.search_companies.return_value = []
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")
        company_id = client.resolve_company_id("NonexistentCompany12345")

        assert company_id is None

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_resolve_company_id_extracts_numeric_id_from_urn(
        self, mock_linkedin_class: MagicMock
    ) -> None:
        """resolve_company_id should extract numeric ID from URN format."""
        mock_instance = MagicMock()
        mock_instance.search_companies.return_value = [
            {"name": "Anthropic", "urn_id": "urn:li:company:28627158"},
        ]
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")
        company_id = client.resolve_company_id("Anthropic")

        assert company_id == "28627158"

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_resolve_company_id_handles_plain_numeric_id(
        self, mock_linkedin_class: MagicMock
    ) -> None:
        """resolve_company_id should handle plain numeric company IDs."""
        mock_instance = MagicMock()
        mock_instance.search_companies.return_value = [
            {"name": "Meta", "urn_id": "10667"},
        ]
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")
        company_id = client.resolve_company_id("Meta")

        assert company_id == "10667"

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_resolve_company_id_returns_none_when_missing_urn(
        self, mock_linkedin_class: MagicMock
    ) -> None:
        """resolve_company_id should return None when result has no urn_id."""
        mock_instance = MagicMock()
        mock_instance.search_companies.return_value = [
            {"name": "Some Company"},  # Missing urn_id
        ]
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")
        company_id = client.resolve_company_id("Some Company")

        assert company_id is None

    @patch("linkedin_scraper.linkedin.client.Linkedin")
    def test_resolve_company_id_handles_api_error(self, mock_linkedin_class: MagicMock) -> None:
        """resolve_company_id should wrap API errors appropriately."""
        mock_instance = MagicMock()
        mock_instance.search_companies.side_effect = Exception("429 Rate limited")
        mock_linkedin_class.return_value = mock_instance

        client = LinkedInClient(li_at="test_cookie")

        with pytest.raises(LinkedInRateLimitError):
            client.resolve_company_id("Test")
