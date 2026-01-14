"""Tests for ModelDocumentStore adapter."""

import json

import pytest
from common.models import DownloadQueueItem
from common.src.adapters.model.document_store import ModelDocumentStore
from common.src.interfaces.document_store import DocumentNotFoundError


@pytest.fixture
def store():
    """Create a ModelDocumentStore instance for testing."""
    return ModelDocumentStore(DownloadQueueItem)


@pytest.fixture
def sample_document():
    """Sample document data."""
    return {
        "youtube_id": "test123",
        "title": "Test Video",
        "channel_id": "channel123",
        "status": "pending",
        "timestamp": 1234567890,
    }


@pytest.mark.django_db
class TestModelDocumentStoreBasicOperations:
    """Test basic CRUD operations."""

    def test_create_and_get_document(self, store, sample_document):
        """Test creating and retrieving a document."""
        store.create("test123", sample_document)

        result = store.get("test123")
        assert result == sample_document

        # Verify in database
        db_obj = DownloadQueueItem.objects.get(doc_id="test123")
        assert json.loads(db_obj.content) == sample_document

    def test_get_nonexistent_document_raises_error(self, store):
        """Test getting a document that doesn't exist."""
        with pytest.raises(DocumentNotFoundError) as exc_info:
            store.get("nonexistent")

        assert exc_info.value.doc_id == "nonexistent"

    def test_create_duplicate_raises_error(self, store, sample_document):
        """Test creating a document that already exists."""
        store.create("test123", sample_document)

        with pytest.raises(ValueError) as exc_info:
            store.create("test123", sample_document)

        assert "already exists" in str(exc_info.value)

    def test_update_existing_document(self, store, sample_document):
        """Test updating an existing document."""
        store.create("test123", sample_document)

        updated_doc = {**sample_document, "status": "ignore"}
        store.update("test123", updated_doc)

        result = store.get("test123")
        assert result["status"] == "ignore"

    def test_update_nonexistent_document_raises_error(self, store, sample_document):
        """Test updating a document that doesn't exist."""
        with pytest.raises(DocumentNotFoundError):
            store.update("nonexistent", sample_document)

    def test_upsert_creates_new_document(self, store, sample_document):
        """Test upsert creates document if it doesn't exist."""
        store.upsert("test123", sample_document)

        result = store.get("test123")
        assert result == sample_document

    def test_upsert_updates_existing_document(self, store, sample_document):
        """Test upsert updates document if it exists."""
        store.create("test123", sample_document)

        updated_doc = {**sample_document, "status": "ignore"}
        store.upsert("test123", updated_doc)

        result = store.get("test123")
        assert result["status"] == "ignore"

    def test_delete_existing_document(self, store, sample_document):
        """Test deleting an existing document."""
        store.create("test123", sample_document)
        assert store.exists("test123")

        store.delete("test123")

        assert not store.exists("test123")
        with pytest.raises(DocumentNotFoundError):
            store.get("test123")

    def test_delete_nonexistent_document_raises_error(self, store):
        """Test deleting a document that doesn't exist."""
        with pytest.raises(DocumentNotFoundError):
            store.delete("nonexistent")

    def test_exists_returns_true_for_existing_document(self, store, sample_document):
        """Test exists returns True for existing document."""
        store.create("test123", sample_document)
        assert store.exists("test123") is True

    def test_exists_returns_false_for_nonexistent_document(self, store):
        """Test exists returns False for nonexistent document."""
        assert store.exists("nonexistent") is False


@pytest.mark.django_db
class TestModelDocumentStoreQuerying:
    """Test query operations."""

    def test_query_all_documents(self, store):
        """Test querying all documents."""
        store.create("doc1", {"status": "pending", "title": "Video 1"})
        store.create("doc2", {"status": "ignore", "title": "Video 2"})
        store.create("doc3", {"status": "pending", "title": "Video 3"})

        results = store.query()
        assert len(results) == 3

    def test_query_with_filters(self, store):
        """Test querying with filters."""
        store.create("doc1", {"status": "pending", "channel_id": "ch1"})
        store.create("doc2", {"status": "ignore", "channel_id": "ch1"})
        store.create("doc3", {"status": "pending", "channel_id": "ch2"})

        # Filter by status
        results = store.query(filters={"status": "pending"})
        assert len(results) == 2
        assert all(doc["status"] == "pending" for doc in results)

        # Filter by multiple fields
        results = store.query(filters={"status": "pending", "channel_id": "ch1"})
        assert len(results) == 1

    def test_query_with_limit(self, store):
        """Test querying with limit."""
        for i in range(10):
            store.create(f"doc{i}", {"index": i})

        results = store.query(limit=5)
        assert len(results) == 5

    def test_query_with_offset(self, store):
        """Test querying with offset."""
        for i in range(10):
            store.create(f"doc{i}", {"index": i})

        results = store.query(offset=5, limit=3)
        assert len(results) == 3

    def test_query_with_sorting(self, store):
        """Test querying with sorting."""
        store.create("doc1", {"timestamp": 3})
        store.create("doc2", {"timestamp": 1})
        store.create("doc3", {"timestamp": 2})

        # Sort ascending
        results = store.query(sort=[("timestamp", "asc")])
        assert [doc["timestamp"] for doc in results] == [1, 2, 3]

        # Sort descending
        results = store.query(sort=[("timestamp", "desc")])
        assert [doc["timestamp"] for doc in results] == [3, 2, 1]

    def test_query_nested_field_filtering(self, store):
        """Test filtering on nested fields."""
        store.create("doc1", {"channel": {"id": "ch1", "name": "Channel 1"}})
        store.create("doc2", {"channel": {"id": "ch2", "name": "Channel 2"}})

        results = store.query(filters={"channel.id": "ch1"})
        assert len(results) == 1
        assert results[0]["channel"]["id"] == "ch1"

    def test_count_all_documents(self, store):
        """Test counting all documents."""
        for i in range(5):
            store.create(f"doc{i}", {"status": "pending"})

        count = store.count()
        assert count == 5

    def test_count_with_filters(self, store):
        """Test counting with filters."""
        store.create("doc1", {"status": "pending"})
        store.create("doc2", {"status": "ignore"})
        store.create("doc3", {"status": "pending"})

        count = store.count(filters={"status": "pending"})
        assert count == 2


@pytest.mark.django_db
class TestModelDocumentStoreBulkOperations:
    """Test bulk operations."""

    def test_bulk_create(self, store):
        """Test bulk creating documents."""
        documents = [
            ("doc1", {"title": "Video 1"}),
            ("doc2", {"title": "Video 2"}),
            ("doc3", {"title": "Video 3"}),
        ]

        store.bulk_create(documents)

        assert store.count() == 3
        assert store.get("doc1")["title"] == "Video 1"
        assert store.get("doc2")["title"] == "Video 2"

    def test_bulk_create_with_duplicates_ignores_conflicts(self, store):
        """Test bulk create ignores existing documents."""
        store.create("doc1", {"title": "Original"})

        documents = [
            ("doc1", {"title": "Duplicate"}),  # Already exists
            ("doc2", {"title": "New"}),
        ]

        store.bulk_create(documents)

        # Original should remain
        assert store.get("doc1")["title"] == "Original"
        # New one should be created
        assert store.exists("doc2")

    def test_bulk_delete(self, store):
        """Test bulk deleting documents."""
        for i in range(5):
            store.create(f"doc{i}", {"index": i})

        deleted_count = store.bulk_delete(["doc1", "doc2", "doc3"])

        assert deleted_count == 3
        assert store.count() == 2
        assert not store.exists("doc1")
        assert store.exists("doc0")  # Not deleted

    def test_bulk_delete_nonexistent_documents(self, store):
        """Test bulk delete with nonexistent documents."""
        store.create("doc1", {"title": "Test"})

        deleted_count = store.bulk_delete(["doc1", "doc2", "doc3"])

        # Only doc1 existed and was deleted
        assert deleted_count == 1


@pytest.mark.django_db
class TestModelDocumentStoreDataTypes:
    """Test handling different data types."""

    def test_store_complex_nested_structure(self, store):
        """Test storing complex nested data."""
        document = {
            "youtube_id": "test123",
            "channel": {
                "channel_id": "ch123",
                "channel_name": "Test Channel",
                "channel_subs": 1000,
            },
            "tags": ["tag1", "tag2", "tag3"],
            "stats": {"views": 100, "likes": 10, "comments": 5},
        }

        store.create("test123", document)
        result = store.get("test123")

        assert result == document
        assert result["channel"]["channel_subs"] == 1000
        assert len(result["tags"]) == 3

    def test_store_unicode_characters(self, store):
        """Test storing unicode characters."""
        document = {"title": "Hello 世界 🌍", "description": "Test 日本語"}

        store.create("test123", document)
        result = store.get("test123")

        assert result["title"] == "Hello 世界 🌍"
        assert result["description"] == "Test 日本語"

    def test_store_empty_document(self, store):
        """Test storing an empty document."""
        store.create("empty", {})

        result = store.get("empty")
        assert result == {}


@pytest.mark.django_db
class TestModelDocumentStoreErrorHandling:
    """Test error handling."""

    def test_invalid_json_in_database_raises_error(self, store):
        """Test that invalid JSON raises ValueError."""
        # Manually insert invalid JSON
        DownloadQueueItem.objects.create(doc_id="invalid", content="not valid json{")

        with pytest.raises(ValueError) as exc_info:
            store.get("invalid")

        assert "Invalid JSON" in str(exc_info.value)

    def test_non_serializable_data_raises_error(self, store):
        """Test that non-serializable data raises ValueError."""

        class NonSerializable:
            pass

        with pytest.raises(ValueError) as exc_info:
            store.create("test", {"obj": NonSerializable()})

        assert "serialize" in str(exc_info.value).lower()
