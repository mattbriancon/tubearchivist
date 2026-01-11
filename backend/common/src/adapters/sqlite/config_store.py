"""
SQLite implementation of ConfigStore interface.

This adapter uses Django ORM to store configuration data in SQLite as
key-value pairs with JSON values.
"""

import json
from typing import Any

from common.src.interfaces.config_store import ConfigStore


class SQLiteConfigStore(ConfigStore):
    """
    SQLite-backed configuration storage using Django ORM.

    Stores configuration as key-value pairs in a ConfigData table where:
    - key: string identifier (document ID from ES)
    - value: JSON-serialized configuration dict

    The table will be created via Django migrations when this adapter is enabled.
    """

    def __init__(self):
        """Initialize the SQLite config store."""
        # Import here to avoid circular imports and to allow this module
        # to be imported even if the model doesn't exist yet
        from common.models import ConfigData

        self.model = ConfigData

    def get(self, key: str) -> tuple[dict[str, Any] | None, int]:
        """
        Retrieve configuration from SQLite.

        Args:
            key: Configuration key

        Returns:
            Tuple of (configuration dict, status code)
            Status codes: 200 (found), 404 (not found)
        """
        try:
            config_obj = self.model.objects.get(key=key)
            # Parse JSON value
            data = json.loads(config_obj.value)
            return data, 200
        except self.model.DoesNotExist:
            return None, 404
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for key {key}: {e}")
            return None, 500

    def set(self, key: str, value: dict[str, Any]) -> tuple[dict[str, Any], int]:
        """
        Store or replace configuration in SQLite.

        Args:
            key: Configuration key
            value: Configuration dict to store

        Returns:
            Tuple of (response dict, status code)
            Status codes: 200 (updated), 201 (created)
        """
        try:
            # Serialize to JSON
            json_value = json.dumps(value)

            # Use update_or_create for upsert behavior
            config_obj, created = self.model.objects.update_or_create(
                key=key, defaults={"value": json_value}
            )

            status_code = 201 if created else 200
            response = {
                "key": key,
                "created": created,
                "updated": not created,
            }
            return response, status_code
        except Exception as e:
            print(f"Error storing config for key {key}: {e}")
            return {"error": str(e)}, 500

    def update(self, key: str, updates: dict[str, Any]) -> tuple[dict[str, Any], int]:
        """
        Update specific fields in the configuration.

        Performs a partial update by:
        1. Retrieving the existing document
        2. Merging the updates (recursive for nested dicts)
        3. Storing the merged result

        Args:
            key: Configuration key
            updates: Dict containing fields to update

        Returns:
            Tuple of (response dict, status code)
            Status codes: 200 (success), 404 (not found)
        """
        # Get existing config
        existing_data, status = self.get(key)

        if status == 404:
            return {"error": "Configuration not found"}, 404

        # Merge updates into existing data
        merged_data = self._deep_merge(existing_data or {}, updates)

        # Store the merged result
        response, status = self.set(key, merged_data)

        # Always return 200 for successful updates (not 201)
        if status in (200, 201):
            return response, 200

        return response, status

    def delete(self, key: str) -> tuple[dict[str, Any], int]:
        """
        Delete configuration from SQLite.

        Args:
            key: Configuration key to delete

        Returns:
            Tuple of (response dict, status code)
            Status codes: 200 (deleted), 404 (not found)
        """
        try:
            config_obj = self.model.objects.get(key=key)
            config_obj.delete()
            return {"key": key, "deleted": True}, 200
        except self.model.DoesNotExist:
            return {"error": "Configuration not found"}, 404
        except Exception as e:
            print(f"Error deleting config for key {key}: {e}")
            return {"error": str(e)}, 500

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
                result[key] = SQLiteConfigStore._deep_merge(result[key], value)
            else:
                # Replace value
                result[key] = value

        return result
