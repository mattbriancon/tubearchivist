"""Tests for document store factory."""

from unittest.mock import patch

import pytest
from common.src.adapters.elasticsearch.document_store import (
    ElasticsearchDocumentStore,
)
from common.src.adapters.model.document_store import ModelDocumentStore
from common.src.document_store_factory import (
    get_channel_store,
    get_comment_store,
    get_document_store,
    get_download_store,
    get_playlist_store,
    get_subtitle_store,
    get_video_store,
)


class TestDocumentStoreFactory:
    """Test the document store factory."""

    @patch("common.src.document_store_factory.settings")
    def test_get_document_store_elasticsearch_default(self, mock_settings):
        """Test factory returns Elasticsearch store by default."""
        mock_settings.DOCUMENT_STORE_BACKEND = "elasticsearch"

        store = get_document_store("ta_download")

        assert isinstance(store, ElasticsearchDocumentStore)
        assert store.index_name == "ta_download"

    @patch("common.src.document_store_factory.settings")
    def test_get_document_store_model_backend(self, mock_settings):
        """Test factory returns Model store when configured."""
        mock_settings.DOCUMENT_STORE_BACKEND = "model"

        store = get_document_store("ta_download")

        assert isinstance(store, ModelDocumentStore)

    @patch("common.src.document_store_factory.settings")
    def test_get_document_store_sqlite_alias(self, mock_settings):
        """Test factory accepts 'sqlite' as alias for 'model'."""
        mock_settings.DOCUMENT_STORE_BACKEND = "sqlite"

        store = get_document_store("ta_video")

        assert isinstance(store, ModelDocumentStore)

    @patch("common.src.document_store_factory.settings")
    def test_get_document_store_case_insensitive(self, mock_settings):
        """Test factory is case insensitive."""
        mock_settings.DOCUMENT_STORE_BACKEND = "ELASTICSEARCH"

        store = get_document_store("ta_channel")

        assert isinstance(store, ElasticsearchDocumentStore)

    @patch("common.src.document_store_factory.settings")
    def test_get_document_store_unsupported_backend_raises_error(self, mock_settings):
        """Test unsupported backend raises ValueError."""
        mock_settings.DOCUMENT_STORE_BACKEND = "unsupported"

        with pytest.raises(ValueError) as exc_info:
            get_document_store("ta_download")

        assert "Unsupported DOCUMENT_STORE_BACKEND" in str(exc_info.value)

    @patch("common.src.document_store_factory.settings")
    def test_get_document_store_unknown_index_raises_error(self, mock_settings):
        """Test unknown index raises ValueError for model backend."""
        mock_settings.DOCUMENT_STORE_BACKEND = "model"

        with pytest.raises(ValueError) as exc_info:
            get_document_store("ta_unknown")

        assert "Unknown index" in str(exc_info.value)

    @patch("common.src.document_store_factory.settings")
    def test_get_document_store_all_valid_indices(self, mock_settings):
        """Test all valid indices work."""
        mock_settings.DOCUMENT_STORE_BACKEND = "elasticsearch"

        valid_indices = [
            "ta_download",
            "ta_video",
            "ta_channel",
            "ta_playlist",
            "ta_comment",
            "ta_subtitle",
        ]

        for index_name in valid_indices:
            store = get_document_store(index_name)
            assert isinstance(store, ElasticsearchDocumentStore)
            assert store.index_name == index_name


class TestConvenienceFunctions:
    """Test convenience functions for specific indices."""

    @patch("common.src.document_store_factory.settings")
    def test_get_download_store(self, mock_settings):
        """Test get_download_store convenience function."""
        mock_settings.DOCUMENT_STORE_BACKEND = "elasticsearch"

        store = get_download_store()

        assert isinstance(store, ElasticsearchDocumentStore)
        assert store.index_name == "ta_download"

    @patch("common.src.document_store_factory.settings")
    def test_get_video_store(self, mock_settings):
        """Test get_video_store convenience function."""
        mock_settings.DOCUMENT_STORE_BACKEND = "elasticsearch"

        store = get_video_store()

        assert isinstance(store, ElasticsearchDocumentStore)
        assert store.index_name == "ta_video"

    @patch("common.src.document_store_factory.settings")
    def test_get_channel_store(self, mock_settings):
        """Test get_channel_store convenience function."""
        mock_settings.DOCUMENT_STORE_BACKEND = "elasticsearch"

        store = get_channel_store()

        assert isinstance(store, ElasticsearchDocumentStore)
        assert store.index_name == "ta_channel"

    @patch("common.src.document_store_factory.settings")
    def test_get_playlist_store(self, mock_settings):
        """Test get_playlist_store convenience function."""
        mock_settings.DOCUMENT_STORE_BACKEND = "elasticsearch"

        store = get_playlist_store()

        assert isinstance(store, ElasticsearchDocumentStore)
        assert store.index_name == "ta_playlist"

    @patch("common.src.document_store_factory.settings")
    def test_get_comment_store(self, mock_settings):
        """Test get_comment_store convenience function."""
        mock_settings.DOCUMENT_STORE_BACKEND = "elasticsearch"

        store = get_comment_store()

        assert isinstance(store, ElasticsearchDocumentStore)
        assert store.index_name == "ta_comment"

    @patch("common.src.document_store_factory.settings")
    def test_get_subtitle_store(self, mock_settings):
        """Test get_subtitle_store convenience function."""
        mock_settings.DOCUMENT_STORE_BACKEND = "elasticsearch"

        store = get_subtitle_store()

        assert isinstance(store, ElasticsearchDocumentStore)
        assert store.index_name == "ta_subtitle"
