# ABOUTME: Tests for the CSV exporter module.
# ABOUTME: Covers CSV export functionality including column formatting and metadata.

import csv
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from linkedin_scraper.models import ConnectionProfile


class TestCSVExporter:
    """Tests for CSVExporter class."""

    @pytest.fixture
    def sample_profiles(self) -> list[ConnectionProfile]:
        """Create sample connection profiles for testing."""
        return [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:123",
                public_id="john-doe",
                first_name="John",
                last_name="Doe",
                headline="Software Engineer at TechCorp",
                location="San Francisco, CA",
                current_company="TechCorp",
                current_title="Software Engineer",
                profile_url="https://linkedin.com/in/john-doe",
                connection_degree=1,
                search_query="software engineer",
                found_at=datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC),
            ),
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:456",
                public_id="jane-smith",
                first_name="Jane",
                last_name="Smith",
                headline="Product Manager",
                location="New York, NY",
                current_company="StartupCo",
                current_title="PM",
                profile_url="https://linkedin.com/in/jane-smith",
                connection_degree=2,
                search_query="software engineer",
                found_at=datetime(2025, 6, 15, 10, 31, 0, tzinfo=UTC),
            ),
        ]

    @pytest.fixture
    def temp_output_path(self) -> Path:
        """Create a temporary file path for CSV output."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            return Path(f.name)

    def test_export_creates_csv_file(
        self, sample_profiles: list[ConnectionProfile], temp_output_path: Path
    ) -> None:
        """Test that export creates a CSV file at the specified path."""
        from linkedin_scraper.export.csv_exporter import CSVExporter

        exporter = CSVExporter()
        result_path = exporter.export(sample_profiles, temp_output_path)

        assert result_path.exists()
        assert result_path == temp_output_path

    def test_export_returns_path(
        self, sample_profiles: list[ConnectionProfile], temp_output_path: Path
    ) -> None:
        """Test that export returns the output path."""
        from linkedin_scraper.export.csv_exporter import CSVExporter

        exporter = CSVExporter()
        result_path = exporter.export(sample_profiles, temp_output_path)

        assert result_path == temp_output_path

    def test_export_contains_correct_headers(
        self, sample_profiles: list[ConnectionProfile], temp_output_path: Path
    ) -> None:
        """Test that exported CSV contains expected column headers."""
        from linkedin_scraper.export.csv_exporter import CSVExporter

        exporter = CSVExporter()
        exporter.export(sample_profiles, temp_output_path)

        with open(temp_output_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Skip metadata row
            next(reader)
            headers = next(reader)

        expected_headers = [
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
        assert headers == expected_headers

    def test_export_contains_profile_data(
        self, sample_profiles: list[ConnectionProfile], temp_output_path: Path
    ) -> None:
        """Test that exported CSV contains the profile data."""
        from linkedin_scraper.export.csv_exporter import CSVExporter

        exporter = CSVExporter()
        exporter.export(sample_profiles, temp_output_path)

        with open(temp_output_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Skip metadata row and headers
            next(reader)
            next(reader)
            rows = list(reader)

        assert len(rows) == 2

        # First row - John Doe
        assert rows[0][0] == "John Doe"  # name
        assert rows[0][1] == "John"  # first_name
        assert rows[0][2] == "Doe"  # last_name
        assert rows[0][3] == "Software Engineer at TechCorp"  # headline
        assert rows[0][4] == "TechCorp"  # company
        assert rows[0][5] == "Software Engineer"  # title
        assert rows[0][6] == "San Francisco, CA"  # location
        assert rows[0][7] == "https://linkedin.com/in/john-doe"  # profile_url
        assert rows[0][8] == "1"  # degree
        assert rows[0][9] == "software engineer"  # search_query

        # Second row - Jane Smith
        assert rows[1][0] == "Jane Smith"  # name
        assert rows[1][1] == "Jane"  # first_name

    def test_export_includes_metadata_row(
        self, sample_profiles: list[ConnectionProfile], temp_output_path: Path
    ) -> None:
        """Test that exported CSV includes a metadata row at the top."""
        from linkedin_scraper.export.csv_exporter import CSVExporter

        exporter = CSVExporter()
        exporter.export(sample_profiles, temp_output_path)

        with open(temp_output_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            metadata_row = next(reader)

        # Metadata row should contain export info
        metadata_text = " ".join(metadata_row)
        assert "export" in metadata_text.lower() or "generated" in metadata_text.lower()

    def test_export_handles_none_values(self, temp_output_path: Path) -> None:
        """Test that export handles profiles with None values gracefully."""
        from linkedin_scraper.export.csv_exporter import CSVExporter

        profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:789",
                public_id="no-info",
                first_name="NoInfo",
                last_name="User",
                headline=None,
                location=None,
                current_company=None,
                current_title=None,
                profile_url="https://linkedin.com/in/no-info",
                connection_degree=3,
                search_query=None,
            )
        ]

        exporter = CSVExporter()
        exporter.export(profiles, temp_output_path)

        with open(temp_output_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Skip metadata row and headers
            next(reader)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        # None values should be empty strings
        assert rows[0][3] == ""  # headline
        assert rows[0][4] == ""  # company
        assert rows[0][5] == ""  # title
        assert rows[0][6] == ""  # location

    def test_export_handles_empty_profiles_list(self, temp_output_path: Path) -> None:
        """Test that export handles empty profiles list."""
        from linkedin_scraper.export.csv_exporter import CSVExporter

        exporter = CSVExporter()
        result_path = exporter.export([], temp_output_path)

        assert result_path.exists()

        with open(temp_output_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Should have metadata row and headers, but no data rows
        assert len(rows) == 2

    def test_export_escapes_special_characters(self, temp_output_path: Path) -> None:
        """Test that export properly escapes special CSV characters."""
        from linkedin_scraper.export.csv_exporter import CSVExporter

        profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:999",
                public_id="special-char",
                first_name="Special",
                last_name="Character",
                headline='Engineer with "quotes" and, commas',
                location="City, State",
                current_company="Company, Inc.",
                current_title="Title",
                profile_url="https://linkedin.com/in/special-char",
                connection_degree=1,
                search_query="test",
            )
        ]

        exporter = CSVExporter()
        exporter.export(profiles, temp_output_path)

        with open(temp_output_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Skip metadata row and headers
            next(reader)
            next(reader)
            rows = list(reader)

        # CSV reader should properly parse the escaped values
        assert rows[0][3] == 'Engineer with "quotes" and, commas'
        assert rows[0][6] == "City, State"
        assert rows[0][4] == "Company, Inc."

    def test_export_uses_utf8_encoding(self, temp_output_path: Path) -> None:
        """Test that export uses UTF-8 encoding for international characters."""
        from linkedin_scraper.export.csv_exporter import CSVExporter

        profiles = [
            ConnectionProfile(
                linkedin_urn_id="urn:li:member:888",
                public_id="international",
                first_name="José",
                last_name="García",
                headline="Développeur à Paris",
                location="北京, 中国",
                current_company="日本株式会社",
                current_title="エンジニア",
                profile_url="https://linkedin.com/in/international",
                connection_degree=1,
                search_query="developer",
            )
        ]

        exporter = CSVExporter()
        exporter.export(profiles, temp_output_path)

        with open(temp_output_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Skip metadata row and headers
            next(reader)
            next(reader)
            rows = list(reader)

        assert rows[0][1] == "José"
        assert rows[0][2] == "García"
        assert rows[0][3] == "Développeur à Paris"
        assert rows[0][6] == "北京, 中国"

    def test_export_with_query_info_in_metadata(
        self, sample_profiles: list[ConnectionProfile], temp_output_path: Path
    ) -> None:
        """Test that metadata row includes query info when profiles share a query."""
        from linkedin_scraper.export.csv_exporter import CSVExporter

        exporter = CSVExporter()
        exporter.export(sample_profiles, temp_output_path, query_info="software engineer")

        with open(temp_output_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            metadata_row = next(reader)

        metadata_text = " ".join(metadata_row)
        assert "software engineer" in metadata_text.lower()
