"""Channel models"""

from datetime import datetime

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

    def to_dict(self):
        """Convert model instance to dictionary (matching ES document structure)"""
        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "channel_banner_url": self.channel_banner_url,
            "channel_tvart_url": self.channel_tvart_url,
            "channel_description": self.channel_description,
            "channel_tags": self.channel_tags,
            "channel_active": self.channel_active,
            "channel_subscribed": self.channel_subscribed,
            "channel_subs": self.channel_subs,
            "channel_last_refresh": (
                int(self.channel_last_refresh.timestamp())
                if self.channel_last_refresh
                else None
            ),
            "channel_overwrites": self.channel_overwrites,
            "channel_tabs": self.channel_tabs,
        }

    @classmethod
    def from_dict(cls, data):
        """Create or update channel from dictionary (ES document format)"""
        # Convert timestamp to datetime if needed
        if "channel_last_refresh" in data and isinstance(
            data["channel_last_refresh"], int
        ):
            data["channel_last_refresh"] = datetime.fromtimestamp(
                data["channel_last_refresh"]
            )

        channel_id = data.pop("channel_id")
        channel, _ = cls.objects.update_or_create(
            channel_id=channel_id, defaults=data
        )
        return channel

    def sync_to_videos(self):
        """Sync channel data to all related videos"""
        from video.models import Video

        # Update all videos with this channel's data
        Video.objects.filter(channel_id=self.channel_id).update(
            channel=self  # Django will handle the FK relationship
        )
        print(f"{self.channel_id}: synced channel data to videos")
