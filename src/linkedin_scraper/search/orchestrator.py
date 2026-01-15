# ABOUTME: Coordinates between RateLimiter, LinkedInClient, and DatabaseService.
# ABOUTME: Provides search operations with rate limiting, company resolution, persistence.

from linkedin_scraper.auth import CookieManager
from linkedin_scraper.database import DatabaseService
from linkedin_scraper.linkedin.client import LinkedInClient
from linkedin_scraper.linkedin.exceptions import LinkedInAuthError
from linkedin_scraper.linkedin.mapper import map_search_result_to_profile
from linkedin_scraper.models import ActionType, ConnectionProfile
from linkedin_scraper.rate_limit.service import RateLimiter
from linkedin_scraper.search.filters import NetworkDepth, SearchFilter


class SearchOrchestrator:
    """Coordinates search operations between services.

    Handles the full search flow including:
    - Loading cookies from keyring
    - Checking and recording rate limits
    - Resolving company names to IDs
    - Executing LinkedIn searches
    - Mapping and persisting results
    """

    def __init__(
        self,
        db_service: DatabaseService,
        rate_limiter: RateLimiter,
        cookie_manager: CookieManager,
    ) -> None:
        """Initialize the search orchestrator.

        Args:
            db_service: Database service for persisting search results.
            rate_limiter: Rate limiter for enforcing API call limits.
            cookie_manager: Cookie manager for retrieving stored credentials.
        """
        self._db_service = db_service
        self._rate_limiter = rate_limiter
        self._cookie_manager = cookie_manager

    def execute_search(
        self,
        filter: SearchFilter,
        account: str = "default",
    ) -> list[ConnectionProfile]:
        """Execute a LinkedIn search with rate limiting and persistence.

        Args:
            filter: Search filter containing keywords, company IDs, etc.
            account: Account name to use for authentication.

        Returns:
            List of ConnectionProfile objects from the search results.

        Raises:
            LinkedInAuthError: If no cookie is found for the account.
            RateLimitExceeded: If the daily rate limit has been reached.
            LinkedInRateLimitError: If LinkedIn's rate limit is triggered.
        """
        # Load cookie for the account
        cookie = self._cookie_manager.get_cookie(account)
        if cookie is None:
            raise LinkedInAuthError(
                f"No cookie found for account '{account}'. "
                "Please run 'linkedin-scraper login' first."
            )

        # Check and record rate limit
        self._rate_limiter.check_and_wait(ActionType.SEARCH)

        # Create client and execute search
        client = LinkedInClient(cookie)
        raw_results = client.search_people(filter)

        # Map results to ConnectionProfile objects
        profiles = [
            map_search_result_to_profile(result, search_query=filter.keywords)
            for result in raw_results
        ]

        # Save results to database
        for profile in profiles:
            self._db_service.save_connection(profile)

        return profiles

    def execute_search_with_company_name(
        self,
        keywords: str,
        company_name: str | None = None,
        location: str | None = None,
        network_depths: list[NetworkDepth] | None = None,
        limit: int = 100,
        account: str = "default",
    ) -> list[ConnectionProfile]:
        """Execute a search with company name resolution.

        This is a higher-level method that resolves company names to IDs
        before executing the search.

        Args:
            keywords: Search keywords (job title, skills, etc.).
            company_name: Optional company name to filter by (will be resolved to ID).
            location: Optional location filter.
            network_depths: Connection degrees to include (default: 1st and 2nd).
            limit: Maximum number of results (default: 100).
            account: Account name to use for authentication.

        Returns:
            List of ConnectionProfile objects from the search results.

        Raises:
            LinkedInAuthError: If no cookie is found for the account.
            RateLimitExceeded: If the daily rate limit has been reached.
            LinkedInRateLimitError: If LinkedIn's rate limit is triggered.
        """
        # Load cookie for the account
        cookie = self._cookie_manager.get_cookie(account)
        if cookie is None:
            raise LinkedInAuthError(
                f"No cookie found for account '{account}'. "
                "Please run 'linkedin-scraper login' first."
            )

        # Create client for company resolution
        client = LinkedInClient(cookie)

        # Resolve company name to ID if provided
        company_ids: list[str] | None = None
        if company_name:
            company_id = client.resolve_company_id(company_name)
            if company_id:
                company_ids = [company_id]
            # If company not found, proceed without company filter

        # Build search filter
        if network_depths is None:
            network_depths = [NetworkDepth.FIRST, NetworkDepth.SECOND]

        filter = SearchFilter(
            keywords=keywords,
            current_company_ids=company_ids,
            regions=[location] if location else None,
            network_depths=network_depths,
            limit=limit,
        )

        # Check and record rate limit
        self._rate_limiter.check_and_wait(ActionType.SEARCH)

        # Execute search
        raw_results = client.search_people(filter)

        # Map results to ConnectionProfile objects
        profiles = [
            map_search_result_to_profile(result, search_query=keywords) for result in raw_results
        ]

        # Save results to database
        for profile in profiles:
            self._db_service.save_connection(profile)

        return profiles

    def get_remaining_actions(self) -> int:
        """Get the number of remaining search actions allowed today.

        Returns:
            Number of actions remaining before the daily limit is reached.
        """
        return self._rate_limiter.get_remaining_actions()
