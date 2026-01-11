"""Tests for ModelConfigStore adapter."""

import json

import pytest
from common.models import ConfigData
from common.src.adapters.model.config_store import ModelConfigStore
from common.src.interfaces.config_store import ConfigNotFoundError


@pytest.fixture
def store():
    """Create a ModelConfigStore instance."""
    return ModelConfigStore()


@pytest.fixture
def sample_config():
    """Sample configuration data."""
    return {
        "subscriptions": {"channel_size": 50, "auto_start": False},
        "downloads": {"limit_speed": None, "format": "best"},
        "application": {"enable_snapshot": True},
    }


@pytest.fixture
def sample_user_config():
    """Sample user configuration data."""
    return {
        "config": {
            "stylesheet": "dark.css",
            "page_size": 25,
            "sort_by": "published",
        }
    }


@pytest.mark.django_db
class TestModelConfigStoreBasicOperations:
    """Test basic CRUD operations."""

    def test_set_and_get_new_config(self, store, sample_config):
        """Test storing and retrieving new configuration."""
        store.set("test_key", sample_config)

        result = store.get("test_key")
        assert result == sample_config

        # Verify it's in the database
        db_obj = ConfigData.objects.get(key="test_key")
        assert json.loads(db_obj.value) == sample_config

    def test_get_nonexistent_key_raises_error(self, store):
        """Test getting a key that doesn't exist raises ConfigNotFoundError."""
        with pytest.raises(ConfigNotFoundError) as exc_info:
            store.get("nonexistent_key")

        assert exc_info.value.key == "nonexistent_key"
        assert "nonexistent_key" in str(exc_info.value)

    def test_set_updates_existing_config(self, store, sample_config):
        """Test that set replaces existing configuration."""
        store.set("test_key", sample_config)

        new_config = {"new": "data"}
        store.set("test_key", new_config)

        result = store.get("test_key")
        assert result == new_config
        assert result != sample_config

    def test_delete_existing_config(self, store, sample_config):
        """Test deleting an existing configuration."""
        store.set("test_key", sample_config)
        assert store.exists("test_key")

        store.delete("test_key")

        assert not store.exists("test_key")
        with pytest.raises(ConfigNotFoundError):
            store.get("test_key")

    def test_delete_nonexistent_key_raises_error(self, store):
        """Test deleting a key that doesn't exist raises ConfigNotFoundError."""
        with pytest.raises(ConfigNotFoundError):
            store.delete("nonexistent_key")

    def test_exists_returns_true_for_existing_key(self, store, sample_config):
        """Test exists returns True for existing key."""
        store.set("test_key", sample_config)
        assert store.exists("test_key") is True

    def test_exists_returns_false_for_nonexistent_key(self, store):
        """Test exists returns False for nonexistent key."""
        assert store.exists("nonexistent_key") is False


@pytest.mark.django_db
class TestModelConfigStoreUpdate:
    """Test update operations."""

    def test_update_merges_nested_dicts(self, store, sample_config):
        """Test that update merges nested dictionaries."""
        store.set("test_key", sample_config)

        updates = {"subscriptions": {"channel_size": 100}}
        store.update("test_key", updates)

        result = store.get("test_key")
        assert result["subscriptions"]["channel_size"] == 100
        assert result["subscriptions"]["auto_start"] is False  # Unchanged
        assert result["downloads"] == sample_config["downloads"]  # Unchanged

    def test_update_replaces_non_dict_values(self, store, sample_config):
        """Test that update replaces non-dict values."""
        store.set("test_key", sample_config)

        updates = {"downloads": "new_value"}
        store.update("test_key", updates)

        result = store.get("test_key")
        assert result["downloads"] == "new_value"

    def test_update_adds_new_keys(self, store, sample_config):
        """Test that update adds new top-level keys."""
        store.set("test_key", sample_config)

        updates = {"new_section": {"new_key": "new_value"}}
        store.update("test_key", updates)

        result = store.get("test_key")
        assert result["new_section"] == {"new_key": "new_value"}
        assert "subscriptions" in result  # Old keys still present

    def test_update_nonexistent_key_raises_error(self, store):
        """Test updating a nonexistent key raises ConfigNotFoundError."""
        with pytest.raises(ConfigNotFoundError):
            store.update("nonexistent_key", {"data": "value"})

    def test_deep_merge_nested_dicts(self, store):
        """Test deep merging of multiple levels of nesting."""
        original = {
            "level1": {"level2": {"level3": {"value": "original", "keep": "me"}}}
        }
        store.set("test_key", original)

        updates = {"level1": {"level2": {"level3": {"value": "updated"}}}}
        store.update("test_key", updates)

        result = store.get("test_key")
        assert result["level1"]["level2"]["level3"]["value"] == "updated"
        assert result["level1"]["level2"]["level3"]["keep"] == "me"


@pytest.mark.django_db
class TestModelConfigStoreListKeys:
    """Test listing configuration keys."""

    def test_list_keys_returns_all_keys(self, store):
        """Test listing all configuration keys."""
        store.set("key1", {"data": "1"})
        store.set("key2", {"data": "2"})
        store.set("key3", {"data": "3"})

        keys = store.list_keys()
        assert set(keys) == {"key1", "key2", "key3"}

    def test_list_keys_with_prefix(self, store):
        """Test listing keys filtered by prefix."""
        store.set("user_123", {"data": "1"})
        store.set("user_456", {"data": "2"})
        store.set("appsettings", {"data": "3"})

        keys = store.list_keys(prefix="user_")
        assert set(keys) == {"user_123", "user_456"}

    def test_list_keys_empty_database(self, store):
        """Test listing keys when database is empty."""
        keys = store.list_keys()
        assert keys == []

    def test_list_keys_no_matches_for_prefix(self, store):
        """Test listing keys with prefix that matches nothing."""
        store.set("key1", {"data": "1"})
        store.set("key2", {"data": "2"})

        keys = store.list_keys(prefix="nonexistent_")
        assert keys == []


@pytest.mark.django_db
class TestModelConfigStoreDataTypes:
    """Test handling of different data types."""

    def test_store_nested_structures(self, store):
        """Test storing complex nested structures."""
        complex_data = {
            "list": [1, 2, 3],
            "nested": {"dict": {"with": {"many": "levels"}}},
            "mixed": [{"key": "value"}, {"key2": "value2"}],
            "boolean": True,
            "null": None,
            "number": 42,
        }
        store.set("complex", complex_data)

        result = store.get("complex")
        assert result == complex_data

    def test_store_unicode_characters(self, store):
        """Test storing unicode characters."""
        unicode_data = {"text": "Hello 世界 🌍", "emoji": "🎉🎊🎈"}
        store.set("unicode", unicode_data)

        result = store.get("unicode")
        assert result == unicode_data

    def test_store_empty_dict(self, store):
        """Test storing an empty dictionary."""
        store.set("empty", {})

        result = store.get("empty")
        assert result == {}


@pytest.mark.django_db
class TestModelConfigStoreErrorHandling:
    """Test error handling."""

    def test_invalid_json_in_database_raises_error(self, store):
        """Test that invalid JSON in database raises ValueError."""
        # Manually insert invalid JSON
        ConfigData.objects.create(key="invalid", value="not valid json{")

        with pytest.raises(ValueError) as exc_info:
            store.get("invalid")

        assert "Invalid JSON" in str(exc_info.value)

    def test_set_with_non_serializable_data_raises_error(self, store):
        """Test that non-serializable data raises ValueError."""

        class NonSerializable:
            pass

        with pytest.raises(ValueError) as exc_info:
            store.set("test", {"obj": NonSerializable()})

        assert "serialize" in str(exc_info.value).lower()
