"""Video models"""

from django.db import models


class Video(models.Model):
    """YouTube video model"""

    youtube_id = models.CharField(max_length=255, primary_key=True)
    title = models.CharField(max_length=500, db_index=True)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=200, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    published = models.DateTimeField(db_index=True)
    vid_last_refresh = models.DateTimeField(null=True, blank=True)
    date_downloaded = models.DateTimeField(db_index=True)
    active = models.BooleanField(default=True, db_index=True)
    vid_type = models.CharField(
        max_length=20, default="videos", db_index=True
    )  # videos, streams, shorts

    # Channel relationship - stored as nested data
    channel = models.ForeignKey(
        "channel.Channel",
        on_delete=models.CASCADE,
        related_name="videos",
        to_field="channel_id",
        db_column="channel_id",
    )

    # Player data (stored as JSON for nested structure)
    player = models.JSONField(default=dict, blank=True)  # watched, duration, etc.

    # Stats data
    stats = models.JSONField(default=dict, blank=True)  # views, likes, etc.

    # Sponsorblock data
    sponsorblock = models.JSONField(default=dict, blank=True)

    # Streams data (quality options)
    streams = models.JSONField(default=list, blank=True)

    # Subtitles metadata
    subtitles = models.JSONField(default=list, blank=True)

    # Playlist relationships
    playlist = models.JSONField(
        default=list, blank=True
    )  # List of playlist IDs this video belongs to

    # Media file info
    media_url = models.CharField(max_length=500, blank=True, null=True)
    media_size = models.BigIntegerField(default=0)
    vid_thumb_url = models.URLField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = "video"
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["channel"]),
            models.Index(fields=["published"]),
            models.Index(fields=["date_downloaded"]),
            models.Index(fields=["active"]),
            models.Index(fields=["vid_type"]),
            models.Index(fields=["-published"]),  # For sorting
            models.Index(fields=["-date_downloaded"]),  # For sorting
        ]

    def __str__(self):
        return f"{self.title} ({self.youtube_id})"


class Subtitle(models.Model):
    """Video subtitle fragments for full-text search"""

    subtitle_fragment_id = models.CharField(max_length=500, primary_key=True)
    youtube_id = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name="subtitle_fragments",
        to_field="youtube_id",
        db_column="youtube_id",
    )
    title = models.CharField(max_length=500, db_index=True)
    subtitle_line = models.TextField(db_index=True)  # The actual searchable text
    subtitle_lang = models.CharField(max_length=10, db_index=True)
    subtitle_source = models.CharField(max_length=50)  # auto, user
    subtitle_channel = models.CharField(max_length=500)
    subtitle_channel_id = models.ForeignKey(
        "channel.Channel",
        on_delete=models.CASCADE,
        related_name="subtitles",
        to_field="channel_id",
        db_column="subtitle_channel_id",
    )
    subtitle_start = models.FloatField()
    subtitle_end = models.FloatField()
    subtitle_index = models.IntegerField()

    class Meta:
        db_table = "subtitle"
        indexes = [
            models.Index(fields=["youtube_id"]),
            models.Index(fields=["subtitle_lang"]),
            models.Index(fields=["subtitle_channel_id"]),
            models.Index(fields=["subtitle_line"]),  # For text search
        ]

    def __str__(self):
        return f"{self.youtube_id} - {self.subtitle_index}"


class Comment(models.Model):
    """Video comments"""

    youtube_id = models.OneToOneField(
        Video,
        on_delete=models.CASCADE,
        related_name="comments",
        to_field="youtube_id",
        db_column="youtube_id",
        primary_key=True,
    )
    comment_channel_id = models.CharField(max_length=255)
    comment_comments = models.JSONField(
        default=list, blank=True
    )  # Nested comment threads
    comment_last_refresh = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "comment"
        indexes = [
            models.Index(fields=["comment_channel_id"]),
            models.Index(fields=["comment_last_refresh"]),
        ]

    def __str__(self):
        return f"Comments for {self.youtube_id}"
