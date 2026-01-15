# ABOUTME: Database statistics functionality for the status command.
# ABOUTME: Provides aggregated stats about stored connections including counts and distributions.

from typing import Any

from sqlmodel import func, select

from linkedin_scraper.database.service import DatabaseService
from linkedin_scraper.models import ConnectionProfile


def get_database_stats(db_service: DatabaseService) -> dict[str, Any]:
    """Get statistics about stored connections in the database.

    Args:
        db_service: The DatabaseService instance to query.

    Returns:
        Dictionary containing:
            - total_connections: Total number of stored profiles
            - unique_companies: Count of distinct company names
            - unique_locations: Count of distinct locations
            - recent_searches_count: Count of distinct search queries
            - search_queries: List of distinct search queries
            - degree_distribution: Dict mapping degree (1, 2, 3) to count
    """
    with db_service.get_session() as session:
        # Total connections
        total_stmt = select(func.count()).select_from(ConnectionProfile)
        total_connections = session.exec(total_stmt).one()

        # Unique companies (non-null)
        companies_stmt = select(func.count(func.distinct(ConnectionProfile.current_company))).where(
            ConnectionProfile.current_company.is_not(None)  # type: ignore[union-attr]
        )
        unique_companies = session.exec(companies_stmt).one()

        # Unique locations (non-null)
        locations_stmt = select(func.count(func.distinct(ConnectionProfile.location))).where(
            ConnectionProfile.location.is_not(None)  # type: ignore[union-attr]
        )
        unique_locations = session.exec(locations_stmt).one()

        # Unique search queries (non-null)
        queries_stmt = select(func.count(func.distinct(ConnectionProfile.search_query))).where(
            ConnectionProfile.search_query.is_not(None)  # type: ignore[union-attr]
        )
        recent_searches_count = session.exec(queries_stmt).one()

        # List of search queries
        queries_list_stmt = (
            select(ConnectionProfile.search_query)
            .where(
                ConnectionProfile.search_query.is_not(None)  # type: ignore[union-attr]
            )
            .distinct()
        )
        search_queries = list(session.exec(queries_list_stmt).all())

        # Degree distribution
        degree_stmt = select(ConnectionProfile.connection_degree, func.count()).group_by(
            ConnectionProfile.connection_degree  # type: ignore[arg-type]
        )
        degree_results = session.exec(degree_stmt).all()
        degree_distribution = dict(degree_results)

    return {
        "total_connections": total_connections,
        "unique_companies": unique_companies,
        "unique_locations": unique_locations,
        "recent_searches_count": recent_searches_count,
        "search_queries": search_queries,
        "degree_distribution": degree_distribution,
    }
