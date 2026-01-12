"""
Django ORM implementation of ConfigStore interface.

This adapter uses Django models to store configuration data, working with
whatever database backend Django is configured to use (SQLite, PostgreSQL, MySQL, etc.).
"""

import json
from typing import Any

from common.src.interfaces.config_store import ConfigNotFoundError, ConfigStore
from django.db import transaction


class ModelConfigStore(ConfigStore):
    """
    Django ORM-backed configuration storage.

    Stores configuration as key-value pairs in the ConfigData model where:
    - key: string identifier (e.g., "appsettings", "user_123")
    - value: JSON-serialized configuration dict

    Works with any database backend Django supports (SQLite, PostgreSQL, MySQL, etc.).
    The ConfigData table is created via Django migrations.
    """

    def __init__(self):
        """Initialize the model config store."""
        # Import here to avoid circular imports and to allow this module
        # to be imported even if the model doesn't exist yet
        from common.models import ConfigData

        self.model = ConfigData

    def get(self, key: str) -> dict[str, Any]:
        """
        Retrieve configuration from database.

        Args:
            key: Configuration key

        Returns:
            Configuration dict

        Raises:
            ConfigNotFoundError: If key doesn't exist
            ValueError: If stored JSON is invalid
        """
        try:
            config_obj = self.model.objects.get(key=key)
            return json.loads(config_obj.value)
        except self.model.DoesNotExist:
            raise ConfigNotFoundError(key)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for key {key}: {e}")

    def set(self, key: str, value: dict[str, Any]) -> None:
        """
        Store or replace configuration in database.

        Args:
            key: Configuration key
            value: Configuration dict to store

        Raises:
            ValueError: If value cannot be serialized to JSON
        """
        try:
            json_value = json.dumps(value)
            self.model.objects.update_or_create(
                key=key, defaults={"value": json_value}
            )
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize config for key {key}: {e}")

    def update(self, key: str, updates: dict[str, Any]) -> None:
        """
        Update specific fields in the configuration.

        Performs a partial update by:
        1. Selecting the row for update (with lock)
        2. Merging the updates (recursive for nested dicts)
        3. Saving the merged result atomically

        Args:
            key: Configuration key
            updates: Dict containing fields to update

        Raises:
            ConfigNotFoundError: If key doesn't exist
            ValueError: If updates cannot be serialized
        """
        try:
            with transaction.atomic():
                # Lock the row for update to prevent race conditions
                config_obj = self.model.objects.select_for_update().get(key=key)
                existing_data = json.loads(config_obj.value)
                merged_data = self._deep_merge(existing_data, updates)
                config_obj.value = json.dumps(merged_data)
                config_obj.save(update_fields=["value"])
        except self.model.DoesNotExist:
            raise ConfigNotFoundError(key)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for key {key}: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize updates for key {key}: {e}")

    def delete(self, key: str) -> None:
        """
        Delete configuration from database.

        Args:
            key: Configuration key to delete

        Raises:
            ConfigNotFoundError: If key doesn't exist
        """
        deleted_count, _ = self.model.objects.filter(key=key).delete()
        if deleted_count == 0:
            raise ConfigNotFoundError(key)

    def exists(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key to check

        Returns:
            True if key exists, False otherwise
        """
        return self.model.objects.filter(key=key).exists()

    def list_keys(self, prefix: str | None = None) -> list[str]:
        """
        List all configuration keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of configuration keys
        """
        queryset = self.model.objects.all()

        if prefix:
            queryset = queryset.filter(key__startswith=prefix)

        return list(queryset.values_list("key", flat=True))

    @staticmethod
    def _deep_merge(base: dict, updates: dict) -> dict:
        """
        Recursively merge updates into base dict.

        Args:
            base: Base dictionary
            updates: Updates to merge in

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in updates.items():
            if (
                isinstance(value, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
                # Recursively merge nested dicts
                result[key] = ModelConfigStore._deep_merge(result[key], value)
            else:
                # Replace value
                result[key] = value

        return result
