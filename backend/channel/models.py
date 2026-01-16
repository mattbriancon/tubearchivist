"""Channel models"""

from django.db import models


class Channel(models.Model):
    """YouTube channel model"""

    channel_id = models.CharField(max_length=255, primary_key=True)
    channel_name = models.CharField(max_length=500, db_index=True)
    channel_banner_url = models.URLField(max_length=500, blank=True, null=True)
    channel_tvart_url = models.URLField(max_length=500, blank=True, null=True)
    channel_description = models.TextField(blank=True, null=True)
    channel_tags = models.JSONField(default=list, blank=True)
    channel_active = models.BooleanField(default=True, db_index=True)
    channel_subscribed = models.BooleanField(default=False, db_index=True)
    channel_subs = models.IntegerField(default=0)
    channel_last_refresh = models.DateTimeField(null=True, blank=True)
    channel_overwrites = models.JSONField(default=dict, blank=True)
    channel_tabs = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "channel"
        indexes = [
            models.Index(fields=["channel_name"]),
            models.Index(fields=["channel_active"]),
            models.Index(fields=["channel_subscribed"]),
            models.Index(fields=["channel_last_refresh"]),
        ]

    def __str__(self):
        return f"{self.channel_name} ({self.channel_id})"
