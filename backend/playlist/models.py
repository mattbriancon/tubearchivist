"""Playlist models"""

from datetime import datetime

from django.db import models


class Playlist(models.Model):
    """YouTube playlist model"""

    playlist_id = models.CharField(max_length=255, primary_key=True)
    playlist_name = models.CharField(max_length=500, db_index=True)
    playlist_thumbnail = models.URLField(max_length=500, blank=True, null=True)
    playlist_description = models.TextField(blank=True, null=True)
    playlist_channel = models.CharField(max_length=500)
    playlist_channel_id = models.ForeignKey(
        "channel.Channel",
        on_delete=models.CASCADE,
        related_name="playlists",
        to_field="channel_id",
        db_column="playlist_channel_id",
    )
    playlist_active = models.BooleanField(default=True, db_index=True)
    playlist_subscribed = models.BooleanField(default=False, db_index=True)
    playlist_entries = models.JSONField(default=list, blank=True)
    playlist_last_refresh = models.DateTimeField(null=True, blank=True)
    playlist_type = models.CharField(max_length=50, default="regular")
    playlist_sort_order = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "playlist"
        indexes = [
            models.Index(fields=["playlist_name"]),
            models.Index(fields=["playlist_channel_id"]),
            models.Index(fields=["playlist_active"]),
            models.Index(fields=["playlist_subscribed"]),
            models.Index(fields=["playlist_last_refresh"]),
        ]

    def __str__(self):
        return f"{self.playlist_name} ({self.playlist_id})"

    def to_dict(self):
        """Convert model instance to dictionary (matching ES document structure)"""
        return {
            "playlist_id": self.playlist_id,
            "playlist_name": self.playlist_name,
            "playlist_thumbnail": self.playlist_thumbnail,
            "playlist_description": self.playlist_description,
            "playlist_channel": self.playlist_channel,
            "playlist_channel_id": self.playlist_channel_id_id,
            "playlist_active": self.playlist_active,
            "playlist_subscribed": self.playlist_subscribed,
            "playlist_entries": self.playlist_entries,
            "playlist_last_refresh": (
                int(self.playlist_last_refresh.timestamp())
                if self.playlist_last_refresh
                else None
            ),
            "playlist_type": self.playlist_type,
            "playlist_sort_order": self.playlist_sort_order,
        }

    @classmethod
    def from_dict(cls, data):
        """Create or update playlist from dictionary (ES document format)"""
        # Convert timestamp to datetime if needed
        if "playlist_last_refresh" in data and isinstance(
            data["playlist_last_refresh"], int
        ):
            data["playlist_last_refresh"] = datetime.fromtimestamp(
                data["playlist_last_refresh"]
            )

        # Handle channel relationship
        if "playlist_channel_id" in data:
            from channel.models import Channel

            try:
                channel = Channel.objects.get(channel_id=data["playlist_channel_id"])
                data["playlist_channel_id"] = channel
            except Channel.DoesNotExist:
                pass

        playlist_id = data.pop("playlist_id")
        playlist, _ = cls.objects.update_or_create(
            playlist_id=playlist_id, defaults=data
        )
        return playlist
