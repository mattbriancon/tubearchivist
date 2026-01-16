"""
ORM-based base class to replace YouTubeItem

This module provides Django ORM-based equivalents of the YouTubeItem
base class functionality, replacing Elasticsearch operations.
"""

from appsettings.src.config import AppConfig
from download.src.yt_dlp_base import YtWrap


class YouTubeItemORM:
    """Base class for YouTube items using Django ORM instead of Elasticsearch"""

    index_name = ""
    model_class = None  # Subclasses should set this to their Django model
    yt_base = ""
    yt_obs: dict[str, bool | str] = {
        "skip_download": True,
        "noplaylist": True,
    }

    def __init__(self, youtube_id):
        self.youtube_id = youtube_id
        self.config = AppConfig().config
        self.error = None
        self.youtube_meta = False
        self.json_data = False
        self.instance = None  # Django model instance

    def build_yt_url(self):
        """Build YouTube URL"""
        return self.yt_base + self.youtube_id

    def get_from_youtube(self, obs_overwrite: dict | None = None):
        """Use yt-dlp to get metadata from YouTube"""
        print(f"{self.youtube_id}: get metadata from youtube")
        obs_request = self.yt_obs.copy()

        if self.config["downloads"]["extractor_lang"]:
            langs = self.config["downloads"]["extractor_lang"]
            langs_list = [i.strip() for i in langs.split(",")]
            obs_request["extractor_args"] = {"youtube": {"lang": langs_list}}

        if obs_overwrite:
            obs_request.update(obs_overwrite)

        url = self.build_yt_url()
        self.youtube_meta, self.error = YtWrap(obs_request, self.config).extract(url)

    def get_from_db(self):
        """Get data from database using Django ORM"""
        if not self.model_class:
            print(f"{self.youtube_id}: model_class not set")
            return

        print(f"{self.youtube_id}: get metadata from database")
        try:
            pk_field = self.model_class._meta.pk.name
            self.instance = self.model_class.objects.get(**{pk_field: self.youtube_id})

            # Convert to dict if model has to_dict method
            if hasattr(self.instance, "to_dict"):
                self.json_data = self.instance.to_dict()
            else:
                self.json_data = {
                    field.name: getattr(self.instance, field.name)
                    for field in self.instance._meta.fields
                }

        except self.model_class.DoesNotExist:
            self.json_data = None

    def save_to_db(self):
        """Save json_data to database using Django ORM"""
        if not self.model_class or not self.json_data:
            return

        try:
            if hasattr(self.model_class, "from_dict"):
                self.instance = self.model_class.from_dict(self.json_data)
            else:
                pk_field = self.model_class._meta.pk.name
                pk_value = self.json_data.get(pk_field) or self.youtube_id
                self.instance, _ = self.model_class.objects.update_or_create(
                    **{pk_field: pk_value}, defaults=self.json_data
                )

            print(f"{self.youtube_id}: saved to database")

        except Exception as e:
            print(f"{self.youtube_id}: error saving to database: {e}")

    def deactivate(self):
        """Deactivate item in database"""
        if not self.model_class:
            return

        print(f"{self.youtube_id}: deactivate document")

        # Map index names to active field names
        key_match = {
            "ta_video": "active",
            "ta_channel": "channel_active",
            "ta_playlist": "playlist_active",
        }

        active_field = key_match.get(self.index_name, "active")

        try:
            pk_field = self.model_class._meta.pk.name
            self.model_class.objects.filter(**{pk_field: self.youtube_id}).update(
                **{active_field: False}
            )
        except Exception as e:
            print(f"{self.youtube_id}: error deactivating: {e}")

    def delete_from_db(self):
        """Delete item from database"""
        if not self.model_class:
            return

        print(f"{self.youtube_id}: delete from database")

        try:
            pk_field = self.model_class._meta.pk.name
            deleted, _ = self.model_class.objects.filter(
                **{pk_field: self.youtube_id}
            ).delete()
            print(f"{self.youtube_id}: deleted {deleted} records")

        except Exception as e:
            print(f"{self.youtube_id}: error deleting: {e}")

    # Compatibility aliases for gradual migration
    get_from_es = get_from_db
    upload_to_es = save_to_db
    del_in_es = delete_from_db
