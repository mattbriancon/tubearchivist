"""
Django models for common app.

This module contains models used across multiple apps, particularly for
datastore abstraction layers.
"""

from django.db import models


class ConfigData(models.Model):
    """
    Key-value storage for configuration data.

    Used by SQLiteConfigStore adapter to replace Elasticsearch ta_config index.
    Stores configuration as JSON-serialized strings.

    Fields:
        key: Unique identifier (e.g., "appsettings", "user_123")
        value: JSON-serialized configuration dict
        created_at: Timestamp when the config was created
        updated_at: Timestamp when the config was last updated
    """

    key = models.CharField(max_length=255, unique=True, db_index=True)
    value = models.TextField()  # JSON-serialized dict
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "common_config_data"
        verbose_name = "Configuration Data"
        verbose_name_plural = "Configuration Data"
        ordering = ["key"]

    def __str__(self):
        return f"Config: {self.key}"
