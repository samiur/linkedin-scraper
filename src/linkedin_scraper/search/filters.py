# ABOUTME: Defines search filter criteria for LinkedIn connection searches.
# ABOUTME: Maps to linkedin-api search_people parameters.

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class NetworkDepth(str, Enum):
    """LinkedIn connection degree filter."""

    FIRST = "F"  # 1st degree connections (direct connections)
    SECOND = "S"  # 2nd degree connections (connections of connections)
    THIRD = "O"  # 3rd+ degree (out of network)


class SearchFilter(BaseModel):
    """Search criteria for LinkedIn connection search."""

    keywords: Annotated[
        str | None, Field(default=None, description="Job title or keyword search terms")
    ] = None

    network_depths: Annotated[
        list[NetworkDepth],
        Field(
            default=[NetworkDepth.FIRST, NetworkDepth.SECOND],
            description="Connection degree filter",
        ),
    ]

    current_company_ids: Annotated[
        list[str] | None, Field(default=None, description="LinkedIn company IDs to filter by")
    ] = None

    regions: Annotated[
        list[str] | None, Field(default=None, description="Region codes (e.g., 'us:0' for USA)")
    ] = None

    limit: Annotated[
        int, Field(default=100, ge=1, le=1000, description="Maximum results to return")
    ] = 100
