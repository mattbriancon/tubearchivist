"""
Configuration Store Factory

Provides a factory function to instantiate the appropriate ConfigStore
implementation based on Django settings.
"""

from django.conf import settings

from common.src.interfaces.config_store import ConfigStore


def get_config_store() -> ConfigStore:
    """
    Get the configured ConfigStore implementation.

    Returns the appropriate ConfigStore backend based on the
    CONFIG_STORE_BACKEND setting in Django settings.

    Supported backends:
    - "elasticsearch" (default): Use Elasticsearch ta_config index
    - "sqlite": Use SQLite ConfigData table

    Returns:
        ConfigStore instance

    Raises:
        ValueError: If an unsupported backend is specified

    Example:
        from common.src.config_store_factory import get_config_store

        store = get_config_store()
        config, status = store.get("appsettings")
    """
    backend = getattr(settings, "CONFIG_STORE_BACKEND", "elasticsearch").lower()

    if backend == "elasticsearch":
        from common.src.adapters.elasticsearch.config_store import (
            ElasticsearchConfigStore,
        )

        return ElasticsearchConfigStore()
    elif backend == "sqlite":
        from common.src.adapters.sqlite.config_store import SQLiteConfigStore

        return SQLiteConfigStore()
    else:
        raise ValueError(
            f"Unsupported CONFIG_STORE_BACKEND: {backend}. "
            f"Supported: 'elasticsearch', 'sqlite'"
        )


# Singleton instance for reuse
_config_store_instance: ConfigStore | None = None


def get_config_store_singleton() -> ConfigStore:
    """
    Get or create a singleton ConfigStore instance.

    This avoids recreating the store on every call, which is useful
    for performance and connection pooling.

    Returns:
        ConfigStore instance (cached)
    """
    global _config_store_instance

    if _config_store_instance is None:
        _config_store_instance = get_config_store()

    return _config_store_instance


def reset_config_store_singleton() -> None:
    """
    Reset the singleton ConfigStore instance.

    Useful for testing or when switching backends at runtime.
    """
    global _config_store_instance
    _config_store_instance = None
