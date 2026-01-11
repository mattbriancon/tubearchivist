"""Tests for ElasticsearchConfigStore adapter."""

from unittest.mock import MagicMock, patch

import pytest
from common.src.adapters.elasticsearch.config_store import ElasticsearchConfigStore
from common.src.interfaces.config_store import ConfigNotFoundError


@pytest.fixture
def store():
    """Create an ElasticsearchConfigStore instance."""
    return ElasticsearchConfigStore()


@pytest.fixture
def sample_config():
    """Sample configuration data."""
    return {
        "subscriptions": {"channel_size": 50},
        "downloads": {"limit_speed": None},
    }


class TestElasticsearchConfigStoreBasicOperations:
    """Test basic CRUD operations."""

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_get_existing_config(self, mock_wrap, store, sample_config):
        """Test retrieving existing configuration."""
        mock_instance = MagicMock()
        mock_instance.get.return_value = ({"_source": sample_config}, 200)
        mock_wrap.return_value = mock_instance

        result = store.get("test_key")

        assert result == sample_config
        mock_wrap.assert_called_once_with("ta_config/_doc/test_key")
        mock_instance.get.assert_called_once_with(print_error=False)

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_get_nonexistent_key_raises_error(self, mock_wrap, store):
        """Test getting nonexistent key raises ConfigNotFoundError."""
        mock_instance = MagicMock()
        mock_instance.get.return_value = ({}, 404)
        mock_wrap.return_value = mock_instance

        with pytest.raises(ConfigNotFoundError) as exc_info:
            store.get("nonexistent_key")

        assert exc_info.value.key == "nonexistent_key"

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_get_elasticsearch_error_raises_value_error(self, mock_wrap, store):
        """Test ES error raises ValueError."""
        mock_instance = MagicMock()
        mock_instance.get.return_value = ({"error": "ES error"}, 500)
        mock_wrap.return_value = mock_instance

        with pytest.raises(ValueError) as exc_info:
            store.get("test_key")

        assert "Elasticsearch error" in str(exc_info.value)

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_set_new_config(self, mock_wrap, store, sample_config):
        """Test storing new configuration."""
        mock_instance = MagicMock()
        mock_instance.post.return_value = ({"result": "created"}, 201)
        mock_wrap.return_value = mock_instance

        store.set("test_key", sample_config)

        mock_wrap.assert_called_once_with("ta_config/_doc/test_key")
        mock_instance.post.assert_called_once_with(sample_config)

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_set_update_existing_config(self, mock_wrap, store, sample_config):
        """Test updating existing configuration."""
        mock_instance = MagicMock()
        mock_instance.post.return_value = ({"result": "updated"}, 200)
        mock_wrap.return_value = mock_instance

        store.set("test_key", sample_config)

        mock_instance.post.assert_called_once_with(sample_config)

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_set_elasticsearch_error_raises_value_error(self, mock_wrap, store):
        """Test ES error on set raises ValueError."""
        mock_instance = MagicMock()
        mock_instance.post.return_value = ({"error": "ES error"}, 500)
        mock_wrap.return_value = mock_instance

        with pytest.raises(ValueError) as exc_info:
            store.set("test_key", {"data": "value"})

        assert "Elasticsearch error" in str(exc_info.value)

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_delete_existing_config(self, mock_wrap, store):
        """Test deleting existing configuration."""
        mock_instance = MagicMock()
        mock_instance.delete.return_value = ({"result": "deleted"}, 200)
        mock_wrap.return_value = mock_instance

        store.delete("test_key")

        mock_wrap.assert_called_once_with("ta_config/_doc/test_key")
        mock_instance.delete.assert_called_once()

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_delete_nonexistent_key_raises_error(self, mock_wrap, store):
        """Test deleting nonexistent key raises ConfigNotFoundError."""
        mock_instance = MagicMock()
        mock_instance.delete.return_value = ({}, 404)
        mock_wrap.return_value = mock_instance

        with pytest.raises(ConfigNotFoundError):
            store.delete("nonexistent_key")

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_delete_elasticsearch_error_raises_value_error(self, mock_wrap, store):
        """Test ES error on delete raises ValueError."""
        mock_instance = MagicMock()
        mock_instance.delete.return_value = ({"error": "ES error"}, 500)
        mock_wrap.return_value = mock_instance

        with pytest.raises(ValueError) as exc_info:
            store.delete("test_key")

        assert "Elasticsearch error" in str(exc_info.value)


class TestElasticsearchConfigStoreUpdate:
    """Test update operations."""

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_update_existing_config(self, mock_wrap, store):
        """Test updating existing configuration."""
        mock_instance = MagicMock()
        mock_instance.post.return_value = ({"result": "updated"}, 200)
        mock_wrap.return_value = mock_instance

        updates = {"subscriptions": {"channel_size": 100}}
        store.update("test_key", updates)

        mock_wrap.assert_called_once_with("ta_config/_update/test_key")
        # ES update API wraps updates in "doc"
        mock_instance.post.assert_called_once_with({"doc": updates})

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_update_nonexistent_key_raises_error(self, mock_wrap, store):
        """Test updating nonexistent key raises ConfigNotFoundError."""
        mock_instance = MagicMock()
        mock_instance.post.return_value = ({}, 404)
        mock_wrap.return_value = mock_instance

        with pytest.raises(ConfigNotFoundError):
            store.update("nonexistent_key", {"data": "value"})

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_update_elasticsearch_error_raises_value_error(self, mock_wrap, store):
        """Test ES error on update raises ValueError."""
        mock_instance = MagicMock()
        mock_instance.post.return_value = ({"error": "ES error"}, 500)
        mock_wrap.return_value = mock_instance

        with pytest.raises(ValueError) as exc_info:
            store.update("test_key", {"data": "value"})

        assert "Elasticsearch error" in str(exc_info.value)


class TestElasticsearchConfigStoreExists:
    """Test exists operations."""

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_exists_returns_true_for_existing_key(self, mock_wrap, store):
        """Test exists returns True for existing key."""
        mock_instance = MagicMock()
        mock_instance.get.return_value = ({"_source": {}}, 200)
        mock_wrap.return_value = mock_instance

        assert store.exists("test_key") is True

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_exists_returns_false_for_nonexistent_key(self, mock_wrap, store):
        """Test exists returns False for nonexistent key."""
        mock_instance = MagicMock()
        mock_instance.get.return_value = ({}, 404)
        mock_wrap.return_value = mock_instance

        assert store.exists("nonexistent_key") is False


class TestElasticsearchConfigStoreListKeys:
    """Test listing configuration keys."""

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_list_all_keys(self, mock_wrap, store):
        """Test listing all configuration keys."""
        mock_instance = MagicMock()
        mock_instance.get.return_value = (
            {
                "hits": {
                    "hits": [
                        {"_id": "key1"},
                        {"_id": "key2"},
                        {"_id": "key3"},
                    ]
                }
            },
            200,
        )
        mock_wrap.return_value = mock_instance

        keys = store.list_keys()

        assert keys == ["key1", "key2", "key3"]
        # Verify query structure
        call_args = mock_instance.get.call_args
        query = call_args[1]["data"]
        assert query["query"] == {"match_all": {}}
        assert query["_source"] is False

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_list_keys_with_prefix(self, mock_wrap, store):
        """Test listing keys with prefix filter."""
        mock_instance = MagicMock()
        mock_instance.get.return_value = (
            {"hits": {"hits": [{"_id": "user_123"}, {"_id": "user_456"}]}},
            200,
        )
        mock_wrap.return_value = mock_instance

        keys = store.list_keys(prefix="user_")

        assert keys == ["user_123", "user_456"]
        # Verify prefix query
        call_args = mock_instance.get.call_args
        query = call_args[1]["data"]
        assert query["query"] == {"prefix": {"_id": "user_"}}

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_list_keys_empty_result(self, mock_wrap, store):
        """Test listing keys when no keys exist."""
        mock_instance = MagicMock()
        mock_instance.get.return_value = ({"hits": {"hits": []}}, 200)
        mock_wrap.return_value = mock_instance

        keys = store.list_keys()

        assert keys == []

    @patch("common.src.adapters.elasticsearch.config_store.ElasticWrap")
    def test_list_keys_elasticsearch_error_raises_value_error(self, mock_wrap, store):
        """Test ES error on list_keys raises ValueError."""
        mock_instance = MagicMock()
        mock_instance.get.return_value = ({"error": "ES error"}, 500)
        mock_wrap.return_value = mock_instance

        with pytest.raises(ValueError) as exc_info:
            store.list_keys()

        assert "Elasticsearch error" in str(exc_info.value)
