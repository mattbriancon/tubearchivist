"""
ORM-based aggregations to replace Elasticsearch aggregations

This module provides statistics and aggregations using Django ORM,
replacing the ES aggregation queries in stats/src/aggs.py
"""

from datetime import datetime, timedelta

from django.db.models import Avg, Count, Max, Min, Sum
from django.db.models.functions import TruncDate


class StatsORM:
    """
    ORM-based statistics aggregations

    Replaces Elasticsearch aggregations with Django ORM aggregate/annotate
    """

    @staticmethod
    def get_video_stats():
        """
        Get video statistics by type and active status

        Returns:
            dict: Video statistics
        """
        from video.models import Video

        stats = {}

        # Total counts
        stats["total"] = Video.objects.count()
        stats["active"] = Video.objects.filter(active=True).count()
        stats["inactive"] = Video.objects.filter(active=False).count()

        # By video type
        stats["by_type"] = {}
        for vid_type in ["videos", "streams", "shorts"]:
            stats["by_type"][vid_type] = {
                "count": Video.objects.filter(vid_type=vid_type).count(),
                "active": Video.objects.filter(
                    vid_type=vid_type, active=True
                ).count(),
            }

        # Media stats
        media_stats = Video.objects.aggregate(
            total_size=Sum("media_size"),
            total_duration=Sum("player__duration"),
            avg_duration=Avg("player__duration"),
        )
        stats["media"] = media_stats

        # View stats
        view_stats = Video.objects.aggregate(
            total_views=Sum("stats__view_count"),
            total_likes=Sum("stats__like_count"),
            avg_views=Avg("stats__view_count"),
        )
        stats["views"] = view_stats

        return stats

    @staticmethod
    def get_channel_stats():
        """
        Get channel statistics

        Returns:
            dict: Channel statistics
        """
        from channel.models import Channel

        stats = {
            "total": Channel.objects.count(),
            "active": Channel.objects.filter(channel_active=True).count(),
            "subscribed": Channel.objects.filter(channel_subscribed=True).count(),
        }

        # Subscriber stats
        sub_stats = Channel.objects.aggregate(
            total_subs=Sum("channel_subs"),
            avg_subs=Avg("channel_subs"),
            max_subs=Max("channel_subs"),
        )
        stats["subscribers"] = sub_stats

        return stats

    @staticmethod
    def get_playlist_stats():
        """
        Get playlist statistics

        Returns:
            dict: Playlist statistics
        """
        from playlist.models import Playlist

        stats = {
            "total": Playlist.objects.count(),
            "active": Playlist.objects.filter(playlist_active=True).count(),
            "subscribed": Playlist.objects.filter(
                playlist_subscribed=True
            ).count(),
        }

        return stats

    @staticmethod
    def get_download_stats():
        """
        Get download queue statistics

        Returns:
            dict: Download queue statistics
        """
        from download.models import Download

        stats = {
            "total": Download.objects.count(),
            "by_status": {},
        }

        # Count by status
        status_counts = (
            Download.objects.values("status")
            .annotate(count=Count("status"))
            .order_by("status")
        )

        for item in status_counts:
            stats["by_status"][item["status"]] = item["count"]

        # By video type
        type_counts = (
            Download.objects.values("vid_type")
            .annotate(count=Count("vid_type"))
            .order_by("vid_type")
        )

        stats["by_type"] = {}
        for item in type_counts:
            stats["by_type"][item["vid_type"]] = item["count"]

        return stats

    @staticmethod
    def get_watch_progress():
        """
        Get watch progress statistics

        Returns:
            dict: Watch progress stats
        """
        from video.models import Video

        total = Video.objects.filter(active=True).count()
        watched = Video.objects.filter(
            active=True, player__watched=True
        ).count()
        unwatched = total - watched

        return {
            "total": total,
            "watched": watched,
            "unwatched": unwatched,
            "percent_watched": (watched / total * 100) if total > 0 else 0,
        }

    @staticmethod
    def get_download_history(days=7):
        """
        Get download history for the last N days

        Args:
            days: Number of days to include (default 7)

        Returns:
            list: Daily download counts
        """
        from video.models import Video

        cutoff_date = datetime.now() - timedelta(days=days)

        # Group by date and count
        history = (
            Video.objects.filter(date_downloaded__gte=cutoff_date)
            .annotate(date=TruncDate("date_downloaded"))
            .values("date")
            .annotate(count=Count("youtube_id"))
            .order_by("date")
        )

        return list(history)

    @staticmethod
    def get_biggest_channels(limit=10):
        """
        Get channels with most videos

        Args:
            limit: Number of channels to return (default 10)

        Returns:
            list: Channels with video counts
        """
        from channel.models import Channel

        # Annotate channels with video count
        channels = (
            Channel.objects.annotate(video_count=Count("videos"))
            .order_by("-video_count")[:limit]
        )

        results = []
        for channel in channels:
            results.append(
                {
                    "channel_id": channel.channel_id,
                    "channel_name": channel.channel_name,
                    "video_count": channel.video_count,
                    "channel_subs": channel.channel_subs,
                }
            )

        return results

    @staticmethod
    def get_recent_videos(limit=20):
        """
        Get most recently downloaded videos

        Args:
            limit: Number of videos to return (default 20)

        Returns:
            list: Recent video dictionaries
        """
        from video.models import Video

        videos = (
            Video.objects.filter(active=True)
            .select_related("channel")
            .order_by("-date_downloaded")[:limit]
        )

        return [v.to_dict() for v in videos]

    @staticmethod
    def get_popular_videos(limit=20):
        """
        Get most viewed videos

        Args:
            limit: Number of videos to return (default 20)

        Returns:
            list: Popular video dictionaries
        """
        from video.models import Video

        videos = (
            Video.objects.filter(active=True)
            .select_related("channel")
            .order_by("-stats__view_count")[:limit]
        )

        return [v.to_dict() for v in videos]

    @staticmethod
    def get_all_stats():
        """
        Get all statistics in one call

        Returns:
            dict: Complete statistics
        """
        return {
            "videos": StatsORM.get_video_stats(),
            "channels": StatsORM.get_channel_stats(),
            "playlists": StatsORM.get_playlist_stats(),
            "downloads": StatsORM.get_download_stats(),
            "watch_progress": StatsORM.get_watch_progress(),
            "download_history": StatsORM.get_download_history(),
            "biggest_channels": StatsORM.get_biggest_channels(),
        }
