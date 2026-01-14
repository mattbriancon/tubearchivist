"""
Django management command to migrate documents from Elasticsearch to database.

Usage:
    python manage.py migrate_documents_to_model [index] [--dry-run] [--verbose]

Arguments:
    index: Which index to migrate (download, video, channel, playlist, comment, subtitle, all)

Options:
    --dry-run: Preview what would be migrated without actually writing
    --verbose: Show detailed output for each document
"""

from django.core.management.base import BaseCommand

from common.src.adapters.elasticsearch.document_store import (
    ElasticsearchDocumentStore,
)
from common.src.adapters.model.document_store import ModelDocumentStore
from common.src.interfaces.document_store import DocumentNotFoundError


class Command(BaseCommand):
    help = "Migrate documents from Elasticsearch to database (via Django ORM)"

    INDEX_MAP = {
        "download": ("ta_download", "DownloadQueueItem"),
        "video": ("ta_video", "VideoDocument"),
        "channel": ("ta_channel", "ChannelDocument"),
        "playlist": ("ta_playlist", "PlaylistDocument"),
        "comment": ("ta_comment", "CommentDocument"),
        "subtitle": ("ta_subtitle", "SubtitleDocument"),
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "index",
            type=str,
            choices=list(self.INDEX_MAP.keys()) + ["all"],
            help="Which index to migrate (or 'all' for all indices)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview migration without writing to database",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output for each document",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for bulk operations (default: 100)",
        )

    def handle(self, *args, **options):
        index_arg = options["index"]
        dry_run = options["dry_run"]
        verbose = options["verbose"]
        batch_size = options["batch_size"]

        # Determine which indices to migrate
        if index_arg == "all":
            indices_to_migrate = list(self.INDEX_MAP.keys())
        else:
            indices_to_migrate = [index_arg]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be written")
            )

        total_migrated = 0
        total_failed = 0
        total_skipped = 0

        for index_name in indices_to_migrate:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.SUCCESS(f"Migrating {index_name}..."))
            self.stdout.write("=" * 60)

            migrated, failed, skipped = self._migrate_index(
                index_name, dry_run, verbose, batch_size
            )

            total_migrated += migrated
            total_failed += failed
            total_skipped += skipped

        # Final summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Overall Migration Summary:"))
        self.stdout.write(f"  Total migrated:      {total_migrated}")
        if total_skipped > 0:
            self.stdout.write(
                self.style.WARNING(f"  Total skipped:       {total_skipped}")
            )
        if total_failed > 0:
            self.stdout.write(self.style.ERROR(f"  Total failed:        {total_failed}"))

        if dry_run:
            self.stdout.write(
                "\n"
                + self.style.WARNING(
                    "DRY RUN completed - run without --dry-run to perform migration"
                )
            )
        elif total_failed == 0:
            self.stdout.write(
                "\n" + self.style.SUCCESS("✓ All migrations completed successfully!")
            )
            self.stdout.write(
                "\nTo use database for document storage, set environment variable:"
            )
            self.stdout.write("  DOCUMENT_STORE_BACKEND=model")
        else:
            self.stdout.write(
                "\n"
                + self.style.ERROR(
                    f"⚠ Migration completed with {total_failed} error(s)"
                )
            )

    def _migrate_index(self, index_name, dry_run, verbose, batch_size):
        """Migrate a single index."""
        from common.models import (
            ChannelDocument,
            CommentDocument,
            DownloadQueueItem,
            PlaylistDocument,
            SubtitleDocument,
            VideoDocument,
        )

        # Get index info
        es_index, model_name = self.INDEX_MAP[index_name]

        # Get model class
        model_map = {
            "DownloadQueueItem": DownloadQueueItem,
            "VideoDocument": VideoDocument,
            "ChannelDocument": ChannelDocument,
            "PlaylistDocument": PlaylistDocument,
            "CommentDocument": CommentDocument,
            "SubtitleDocument": SubtitleDocument,
        }
        model_class = model_map[model_name]

        # Initialize stores
        es_store = ElasticsearchDocumentStore(es_index)
        model_store = ModelDocumentStore(model_class)

        # Get all documents from ES
        self.stdout.write(f"Fetching documents from {es_index}...")
        try:
            # Query all documents (no filters)
            all_docs = es_store.query()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to fetch documents from ES: {e}")
            )
            return 0, 0, 0

        if not all_docs:
            self.stdout.write(
                self.style.WARNING(f"No documents found in {es_index}")
            )
            return 0, 0, 0

        self.stdout.write(f"Found {len(all_docs)} document(s)")

        migrated = 0
        failed = 0
        skipped = 0

        # Process in batches for efficiency
        for i in range(0, len(all_docs), batch_size):
            batch = all_docs[i : i + batch_size]

            for doc in batch:
                # Get doc ID (ES stores it as _id or youtube_id depending on index)
                doc_id = doc.get("_id") or doc.get("youtube_id") or doc.get(
                    "channel_id"
                ) or doc.get("playlist_id")

                if not doc_id:
                    if verbose:
                        self.stdout.write(
                            self.style.ERROR(f"  ✗ Document has no ID, skipping")
                        )
                    failed += 1
                    continue

                # Check if already exists
                if model_store.exists(doc_id):
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⊘ {doc_id} - already exists in database"
                            )
                        )
                    skipped += 1
                    continue

                # Remove _id from document content before storing
                doc_content = {k: v for k, v in doc.items() if k != "_id"}

                # Migrate document (unless dry run)
                if not dry_run:
                    try:
                        model_store.create(doc_id, doc_content)
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"  ✗ {doc_id} - error writing to database: {e}"
                            )
                        )
                        failed += 1
                        continue

                if verbose:
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {doc_id} - migrated successfully")
                    )
                migrated += 1

        # Summary for this index
        self.stdout.write(f"\n{index_name} Summary:")
        self.stdout.write(self.style.SUCCESS(f"  Migrated:            {migrated}"))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f"  Skipped (existing):  {skipped}"))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f"  Failed:              {failed}"))

        return migrated, failed, skipped
