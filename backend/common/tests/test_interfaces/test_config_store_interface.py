"""Tests for ConfigStore interface contract.

These tests verify that the interface is correctly defined and that
implementations adhere to the contract.
"""

from abc import ABC

import pytest
from common.src.interfaces.config_store import ConfigNotFoundError, ConfigStore


class TestConfigStoreInterface:
    """Test the ConfigStore interface definition."""

    def test_config_store_is_abstract(self):
        """Test that ConfigStore is an abstract base class."""
        assert issubclass(ConfigStore, ABC)

    def test_config_store_cannot_be_instantiated(self):
        """Test that ConfigStore cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ConfigStore()

    def test_config_store_has_required_methods(self):
        """Test that ConfigStore defines all required abstract methods."""
        required_methods = ["get", "set", "update", "delete", "exists", "list_keys"]

        for method_name in required_methods:
            assert hasattr(ConfigStore, method_name)
            method = getattr(ConfigStore, method_name)
            assert callable(method)


class TestConfigNotFoundError:
    """Test ConfigNotFoundError exception."""

    def test_exception_stores_key(self):
        """Test that exception stores the key that wasn't found."""
        error = ConfigNotFoundError("test_key")
        assert error.key == "test_key"

    def test_exception_message_includes_key(self):
        """Test that exception message includes the key."""
        error = ConfigNotFoundError("test_key")
        assert "test_key" in str(error)

    def test_exception_is_subclass_of_exception(self):
        """Test that ConfigNotFoundError is a proper exception."""
        assert issubclass(ConfigNotFoundError, Exception)

    def test_exception_can_be_raised_and_caught(self):
        """Test that exception can be raised and caught normally."""
        with pytest.raises(ConfigNotFoundError) as exc_info:
            raise ConfigNotFoundError("my_key")

        assert exc_info.value.key == "my_key"


class MockConfigStore(ConfigStore):
    """Mock implementation for testing interface contract."""

    def __init__(self):
        self.data = {}

    def get(self, key: str) -> dict:
        if key not in self.data:
            raise ConfigNotFoundError(key)
        return self.data[key]

    def set(self, key: str, value: dict) -> None:
        self.data[key] = value

    def update(self, key: str, updates: dict) -> None:
        if key not in self.data:
            raise ConfigNotFoundError(key)
        self.data[key].update(updates)

    def delete(self, key: str) -> None:
        if key not in self.data:
            raise ConfigNotFoundError(key)
        del self.data[key]

    def exists(self, key: str) -> bool:
        return key in self.data

    def list_keys(self, prefix: str | None = None) -> list[str]:
        if prefix is None:
            return list(self.data.keys())
        return [k for k in self.data.keys() if k.startswith(prefix)]


class TestConfigStoreContract:
    """Test that a proper implementation adheres to the interface contract."""

    @pytest.fixture
    def store(self):
        """Create a mock store for testing."""
        return MockConfigStore()

    def test_get_returns_dict(self, store):
        """Test that get returns a dictionary."""
        store.set("key", {"data": "value"})
        result = store.get("key")
        assert isinstance(result, dict)

    def test_get_raises_config_not_found_error(self, store):
        """Test that get raises ConfigNotFoundError for missing keys."""
        with pytest.raises(ConfigNotFoundError):
            store.get("nonexistent")

    def test_set_accepts_dict_value(self, store):
        """Test that set accepts dictionary values."""
        store.set("key", {"data": "value"})
        # Should not raise

    def test_set_returns_none(self, store):
        """Test that set returns None."""
        result = store.set("key", {"data": "value"})
        assert result is None

    def test_update_returns_none(self, store):
        """Test that update returns None."""
        store.set("key", {"data": "value"})
        result = store.update("key", {"new": "data"})
        assert result is None

    def test_update_raises_config_not_found_error(self, store):
        """Test that update raises ConfigNotFoundError for missing keys."""
        with pytest.raises(ConfigNotFoundError):
            store.update("nonexistent", {"data": "value"})

    def test_delete_returns_none(self, store):
        """Test that delete returns None."""
        store.set("key", {"data": "value"})
        result = store.delete("key")
        assert result is None

    def test_delete_raises_config_not_found_error(self, store):
        """Test that delete raises ConfigNotFoundError for missing keys."""
        with pytest.raises(ConfigNotFoundError):
            store.delete("nonexistent")

    def test_exists_returns_bool(self, store):
        """Test that exists returns a boolean."""
        result = store.exists("key")
        assert isinstance(result, bool)

    def test_exists_true_for_existing_key(self, store):
        """Test that exists returns True for existing keys."""
        store.set("key", {"data": "value"})
        assert store.exists("key") is True

    def test_exists_false_for_missing_key(self, store):
        """Test that exists returns False for missing keys."""
        assert store.exists("nonexistent") is False

    def test_list_keys_returns_list(self, store):
        """Test that list_keys returns a list."""
        result = store.list_keys()
        assert isinstance(result, list)

    def test_list_keys_returns_list_of_strings(self, store):
        """Test that list_keys returns a list of strings."""
        store.set("key1", {})
        store.set("key2", {})
        keys = store.list_keys()
        assert all(isinstance(k, str) for k in keys)

    def test_list_keys_with_prefix_filters_correctly(self, store):
        """Test that list_keys filters by prefix."""
        store.set("user_1", {})
        store.set("user_2", {})
        store.set("config", {})

        keys = store.list_keys(prefix="user_")
        assert "user_1" in keys
        assert "user_2" in keys
        assert "config" not in keys
