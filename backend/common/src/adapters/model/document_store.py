"""
Django ORM implementation of DocumentStore interface.

This adapter provides a generic way to store ES-like documents in Django models.
Each document is stored with its ID and JSON-serialized content.
"""

import json
from typing import Any

from common.src.interfaces.document_store import (
    DocumentNotFoundError,
    DocumentStore,
)
from django.db import models, transaction
from django.db.models import Q


class ModelDocumentStore(DocumentStore):
    """
    Generic Django ORM-backed document storage.

    Uses a provided Django model to store documents as JSON.
    The model must have: doc_id (CharField, unique), content (TextField), created_at, updated_at
    """

    def __init__(self, model: type[models.Model]):
        """
        Initialize with a Django model.

        Args:
            model: Django model class with doc_id and content fields
        """
        self.model = model

    def get(self, doc_id: str) -> dict[str, Any]:
        """Retrieve a document by ID."""
        try:
            doc = self.model.objects.get(doc_id=doc_id)
            return json.loads(doc.content)
        except self.model.DoesNotExist:
            raise DocumentNotFoundError(doc_id)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for document {doc_id}: {e}")

    def create(self, doc_id: str, document: dict[str, Any]) -> None:
        """Create a new document."""
        if self.exists(doc_id):
            raise ValueError(f"Document {doc_id} already exists")

        try:
            content = json.dumps(document)
            self.model.objects.create(doc_id=doc_id, content=content)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize document {doc_id}: {e}")

    def update(self, doc_id: str, document: dict[str, Any]) -> None:
        """Update an existing document."""
        try:
            content = json.dumps(document)
            updated = self.model.objects.filter(doc_id=doc_id).update(
                content=content
            )
            if updated == 0:
                raise DocumentNotFoundError(doc_id)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize document {doc_id}: {e}")

    def upsert(self, doc_id: str, document: dict[str, Any]) -> None:
        """Create or update a document."""
        try:
            content = json.dumps(document)
            self.model.objects.update_or_create(
                doc_id=doc_id, defaults={"content": content}
            )
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize document {doc_id}: {e}")

    def delete(self, doc_id: str) -> None:
        """Delete a document."""
        deleted_count, _ = self.model.objects.filter(doc_id=doc_id).delete()
        if deleted_count == 0:
            raise DocumentNotFoundError(doc_id)

    def exists(self, doc_id: str) -> bool:
        """Check if a document exists."""
        return self.model.objects.filter(doc_id=doc_id).exists()

    def query(
        self,
        filters: dict[str, Any] | None = None,
        sort: list[tuple[str, str]] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Query documents with filtering, sorting, and pagination.

        Filters are applied by deserializing JSON and checking fields.
        This is not as efficient as native DB queries but works generically.
        """
        queryset = self.model.objects.all()

        # Apply pagination
        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[: offset + limit if offset else limit]

        # Get all documents
        documents = []
        for doc in queryset:
            try:
                data = json.loads(doc.content)
                data["_id"] = doc.doc_id  # Include ID

                # Apply filters
                if filters and not self._matches_filters(data, filters):
                    continue

                documents.append(data)
            except json.JSONDecodeError:
                continue

        # Apply sorting
        if sort:
            documents = self._sort_documents(documents, sort)

        return documents

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count documents matching filters."""
        if not filters:
            return self.model.objects.count()

        # For filtered counts, we need to deserialize and check
        count = 0
        for doc in self.model.objects.all():
            try:
                data = json.loads(doc.content)
                if self._matches_filters(data, filters):
                    count += 1
            except json.JSONDecodeError:
                continue

        return count

    def bulk_create(self, documents: list[tuple[str, dict[str, Any]]]) -> None:
        """Create multiple documents in bulk."""
        objects = []
        for doc_id, document in documents:
            try:
                content = json.dumps(document)
                objects.append(self.model(doc_id=doc_id, content=content))
            except (TypeError, ValueError):
                continue

        self.model.objects.bulk_create(objects, ignore_conflicts=True)

    def bulk_delete(self, doc_ids: list[str]) -> int:
        """Delete multiple documents in bulk."""
        deleted_count, _ = self.model.objects.filter(doc_id__in=doc_ids).delete()
        return deleted_count

    @staticmethod
    def _matches_filters(data: dict, filters: dict[str, Any]) -> bool:
        """Check if document matches all filters."""
        for key, value in filters.items():
            # Support nested field access with dot notation
            current = data
            for part in key.split("."):
                if not isinstance(current, dict) or part not in current:
                    return False
                current = current[part]

            if current != value:
                return False

        return True

    def claim_next_job(
        self,
        filters: dict[str, Any],
        sort: list[tuple[str, str]],
        claim_updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Atomically fetch and claim the next job using SELECT FOR UPDATE.

        This provides true atomicity for queue operations with multiple workers.
        Uses row-level locking to prevent race conditions.
        """
        with transaction.atomic():
            # Build queryset with filters
            queryset = self.model.objects.all()

            # We need to filter in the database for efficiency
            # For simple filters, we can use Q objects
            q_filters = Q()
            for key, value in (filters or {}).items():
                # For nested filters like "status", we need to deserialize
                # For now, we'll fetch all and filter in-memory for complex cases
                # But optimize for common case of simple top-level filters
                pass

            # Get all candidates and filter in-memory
            # This is not ideal but works generically
            candidates = []
            for doc in queryset.select_for_update(skip_locked=True):
                try:
                    data = json.loads(doc.content)
                    data["_id"] = doc.doc_id

                    # Apply filters
                    if filters and not self._matches_filters(data, filters):
                        continue

                    candidates.append((doc, data))
                except json.JSONDecodeError:
                    continue

            if not candidates:
                return None

            # Sort candidates
            if sort:
                sorted_data = self._sort_documents(
                    [c[1] for c in candidates], sort
                )
                # Reorder candidates to match sorted data
                sorted_candidates = []
                for sorted_doc in sorted_data:
                    for doc_obj, data in candidates:
                        if data["_id"] == sorted_doc["_id"]:
                            sorted_candidates.append((doc_obj, data))
                            break
                candidates = sorted_candidates

            # Take the first one
            doc_obj, data = candidates[0]

            # Apply claim updates
            updated_data = {**data}
            updated_data.update(claim_updates)

            # Update the document
            doc_obj.content = json.dumps(updated_data)
            doc_obj.save(update_fields=["content"])

            return updated_data

    @staticmethod
    def _sort_documents(
        documents: list[dict], sort: list[tuple[str, str]]
    ) -> list[dict]:
        """Sort documents by specified fields."""
        for field, direction in reversed(sort):
            reverse = direction.lower() == "desc"

            def get_sort_key(doc):
                # Support nested fields
                current = doc
                for part in field.split("."):
                    if isinstance(current, dict):
                        current = current.get(part)
                    else:
                        return None
                return current

            documents.sort(key=get_sort_key, reverse=reverse)

        return documents
