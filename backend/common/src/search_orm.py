"""
ORM-based search functionality to replace Elasticsearch queries

This module provides search capabilities using Django ORM and Q objects,
replacing the Elasticsearch-based search in searching.py
"""

from django.db.models import Q


class SearchORM:
    """
    ORM-based search to replace SearchForm and QueryBuilder

    Provides search across Channel, Video, and Playlist models using
    Django's Q objects and case-insensitive contains queries.
    """

    def __init__(self, search_query, search_type="simple"):
        """
        Initialize search

        Args:
            search_query: The search term(s)
            search_type: Type of search (simple, video, channel, playlist, full)
        """
        self.search_query = search_query
        self.search_type = search_type

    def search_simple(self):
        """
        Simple search across videos, channels, and playlists

        Returns:
            dict: Results organized by content type
        """
        from channel.models import Channel
        from playlist.models import Playlist
        from video.models import Video

        results = {
            "videos": [],
            "channels": [],
            "playlists": [],
        }

        # Search videos
        videos = Video.objects.filter(
            Q(title__icontains=self.search_query)
            | Q(description__icontains=self.search_query)
            | Q(channel__channel_name__icontains=self.search_query)
            | Q(tags__icontains=self.search_query)
        ).select_related("channel")[:20]

        results["videos"] = [v.to_dict() for v in videos]

        # Search channels
        channels = Channel.objects.filter(
            Q(channel_name__icontains=self.search_query)
            | Q(channel_description__icontains=self.search_query)
            | Q(channel_tags__icontains=self.search_query)
        )[:20]

        results["channels"] = [c.to_dict() for c in channels]

        # Search playlists
        playlists = Playlist.objects.filter(
            Q(playlist_name__icontains=self.search_query)
            | Q(playlist_description__icontains=self.search_query)
        ).select_related("playlist_channel_id")[:20]

        results["playlists"] = [p.to_dict() for p in playlists]

        return results

    def search_videos(self, filters=None):
        """
        Search videos with optional filters

        Args:
            filters: Dictionary with filter options (channel, active, vid_type, etc.)

        Returns:
            list: Video results
        """
        from video.models import Video

        queryset = Video.objects.all()

        # Apply search query
        if self.search_query:
            queryset = queryset.filter(
                Q(title__icontains=self.search_query)
                | Q(description__icontains=self.search_query)
                | Q(tags__icontains=self.search_query)
                | Q(category__icontains=self.search_query)
            )

        # Apply filters
        if filters:
            if "channel" in filters:
                queryset = queryset.filter(channel_id=filters["channel"])

            if "active" in filters:
                queryset = queryset.filter(active=filters["active"])

            if "vid_type" in filters:
                queryset = queryset.filter(vid_type=filters["vid_type"])

            if "watched" in filters:
                # Filter by watched status in player JSON field
                if filters["watched"]:
                    queryset = queryset.filter(player__watched=True)
                else:
                    queryset = queryset.exclude(player__watched=True)

        # Order by published date (newest first)
        queryset = queryset.select_related("channel").order_by("-published")

        return [v.to_dict() for v in queryset]

    def search_channels(self, filters=None):
        """
        Search channels with optional filters

        Args:
            filters: Dictionary with filter options (active, subscribed)

        Returns:
            list: Channel results
        """
        from channel.models import Channel

        queryset = Channel.objects.all()

        # Apply search query
        if self.search_query:
            queryset = queryset.filter(
                Q(channel_name__icontains=self.search_query)
                | Q(channel_description__icontains=self.search_query)
                | Q(channel_tags__icontains=self.search_query)
            )

        # Apply filters
        if filters:
            if "active" in filters:
                queryset = queryset.filter(channel_active=filters["active"])

            if "subscribed" in filters:
                queryset = queryset.filter(channel_subscribed=filters["subscribed"])

        queryset = queryset.order_by("-channel_last_refresh")

        return [c.to_dict() for c in queryset]

    def search_playlists(self, filters=None):
        """
        Search playlists with optional filters

        Args:
            filters: Dictionary with filter options (active, subscribed)

        Returns:
            list: Playlist results
        """
        from playlist.models import Playlist

        queryset = Playlist.objects.all()

        # Apply search query
        if self.search_query:
            queryset = queryset.filter(
                Q(playlist_name__icontains=self.search_query)
                | Q(playlist_description__icontains=self.search_query)
            )

        # Apply filters
        if filters:
            if "active" in filters:
                queryset = queryset.filter(playlist_active=filters["active"])

            if "subscribed" in filters:
                queryset = queryset.filter(playlist_subscribed=filters["subscribed"])

        queryset = queryset.select_related("playlist_channel_id").order_by(
            "-playlist_last_refresh"
        )

        return [p.to_dict() for p in queryset]

    def search_subtitles(self):
        """
        Full-text search of video subtitles

        Returns:
            list: Subtitle fragment results with video info
        """
        from video.models import Subtitle

        queryset = Subtitle.objects.filter(
            subtitle_line__icontains=self.search_query
        ).select_related("youtube_id", "subtitle_channel_id")[:100]

        results = []
        for subtitle in queryset:
            result = {
                "subtitle_fragment_id": subtitle.subtitle_fragment_id,
                "youtube_id": subtitle.youtube_id_id,
                "title": subtitle.title,
                "subtitle_line": subtitle.subtitle_line,
                "subtitle_start": subtitle.subtitle_start,
                "subtitle_end": subtitle.subtitle_end,
                "subtitle_lang": subtitle.subtitle_lang,
                "subtitle_channel": subtitle.subtitle_channel,
            }
            results.append(result)

        return results

    def search(self, filters=None):
        """
        Perform search based on search_type

        Args:
            filters: Optional filters for specific search types

        Returns:
            Search results (format depends on search_type)
        """
        if self.search_type == "simple":
            return self.search_simple()
        elif self.search_type == "video":
            return self.search_videos(filters)
        elif self.search_type == "channel":
            return self.search_channels(filters)
        elif self.search_type == "playlist":
            return self.search_playlists(filters)
        elif self.search_type == "full":
            return self.search_subtitles()
        else:
            return []


class VideoQueryORM:
    """
    ORM-based video query builder

    Replaces the ES-based query building in video/src/query_building.py
    """

    def __init__(self, filters=None, sort_by="published", sort_order="desc"):
        """
        Initialize query builder

        Args:
            filters: Dictionary of filter conditions
            sort_by: Field to sort by (published, downloaded, views, likes, duration, filesize)
            sort_order: Sort order (asc or desc)
        """
        self.filters = filters or {}
        self.sort_by = sort_by
        self.sort_order = sort_order

    def build_query(self):
        """
        Build and execute Django ORM query

        Returns:
            QuerySet: Filtered and sorted video queryset
        """
        from video.models import Video

        queryset = Video.objects.all()

        # Apply filters
        if "channel" in self.filters:
            queryset = queryset.filter(channel_id=self.filters["channel"])

        if "playlist" in self.filters:
            # Search in playlist JSON field (contains playlist ID)
            queryset = queryset.filter(playlist__contains=self.filters["playlist"])

        if "active" in self.filters:
            queryset = queryset.filter(active=self.filters["active"])

        if "vid_type" in self.filters:
            queryset = queryset.filter(vid_type=self.filters["vid_type"])

        if "watched" in self.filters:
            if self.filters["watched"]:
                queryset = queryset.filter(player__watched=True)
            else:
                queryset = queryset.exclude(player__watched=True)

        if "height" in self.filters:
            # Filter by video height (in streams JSON field)
            queryset = queryset.filter(streams__contains=[{"height": self.filters["height"]}])

        # Apply sorting
        sort_field_map = {
            "published": "published",
            "downloaded": "date_downloaded",
            "views": "stats__view_count",
            "likes": "stats__like_count",
            "duration": "player__duration",
            "filesize": "media_size",
        }

        sort_field = sort_field_map.get(self.sort_by, "published")

        if self.sort_order == "desc":
            sort_field = f"-{sort_field}"

        queryset = queryset.select_related("channel").order_by(sort_field)

        return queryset

    def get_results(self, limit=None):
        """
        Get query results as dictionaries

        Args:
            limit: Optional limit on number of results

        Returns:
            list: Video dictionaries
        """
        queryset = self.build_query()

        if limit:
            queryset = queryset[:limit]

        return [v.to_dict() for v in queryset]
