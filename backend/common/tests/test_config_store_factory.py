"""Tests for config store factory."""

from unittest.mock import patch

import pytest
from common.src.adapters.elasticsearch.config_store import ElasticsearchConfigStore
from common.src.adapters.model.config_store import ModelConfigStore
from common.src.config_store_factory import get_config_store


class TestConfigStoreFactory:
    """Test the config store factory."""

    @patch("common.src.config_store_factory.settings")
    def test_get_config_store_elasticsearch_default(self, mock_settings):
        """Test factory returns Elasticsearch store by default."""
        mock_settings.CONFIG_STORE_BACKEND = "elasticsearch"

        store = get_config_store()

        assert isinstance(store, ElasticsearchConfigStore)

    @patch("common.src.config_store_factory.settings")
    def test_get_config_store_model_backend(self, mock_settings):
        """Test factory returns Model store when configured."""
        mock_settings.CONFIG_STORE_BACKEND = "model"

        store = get_config_store()

        assert isinstance(store, ModelConfigStore)

    @patch("common.src.config_store_factory.settings")
    def test_get_config_store_sqlite_alias(self, mock_settings):
        """Test factory accepts 'sqlite' as alias for 'model'."""
        mock_settings.CONFIG_STORE_BACKEND = "sqlite"

        store = get_config_store()

        assert isinstance(store, ModelConfigStore)

    @patch("common.src.config_store_factory.settings")
    def test_get_config_store_case_insensitive(self, mock_settings):
        """Test factory is case insensitive."""
        mock_settings.CONFIG_STORE_BACKEND = "ELASTICSEARCH"

        store = get_config_store()

        assert isinstance(store, ElasticsearchConfigStore)

    @patch("common.src.config_store_factory.settings")
    def test_get_config_store_unsupported_backend_raises_error(self, mock_settings):
        """Test unsupported backend raises ValueError."""
        mock_settings.CONFIG_STORE_BACKEND = "unsupported"

        with pytest.raises(ValueError) as exc_info:
            get_config_store()

        assert "Unsupported CONFIG_STORE_BACKEND" in str(exc_info.value)
        assert "unsupported" in str(exc_info.value)

    @patch("common.src.config_store_factory.settings")
    def test_get_config_store_returns_new_instance_each_time(self, mock_settings):
        """Test factory returns new instances (not singleton)."""
        mock_settings.CONFIG_STORE_BACKEND = "elasticsearch"

        store1 = get_config_store()
        store2 = get_config_store()

        # Should be different instances
        assert store1 is not store2
        # But same type
        assert type(store1) == type(store2)
