"""
Elasticsearch implementation of ConfigStore interface.

This adapter wraps the existing Elasticsearch logic for storing configuration
data in the ta_config index.
"""

from typing import Any

from common.src.es_connect import ElasticWrap
from common.src.interfaces.config_store import ConfigNotFoundError, ConfigStore


class ElasticsearchConfigStore(ConfigStore):
    """
    Elasticsearch-backed configuration storage.

    Stores configuration documents in the ta_config index with document IDs
    as the configuration keys.

    Example ES document structure:
        Index: ta_config
        Document ID: appsettings
        Document body: {
            "subscriptions": {"channel_size": 50, ...},
            "downloads": {"limit_speed": null, ...},
            "application": {"enable_snapshot": true, ...}
        }

        Document ID: user_123
        Document body: {
            "config": {
                "stylesheet": "dark.css",
                "page_size": 25,
                ...
            }
        }
    """

    INDEX_NAME = "ta_config"

    def _get_doc_path(self, key: str) -> str:
        """Get the ES document path for a key."""
        return f"{self.INDEX_NAME}/_doc/{key}"

    def _get_update_path(self, key: str) -> str:
        """Get the ES update path for a key."""
        return f"{self.INDEX_NAME}/_update/{key}"

    def get(self, key: str) -> dict[str, Any]:
        """
        Retrieve configuration from Elasticsearch.

        Args:
            key: Document ID in ta_config index

        Returns:
            Configuration dict

        Raises:
            ConfigNotFoundError: If key doesn't exist
        """
        path = self._get_doc_path(key)
        response, status_code = ElasticWrap(path).get(print_error=False)

        if status_code == 200:
            return response.get("_source")
        elif status_code == 404:
            raise ConfigNotFoundError(key)
        else:
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

    def set(self, key: str, value: dict[str, Any]) -> None:
        """
        Store or replace configuration in Elasticsearch.

        Args:
            key: Document ID in ta_config index
            value: Complete document to store

        Raises:
            ValueError: If Elasticsearch returns an error
        """
        path = self._get_doc_path(key)
        response, status_code = ElasticWrap(path).post(value)

        if status_code not in (200, 201):
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

    def update(self, key: str, updates: dict[str, Any]) -> None:
        """
        Update specific fields in Elasticsearch document.

        Uses ES _update API with "doc" parameter for partial updates.

        Args:
            key: Document ID in ta_config index
            updates: Fields to update (will be merged)

        Raises:
            ConfigNotFoundError: If key doesn't exist
            ValueError: If Elasticsearch returns an error
        """
        path = self._get_update_path(key)
        # ES update API requires wrapping updates in "doc"
        data = {"doc": updates}
        response, status_code = ElasticWrap(path).post(data)

        if status_code == 404:
            raise ConfigNotFoundError(key)
        elif status_code != 200:
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

    def delete(self, key: str) -> None:
        """
        Delete configuration from Elasticsearch.

        Args:
            key: Document ID in ta_config index

        Raises:
            ConfigNotFoundError: If key doesn't exist
            ValueError: If Elasticsearch returns an error
        """
        path = self._get_doc_path(key)
        response, status_code = ElasticWrap(path).delete()

        if status_code == 404:
            raise ConfigNotFoundError(key)
        elif status_code != 200:
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

    def exists(self, key: str) -> bool:
        """
        Check if a configuration document exists.

        Args:
            key: Document ID to check

        Returns:
            True if document exists, False otherwise
        """
        try:
            self.get(key)
            return True
        except ConfigNotFoundError:
            return False

    def list_keys(self, prefix: str | None = None) -> list[str]:
        """
        List all configuration keys in the index.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of document IDs (configuration keys)
        """
        # Build search query
        path = f"{self.INDEX_NAME}/_search"
        query: dict[str, Any] = {
            "size": 1000,  # Arbitrary limit, config should be small
            "_source": False,  # We only need IDs
            "query": {"match_all": {}},
        }

        if prefix:
            # Use prefix query to filter by document ID
            query["query"] = {"prefix": {"_id": prefix}}

        response, status_code = ElasticWrap(path).get(data=query)

        if status_code != 200:
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

        # Extract document IDs from hits
        hits = response.get("hits", {}).get("hits", [])
        return [hit["_id"] for hit in hits]
