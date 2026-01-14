# Pluggable Datastores Implementation

This document describes the pluggable datastore architecture that allows TubeArchivist to use either Elasticsearch or database backends (SQLite, PostgreSQL, MySQL) for document storage.

## Overview

TubeArchivist has been refactored to support pluggable datastores through abstract interfaces and factory patterns. This allows users to choose between:

- **Elasticsearch** (default) - Original backend, full-featured
- **Model** (SQLite/PostgreSQL/MySQL) - Database-backed alternative for reduced dependencies

## Architecture

### Core Components

1. **Interfaces** (`backend/common/src/interfaces/`)
   - `ConfigStore` - Abstract interface for configuration storage
   - `DocumentStore` - Abstract interface for document storage (videos, channels, etc.)

2. **Adapters** (`backend/common/src/adapters/`)
   - `ElasticsearchConfigStore` - ES implementation for config
   - `ModelConfigStore` - Django ORM implementation for config
   - `ElasticsearchDocumentStore` - ES implementation for documents
   - `ModelDocumentStore` - Django ORM implementation for documents

3. **Factories** (`backend/common/src/`)
   - `get_config_store()` - Returns appropriate config store
   - `get_document_store(index_name)` - Returns appropriate document store
   - Convenience functions: `get_video_store()`, `get_channel_store()`, etc.

4. **Models** (`backend/common/models.py`)
   - `ConfigData` - Stores configuration key-value pairs
   - `BaseDocument` - Abstract base for document models
   - `VideoDocument`, `ChannelDocument`, `PlaylistDocument`, etc.

### What's Been Integrated

✅ **Fully Integrated (using factories):**
- `ta_video` - Video documents via `YouTubeItem` base class
- `ta_channel` - Channel documents via `YouTubeItem` base class
- `ta_playlist` - Playlist documents via `YouTubeItem` base class
- `ta_download` - Download queue via `PendingInteract` class
- `ta_comment` - Comments via `Comments` class
- `ta_config` - Configuration via `AppConfig` and `UserConfig`

⏸️ **Partial Integration:**
- `ta_subtitle` - Still uses ElasticWrap for bulk operations (complex queries)

## Configuration

### Environment Variables

```bash
# Configuration storage backend (default: elasticsearch)
CONFIG_STORE_BACKEND=model|elasticsearch

# Document storage backend (default: elasticsearch)
DOCUMENT_STORE_BACKEND=model|elasticsearch
```

### Using SQLite/PostgreSQL/MySQL

1. Set environment variables:
```bash
export CONFIG_STORE_BACKEND=model
export DOCUMENT_STORE_BACKEND=model
```

2. Run Django migrations:
```bash
python manage.py migrate
```

3. Migrate existing data (if upgrading from Elasticsearch):
```bash
# Migrate configuration
python manage.py migrate_config_to_model [--dry-run] [--verbose]

# Migrate all documents
python manage.py migrate_documents_to_model all [--dry-run] [--verbose]

# Or migrate specific indices
python manage.py migrate_documents_to_model video [--dry-run]
python manage.py migrate_documents_to_model channel [--dry-run]
```

### Using Elasticsearch (default)

No changes needed - set environment variables to `elasticsearch` or leave unset.

## Implementation Details

### Interface Design

All interfaces use exception-based error handling (Pythonic) rather than HTTP status codes:

```python
from common.src.interfaces.config_store import ConfigNotFoundError
from common.src.interfaces.document_store import DocumentNotFoundError

try:
    doc = store.get("doc_id")
except DocumentNotFoundError:
    # Handle not found
    pass
```

### Document Store Operations

```python
from common.src.document_store_factory import get_video_store

store = get_video_store()

# Create
store.create("video_id", {"title": "Video Title", ...})

# Read
doc = store.get("video_id")  # Raises DocumentNotFoundError if not found

# Update (partial merge)
store.update("video_id", {"view_count": 1000})

# Delete
store.delete("video_id")  # Raises DocumentNotFoundError if not found

# Check existence
if store.exists("video_id"):
    ...

# Query (basic filtering)
results = store.query(
    filters={"channel_id": "UC..."},
    sort=[("published", "desc")],
    limit=10,
    offset=0
)

# Bulk operations
store.bulk_create([
    ("vid1", {"title": "Video 1"}),
    ("vid2", {"title": "Video 2"}),
])
```

### Config Store Operations

```python
from common.src.config_store_factory import get_config_store

store = get_config_store()

# Get config
config = store.get("app_config")  # Raises ConfigNotFoundError if not found

# Set config (full replacement)
store.set("app_config", {"downloads": {...}})

# Update config (partial merge)
store.update("app_config", {"downloads": {"throttle": "3"}})

# Delete config
store.delete("app_config")  # Raises ConfigNotFoundError if not found
```

## Migration Commands

### migrate_config_to_model

Migrates configuration data from Elasticsearch to database.

```bash
# Preview migration
python manage.py migrate_config_to_model --dry-run --verbose

# Perform migration
python manage.py migrate_config_to_model --verbose
```

### migrate_documents_to_model

Migrates document data from Elasticsearch to database.

```bash
# Migrate all indices
python manage.py migrate_documents_to_model all --verbose

# Migrate specific index
python manage.py migrate_documents_to_model video --verbose

# Preview migration with batch size
python manage.py migrate_documents_to_model download --dry-run --batch-size 50

# Available indices:
# - download (ta_download)
# - video (ta_video)
# - channel (ta_channel)
# - playlist (ta_playlist)
# - comment (ta_comment)
# - subtitle (ta_subtitle)
```

## Testing

Comprehensive test suite covers all implementations:

```bash
# Run all tests
python manage.py test backend.common.tests

# Test specific components
python manage.py test backend.common.tests.test_adapters.test_model_document_store
python manage.py test backend.common.tests.test_document_store_factory
python manage.py test backend.common.tests.test_adapters.test_elasticsearch_document_store
```

Test coverage:
- Config store adapters: 44 tests
- Document store adapters: 45+ tests
- Factory functions: 20 tests
- Integration tests: 15 tests
- **Total: 120+ tests**

## Limitations & Future Work

### Current Limitations

1. **Subtitle bulk operations** - `ta_subtitle` still uses ElasticWrap directly for bulk indexing and complex queries. Would require extending DocumentStore interface.

2. **Complex queries** - Some advanced Elasticsearch queries (`_update_by_query`, `_delete_by_query`, bulk scripts) still use ElasticWrap directly. The model backend handles these by fetching, filtering, and updating in memory.

3. **Performance** - Model backend query performance is not optimized for large datasets (deserializes all documents to filter). Consider using database-specific queries for production.

### Future Enhancements

1. Add native database queries to ModelDocumentStore for better performance
2. Extend DocumentStore interface to support bulk update/delete operations
3. Add support for full-text search in model backend
4. Implement Redis replacement for cache/queue operations
5. Add database indexes for commonly filtered fields

## Benefits

1. **Reduced Dependencies** - Can run with just PostgreSQL/MySQL instead of Elasticsearch
2. **Simpler Deployment** - Fewer moving parts for small deployments
3. **Cost Savings** - Lower resource usage for self-hosted instances
4. **Flexibility** - Choose backend based on needs and infrastructure
5. **Upstream Compatible** - Pluggable design maintains compatibility with upstream

## Examples

### Switching from Elasticsearch to SQLite

```bash
# 1. Backup your data
python manage.py migrate_documents_to_model all --verbose

# 2. Update environment
export CONFIG_STORE_BACKEND=model
export DOCUMENT_STORE_BACKEND=model

# 3. Restart application
# Application now uses SQLite for all document storage
```

### Hybrid Setup (Advanced)

You can mix backends:

```bash
# Use database for config, Elasticsearch for documents
export CONFIG_STORE_BACKEND=model
export DOCUMENT_STORE_BACKEND=elasticsearch
```

## Troubleshooting

### "Unknown index" error

Make sure you're using one of the supported index names:
- ta_config (config only)
- ta_download, ta_video, ta_channel, ta_playlist, ta_comment, ta_subtitle (documents)

### Migration fails with "Document has no ID"

Some documents in Elasticsearch may have malformed data. Use `--verbose` flag to identify problematic documents and clean them up manually.

### Tests failing

Ensure Django migrations are up to date:
```bash
python manage.py migrate
```

## Architecture Decisions

### Why Exceptions Instead of Status Codes?

The interface uses exceptions (ConfigNotFoundError, DocumentNotFoundError) rather than returning HTTP status codes because:
1. More Pythonic and idiomatic
2. Keeps implementation details (HTTP) separate from interface
3. Forces explicit error handling
4. Compatible with both ES and database backends

### Why Lazy Loading?

Document stores are lazy-loaded (`@property` with `_doc_store`) to avoid circular imports and only instantiate when needed.

### Why Delete-Then-Create for Upsert?

The `upload_to_es()` method does delete+create instead of update because Elasticsearch PUT has upsert semantics (full replacement), and this maintains backward compatibility.

## Contributing

When adding new document types:

1. Add Django model extending `BaseDocument`
2. Add entry to `INDEX_MODEL_MAP` in `document_store_factory.py`
3. Add convenience function (`get_xxx_store()`)
4. Create migration for the model
5. Add migration command support
6. Add tests

## See Also

- `Claude.md` - Project overview and architecture
- `DATASTORE_MIGRATION.md` - Detailed migration plan
- `backend/common/src/interfaces/` - Interface definitions
- `backend/common/src/adapters/` - Adapter implementations
- `backend/common/tests/` - Test suite
