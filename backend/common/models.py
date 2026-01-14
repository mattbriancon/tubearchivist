"""
Django models for common app.

This module contains models used across multiple apps, particularly for
datastore abstraction layers.
"""

from django.db import models


class ConfigData(models.Model):
    """
    Key-value storage for configuration data.

    Used by SQLiteConfigStore adapter to replace Elasticsearch ta_config index.
    Stores configuration as JSON-serialized strings.

    Fields:
        key: Unique identifier (e.g., "appsettings", "user_123")
        value: JSON-serialized configuration dict
        created_at: Timestamp when the config was created
        updated_at: Timestamp when the config was last updated
    """

    key = models.CharField(max_length=255, unique=True, db_index=True)
    value = models.TextField()  # JSON-serialized dict
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "common_config_data"
        verbose_name = "Configuration Data"
        verbose_name_plural = "Configuration Data"
        ordering = ["key"]

    def __str__(self):
        return f"Config: {self.key}"


class BaseDocument(models.Model):
    """
    Abstract base model for document storage.

    All ES index replacements inherit from this to provide consistent
    document storage with JSON content.
    """

    doc_id = models.CharField(max_length=255, unique=True, db_index=True)
    content = models.TextField()  # JSON-serialized document
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.__class__.__name__}: {self.doc_id}"


class DownloadQueueItem(BaseDocument):
    """
    Download queue items (replaces ta_download index).

    Stores pending, ignored, and priority downloads.
    """

    class Meta:
        db_table = "download_queue_item"
        verbose_name = "Download Queue Item"
        verbose_name_plural = "Download Queue Items"


class VideoDocument(BaseDocument):
    """
    Video metadata (replaces ta_video index).

    Stores all video data including metadata, stats, and playback info.
    """

    class Meta:
        db_table = "video_document"
        verbose_name = "Video Document"
        verbose_name_plural = "Video Documents"


class ChannelDocument(BaseDocument):
    """
    Channel metadata (replaces ta_channel index).

    Stores channel information, subscriber counts, and settings.
    """

    class Meta:
        db_table = "channel_document"
        verbose_name = "Channel Document"
        verbose_name_plural = "Channel Documents"


class PlaylistDocument(BaseDocument):
    """
    Playlist metadata (replaces ta_playlist index).

    Stores playlist information and video lists.
    """

    class Meta:
        db_table = "playlist_document"
        verbose_name = "Playlist Document"
        verbose_name_plural = "Playlist Documents"


class CommentDocument(BaseDocument):
    """
    Video comments (replaces ta_comment index).

    Stores comments for videos.
    """

    class Meta:
        db_table = "comment_document"
        verbose_name = "Comment Document"
        verbose_name_plural = "Comment Documents"


class SubtitleDocument(BaseDocument):
    """
    Subtitle data (replaces ta_subtitle index).

    Stores subtitle fragments for full-text search.
    """

    class Meta:
        db_table = "subtitle_document"
        verbose_name = "Subtitle Document"
        verbose_name_plural = "Subtitle Documents"

