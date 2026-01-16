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

### 2. Infrastructure Changes

- **Docker Compose**: Removed Elasticsearch service and volume
- **Environment Settings**: Removed all ES-related environment variables from `backend/common/src/env_settings.py`
- **Migration Structure**: Created migration directories for all apps

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

### Phase 2: Replace Elasticsearch Code

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
