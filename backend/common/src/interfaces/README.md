# TubeArchivist Datastore Interfaces

This package provides abstract base classes for pluggable datastore backends, enabling TubeArchivist to support multiple storage implementations (Elasticsearch, SQLite, etc.) without changing application code.

## Architecture

```
Application Code (AppConfig, UserConfig, etc.)
        ↓
    Factory (get_config_store())
        ↓
    Interface (ConfigStore ABC)
        ↓
    ┌───────────┴───────────┐
    ↓                       ↓
Elasticsearch          SQLite
  Adapter              Adapter
```

## Available Interfaces

### ConfigStore

**Purpose**: Key-value configuration storage for application and user settings.

**Location**: `config_store.py`

**Methods**:
- `get(key)` - Retrieve configuration by key
- `set(key, value)` - Store/replace configuration
- `update(key, updates)` - Partial update (merge)
- `delete(key)` - Remove configuration
- `exists(key)` - Check if key exists
- `list_keys(prefix)` - List all keys (optionally filtered)

**Implementations**:
- `ElasticsearchConfigStore` - Stores in `ta_config` index
- `SQLiteConfigStore` - Stores in `common_config_data` table

**Usage**:
```python
from common.src.config_store_factory import get_config_store

store = get_config_store()
config, status = store.get("appsettings")
if status == 200:
    print(config["subscriptions"]["channel_size"])
```

## Adding New Interfaces

When adding support for other datastores (video, channel, etc.), follow this pattern:

1. **Define the interface** in `interfaces/<name>_store.py`:
```python
from abc import ABC, abstractmethod

class VideoStore(ABC):
    @abstractmethod
    def get_video(self, video_id: str) -> tuple[dict | None, int]:
        """Get video by ID"""
        pass

    # ... other methods
```

2. **Implement adapters** in `adapters/<backend>/<name>_store.py`:
```python
from common.src.interfaces.video_store import VideoStore

class ElasticsearchVideoStore(VideoStore):
    def get_video(self, video_id: str) -> tuple[dict | None, int]:
        # Implementation using ES
        pass

class SQLiteVideoStore(VideoStore):
    def get_video(self, video_id: str) -> tuple[dict | None, int]:
        # Implementation using SQLite
        pass
```

3. **Create factory** in `src/<name>_store_factory.py`:
```python
from django.conf import settings

def get_video_store():
    backend = getattr(settings, "VIDEO_STORE_BACKEND", "elasticsearch")
    if backend == "elasticsearch":
        return ElasticsearchVideoStore()
    elif backend == "sqlite":
        return SQLiteVideoStore()
```

4. **Update application code** to use the factory:
```python
from common.src.video_store_factory import get_video_store

store = get_video_store()
video, status = store.get_video("abc123")
```

## Design Principles

1. **Backward Compatibility**: Default to Elasticsearch for existing deployments
2. **Configuration-based**: Switch backends via environment variables
3. **Consistent Interface**: All backends implement the same methods
4. **Status Codes**: HTTP-style status codes (200, 404, etc.) for consistency
5. **Type Hints**: Full type annotations for IDE support
6. **Documentation**: Comprehensive docstrings with examples

## Configuration

Set the backend via Django settings or environment variables:

```bash
# Elasticsearch (default)
CONFIG_STORE_BACKEND=elasticsearch

# SQLite
CONFIG_STORE_BACKEND=sqlite
```

In `config/settings.py`:
```python
CONFIG_STORE_BACKEND = environ.get("CONFIG_STORE_BACKEND", "elasticsearch")
```

## Migration

Each interface should provide a migration command to move data between backends:

```bash
python manage.py migrate_config_to_sqlite --dry-run
python manage.py migrate_config_to_sqlite --verbose
```

See `common/management/commands/migrate_config_to_sqlite.py` for reference implementation.
