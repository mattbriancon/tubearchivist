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
    - "model": Use Django ORM (works with any DB: SQLite, PostgreSQL, MySQL, etc.)

    Returns:
        ConfigStore instance

    Raises:
        ValueError: If an unsupported backend is specified

    Example:
        from common.src.config_store_factory import get_config_store

        store = get_config_store()
        config = store.get("appsettings")
    """
    backend = getattr(settings, "CONFIG_STORE_BACKEND", "elasticsearch").lower()

    if backend == "elasticsearch":
        from common.src.adapters.elasticsearch.config_store import (
            ElasticsearchConfigStore,
        )

        return ElasticsearchConfigStore()
    elif backend in ("model", "sqlite"):  # Accept 'sqlite' for backwards compat
        from common.src.adapters.model.config_store import ModelConfigStore

        return ModelConfigStore()
    else:
        raise ValueError(
            f"Unsupported CONFIG_STORE_BACKEND: {backend}. "
            f"Supported: 'elasticsearch', 'model'"
        )
