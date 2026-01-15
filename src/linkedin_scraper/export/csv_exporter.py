# ABOUTME: CSV exporter for LinkedIn connection profiles.
# ABOUTME: Exports profiles to CSV format with metadata header and proper escaping.

import csv
from datetime import UTC, datetime
from pathlib import Path

from linkedin_scraper.models import ConnectionProfile


class CSVExporter:
    """Exports LinkedIn connection profiles to CSV format."""

    HEADERS = [
        "name",
        "first_name",
        "last_name",
        "headline",
        "company",
        "title",
        "location",
        "profile_url",
        "degree",
        "search_query",
        "found_at",
    ]

    def export(
        self,
        profiles: list[ConnectionProfile],
        output_path: Path,
        query_info: str | None = None,
    ) -> Path:
        """Export connection profiles to a CSV file.

        Args:
            profiles: List of ConnectionProfile objects to export.
            output_path: Path to the output CSV file.
            query_info: Optional query string to include in metadata.

        Returns:
            Path to the created CSV file.
        """
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write metadata row
            metadata = self._create_metadata_row(len(profiles), query_info)
            writer.writerow(metadata)

            # Write headers
            writer.writerow(self.HEADERS)

            # Write profile data
            for profile in profiles:
                row = self._profile_to_row(profile)
                writer.writerow(row)

        return output_path

    def _create_metadata_row(self, count: int, query_info: str | None) -> list[str]:
        """Create a metadata row with export information.

        Args:
            count: Number of profiles being exported.
            query_info: Optional query string to include.

        Returns:
            List of strings for the metadata row.
        """
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        metadata_parts = [f"# Exported at: {timestamp}", f"Records: {count}"]

        if query_info:
            metadata_parts.append(f"Query: {query_info}")

        # Return as single cell to avoid CSV interpretation issues
        return [" | ".join(metadata_parts)]

    def _profile_to_row(self, profile: ConnectionProfile) -> list[str]:
        """Convert a ConnectionProfile to a CSV row.

        Args:
            profile: The ConnectionProfile to convert.

        Returns:
            List of strings representing the profile data.
        """
        return [
            profile.full_name,
            profile.first_name,
            profile.last_name,
            profile.headline or "",
            profile.current_company or "",
            profile.current_title or "",
            profile.location or "",
            profile.profile_url,
            str(profile.connection_degree),
            profile.search_query or "",
            profile.found_at.strftime("%Y-%m-%d %H:%M:%S") if profile.found_at else "",
        ]
