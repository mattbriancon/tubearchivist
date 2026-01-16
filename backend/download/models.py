"""Download queue models"""

from django.db import models


class Download(models.Model):
    """Download queue model"""

    youtube_id = models.CharField(max_length=255, primary_key=True)
    title = models.CharField(max_length=500, db_index=True)
    channel_id = models.CharField(max_length=255, db_index=True)
    channel_name = models.CharField(max_length=500)
    status = models.CharField(max_length=50, db_index=True)  # pending, downloading, etc.
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    published = models.DateTimeField(null=True, blank=True)
    vid_type = models.CharField(max_length=20, default="videos")  # videos, streams, shorts
    auto_start = models.BooleanField(default=False)
    message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "download"
        indexes = [
            models.Index(fields=["channel_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["vid_type"]),
            models.Index(fields=["-timestamp"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.youtube_id}) - {self.status}"
