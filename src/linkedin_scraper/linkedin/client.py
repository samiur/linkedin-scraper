# ABOUTME: LinkedIn API client wrapper for authenticated operations.
# ABOUTME: Wraps linkedin-api library and provides clean interface with proper error handling.

from typing import TYPE_CHECKING, Any

from linkedin_api import Linkedin

from linkedin_scraper.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInError,
    LinkedInRateLimitError,
)
from linkedin_scraper.linkedin.mapper import _extract_company_id_from_urn

if TYPE_CHECKING:
    from linkedin_scraper.search.filters import SearchFilter


class LinkedInClient:
    """Wrapper around linkedin-api library for authenticated LinkedIn operations."""

    def __init__(self, cookie: str) -> None:
        """Create an authenticated LinkedIn client using a li_at cookie.

        Args:
            cookie: The li_at cookie value for authentication.

        Raises:
            LinkedInAuthError: If the cookie is invalid or authentication fails.
            LinkedInRateLimitError: If LinkedIn rate limiting is triggered.
            LinkedInError: For other unexpected errors.
        """
        try:
            self._client: Linkedin = Linkedin(
                cookies={"li_at": cookie},
                refresh_cookies=False,
            )
        except Exception as e:
            raise self._wrap_exception(e) from e

    def validate_session(self) -> bool:
        """Test if the current session is valid by making a simple API call.

        Returns:
            True if the session is valid, False otherwise.
        """
        try:
            profile = self._client.get_user_profile()
            return profile is not None and len(profile) > 0
        except Exception:
            return False

    def get_profile_id(self) -> str | None:
        """Get the logged-in user's profile ID (public identifier).

        Returns:
            The user's public profile identifier, or None if it cannot be retrieved.
        """
        try:
            profile = self._client.get_user_profile()
            if not profile:
                return None

            mini_profile = profile.get("miniProfile")
            if isinstance(mini_profile, dict):
                public_id = mini_profile.get("publicIdentifier")
                if public_id:
                    return str(public_id)

            return None
        except Exception:
            return None

    def _wrap_exception(self, exception: Exception) -> LinkedInError:
        """Convert a generic exception to the appropriate LinkedIn exception type.

        Args:
            exception: The original exception from the linkedin-api library.

        Returns:
            The appropriate LinkedInError subclass for the exception.
        """
        error_message = str(exception).lower()

        if "429" in error_message or "rate" in error_message:
            return LinkedInRateLimitError(str(exception))

        if (
            "401" in error_message
            or "unauthorized" in error_message
            or "challenge" in error_message
            or "auth" in error_message
        ):
            return LinkedInAuthError(str(exception))

        return LinkedInError(str(exception))

    def _get_raw_client(self) -> Any:
        """Get the underlying linkedin-api client for advanced operations.

        This is intended for internal use by other modules that need direct access.

        Returns:
            The underlying Linkedin client instance.
        """
        return self._client

    def search_people(self, filter: "SearchFilter") -> list[dict[str, Any]]:
        """Search for people on LinkedIn based on filter criteria.

        Args:
            filter: SearchFilter containing search parameters like keywords,
                company IDs, network depths, regions, and result limit.

        Returns:
            List of raw result dictionaries from the LinkedIn API.

        Raises:
            LinkedInAuthError: If authentication has expired.
            LinkedInRateLimitError: If LinkedIn rate limiting is triggered.
            LinkedInError: For other unexpected errors.
        """
        try:
            # Convert NetworkDepth enums to string values expected by linkedin-api
            network_depths = [depth.value for depth in filter.network_depths]

            results: list[dict[str, Any]] = self._client.search_people(
                keywords=filter.keywords,
                current_company=filter.current_company_ids,
                network_depths=network_depths,
                regions=filter.regions,
                limit=filter.limit,
            )
            return results
        except Exception as e:
            raise self._wrap_exception(e) from e

    def search_companies(self, name: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for companies on LinkedIn by name.

        Args:
            name: Company name to search for.
            limit: Maximum number of results to return (default: 5).

        Returns:
            List of raw result dictionaries from the LinkedIn API.

        Raises:
            LinkedInAuthError: If authentication has expired.
            LinkedInRateLimitError: If LinkedIn rate limiting is triggered.
            LinkedInError: For other unexpected errors.
        """
        try:
            results: list[dict[str, Any]] = self._client.search_companies(
                keywords=name,
                limit=limit,
            )
            return results
        except Exception as e:
            raise self._wrap_exception(e) from e

    def resolve_company_id(self, name: str) -> str | None:
        """Resolve a company name to its LinkedIn company ID.

        Searches for companies by name and returns the ID of the best match
        (first result).

        Args:
            name: Company name to search for.

        Returns:
            The numeric company ID of the best match, or None if no match found.

        Raises:
            LinkedInAuthError: If authentication has expired.
            LinkedInRateLimitError: If LinkedIn rate limiting is triggered.
            LinkedInError: For other unexpected errors.
        """
        results = self.search_companies(name, limit=1)
        if not results:
            return None

        first_result = results[0]
        urn_id = first_result.get("urn_id")
        if not urn_id:
            return None

        return _extract_company_id_from_urn(urn_id)
