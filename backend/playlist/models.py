"""Playlist models"""

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
