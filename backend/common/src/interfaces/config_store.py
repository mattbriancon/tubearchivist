"""
Configuration Store Interface

Defines the abstract interface for storing and retrieving configuration data.
This is a simple key-value store with support for nested updates.
"""

from abc import ABC, abstractmethod
from typing import Any


class ConfigNotFoundError(Exception):
    """Raised when a configuration key is not found."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Configuration not found: {key}")


class ConfigStore(ABC):
    """
    Abstract base class for configuration storage backends.

    Configuration data is stored as key-value pairs where:
    - key: string identifier (e.g., "appsettings", "user_{user_id}")
    - value: dict containing configuration data

    Operations raise ConfigNotFoundError when a key doesn't exist.
    Other errors raise appropriate exceptions (ValueError, etc.).
    """

    @abstractmethod
    def get(self, key: str) -> dict[str, Any]:
        """
        Retrieve configuration data for the given key.

        Args:
            key: Configuration key (e.g., "appsettings", "user_123")

        Returns:
            Configuration dict

        Raises:
            ConfigNotFoundError: If the key doesn't exist

        Example:
            try:
                config = store.get("appsettings")
                print(config["subscriptions"]["channel_size"])
            except ConfigNotFoundError:
                print("Config not found")
        """

    @abstractmethod
    def set(self, key: str, value: dict[str, Any]) -> None:
        """
        Store or replace configuration data for the given key.

        This performs a full replacement of the configuration document.

        Args:
            key: Configuration key
            value: Complete configuration dict to store

        Raises:
            ValueError: If value is invalid

        Example:
            config = {"subscriptions": {"channel_size": 50}}
            store.set("appsettings", config)
        """

    @abstractmethod
    def update(self, key: str, updates: dict[str, Any]) -> None:
        """
        Update specific fields in the configuration document.

        This performs a partial update, merging the updates into the existing
        configuration. Nested dicts are merged recursively.

        Args:
            key: Configuration key
            updates: Dict containing fields to update

        Raises:
            ConfigNotFoundError: If the key doesn't exist
            ValueError: If updates are invalid

        Example:
            # Only update channel_size, leave other fields unchanged
            updates = {"subscriptions": {"channel_size": 100}}
            store.update("appsettings", updates)
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete configuration data for the given key.

        Args:
            key: Configuration key to delete

        Raises:
            ConfigNotFoundError: If the key doesn't exist

        Example:
            store.delete("user_123")
        """

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if configuration data exists for the given key.

        Args:
            key: Configuration key to check

        Returns:
            True if the key exists, False otherwise

        Example:
            if store.exists("appsettings"):
                config = store.get("appsettings")
        """

    @abstractmethod
    def list_keys(self, prefix: str | None = None) -> list[str]:
        """
        List all configuration keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys (e.g., "user_" to get all user configs)

        Returns:
            List of configuration keys

        Example:
            # Get all user config keys
            user_keys = store.list_keys(prefix="user_")
            # Returns: ["user_123", "user_456", ...]
        """
