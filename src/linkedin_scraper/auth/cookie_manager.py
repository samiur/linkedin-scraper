# ABOUTME: Cookie manager service for securely storing LinkedIn cookies.
# ABOUTME: Uses OS keyring for secure storage and maintains a list of account names.

import json
from pathlib import Path
from typing import Any

import keyring


class CookieManager:
    """Service for managing LinkedIn cookie storage using the OS keyring."""

    SERVICE_NAME = "linkedin-scraper"
    DEFAULT_ACCOUNTS_FILE = Path.home() / ".linkedin-scraper" / "accounts.json"
    MIN_COOKIE_LENGTH = 10

    def __init__(self, accounts_file: Path | None = None) -> None:
        """Initialize the cookie manager.

        Args:
            accounts_file: Path to JSON file storing account names.
                Defaults to ~/.linkedin-scraper/accounts.json
        """
        self.accounts_file = (
            accounts_file if accounts_file is not None else self.DEFAULT_ACCOUNTS_FILE
        )

    def validate_cookie_format(self, cookie: str) -> bool:
        """Validate the format of a LinkedIn cookie.

        Performs basic validation: checks for non-empty, reasonable length.

        Args:
            cookie: The cookie string to validate.

        Returns:
            True if the cookie format appears valid, False otherwise.
        """
        if not cookie or not cookie.strip():
            return False
        return len(cookie.strip()) >= self.MIN_COOKIE_LENGTH

    def store_cookie(self, cookie: str, account_name: str = "default") -> None:
        """Store a LinkedIn cookie in the OS keyring (legacy single-cookie method).

        Args:
            cookie: The li_at cookie value to store.
            account_name: Name to identify this account. Defaults to "default".
        """
        keyring.set_password(self.SERVICE_NAME, account_name, cookie)
        self._add_account_to_list(account_name)

    def store_cookies(
        self, li_at: str, jsessionid: str, account_name: str = "default"
    ) -> None:
        """Store LinkedIn cookies (li_at and JSESSIONID) in the OS keyring.

        Args:
            li_at: The li_at cookie value.
            jsessionid: The JSESSIONID cookie value.
            account_name: Name to identify this account. Defaults to "default".
        """
        cookie_data = json.dumps({"li_at": li_at, "JSESSIONID": jsessionid})
        keyring.set_password(self.SERVICE_NAME, account_name, cookie_data)
        self._add_account_to_list(account_name)

    def get_cookie(self, account_name: str = "default") -> str | None:
        """Retrieve the li_at cookie from the OS keyring.

        Handles both legacy (plain string) and new (JSON) storage formats.

        Args:
            account_name: Name of the account to retrieve. Defaults to "default".

        Returns:
            The li_at cookie string if found, None otherwise.
        """
        stored = keyring.get_password(self.SERVICE_NAME, account_name)
        if stored is None:
            return None

        # Try to parse as JSON (new format)
        try:
            data = json.loads(stored)
            if isinstance(data, dict):
                return data.get("li_at")
        except json.JSONDecodeError:
            pass

        # Fall back to treating it as a plain li_at string (legacy format)
        return stored

    def get_cookies(self, account_name: str = "default") -> dict[str, str] | None:
        """Retrieve both LinkedIn cookies from the OS keyring.

        Args:
            account_name: Name of the account to retrieve. Defaults to "default".

        Returns:
            Dictionary with 'li_at' and 'JSESSIONID' keys if found, None otherwise.
            If only li_at is stored (legacy format), JSESSIONID will be missing.
        """
        stored = keyring.get_password(self.SERVICE_NAME, account_name)
        if stored is None:
            return None

        # Try to parse as JSON (new format)
        try:
            data = json.loads(stored)
            if isinstance(data, dict) and "li_at" in data:
                return {"li_at": data["li_at"], "JSESSIONID": data.get("JSESSIONID", "")}
        except json.JSONDecodeError:
            pass

        # Fall back to treating it as a plain li_at string (legacy format)
        return {"li_at": stored, "JSESSIONID": ""}

    def delete_cookie(self, account_name: str = "default") -> None:
        """Delete a LinkedIn cookie from the OS keyring.

        Args:
            account_name: Name of the account to delete. Defaults to "default".
        """
        keyring.delete_password(self.SERVICE_NAME, account_name)
        self._remove_account_from_list(account_name)

    def list_accounts(self) -> list[str]:
        """List all stored account names.

        Returns:
            List of account names that have stored cookies.
        """
        return self._load_accounts()

    def _load_accounts(self) -> list[str]:
        """Load account names from the accounts file.

        Returns:
            List of account names, or empty list if file doesn't exist or is empty/invalid.
        """
        if not self.accounts_file.exists():
            return []

        try:
            content = self.accounts_file.read_text().strip()
            if not content:
                return []
            data: dict[str, Any] = json.loads(content)
            accounts = data.get("accounts", [])
            if isinstance(accounts, list):
                return [str(acc) for acc in accounts]
            return []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_accounts(self, accounts: list[str]) -> None:
        """Save account names to the accounts file.

        Args:
            accounts: List of account names to save.
        """
        self.accounts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.accounts_file, "w") as f:
            json.dump({"accounts": accounts}, f, indent=2)

    def _add_account_to_list(self, account_name: str) -> None:
        """Add an account name to the accounts list if not already present.

        Args:
            account_name: The account name to add.
        """
        accounts = self._load_accounts()
        if account_name not in accounts:
            accounts.append(account_name)
            self._save_accounts(accounts)

    def _remove_account_from_list(self, account_name: str) -> None:
        """Remove an account name from the accounts list.

        Args:
            account_name: The account name to remove.
        """
        accounts = self._load_accounts()
        if account_name in accounts:
            accounts.remove(account_name)
            self._save_accounts(accounts)
