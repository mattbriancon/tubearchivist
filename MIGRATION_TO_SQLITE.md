# Migration from Elasticsearch to SQLite

This document describes the ongoing migration from Elasticsearch to SQLite with Django ORM for TubeArchivist.

## Motivation

Elasticsearch is powerful but overkill for a self-hosted tool. This migration simplifies the architecture by:
- Removing the Elasticsearch dependency
- Using SQLite for data storage (already configured in Django)
- Utilizing Django ORM for queries instead of ES queries
- Reducing resource requirements for self-hosting

## Completed Work

### 1. Django Models Created

All necessary Django models have been created to replace Elasticsearch indices:

- **Channel Model** (`backend/channel/models.py`): Replaces `ta_channel` index
- **Playlist Model** (`backend/playlist/models.py`): Replaces `ta_playlist` index
- **Video Model** (`backend/video/models.py`): Replaces `ta_video` index
- **Subtitle Model** (`backend/video/models.py`): Replaces `ta_subtitle` index for full-text search
- **Comment Model** (`backend/video/models.py`): Replaces `ta_comment` index
- **Download Model** (`backend/download/models.py`): Replaces `ta_download` index
- **AppConfig Model** (`backend/appsettings/models.py`): Replaces `ta_config` index

Each model includes:
- Appropriate field types matching ES mappings
- Database indexes for commonly queried fields
- Foreign key relationships between models
- JSONField for nested/complex data structures

### 2. Model Helper Methods

All models now include helper methods for ES compatibility:

- **`to_dict()`**: Converts model instance to dictionary (matching ES document structure)
- **`from_dict(data)`**: Creates or updates model from ES-style dictionary
- **`sync_to_videos()`** (Channel only): Syncs channel data to related videos

These methods maintain compatibility with existing ES document formats while using ORM internally.

### 3. ORM Compatibility Layer

Created ORM-based replacements that match ElasticWrap interface for easier migration:

- **`backend/common/src/orm_wrap.py`**:
  - `ORMWrap` class - Drop-in replacement for `ElasticWrap`
  - `ORMPaginate` class - Drop-in replacement for `IndexPaginate`
  - Supports same method signatures: `get()`, `put()`, `post()`, `delete()`
  - Translates ES queries to Django ORM automatically

- **`backend/common/src/orm_generic.py`**:
  - `YouTubeItemORM` class - ORM-based replacement for `YouTubeItem`
  - Methods: `get_from_db()`, `save_to_db()`, `delete_from_db()`, `deactivate()`
  - Compatible aliases: `get_from_es`, `upload_to_es`, `del_in_es`

### 4. ORM-Based Search

- **`backend/common/src/search_orm.py`**:
  - `SearchORM` class - Replaces ES-based SearchForm
  - Search types: simple, video, channel, playlist, full (subtitles)
  - Uses Django Q objects for complex queries
  - `VideoQueryORM` class - Replaces ES query builder
  - Supports filtering by: channel, playlist, active, vid_type, watched, height
  - Sorting by: published, downloaded, views, likes, duration, filesize

### 5. ORM-Based Aggregations

- **`backend/stats/src/aggs_orm.py`**:
  - `StatsORM` class - Replaces ES aggregations
  - Methods for all statistics:
    - `get_video_stats()` - Video counts, media stats, view stats
    - `get_channel_stats()` - Channel counts and subscriber stats
    - `get_playlist_stats()` - Playlist counts
    - `get_download_stats()` - Download queue stats
    - `get_watch_progress()` - Watched/unwatched breakdown
    - `get_download_history()` - Daily download counts
    - `get_biggest_channels()` - Channels with most videos
    - `get_recent_videos()` - Most recently downloaded
    - `get_popular_videos()` - Most viewed videos
    - `get_all_stats()` - Complete statistics in one call

### 6. Infrastructure Changes

- **Docker Compose**: Removed Elasticsearch service and volume
- **Environment Settings**: Removed all ES-related environment variables from `backend/common/src/env_settings.py`
- **Migration Structure**: Created migration directories for all apps

## Quick Start: Using the New ORM Layer

The ORM compatibility layer allows you to start using ORM operations with minimal code changes:

### Example 1: Using ORMWrap (Drop-in ElasticWrap Replacement)

```python
# OLD (ElasticWrap):
from common.src.es_connect import ElasticWrap
response, status = ElasticWrap("ta_channel/_doc/UC123").get()
channel_data = response["_source"]

# NEW (ORMWrap - same interface!):
from common.src.orm_wrap import ORMWrap
response, status = ORMWrap("ta_channel/_doc/UC123").get()
channel_data = response["_source"]

# Or use Django ORM directly:
from channel.models import Channel
channel = Channel.objects.get(channel_id="UC123")
channel_data = channel.to_dict()
```

### Example 2: Using YouTubeItemORM

```python
# Create a new ORM-based channel handler:
from common.src.orm_generic import YouTubeItemORM
from channel.models import Channel

class YoutubeChannelORM(YouTubeItemORM):
    index_name = "ta_channel"
    model_class = Channel
    yt_base = "https://www.youtube.com/channel/"

# Use it the same way as YoutubeChannel:
channel = YoutubeChannelORM("UC123")
channel.get_from_db()  # Instead of get_from_es()
channel.save_to_db()   # Instead of upload_to_es()
```

### Example 3: Search with SearchORM

```python
from common.src.search_orm import SearchORM

# Simple search across all content:
searcher = SearchORM("python tutorial", search_type="simple")
results = searcher.search()
# Returns: {"videos": [...], "channels": [...], "playlists": [...]}

# Video search with filters:
searcher = SearchORM("django", search_type="video")
results = searcher.search(filters={"active": True, "vid_type": "videos"})

# Full-text subtitle search:
searcher = SearchORM("machine learning", search_type="full")
subtitle_results = searcher.search()
```

### Example 4: Statistics with StatsORM

```python
from stats.src.aggs_orm import StatsORM

# Get all statistics:
all_stats = StatsORM.get_all_stats()

# Get specific stats:
video_stats = StatsORM.get_video_stats()
channel_stats = StatsORM.get_channel_stats()
watch_progress = StatsORM.get_watch_progress()
biggest_channels = StatsORM.get_biggest_channels(limit=10)
```

### Example 5: Video Queries with VideoQueryORM

```python
from common.src.search_orm import VideoQueryORM

# Build complex video query:
query = VideoQueryORM(
    filters={"channel": "UC123", "active": True},
    sort_by="published",
    sort_order="desc"
)
videos = query.get_results(limit=50)
```

## Remaining Work

### Phase 1: Database Migrations (HIGH PRIORITY)

1. **Run Migrations**:
   ```bash
   python manage.py makemigrations channel playlist video download appsettings
   python manage.py migrate
   ```

2. **Data Migration**: If you have existing ES data, you'll need to:
   - Export data from Elasticsearch indices
   - Transform and import into SQLite tables
   - See section below on data migration strategy

### Phase 2: Gradual Code Migration Strategy

**Two Approaches:**

1. **Quick Migration (Using Compatibility Layer)**:
   - Replace `ElasticWrap` imports with `ORMWrap`
   - Replace `IndexPaginate` imports with `ORMPaginate`
   - Replace `YouTubeItem` with `YouTubeItemORM`
   - Minimal code changes, maintains same interface
   - Good for quick wins and testing

2. **Complete Migration (Direct ORM Usage)**:
   - Replace ES operations with Django ORM directly
   - Use model methods: `.objects.get()`, `.filter()`, `.save()`, `.delete()`
   - More maintainable long-term
   - Better performance
   - Requires more extensive code changes

**Recommended: Start with approach #1, then gradually refactor to #2**

### Phase 3: Replace Elasticsearch Code

The following files/modules heavily use Elasticsearch and need to be refactored:

#### Core Infrastructure
- `backend/common/src/es_connect.py` - **DELETE**: ElasticWrap class and IndexPaginate
- `backend/config/management/commands/ta_connection.py` - Remove ES connection checks

#### Index/CRUD Operations
These files contain classes that inherit from `YouTubeItem` and use ES operations:
- `backend/channel/src/index.py` - YoutubeChannel class
- `backend/playlist/src/index.py` - YoutubePlaylist class
- `backend/video/src/index.py` - YoutubeVideo class
- `backend/video/src/subtitle.py` - YoutubeSubtitle class
- `backend/video/src/comments.py` - Comments class
- `backend/download/src/index.py` - Download queue operations
- `backend/appsettings/src/config.py` - AppConfig class

**Refactoring Strategy for Index Files**:
```python
# OLD (Elasticsearch):
from common.src.es_connect import ElasticWrap
response, status = ElasticWrap(self.es_path).get()

# NEW (Django ORM):
from channel.models import Channel
channel = Channel.objects.get(channel_id=channel_id)
```

#### Search Functionality
- `backend/common/src/searching.py` - SearchForm and QueryBuilder classes
  - Replace multi_match queries with Q objects and __icontains
  - Replace fuzzy search with trigram similarity (or simple contains)

**Example Migration**:
```python
# OLD (ES):
query = {
    "multi_match": {
        "query": search_term,
        "fields": ["title", "description", "channel.channel_name"],
        "type": "bool_prefix",
        "fuzziness": "auto"
    }
}

# NEW (Django ORM):
from django.db.models import Q
results = Video.objects.filter(
    Q(title__icontains=search_term) |
    Q(description__icontains=search_term) |
    Q(channel__channel_name__icontains=search_term)
).select_related('channel')
```

#### Query Building
- `backend/video/src/query_building.py` - Video filtering and sorting
  - Replace ES bool queries with Django Q objects
  - Replace ES sorting with .order_by()
  - Replace Painless scripts with Python logic

**Example Migration**:
```python
# OLD (ES):
query = {
    "bool": {
        "must": [
            {"term": {"active": True}},
            {"term": {"channel.channel_id": channel_id}}
        ]
    },
    "sort": [{"published": {"order": "desc"}}]
}

# NEW (Django ORM):
videos = Video.objects.filter(
    active=True,
    channel_id=channel_id
).order_by('-published')
```

#### Aggregations/Statistics
- `backend/stats/src/aggs.py` - All aggregation queries
  - Replace ES aggregations with Django's aggregate() and annotate()

**Example Migration**:
```python
# OLD (ES):
aggs = {
    "total_size": {"sum": {"field": "media_size"}},
    "video_count": {"value_count": {"field": "youtube_id"}}
}

# NEW (Django ORM):
from django.db.models import Sum, Count
stats = Video.objects.aggregate(
    total_size=Sum('media_size'),
    video_count=Count('youtube_id')
)
```

#### Pagination
- `backend/common/src/es_connect.py` - IndexPaginate class
  - Replace Point-in-Time pagination with Django's standard pagination
  - Or use keyset pagination for better performance

**Example Migration**:
```python
# OLD (ES PIT):
paginator = IndexPaginate(index_name, data, keep_source=True)
results = paginator.get_results()

# NEW (Django):
from django.core.paginator import Paginator
paginator = Paginator(queryset, per_page=500)
page = paginator.get_page(page_number)
```

### Phase 3: Full-Text Search

For subtitle full-text search, you have options:

**Option 1: Simple Contains (Recommended for MVP)**:
```python
# Simple but works for most cases
results = Subtitle.objects.filter(subtitle_line__icontains=search_term)
```

**Option 2: SQLite FTS5 Extension (Better Performance)**:
```python
# Requires enabling FTS5 virtual table
# More complex to set up but provides better search
```

**Option 3: PostgreSQL (If You Switch Later)**:
```python
# Django's SearchVector/SearchRank work great with Postgres
from django.contrib.postgres.search import SearchVector, SearchRank
```

### Phase 4: Serializers (Lower Priority)

Update DRF serializers to use Django model instances instead of ES documents:
- `backend/video/serializers.py`
- `backend/channel/serializers.py`
- `backend/playlist/serializers.py`

Most serializers should work with minimal changes since they already define the field structure.

### Phase 5: Views and API Endpoints

Update all views/viewsets that call ES code:
- Replace `.get_from_es()` with `.objects.get()`
- Replace `.upload_to_es()` with `.save()`
- Replace `.delete_from_es()` with `.delete()`

### Phase 6: Testing and Cleanup

1. **Update Tests**: All tests that mock ES responses need updating
2. **Remove ES Files**: Delete `backend/common/src/es_connect.py` and related files
3. **Remove ES Mappings**: Delete `backend/appsettings/index_mapping.json`
4. **Update Documentation**: Update README and other docs to remove ES references

## Data Migration Strategy

If you have existing data in Elasticsearch:

1. **Export from ES**:
   ```python
   # Use ElasticWrap to export all documents from each index
   # Save to JSON files
   ```

2. **Transform Data**:
   - Map ES document structure to Django model fields
   - Handle nested objects (convert to JSONField or related models)
   - Transform date formats (epoch_second → datetime)

3. **Import to SQLite**:
   ```python
   # Use Django ORM bulk_create for efficient imports
   Channel.objects.bulk_create(channel_list, batch_size=1000)
   ```

## Search Performance Considerations

- **Indexes**: Models have indexes on commonly queried fields
- **LIKE Queries**: SQLite handles `LIKE '%term%'` decently for small-medium datasets
- **Optimization**: If search becomes slow, consider:
  - Adding more indexes
  - Using SQLite FTS5 extension
  - Migrating to PostgreSQL for better full-text search
  - Caching frequent searches with Redis

## Key Differences from Elasticsearch

| Feature | Elasticsearch | SQLite + Django ORM |
|---------|---------------|---------------------|
| Full-text search | Powerful, with stemming, fuzzy matching | Basic LIKE queries or FTS5 |
| Nested objects | Native support | Use JSONField or relations |
| Aggregations | Rich aggregation framework | Django aggregate/annotate |
| Bulk operations | Fast bulk indexing | Use bulk_create/bulk_update |
| Scalability | Horizontal scaling | Vertical scaling only |
| Resource usage | High (JVM, memory) | Low (embedded database) |
| Setup complexity | Requires separate service | Built into Django |

## Testing the Migration

After implementing changes:

1. **Unit Tests**: Test each model's CRUD operations
2. **Integration Tests**: Test search functionality end-to-end
3. **Performance Tests**: Compare query performance
4. **Data Integrity**: Verify all data migrated correctly

## Notes for Developers

- The codebase is extensive and deeply integrated with ES
- This migration will touch 50+ files
- Expect this to be multiple PRs worth of work
- Consider doing the migration incrementally (one domain at a time)
- Keep the ES code path until the new code is proven stable (feature flag)

## Questions?

This is a major architectural change. If you have questions about specific components or need help with the migration, please open an issue.
