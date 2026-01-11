# TubeArchivist Datastore Migration Plan

## Goal
Replace multiple datastores (Elasticsearch, Redis) with SQLite using pluggable interfaces for upstream compatibility.

---

## Current Datastores

### 1. ELASTICSEARCH (Primary Application Data)
**Complexity to Replace**: ⭐⭐⭐⭐⭐ VERY HIGH

#### Indices:

**ta_video** - Video metadata and content
- Fields: title, description, tags, category, duration, watch status, stats, media info, SponsorBlock segments
- Nested: Full channel object embedded
- Size: Largest index (all downloaded videos)
- Access: `backend/video/src/index.py:152`
- Mapping: `backend/appsettings/index_mapping.json:111-428`

**ta_channel** - Channel information
- Fields: name, description, tags, subscriber_count, artwork URLs, subscription status, per-channel settings
- Access: `backend/channel/src/index.py:24`
- Mapping: `backend/appsettings/index_mapping.json:10-108`

**ta_playlist** - Playlist metadata
- Fields: name, description, entries (array of videos), type (regular/custom), sort order
- Access: `backend/playlist/src/index.py:21`
- Mapping: `backend/appsettings/index_mapping.json:502-604`

**ta_download** - Download queue
- Fields: video_id, status (pending/ignore/priority), timestamp, channel info
- Access: `backend/download/src/queue.py`
- Mapping: `backend/appsettings/index_mapping.json:431-499`

**ta_comment** - Video comments
- Fields: comment arrays, author, text, timestamps, like counts, parent references
- Access: `backend/video/src/comments.py:22`
- Mapping: `backend/appsettings/index_mapping.json:675-743`

**ta_subtitle** - Searchable subtitle fragments
- Fields: subtitle chunks (5 cues each), text, timestamps, language, video/channel associations
- Access: `backend/video/src/subtitle.py:334`
- Mapping: `backend/appsettings/index_mapping.json:607-672`

**ta_config** - Application and user configuration
- Fields: app settings, user preferences (per user_id)
- Access: `backend/appsettings/src/config.py:69,159`
- Mapping: `backend/appsettings/index_mapping.json:3-7`

#### Key Features Used:
- **Full-text search** with English analyzer
- **Nested object queries** (channel data embedded in videos)
- **Aggregations** for statistics
- **Bulk operations** for performance
- **Search-as-you-type** fields
- **Point-in-Time (PIT)** pagination

#### Abstraction Layer:
- `backend/common/src/es_connect.py` - ElasticWrap class (direct HTTP API)
- `backend/common/src/index_generic.py` - Base index operations
- Each app has `src/index.py` with domain-specific logic

---

### 2. REDIS (Queue + Cache + Message Broker)
**Complexity to Replace**: ⭐⭐⭐⭐ HIGH

#### Usage Patterns:

**RedisArchivist** - Key-value storage (`backend/common/src/ta_redis.py:31-117`)
- Message storage: `ta:message:{group}:{task_id}`
- Task progress notifications
- Version check cache: `ta:versioncheck:new`
- App start timestamp: `ta:STARTTIMESTAMP`
- TTL support for auto-expiration

**RedisQueue** - Sorted set queues (`backend/common/src/ta_redis.py:119-204`)
- `ta:download:channel` - Channel download queue
- `ta:download:playlist:full` - Full playlist refresh queue
- `ta:download:playlist:quick` - Quick playlist refresh queue
- `ta:download:video` - Video download queue
- `ta:index:comment` - Comment indexing queue
- `ta:reindex:ta_video` - Video reindex queue
- `ta:reindex:ta_channel` - Channel reindex queue
- `ta:reindex:ta_playlist` - Playlist reindex queue
- FIFO ordering via ZADD scores + ZPOPMIN

**TaskRedis** - Celery task management (`backend/common/src/ta_redis.py:206-259`)
- Pattern: `celery-task-meta-{task_id}`
- Task result storage
- Task commands (STOP, KILL)
- 24-hour TTL

**Celery Integration** (`backend/task/celery.py:21-23`)
- Broker: Task queue distribution
- Backend: Result storage
- Supports unix socket connections
- Namespace: `ta:`

**Pub/Sub Channels**:
- download, add, rescan, subchannel, subplaylist, playlistscan, setting

#### Critical Dependencies:
- Celery task queue (5.6.1)
- Sorted sets for queue ordering
- TTL for message cleanup
- Pub/sub for real-time updates

---

### 3. SQLITE (Django Essentials Only)
**Complexity to Replace**: ⭐ VERY LOW (Already using SQLite!)

#### Current Usage:
- Location: `{CACHE_DIR}/db.sqlite3`
- Size: Minimal (only 2 custom models + Django tables)

**user.Account** - Custom user model (`backend/user/models.py`)
- name, password, last_login, is_superuser, is_staff
- Groups and permissions (Django auth)
- Used for: Login, authentication, API auth

**task.CustomPeriodicTask** - Scheduled tasks (`backend/task/models.py`)
- Inherits django_celery_beat.PeriodicTask
- task_config (JSONField)
- Used for: Celery Beat scheduling

**Django Core Tables**:
- django_session, django_migrations, auth_group, auth_permission, django_admin_log, django_content_type

#### What's NOT in SQLite:
- ALL application data lives in Elasticsearch
- No video/channel/playlist models
- No relational joins for app logic

---

### 4. FILESYSTEM (Binary Storage)
**Complexity to Replace**: ⭐⭐⭐ MEDIUM

#### Structure:
```
/youtube/              # MEDIA_DIR - Permanent storage
  └── {channel_id}/
      ├── {video_id}.mp4
      └── {video_id}.{lang}.vtt

/cache/                # CACHE_DIR - Temporary storage
  ├── videos/          # Video thumbnails
  ├── channels/        # Channel artwork (thumb, banner, tvart)
  ├── playlists/       # Playlist thumbnails
  ├── download/        # Download staging
  ├── import/          # Manual import staging
  ├── backup/          # ES JSON backups
  └── db.sqlite3       # SQLite database
```

#### Key Files:
- `backend/download/src/thumbnails.py` - ThumbManager class
- `backend/video/src/subtitle.py:202-212` - Subtitle file writes
- `backend/video/src/index.py:315-333` - Video deletion
- `backend/channel/src/index.py:302-311` - Channel folder cleanup

---

## Migration Strategy Overview

### Phase 1: Create Pluggable Interfaces ✓ START HERE
1. **DataStore Interface** - Abstract base for all data operations
2. **SearchStore Interface** - Abstract search/query capabilities
3. **QueueStore Interface** - Abstract queue operations
4. **CacheStore Interface** - Abstract cache operations

### Phase 2: Implement Elasticsearch Adapters
Wrap existing ES logic behind interfaces (no behavior change)

### Phase 3: Implement SQLite Adapters
Build SQLite implementations of each interface

### Phase 4: Configuration Layer
Add settings to choose datastore backend (ES vs SQLite)

### Phase 5: Testing & Migration Tools
Data migration scripts, test parity

---

## Recommended Migration Order

### 1️⃣ **ta_config** (Easiest)
- Simple key-value data
- No search requirements
- Low complexity
- **Effort**: 1-2 days

### 2️⃣ **Redis Cache/Messages** (Medium)
- Key-value with TTL
- No complex data structures yet
- **Effort**: 2-3 days

### 3️⃣ **Redis Queues** (Medium-Hard)
- Need sorted set equivalent (SQLite ORDER BY + score)
- Multiple queue types
- **Effort**: 3-4 days

### 4️⃣ **ta_download** (Medium)
- Simple queue-like structure
- Basic filtering
- **Effort**: 2-3 days

### 5️⃣ **ta_channel** (Medium)
- Moderate complexity
- Some search requirements
- **Effort**: 3-4 days

### 6️⃣ **ta_playlist** (Medium-Hard)
- Array of videos (JSON field)
- Nested data
- **Effort**: 3-5 days

### 7️⃣ **ta_video** (Hardest)
- Largest dataset
- Complex nested objects
- Full-text search on multiple fields
- **Effort**: 5-7 days

### 8️⃣ **ta_comment** (Hard)
- Array data structures
- Search requirements
- **Effort**: 3-4 days

### 9️⃣ **ta_subtitle** (Very Hard)
- Full-text search critical
- Fragmented/chunked data
- Timestamp ranges
- **Effort**: 4-5 days

### 🔟 **Celery Broker** (Special Case)
- May need to keep Redis or use alternative (RabbitMQ, Database-backed)
- SQLite not recommended for Celery broker in production
- **Effort**: Research alternatives

---

## Key Challenges

### Full-Text Search
- **ES**: Built-in analyzers, tokenization, relevance scoring
- **SQLite**: FTS5 extension (good but different syntax/features)
- **Solution**: Abstract search query language

### Nested Objects
- **ES**: Native nested type with nested queries
- **SQLite**: JSON field + JSON functions (json_extract, json_each)
- **Solution**: ORM layer to translate queries

### Bulk Operations
- **ES**: _bulk API for high throughput
- **SQLite**: BEGIN TRANSACTION + executemany()
- **Solution**: Batch interface in abstraction

### Aggregations
- **ES**: Bucket/metric aggregations
- **SQLite**: Standard SQL GROUP BY
- **Solution**: Aggregate query builder

### Pagination
- **ES**: search_after + PIT
- **SQLite**: OFFSET/LIMIT or cursor-based
- **Solution**: Paginator interface

---

## Files to Modify (Pluggable Architecture)

### New Interface Modules:
- `backend/common/src/interfaces/datastore.py` - Base datastore interface
- `backend/common/src/interfaces/search.py` - Search interface
- `backend/common/src/interfaces/queue.py` - Queue interface
- `backend/common/src/interfaces/cache.py` - Cache interface

### ES Adapters (wrappers):
- `backend/common/src/adapters/elasticsearch/datastore.py`
- `backend/common/src/adapters/elasticsearch/search.py`
- `backend/common/src/adapters/redis/queue.py`
- `backend/common/src/adapters/redis/cache.py`

### SQLite Adapters (new):
- `backend/common/src/adapters/sqlite/datastore.py`
- `backend/common/src/adapters/sqlite/search.py`
- `backend/common/src/adapters/sqlite/queue.py`
- `backend/common/src/adapters/sqlite/cache.py`

### Configuration:
- `backend/config/settings.py` - Add DATASTORE_BACKEND setting
- `backend/common/src/datastore_factory.py` - Factory to instantiate correct backend

---

## Implementation Status

### ✅ Phase 1: ta_config Migration (COMPLETED)

**Completed:**
1. ✅ Created pluggable ConfigStore interface (`backend/common/src/interfaces/config_store.py`)
2. ✅ Implemented Elasticsearch adapter (`backend/common/src/adapters/elasticsearch/config_store.py`)
3. ✅ Implemented SQLite adapter (`backend/common/src/adapters/sqlite/config_store.py`)
4. ✅ Created factory pattern (`backend/common/src/config_store_factory.py`)
5. ✅ Added Django model ConfigData (`backend/common/models.py`)
6. ✅ Updated AppConfig to use interface (`backend/appsettings/src/config.py`)
7. ✅ Updated UserConfig to use interface (`backend/user/src/user_config.py`)
8. ✅ Created Django migration (`backend/common/migrations/0001_add_config_data_model.py`)
9. ✅ Created data migration command (`python manage.py migrate_config_to_sqlite`)

**How to Use:**

```bash
# Default: Uses Elasticsearch (backward compatible)
# No changes needed

# Switch to SQLite:
# 1. Run Django migration
python manage.py migrate

# 2. Migrate data from Elasticsearch to SQLite
python manage.py migrate_config_to_sqlite --verbose

# 3. Set environment variable
export CONFIG_STORE_BACKEND=sqlite

# 4. Restart application
```

**Testing:**
```bash
# Dry run to preview migration
python manage.py migrate_config_to_sqlite --dry-run --verbose

# Actual migration
python manage.py migrate_config_to_sqlite --verbose
```

**Architecture:**
- Interface: `ConfigStore` (abstract base class)
- Implementations: `ElasticsearchConfigStore`, `SQLiteConfigStore`
- Factory: `get_config_store()` returns configured backend
- Configuration: `CONFIG_STORE_BACKEND` setting (elasticsearch|sqlite)
- Backward compatible: Defaults to Elasticsearch

---

## Next Steps

**Recommendation**: Continue with **Redis Cache/Messages** migration:
- Similar key-value patterns
- Build on ta_config interface experience
- No complex data structures
- Moderate complexity
