"""
ORM-based data access layer to replace Elasticsearch operations

This module provides Django ORM operations that match the ElasticWrap interface,
allowing for gradual migration from Elasticsearch to SQLite.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Q


class ORMWrap:
    """
    ORM wrapper that mimics ElasticWrap interface for compatibility

    This class provides a transition layer from Elasticsearch to Django ORM,
    maintaining the same method signatures to minimize code changes.
    """

    MODEL_MAP = {
        "ta_channel": "channel.models.Channel",
        "ta_playlist": "playlist.models.Playlist",
        "ta_video": "video.models.Video",
        "ta_subtitle": "video.models.Subtitle",
        "ta_comment": "video.models.Comment",
        "ta_download": "download.models.Download",
        "ta_config": "appsettings.models.AppConfig",
    }

    def __init__(self, path):
        """
        Initialize with a path similar to ES path format

        Args:
            path: String like "ta_channel/_doc/UC..." or "ta_video/_search"
        """
        self.path = path
        self.index_name, self.operation, self.doc_id = self._parse_path(path)
        self.model = self._get_model()

    def _parse_path(self, path):
        """Parse ES-style path into components"""
        parts = path.split("/")
        index_name = parts[0]
        operation = parts[1] if len(parts) > 1 else None
        doc_id = parts[2] if len(parts) > 2 else None
        return index_name, operation, doc_id

    def _get_model(self):
        """Get Django model class from index name"""
        if self.index_name not in self.MODEL_MAP:
            return None

        model_path = self.MODEL_MAP[self.index_name]
        module_path, class_name = model_path.rsplit(".", 1)

        # Dynamic import
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def get(self, data=None):
        """
        Get a document by ID (matches ElasticWrap.get())

        Returns:
            tuple: (response_dict, status_code)
        """
        if not self.model or not self.doc_id:
            return {"_source": None}, 404

        try:
            # Get the primary key field name
            pk_field = self.model._meta.pk.name
            obj = self.model.objects.get(**{pk_field: self.doc_id})

            # Convert to dict if model has to_dict method
            if hasattr(obj, "to_dict"):
                source = obj.to_dict()
            else:
                source = {
                    field.name: getattr(obj, field.name)
                    for field in obj._meta.fields
                }

            return {"_source": source}, 200

        except ObjectDoesNotExist:
            return {"_source": None}, 404

    def put(self, data, refresh=False):
        """
        Create or update a document (matches ElasticWrap.put())

        Args:
            data: Dictionary with document data
            refresh: Ignored for ORM (kept for compatibility)

        Returns:
            tuple: (response_dict, status_code)
        """
        if not self.model:
            return {}, 400

        try:
            if hasattr(self.model, "from_dict"):
                obj = self.model.from_dict(data)
            else:
                pk_field = self.model._meta.pk.name
                pk_value = data.get(pk_field) or self.doc_id
                obj, created = self.model.objects.update_or_create(
                    **{pk_field: pk_value}, defaults=data
                )

            return {"result": "created" if created else "updated"}, 201 if created else 200

        except Exception as e:
            return {"error": str(e)}, 400

    def post(self, data):
        """
        Perform bulk operations like _update_by_query or _delete_by_query

        Args:
            data: Dictionary with query and operation details

        Returns:
            tuple: (response_dict, status_code)
        """
        if not self.model:
            return {}, 400

        try:
            # Handle different ES operations
            if "_update_by_query" in self.path:
                return self._update_by_query(data)
            elif "_delete_by_query" in self.path:
                return self._delete_by_query(data)
            elif "_search" in self.path:
                return self._search(data)
            else:
                return {}, 400

        except Exception as e:
            return {"error": str(e)}, 400

    def delete(self, refresh=False):
        """
        Delete a document by ID (matches ElasticWrap.delete())

        Args:
            refresh: Ignored for ORM (kept for compatibility)

        Returns:
            tuple: (response_dict, status_code)
        """
        if not self.model or not self.doc_id:
            return {}, 404

        try:
            pk_field = self.model._meta.pk.name
            obj = self.model.objects.get(**{pk_field: self.doc_id})
            obj.delete()
            return {"result": "deleted"}, 200

        except ObjectDoesNotExist:
            return {}, 404

    def _update_by_query(self, data):
        """Handle Elasticsearch _update_by_query operations"""
        query = data.get("query", {})
        script = data.get("script", {})

        # Build Django Q object from ES query
        queryset = self._build_queryset(query)

        # Extract update values from script params
        update_data = script.get("params", {})

        # Perform update
        count = queryset.update(**update_data)

        return {"updated": count}, 200

    def _delete_by_query(self, data):
        """Handle Elasticsearch _delete_by_query operations"""
        query = data.get("query", {})

        # Build Django Q object from ES query
        queryset = self._build_queryset(query)

        # Perform deletion
        count, _ = queryset.delete()

        return {"deleted": count}, 200

    def _search(self, data):
        """Handle Elasticsearch _search operations"""
        query = data.get("query", {})
        source = data.get("_source", None)
        size = data.get("size", 10)

        # Build Django queryset
        queryset = self._build_queryset(query)

        # Apply field selection if specified
        if source:
            queryset = queryset.values(*source)

        # Apply limit
        results = list(queryset[:size])

        return {
            "hits": {
                "total": {"value": queryset.count()},
                "hits": [{"_source": result} for result in results],
            }
        }, 200

    def _build_queryset(self, es_query):
        """
        Convert Elasticsearch query to Django Q object

        This is a simplified converter for common ES query patterns.
        Supports: term, match, bool queries
        """
        queryset = self.model.objects.all()

        if not es_query:
            return queryset

        # Handle term queries
        if "term" in es_query:
            for field, value_dict in es_query["term"].items():
                # Handle nested field notation (e.g., "channel.channel_id")
                field = field.replace(".", "__")
                value = value_dict.get("value") if isinstance(value_dict, dict) else value_dict
                queryset = queryset.filter(**{field: value})

        # Handle bool queries
        elif "bool" in es_query:
            must = es_query["bool"].get("must", [])
            for clause in must:
                if "term" in clause:
                    for field, value_dict in clause["term"].items():
                        field = field.replace(".", "__")
                        value = value_dict.get("value") if isinstance(value_dict, dict) else value_dict
                        queryset = queryset.filter(**{field: value})

        # Handle match_all
        elif "match_all" in es_query:
            pass  # Already returning all()

        return queryset


class ORMPaginate:
    """
    ORM-based pagination to replace IndexPaginate

    Provides efficient pagination using Django's Paginator.
    """

    def __init__(self, index_name, data, keep_source=True, size=500):
        """
        Initialize paginator

        Args:
            index_name: Name of the index (e.g., "ta_video")
            data: Dictionary with query and other parameters
            keep_source: Whether to include full source (ignored, kept for compat)
            size: Page size (default 500 to match ES behavior)
        """
        self.index_name = index_name
        self.data = data
        self.size = size
        self.model = self._get_model()

    def _get_model(self):
        """Get Django model from index name"""
        wrap = ORMWrap(f"{self.index_name}/_doc")
        return wrap.model

    def get_results(self):
        """
        Get all results (handles pagination internally)

        Returns:
            list: All matching results as dictionaries
        """
        if not self.model:
            return []

        # Build queryset from query
        query = self.data.get("query", {})
        source_fields = self.data.get("_source", None)

        wrap = ORMWrap(f"{self.index_name}/_search")
        queryset = wrap._build_queryset(query)

        # Convert to list of dicts
        results = []
        for obj in queryset:
            if hasattr(obj, "to_dict"):
                result = obj.to_dict()
            else:
                result = {
                    field.name: getattr(obj, field.name)
                    for field in obj._meta.fields
                }

            # Filter fields if _source specified
            if source_fields:
                result = {k: v for k, v in result.items() if k in source_fields}

            results.append(result)

        return results
