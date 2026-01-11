"""
Configuration Store Interface

Defines the abstract interface for storing and retrieving configuration data.
This is a simple key-value store with support for nested updates.
"""

from abc import ABC, abstractmethod
from typing import Any


class ConfigStore(ABC):
    """
    Abstract base class for configuration storage backends.

    Configuration data is stored as key-value pairs where:
    - key: string identifier (e.g., "appsettings", "user_{user_id}")
    - value: dict containing configuration data

    Implementations must handle:
    - Full document retrieval (get)
    - Full document replacement (set)
    - Partial document updates (update)
    - Document deletion (delete)
    - Existence checks (exists)
    """

    @abstractmethod
    def get(self, key: str) -> tuple[dict[str, Any] | None, int]:
        """
        Retrieve configuration data for the given key.

        Args:
            key: Configuration key (e.g., "appsettings", "user_123")

        Returns:
            Tuple of (data, status_code) where:
            - data: Configuration dict if found, None if not found
            - status_code: HTTP-style status code (200=success, 404=not found, etc.)

        Example:
            config, status = store.get("appsettings")
            if status == 200:
                print(config["subscriptions"]["channel_size"])
        """

    @abstractmethod
    def set(self, key: str, value: dict[str, Any]) -> tuple[dict[str, Any], int]:
        """
        Store or replace configuration data for the given key.

        This performs a full replacement of the configuration document.

        Args:
            key: Configuration key
            value: Complete configuration dict to store

        Returns:
            Tuple of (response, status_code) where:
            - response: Backend-specific response (e.g., ES response, row data)
            - status_code: HTTP-style status code (200=success, 201=created, etc.)

        Example:
            config = {"subscriptions": {"channel_size": 50}}
            response, status = store.set("appsettings", config)
        """

    @abstractmethod
    def update(self, key: str, updates: dict[str, Any]) -> tuple[dict[str, Any], int]:
        """
        Update specific fields in the configuration document.

        This performs a partial update, merging the updates into the existing
        configuration. Nested dicts are merged recursively.

        Args:
            key: Configuration key
            updates: Dict containing fields to update

        Returns:
            Tuple of (response, status_code) where:
            - response: Backend-specific response
            - status_code: HTTP-style status code (200=success, 404=not found, etc.)

        Example:
            # Only update channel_size, leave other fields unchanged
            updates = {"subscriptions": {"channel_size": 100}}
            response, status = store.update("appsettings", updates)
        """

    @abstractmethod
    def delete(self, key: str) -> tuple[dict[str, Any], int]:
        """
        Delete configuration data for the given key.

        Args:
            key: Configuration key to delete

        Returns:
            Tuple of (response, status_code) where:
            - response: Backend-specific response
            - status_code: HTTP-style status code (200=success, 404=not found, etc.)

        Example:
            response, status = store.delete("user_123")
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
                config, _ = store.get("appsettings")
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
