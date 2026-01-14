# ABOUTME: Tests for the cookie manager service module.
# ABOUTME: Covers cookie storage, retrieval, validation, and account management.

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from linkedin_scraper.auth import CookieManager


@pytest.fixture
def temp_accounts_file() -> Path:
    """Create a temporary accounts file path."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        return Path(f.name)


@pytest.fixture
def mock_keyring() -> MagicMock:
    """Create a mock keyring for testing."""
    with patch("linkedin_scraper.auth.cookie_manager.keyring") as mock:
        mock.get_password = MagicMock(return_value=None)
        mock.set_password = MagicMock()
        mock.delete_password = MagicMock()
        yield mock


@pytest.fixture
def cookie_manager(temp_accounts_file: Path, mock_keyring: MagicMock) -> CookieManager:
    """Create a CookieManager instance with mocked dependencies."""
    return CookieManager(accounts_file=temp_accounts_file)


class TestCookieManagerInit:
    """Tests for CookieManager initialization."""

    def test_init_with_custom_accounts_file(
        self, temp_accounts_file: Path, mock_keyring: MagicMock
    ) -> None:
        """Test that CookieManager accepts a custom accounts file path."""
        manager = CookieManager(accounts_file=temp_accounts_file)
        assert manager.accounts_file == temp_accounts_file

    def test_init_with_default_accounts_file(self, mock_keyring: MagicMock) -> None:
        """Test that CookieManager uses default path when none provided."""
        manager = CookieManager()
        expected_path = Path.home() / ".linkedin-scraper" / "accounts.json"
        assert manager.accounts_file == expected_path


class TestCookieValidation:
    """Tests for cookie format validation."""

    def test_validate_cookie_format_with_valid_cookie(
        self, cookie_manager: CookieManager
    ) -> None:
        """Test that a valid cookie passes validation."""
        valid_cookie = "AQEDAQNhS28F1234AbCdEfGhIjKlMnOpQrStUvWxYz"
        assert cookie_manager.validate_cookie_format(valid_cookie) is True

    def test_validate_cookie_format_with_empty_string(
        self, cookie_manager: CookieManager
    ) -> None:
        """Test that an empty string fails validation."""
        assert cookie_manager.validate_cookie_format("") is False

    def test_validate_cookie_format_with_whitespace_only(
        self, cookie_manager: CookieManager
    ) -> None:
        """Test that whitespace-only string fails validation."""
        assert cookie_manager.validate_cookie_format("   ") is False

    def test_validate_cookie_format_with_too_short_cookie(
        self, cookie_manager: CookieManager
    ) -> None:
        """Test that a too-short cookie fails validation."""
        assert cookie_manager.validate_cookie_format("abc") is False

    def test_validate_cookie_format_with_reasonable_length(
        self, cookie_manager: CookieManager
    ) -> None:
        """Test that a cookie with reasonable length passes validation."""
        # LinkedIn li_at cookies are typically around 200+ characters
        reasonable_cookie = "A" * 50
        assert cookie_manager.validate_cookie_format(reasonable_cookie) is True


class TestStoreCookie:
    """Tests for storing cookies."""

    def test_store_cookie_saves_to_keyring(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that store_cookie saves the cookie to keyring."""
        cookie = "AQEDAQNhS28F1234test_cookie_value"
        cookie_manager.store_cookie(cookie)

        mock_keyring.set_password.assert_called_once_with(
            "linkedin-scraper", "default", cookie
        )

    def test_store_cookie_with_custom_account_name(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that store_cookie uses custom account name."""
        cookie = "AQEDAQNhS28F1234test_cookie_value"
        cookie_manager.store_cookie(cookie, account_name="work")

        mock_keyring.set_password.assert_called_once_with(
            "linkedin-scraper", "work", cookie
        )

    def test_store_cookie_adds_account_to_list(
        self, cookie_manager: CookieManager, temp_accounts_file: Path, mock_keyring: MagicMock
    ) -> None:
        """Test that store_cookie adds account name to accounts list."""
        cookie = "AQEDAQNhS28F1234test_cookie_value"
        cookie_manager.store_cookie(cookie, account_name="personal")

        accounts = cookie_manager.list_accounts()
        assert "personal" in accounts

    def test_store_cookie_does_not_duplicate_accounts(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that storing same account twice doesn't create duplicates."""
        cookie = "AQEDAQNhS28F1234test_cookie_value"
        cookie_manager.store_cookie(cookie, account_name="myaccount")
        cookie_manager.store_cookie(cookie, account_name="myaccount")

        accounts = cookie_manager.list_accounts()
        assert accounts.count("myaccount") == 1


class TestGetCookie:
    """Tests for retrieving cookies."""

    def test_get_cookie_retrieves_from_keyring(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that get_cookie retrieves from keyring."""
        expected_cookie = "AQEDAQNhS28F1234stored_cookie"
        mock_keyring.get_password.return_value = expected_cookie

        cookie = cookie_manager.get_cookie()

        mock_keyring.get_password.assert_called_with("linkedin-scraper", "default")
        assert cookie == expected_cookie

    def test_get_cookie_with_custom_account_name(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that get_cookie uses custom account name."""
        expected_cookie = "AQEDAQNhS28F1234work_cookie"
        mock_keyring.get_password.return_value = expected_cookie

        cookie = cookie_manager.get_cookie(account_name="work")

        mock_keyring.get_password.assert_called_with("linkedin-scraper", "work")
        assert cookie == expected_cookie

    def test_get_cookie_returns_none_when_not_found(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that get_cookie returns None when cookie doesn't exist."""
        mock_keyring.get_password.return_value = None

        cookie = cookie_manager.get_cookie(account_name="nonexistent")

        assert cookie is None


class TestDeleteCookie:
    """Tests for deleting cookies."""

    def test_delete_cookie_removes_from_keyring(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that delete_cookie removes from keyring."""
        # First store a cookie
        cookie_manager.store_cookie("test_cookie", account_name="todelete")

        cookie_manager.delete_cookie(account_name="todelete")

        mock_keyring.delete_password.assert_called_with("linkedin-scraper", "todelete")

    def test_delete_cookie_removes_from_accounts_list(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that delete_cookie removes account from accounts list."""
        # First store a cookie
        cookie_manager.store_cookie("test_cookie", account_name="todelete")

        cookie_manager.delete_cookie(account_name="todelete")

        accounts = cookie_manager.list_accounts()
        assert "todelete" not in accounts

    def test_delete_cookie_with_default_account(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that delete_cookie works with default account name."""
        cookie_manager.store_cookie("test_cookie")
        cookie_manager.delete_cookie()

        mock_keyring.delete_password.assert_called_with("linkedin-scraper", "default")


class TestListAccounts:
    """Tests for listing accounts."""

    def test_list_accounts_returns_empty_list_initially(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that list_accounts returns empty list when no accounts stored."""
        accounts = cookie_manager.list_accounts()
        assert accounts == []

    def test_list_accounts_returns_stored_accounts(
        self, cookie_manager: CookieManager, mock_keyring: MagicMock
    ) -> None:
        """Test that list_accounts returns all stored account names."""
        cookie_manager.store_cookie("cookie1", account_name="account1")
        cookie_manager.store_cookie("cookie2", account_name="account2")

        accounts = cookie_manager.list_accounts()

        assert "account1" in accounts
        assert "account2" in accounts
        assert len(accounts) == 2

    def test_list_accounts_persists_across_instances(
        self, temp_accounts_file: Path, mock_keyring: MagicMock
    ) -> None:
        """Test that accounts list persists across CookieManager instances."""
        manager1 = CookieManager(accounts_file=temp_accounts_file)
        manager1.store_cookie("cookie1", account_name="persistent")

        # Create a new instance with the same accounts file
        manager2 = CookieManager(accounts_file=temp_accounts_file)
        accounts = manager2.list_accounts()

        assert "persistent" in accounts


class TestAccountsFilePersistence:
    """Tests for accounts file persistence."""

    def test_accounts_file_created_when_storing(
        self, cookie_manager: CookieManager, temp_accounts_file: Path, mock_keyring: MagicMock
    ) -> None:
        """Test that accounts file is created when storing a cookie."""
        # Remove the temp file first
        temp_accounts_file.unlink(missing_ok=True)

        cookie_manager.store_cookie("test_cookie", account_name="testaccount")

        assert temp_accounts_file.exists()

    def test_accounts_file_contains_valid_json(
        self, cookie_manager: CookieManager, temp_accounts_file: Path, mock_keyring: MagicMock
    ) -> None:
        """Test that accounts file contains valid JSON."""
        cookie_manager.store_cookie("test_cookie", account_name="testaccount")

        with open(temp_accounts_file) as f:
            data = json.load(f)

        assert "accounts" in data
        assert "testaccount" in data["accounts"]

    def test_accounts_file_directory_created_if_missing(
        self, mock_keyring: MagicMock
    ) -> None:
        """Test that parent directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            accounts_file = Path(tmpdir) / "nested" / "dir" / "accounts.json"
            manager = CookieManager(accounts_file=accounts_file)
            manager.store_cookie("test_cookie", account_name="test")

            assert accounts_file.exists()
