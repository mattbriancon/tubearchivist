"""Application settings models"""

from django.db import models


class AppConfig(models.Model):
    """Application configuration model - singleton pattern"""

    # Using a single row for config (id=1)
    config_id = models.IntegerField(primary_key=True, default=1)
    config = models.JSONField(default=dict)  # Stores all app settings

    class Meta:
        db_table = "appconfig"

    def save(self, *args, **kwargs):
        """Ensure only one config exists"""
        self.config_id = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """Get the application config"""
        config, _ = cls.objects.get_or_create(config_id=1)
        return config

    def __str__(self):
        return "Application Configuration"
