# TubeArchivist

A self-hosted YouTube media server for archiving, organizing, and searching YouTube video collections offline.

## Tech Stack

**Backend**: Python 3.13, Django 5.2.9, Django REST Framework
**Frontend**: React 19.2.3, TypeScript, Vite
**Data**: Elasticsearch 8.18.2 (primary datastore), SQLite3 (Django metadata)
**Queue**: Celery 5.6.1 with Redis 7.1.0
**Downloader**: yt-dlp
**Server**: Uvicorn (ASGI) + Nginx

## Project Structure

```
backend/              # Django REST API
├── appsettings/     # Settings, backups, snapshots, ES index setup
├── channel/         # YouTube channel indexing
├── common/          # Shared utilities (ES wrapper, Redis, URL parsing)
├── config/          # Django configuration
├── download/        # Download queue, yt-dlp integration
├── playlist/        # Playlist management
├── stats/           # Statistics aggregations
├── task/            # Celery task definitions
├── user/            # User authentication and configuration
└── video/           # Video indexing, comments, subtitles

frontend/            # React SPA
└── src/
    ├── api/         # Backend API communication (loaders + actions)
    ├── components/  # Reusable React components
    ├── pages/       # Page components
    └── stores/      # Zustand state management
```

## Architecture

### Data Flow
1. **Download**: Celery tasks use yt-dlp to download videos from YouTube
2. **Index**: Metadata extracted and stored in Elasticsearch
3. **Serve**: React frontend queries Django REST API
4. **Background**: Celery Beat schedules periodic tasks (subscription updates, reindexing)

### Key Patterns

**Elasticsearch-centric**: Primary datastore with indices:
- `ta_video` - Video metadata
- `ta_channel` - Channel metadata
- `ta_playlist` - Playlist metadata
- `ta_download` - Download queue
- `ta_subtitle` - Video subtitles
- `ta_comment` - Video comments
- Mappings defined in `backend/appsettings/index_mapping.json`

**Task Queue**: Celery handles background operations:
- Download videos: `download_pending`
- Update subscriptions: `update_subscribed`
- Reindex content: `check_reindex`
- Run backups: `run_backup`
- Task definitions in `backend/task/tasks.py`

**Redis**: Message broker, cache, and queue management using custom `RedisQueue` class

**API-first**: RESTful endpoints with Swagger docs at `/api/docs/`

## Important Files

### Backend Core
- `backend/common/src/es_connect.py` - Elasticsearch wrapper
- `backend/common/src/ta_redis.py` - Redis interaction
- `backend/download/src/yt_dlp_handler.py` - yt-dlp integration
- `backend/task/tasks.py` - All Celery tasks
- `backend/appsettings/src/index_setup.py` - ES index management
- `docker_assets/run.sh` - Container startup sequence

### Frontend Core
- `frontend/src/main.tsx` - React entry point
- `frontend/src/configuration/routes.tsx` - Route definitions
- `frontend/src/api/` - API client layer

## Running Locally

The application runs in Docker containers:
1. **Nginx** (port 8000) - Serves frontend, proxies API
2. **Uvicorn** (port 8080 internal) - Django backend with 4 workers
3. **Celery Worker** - Background task processor
4. **Celery Beat** - Task scheduler
5. **Elasticsearch** - Search and primary data storage
6. **Redis** - Cache and message broker

Entry point: `docker_assets/run.sh` orchestrates migrations, static collection, and service startup.

## Development

- **Testing**: pytest for backend unit tests
- **Linting**: Pre-commit hooks with Black, isort, flake8, ESLint, Prettier
- **API Docs**: Auto-generated Swagger via drf-spectacular
- **Dev Server**: Vite dev server on port 3000 for frontend development
