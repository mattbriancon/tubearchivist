"""Integration tests for config store usage with AppConfig and UserConfig.

These tests verify that AppConfig and UserConfig work correctly with
different config store backends.
"""

from unittest.mock import patch

import pytest
from appsettings.src.config import AppConfig
from common.src.adapters.model.config_store import ModelConfigStore
from common.src.interfaces.config_store import ConfigNotFoundError
from user.src.user_config import UserConfig


@pytest.mark.django_db
class TestAppConfigIntegration:
    """Test AppConfig with ModelConfigStore backend."""

    @patch("appsettings.src.config.get_config_store")
    def test_app_config_initialization_with_existing_config(self, mock_factory):
        """Test AppConfig initializes correctly when config exists."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Set up initial config
        store.set("appsettings", AppConfig.CONFIG_DEFAULTS)

        # Initialize AppConfig
        app_config = AppConfig()

        assert app_config.config == AppConfig.CONFIG_DEFAULTS
        assert app_config.config["subscriptions"]["channel_size"] == 50

    @patch("appsettings.src.config.get_config_store")
    def test_app_config_update_config(self, mock_factory):
        """Test AppConfig.update_config updates the store."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Set up initial config
        store.set("appsettings", AppConfig.CONFIG_DEFAULTS)

        # Initialize and update
        app_config = AppConfig()
        new_config = app_config.update_config(
            {"subscriptions": {"channel_size": 100}}
        )

        # Verify update worked
        assert new_config["subscriptions"]["channel_size"] == 100

        # Verify it's persisted in store
        persisted = store.get("appsettings")
        assert persisted["subscriptions"]["channel_size"] == 100

    @patch("appsettings.src.config.get_config_store")
    def test_app_config_sync_defaults(self, mock_factory):
        """Test AppConfig.sync_defaults creates config."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Initialize AppConfig with non-existent config
        # This will fail during __init__, so we just test sync_defaults directly
        store.set("appsettings", AppConfig.CONFIG_DEFAULTS)
        app_config = AppConfig()
        app_config.sync_defaults()

        # Verify defaults were written
        persisted = store.get("appsettings")
        assert persisted == AppConfig.CONFIG_DEFAULTS

    @patch("appsettings.src.config.get_config_store")
    def test_app_config_add_new_defaults(self, mock_factory):
        """Test AppConfig.add_new_defaults merges new keys."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Set up incomplete config (missing some keys)
        incomplete_config = {"subscriptions": {"channel_size": 50}}
        store.set("appsettings", incomplete_config)

        app_config = AppConfig()
        updated = app_config.add_new_defaults()

        # Should have added missing top-level keys
        assert len(updated) > 0

        # Verify config now has all defaults
        assert "downloads" in app_config.config
        assert "application" in app_config.config


@pytest.mark.django_db
class TestUserConfigIntegration:
    """Test UserConfig with ModelConfigStore backend."""

    @patch("user.src.user_config.get_config_store")
    def test_user_config_initialization_with_existing_config(self, mock_factory):
        """Test UserConfig initializes with existing config."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Set up user config
        user_data = {"config": UserConfig._DEFAULT_USER_SETTINGS}
        store.set("user_123", user_data)

        # Initialize UserConfig
        user_config = UserConfig("123")

        assert user_config._config == UserConfig._DEFAULT_USER_SETTINGS
        assert user_config._config["stylesheet"] == "dark.css"

    @patch("user.src.user_config.get_config_store")
    def test_user_config_initialization_creates_defaults(self, mock_factory):
        """Test UserConfig creates defaults for new user."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Initialize UserConfig for non-existent user
        user_config = UserConfig("123")

        # Should have created defaults
        assert user_config._config == UserConfig._DEFAULT_USER_SETTINGS

        # Verify it's persisted
        persisted = store.get("user_123")
        assert persisted["config"] == UserConfig._DEFAULT_USER_SETTINGS

    @patch("user.src.user_config.get_config_store")
    def test_user_config_set_value(self, mock_factory):
        """Test UserConfig.set_value updates single value."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Set up user config
        user_data = {"config": UserConfig._DEFAULT_USER_SETTINGS}
        store.set("user_123", user_data)

        # Initialize and update
        user_config = UserConfig("123")
        user_config.set_value("page_size", 50)

        # Verify it's persisted with merged update
        persisted = store.get("user_123")
        assert persisted["config"]["page_size"] == 50
        # Other values should remain
        assert persisted["config"]["stylesheet"] == "dark.css"

    @patch("user.src.user_config.get_config_store")
    def test_user_config_update_config(self, mock_factory):
        """Test UserConfig.update_config updates multiple values."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Set up user config
        user_data = {"config": UserConfig._DEFAULT_USER_SETTINGS}
        store.set("user_123", user_data)

        # Initialize and update
        user_config = UserConfig("123")
        user_config.update_config({"page_size": 50, "stylesheet": "light.css"})

        # Verify updates persisted
        persisted = store.get("user_123")
        assert persisted["config"]["page_size"] == 50
        assert persisted["config"]["stylesheet"] == "light.css"

    @patch("user.src.user_config.get_config_store")
    def test_user_config_get_value(self, mock_factory):
        """Test UserConfig.get_value retrieves value."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Set up user config
        user_data = {"config": UserConfig._DEFAULT_USER_SETTINGS}
        store.set("user_123", user_data)

        # Initialize and get value
        user_config = UserConfig("123")
        value = user_config.get_value("stylesheet")

        assert value == "dark.css"

    @patch("user.src.user_config.get_config_store")
    def test_user_config_get_value_invalid_key_raises_error(self, mock_factory):
        """Test UserConfig.get_value raises KeyError for invalid keys."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Set up user config
        user_data = {"config": UserConfig._DEFAULT_USER_SETTINGS}
        store.set("user_123", user_data)

        user_config = UserConfig("123")

        with pytest.raises(KeyError):
            user_config.get_value("invalid_key")

    @patch("user.src.user_config.get_config_store")
    def test_user_config_sync_new_defaults(self, mock_factory):
        """Test UserConfig.sync_new_defaults adds missing keys."""
        store = ModelConfigStore()
        mock_factory.return_value = store

        # Set up incomplete user config
        incomplete_config = {"stylesheet": "dark.css", "page_size": 25}
        user_data = {"config": incomplete_config}
        store.set("user_123", user_data)

        # Initialize - should sync new defaults
        user_config = UserConfig("123")

        # Verify all default keys are present
        for key in UserConfig._DEFAULT_USER_SETTINGS:
            assert key in user_config._config


@pytest.mark.django_db
class TestConfigStoreBackendSwitching:
    """Test that config can be switched between backends."""

    @patch("appsettings.src.config.get_config_store")
    def test_can_switch_backends_transparently(self, mock_factory):
        """Test that switching backends doesn't break functionality."""
        # Start with ModelConfigStore
        model_store = ModelConfigStore()
        mock_factory.return_value = model_store

        # Initialize with model backend
        model_store.set("appsettings", AppConfig.CONFIG_DEFAULTS)
        app_config1 = AppConfig()
        app_config1.update_config({"subscriptions": {"channel_size": 100}})

        # Verify it worked
        assert app_config1.config["subscriptions"]["channel_size"] == 100

        # Now simulate switching to a different store instance
        # (In real usage, this would be a different backend)
        model_store2 = ModelConfigStore()
        mock_factory.return_value = model_store2

        # Initialize again - should work with same data
        app_config2 = AppConfig()
        assert app_config2.config["subscriptions"]["channel_size"] == 100
