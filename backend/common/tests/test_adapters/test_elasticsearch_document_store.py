"""Tests for Elasticsearch document store adapter."""

from unittest.mock import MagicMock, patch

import pytest
from common.src.adapters.elasticsearch.document_store import (
    ElasticsearchDocumentStore,
)
from common.src.interfaces.document_store import DocumentNotFoundError


class TestElasticsearchDocumentStore:
    """Test Elasticsearch document store adapter."""

    @pytest.fixture
    def mock_es_index(self):
        """Mock ElasticIndex."""
        with patch(
            "common.src.adapters.elasticsearch.document_store.ElasticIndex"
        ) as mock:
            yield mock

    @pytest.fixture
    def store(self, mock_es_index):
        """Create store with mocked ES backend."""
        return ElasticsearchDocumentStore("ta_video")

    def test_init_sets_index_name(self, store):
        """Test initialization sets index name."""
        assert store.index_name == "ta_video"

    def test_get_document_found(self, store, mock_es_index):
        """Test get returns document when found."""
        mock_instance = mock_es_index.return_value
        mock_instance.get_document.return_value = {
            "youtube_id": "test123",
            "title": "Test Video",
        }

        result = store.get("test123")

        assert result == {"youtube_id": "test123", "title": "Test Video"}
        mock_instance.get_document.assert_called_once_with("test123")

    def test_get_document_not_found(self, store, mock_es_index):
        """Test get raises DocumentNotFoundError when not found."""
        mock_instance = mock_es_index.return_value
        mock_instance.get_document.return_value = None

        with pytest.raises(DocumentNotFoundError) as exc_info:
            store.get("nonexistent")

        assert exc_info.value.doc_id == "nonexistent"
        mock_instance.get_document.assert_called_once_with("nonexistent")

    def test_create_document(self, store, mock_es_index):
        """Test create stores document."""
        mock_instance = mock_es_index.return_value
        doc = {"youtube_id": "test123", "title": "Test Video"}

        store.create("test123", doc)

        mock_instance.add_document.assert_called_once_with("test123", doc)

    def test_update_document_found(self, store, mock_es_index):
        """Test update merges updates into existing document."""
        mock_instance = mock_es_index.return_value
        mock_instance.get_document.return_value = {
            "youtube_id": "test123",
            "title": "Old Title",
            "channel": "test_channel",
        }

        updates = {"title": "New Title"}
        store.update("test123", updates)

        # Should fetch existing, merge, then update
        mock_instance.get_document.assert_called_once_with("test123")
        mock_instance.update_document.assert_called_once_with(
            "test123",
            {"youtube_id": "test123", "title": "New Title", "channel": "test_channel"},
        )

    def test_update_document_not_found(self, store, mock_es_index):
        """Test update raises DocumentNotFoundError when not found."""
        mock_instance = mock_es_index.return_value
        mock_instance.get_document.return_value = None

        with pytest.raises(DocumentNotFoundError) as exc_info:
            store.update("nonexistent", {"title": "New"})

        assert exc_info.value.doc_id == "nonexistent"
        mock_instance.get_document.assert_called_once_with("nonexistent")
        mock_instance.update_document.assert_not_called()

    def test_delete_document_found(self, store, mock_es_index):
        """Test delete removes document."""
        mock_instance = mock_es_index.return_value
        mock_instance.delete_document.return_value = True

        store.delete("test123")

        mock_instance.delete_document.assert_called_once_with("test123")

    def test_delete_document_not_found(self, store, mock_es_index):
        """Test delete raises DocumentNotFoundError when not found."""
        mock_instance = mock_es_index.return_value
        mock_instance.delete_document.return_value = False

        with pytest.raises(DocumentNotFoundError) as exc_info:
            store.delete("nonexistent")

        assert exc_info.value.doc_id == "nonexistent"
        mock_instance.delete_document.assert_called_once_with("nonexistent")

    def test_exists_returns_true(self, store, mock_es_index):
        """Test exists returns True when document exists."""
        mock_instance = mock_es_index.return_value
        mock_instance.get_document.return_value = {"youtube_id": "test123"}

        assert store.exists("test123") is True
        mock_instance.get_document.assert_called_once_with("test123")

    def test_exists_returns_false(self, store, mock_es_index):
        """Test exists returns False when document doesn't exist."""
        mock_instance = mock_es_index.return_value
        mock_instance.get_document.return_value = None

        assert store.exists("nonexistent") is False
        mock_instance.get_document.assert_called_once_with("nonexistent")

    def test_query_all_documents(self, store, mock_es_index):
        """Test query returns all documents when no filters."""
        mock_instance = mock_es_index.return_value
        mock_instance.get_all_documents.return_value = [
            {"youtube_id": "vid1", "title": "Video 1"},
            {"youtube_id": "vid2", "title": "Video 2"},
        ]

        results = store.query()

        assert len(results) == 2
        assert results[0]["youtube_id"] == "vid1"
        assert results[1]["youtube_id"] == "vid2"
        mock_instance.get_all_documents.assert_called_once()

    def test_query_with_filters(self, store, mock_es_index):
        """Test query passes filters to ES."""
        mock_instance = mock_es_index.return_value
        mock_instance.search.return_value = [{"youtube_id": "vid1"}]

        filters = {"channel_id": "test_channel"}
        results = store.query(filters=filters)

        assert len(results) == 1
        mock_instance.search.assert_called_once_with(filters)

    def test_query_with_sort(self, store, mock_es_index):
        """Test query applies sorting."""
        mock_instance = mock_es_index.return_value
        mock_instance.search.return_value = [
            {"youtube_id": "vid2", "published": "2024-01-02"},
            {"youtube_id": "vid1", "published": "2024-01-01"},
        ]

        # Note: ES handles sorting on its side, we just pass the parameter
        sort = [("published", "desc")]
        results = store.query(sort=sort)

        assert len(results) == 2
        # Sorting is handled by ES, we just verify the call happened
        mock_instance.search.assert_called_once()

    def test_query_with_limit_and_offset(self, store, mock_es_index):
        """Test query applies limit and offset."""
        mock_instance = mock_es_index.return_value
        mock_instance.search.return_value = [{"youtube_id": "vid2"}]

        results = store.query(limit=1, offset=1)

        assert len(results) == 1
        # ES handles pagination on its side
        mock_instance.search.assert_called_once()

    def test_bulk_create_documents(self, store, mock_es_index):
        """Test bulk_create stores multiple documents."""
        mock_instance = mock_es_index.return_value

        documents = [
            ("vid1", {"youtube_id": "vid1", "title": "Video 1"}),
            ("vid2", {"youtube_id": "vid2", "title": "Video 2"}),
        ]

        store.bulk_create(documents)

        # Should call add_document for each
        assert mock_instance.add_document.call_count == 2
        mock_instance.add_document.assert_any_call(
            "vid1", {"youtube_id": "vid1", "title": "Video 1"}
        )
        mock_instance.add_document.assert_any_call(
            "vid2", {"youtube_id": "vid2", "title": "Video 2"}
        )

    def test_bulk_update_documents(self, store, mock_es_index):
        """Test bulk_update updates multiple documents."""
        mock_instance = mock_es_index.return_value

        documents = [
            ("vid1", {"title": "Updated 1"}),
            ("vid2", {"title": "Updated 2"}),
        ]

        store.bulk_update(documents)

        # Should call update_document for each
        assert mock_instance.update_document.call_count == 2
        mock_instance.update_document.assert_any_call("vid1", {"title": "Updated 1"})
        mock_instance.update_document.assert_any_call("vid2", {"title": "Updated 2"})

    def test_bulk_delete_documents(self, store, mock_es_index):
        """Test bulk_delete removes multiple documents."""
        mock_instance = mock_es_index.return_value

        doc_ids = ["vid1", "vid2", "vid3"]
        store.bulk_delete(doc_ids)

        # Should call delete_document for each
        assert mock_instance.delete_document.call_count == 3
        mock_instance.delete_document.assert_any_call("vid1")
        mock_instance.delete_document.assert_any_call("vid2")
        mock_instance.delete_document.assert_any_call("vid3")

    def test_count_all_documents(self, store, mock_es_index):
        """Test count returns total document count."""
        mock_instance = mock_es_index.return_value
        mock_instance.get_document_count.return_value = 42

        count = store.count()

        assert count == 42
        mock_instance.get_document_count.assert_called_once()

    def test_count_with_filters(self, store, mock_es_index):
        """Test count applies filters."""
        mock_instance = mock_es_index.return_value
        mock_instance.count_documents.return_value = 5

        filters = {"channel_id": "test_channel"}
        count = store.count(filters=filters)

        assert count == 5
        mock_instance.count_documents.assert_called_once_with(filters)
