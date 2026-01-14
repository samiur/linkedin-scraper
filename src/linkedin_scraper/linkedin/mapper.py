# ABOUTME: Maps LinkedIn API search results to ConnectionProfile models.
# ABOUTME: Handles data extraction and transformation from raw API responses.

from datetime import UTC, datetime
from typing import Any

from linkedin_scraper.models.connection import ConnectionProfile


def map_search_result_to_profile(
    result: dict[str, Any],
    search_query: str | None = None,
) -> ConnectionProfile:
    """Map a LinkedIn search result dictionary to a ConnectionProfile model.

    Args:
        result: Raw dictionary from linkedin-api search_people response.
        search_query: Optional search query string that found this profile.

    Returns:
        ConnectionProfile model populated with data from the search result.
    """
    urn_id = result.get("urn_id", "")
    public_id = result.get("public_id", "")

    first_name, last_name = _parse_name(result.get("name", ""))

    headline = result.get("jobtitle")
    location = result.get("location")

    profile_url = f"https://www.linkedin.com/in/{public_id}"

    connection_degree = _parse_connection_degree(result.get("distance"))

    return ConnectionProfile(
        linkedin_urn_id=urn_id,
        public_id=public_id,
        first_name=first_name,
        last_name=last_name,
        headline=headline,
        location=location,
        profile_url=profile_url,
        connection_degree=connection_degree,
        search_query=search_query,
        found_at=datetime.now(UTC),
    )


def _parse_name(full_name: str) -> tuple[str, str]:
    """Parse a full name into first and last name components.

    Args:
        full_name: The full name string to parse.

    Returns:
        Tuple of (first_name, last_name). If name has only one part,
        last_name will be empty string.
    """
    if not full_name:
        return "", ""

    parts = full_name.strip().split()
    if len(parts) == 0:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""

    first_name = parts[0]
    last_name = " ".join(parts[1:])
    return first_name, last_name


def _parse_connection_degree(distance: str | None) -> int:
    """Parse LinkedIn distance string to connection degree integer.

    Args:
        distance: Distance string from LinkedIn API (e.g., "DISTANCE_1").

    Returns:
        Integer connection degree (1, 2, or 3). Defaults to 3 for
        unknown/missing values.
    """
    if not distance:
        return 3

    distance_mapping = {
        "DISTANCE_1": 1,
        "DISTANCE_2": 2,
        "DISTANCE_3": 3,
        "OUT_OF_NETWORK": 3,
    }

    return distance_mapping.get(distance, 3)
