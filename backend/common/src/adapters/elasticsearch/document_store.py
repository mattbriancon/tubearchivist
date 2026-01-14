"""
Elasticsearch implementation of DocumentStore interface.

This adapter wraps Elasticsearch operations for document storage.
"""

from typing import Any

from common.src.es_connect import ElasticWrap, IndexPaginate
from common.src.interfaces.document_store import (
    DocumentNotFoundError,
    DocumentStore,
)


class ElasticsearchDocumentStore(DocumentStore):
    """
    Elasticsearch-backed document storage.

    Stores documents in an ES index with document IDs.
    """

    def __init__(self, index_name: str):
        """
        Initialize with an index name.

        Args:
            index_name: Elasticsearch index name (e.g., "ta_download")
        """
        self.index_name = index_name

    def _get_doc_path(self, doc_id: str) -> str:
        """Get ES document path."""
        return f"{self.index_name}/_doc/{doc_id}"

    def _get_update_path(self, doc_id: str) -> str:
        """Get ES update path."""
        return f"{self.index_name}/_update/{doc_id}"

    def get(self, doc_id: str) -> dict[str, Any]:
        """Retrieve a document by ID."""
        path = self._get_doc_path(doc_id)
        response, status_code = ElasticWrap(path).get(print_error=False)

        if status_code == 200:
            return response.get("_source", {})
        elif status_code == 404:
            raise DocumentNotFoundError(doc_id)
        else:
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

    def create(self, doc_id: str, document: dict[str, Any]) -> None:
        """Create a new document."""
        path = self._get_doc_path(doc_id)

        # Use create operation to fail if document exists
        response, status_code = ElasticWrap(path).put(document, params={"op_type": "create"})

        if status_code == 409:
            raise ValueError(f"Document {doc_id} already exists")
        elif status_code not in (200, 201):
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

    def update(self, doc_id: str, document: dict[str, Any]) -> None:
        """Update an existing document."""
        path = self._get_doc_path(doc_id)
        response, status_code = ElasticWrap(path).post(document)

        if status_code == 404:
            raise DocumentNotFoundError(doc_id)
        elif status_code not in (200, 201):
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

    def upsert(self, doc_id: str, document: dict[str, Any]) -> None:
        """Create or update a document."""
        path = self._get_doc_path(doc_id)
        response, status_code = ElasticWrap(path).post(document)

        if status_code not in (200, 201):
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

    def delete(self, doc_id: str) -> None:
        """Delete a document."""
        path = self._get_doc_path(doc_id)
        response, status_code = ElasticWrap(path).delete()

        if status_code == 404:
            raise DocumentNotFoundError(doc_id)
        elif status_code != 200:
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

    def exists(self, doc_id: str) -> bool:
        """Check if a document exists."""
        try:
            self.get(doc_id)
            return True
        except DocumentNotFoundError:
            return False

    def query(
        self,
        filters: dict[str, Any] | None = None,
        sort: list[tuple[str, str]] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query documents with filtering, sorting, and pagination."""
        # Build ES query
        query: dict[str, Any] = {}

        # Build filters
        if filters:
            must_clauses = []
            for field, value in filters.items():
                must_clauses.append({"term": {field: value}})

            query["query"] = {"bool": {"must": must_clauses}}
        else:
            query["query"] = {"match_all": {}}

        # Build sort
        if sort:
            query["sort"] = [{field: {"order": direction}} for field, direction in sort]

        # Pagination
        if limit:
            query["size"] = limit
        if offset:
            query["from"] = offset

        # Execute query using IndexPaginate for large result sets
        if limit and limit <= 1000:
            # Small query, use direct search
            path = f"{self.index_name}/_search"
            response, status_code = ElasticWrap(path).get(data=query)

            if status_code != 200:
                raise ValueError(f"Elasticsearch error: {status_code} - {response}")

            hits = response.get("hits", {}).get("hits", [])
            return [hit["_source"] for hit in hits]
        else:
            # Large query, use pagination
            return IndexPaginate(self.index_name, query).get_results()

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count documents matching filters."""
        query: dict[str, Any] = {}

        if filters:
            must_clauses = []
            for field, value in filters.items():
                must_clauses.append({"term": {field: value}})
            query["query"] = {"bool": {"must": must_clauses}}
        else:
            query["query"] = {"match_all": {}}

        path = f"{self.index_name}/_count"
        response, status_code = ElasticWrap(path).get(data=query)

        if status_code != 200:
            raise ValueError(f"Elasticsearch error: {status_code} - {response}")

        return response.get("count", 0)

    def bulk_create(self, documents: list[tuple[str, dict[str, Any]]]) -> None:
        """Create multiple documents in bulk."""
        if not documents:
            return

        # Build bulk request
        bulk_data = []
        for doc_id, document in documents:
            bulk_data.append({"index": {"_index": self.index_name, "_id": doc_id}})
            bulk_data.append(document)

        path = "_bulk"
        response, status_code = ElasticWrap(path).post(data=bulk_data)

        if status_code not in (200, 201):
            raise ValueError(f"Elasticsearch bulk error: {status_code} - {response}")

    def bulk_delete(self, doc_ids: list[str]) -> int:
        """Delete multiple documents in bulk."""
        if not documents:
            return 0

        # Build bulk delete request
        bulk_data = []
        for doc_id in doc_ids:
            bulk_data.append({"delete": {"_index": self.index_name, "_id": doc_id}})

        path = "_bulk"
        response, status_code = ElasticWrap(path).post(data=bulk_data)

        if status_code not in (200, 201):
            raise ValueError(f"Elasticsearch bulk error: {status_code} - {response}")

        # Count successful deletes
        items = response.get("items", [])
        deleted_count = sum(1 for item in items if item.get("delete", {}).get("result") == "deleted")
        return deleted_count
