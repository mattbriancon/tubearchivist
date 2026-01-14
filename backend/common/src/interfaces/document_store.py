"""
Document Store Interface

Defines the abstract interface for storing and querying documents.
This interface is designed for document-oriented data (like ES indices).
"""

from abc import ABC, abstractmethod
from typing import Any


class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        super().__init__(f"Document not found: {doc_id}")


class DocumentStore(ABC):
    """
    Abstract base class for document storage backends.

    Documents are stored as dictionaries with a unique ID.
    Supports CRUD operations plus querying, filtering, and pagination.
    """

    @abstractmethod
    def get(self, doc_id: str) -> dict[str, Any]:
        """
        Retrieve a document by ID.

        Args:
            doc_id: Document identifier

        Returns:
            Document dict

        Raises:
            DocumentNotFoundError: If document doesn't exist
        """

    @abstractmethod
    def create(self, doc_id: str, document: dict[str, Any]) -> None:
        """
        Create a new document.

        Args:
            doc_id: Document identifier
            document: Document data

        Raises:
            ValueError: If document already exists or data is invalid
        """

    @abstractmethod
    def update(self, doc_id: str, document: dict[str, Any]) -> None:
        """
        Update an existing document (full replacement).

        Args:
            doc_id: Document identifier
            document: New document data

        Raises:
            DocumentNotFoundError: If document doesn't exist
        """

    @abstractmethod
    def upsert(self, doc_id: str, document: dict[str, Any]) -> None:
        """
        Create or update a document.

        Args:
            doc_id: Document identifier
            document: Document data
        """

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """
        Delete a document.

        Args:
            doc_id: Document identifier

        Raises:
            DocumentNotFoundError: If document doesn't exist
        """

    @abstractmethod
    def exists(self, doc_id: str) -> bool:
        """
        Check if a document exists.

        Args:
            doc_id: Document identifier

        Returns:
            True if document exists
        """

    @abstractmethod
    def query(
        self,
        filters: dict[str, Any] | None = None,
        sort: list[tuple[str, str]] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Query documents with filtering, sorting, and pagination.

        Args:
            filters: Field filters (e.g., {"status": "pending", "channel_id": "abc"})
            sort: List of (field, direction) tuples, e.g., [("timestamp", "asc")]
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of documents matching the query
        """

    @abstractmethod
    def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        Count documents matching filters.

        Args:
            filters: Field filters

        Returns:
            Number of matching documents
        """

    @abstractmethod
    def bulk_create(self, documents: list[tuple[str, dict[str, Any]]]) -> None:
        """
        Create multiple documents in bulk.

        Args:
            documents: List of (doc_id, document) tuples
        """

    @abstractmethod
    def bulk_delete(self, doc_ids: list[str]) -> int:
        """
        Delete multiple documents in bulk.

        Args:
            doc_ids: List of document IDs to delete

        Returns:
            Number of documents deleted
        """

    def claim_next_job(
        self,
        filters: dict[str, Any],
        sort: list[tuple[str, str]],
        claim_updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Atomically fetch and claim the next job matching filters.

        This is a queue-specific operation that uses row-level locking
        (SELECT FOR UPDATE) to safely handle multiple workers competing
        for jobs.

        Args:
            filters: Filters to find eligible jobs (e.g., {"status": "pending"})
            sort: Sort order (e.g., [("timestamp", "asc")])
            claim_updates: Updates to apply when claiming (e.g., {"status": "processing"})

        Returns:
            The claimed job document, or None if no jobs available

        Note:
            - Default implementation queries then updates (not atomic)
            - Model backend overrides with SELECT FOR UPDATE for atomicity
            - Elasticsearch doesn't support row locking, relies on versioning
        """
        # Default implementation: query then update (not truly atomic)
        # Subclasses should override for proper locking
        results = self.query(filters=filters, sort=sort, limit=1)
        if not results:
            return None

        job = results[0]
        doc_id = job.get("youtube_id") or job.get("_id")
        if not doc_id:
            return None

        try:
            self.update(doc_id, claim_updates)
            # Re-fetch to get updated version
            return self.get(doc_id)
        except (DocumentNotFoundError, Exception):
            # Job was claimed by another worker or deleted
            return None
