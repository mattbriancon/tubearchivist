"""
Document Store Factory

Provides factory functions to get the appropriate DocumentStore implementation
for each Elasticsearch index based on Django settings.
"""

from django.conf import settings

from common.src.interfaces.document_store import DocumentStore


# Index name to model mapping
INDEX_MODEL_MAP = {
    "ta_download": "DownloadQueueItem",
    "ta_video": "VideoDocument",
    "ta_channel": "ChannelDocument",
    "ta_playlist": "PlaylistDocument",
    "ta_comment": "CommentDocument",
    "ta_subtitle": "SubtitleDocument",
}


def get_document_store(index_name: str) -> DocumentStore:
    """
    Get the configured DocumentStore implementation for an index.

    Args:
        index_name: ES index name (e.g., "ta_download", "ta_video")

    Returns:
        DocumentStore instance

    Raises:
        ValueError: If unsupported backend or unknown index

    Example:
        store = get_document_store("ta_download")
        doc = store.get("youtube_id_123")
    """
    backend = getattr(settings, "DOCUMENT_STORE_BACKEND", "elasticsearch").lower()

    if backend == "elasticsearch":
        from common.src.adapters.elasticsearch.document_store import (
            ElasticsearchDocumentStore,
        )

        return ElasticsearchDocumentStore(index_name)
    elif backend in ("model", "sqlite"):
        from common.models import (
            ChannelDocument,
            CommentDocument,
            DownloadQueueItem,
            PlaylistDocument,
            SubtitleDocument,
            VideoDocument,
        )
        from common.src.adapters.model.document_store import ModelDocumentStore

        # Map index name to model class
        model_map = {
            "ta_download": DownloadQueueItem,
            "ta_video": VideoDocument,
            "ta_channel": ChannelDocument,
            "ta_playlist": PlaylistDocument,
            "ta_comment": CommentDocument,
            "ta_subtitle": SubtitleDocument,
        }

        if index_name not in model_map:
            raise ValueError(f"Unknown index: {index_name}")

        return ModelDocumentStore(model_map[index_name])
    else:
        raise ValueError(
            f"Unsupported DOCUMENT_STORE_BACKEND: {backend}. "
            f"Supported: 'elasticsearch', 'model'"
        )


# Convenience functions for specific indices
def get_download_store() -> DocumentStore:
    """Get DocumentStore for ta_download index."""
    return get_document_store("ta_download")


def get_video_store() -> DocumentStore:
    """Get DocumentStore for ta_video index."""
    return get_document_store("ta_video")


def get_channel_store() -> DocumentStore:
    """Get DocumentStore for ta_channel index."""
    return get_document_store("ta_channel")


def get_playlist_store() -> DocumentStore:
    """Get DocumentStore for ta_playlist index."""
    return get_document_store("ta_playlist")


def get_comment_store() -> DocumentStore:
    """Get DocumentStore for ta_comment index."""
    return get_document_store("ta_comment")


def get_subtitle_store() -> DocumentStore:
    """Get DocumentStore for ta_subtitle index."""
    return get_document_store("ta_subtitle")
