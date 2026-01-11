"""
Django management command to migrate configuration data from Elasticsearch to SQLite.

Usage:
    python manage.py migrate_config_to_sqlite [--dry-run] [--verbose]

Options:
    --dry-run: Preview what would be migrated without actually writing to SQLite
    --verbose: Show detailed output for each configuration key migrated
"""

from django.core.management.base import BaseCommand

from common.src.adapters.elasticsearch.config_store import ElasticsearchConfigStore
from common.src.adapters.sqlite.config_store import SQLiteConfigStore


class Command(BaseCommand):
    help = "Migrate configuration data from Elasticsearch to SQLite"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview migration without writing to SQLite",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output for each config key",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be written")
            )

        # Initialize both stores
        self.stdout.write("Initializing datastores...")
        es_store = ElasticsearchConfigStore()
        sqlite_store = SQLiteConfigStore()

        # Get all keys from Elasticsearch
        self.stdout.write("Fetching configuration keys from Elasticsearch...")
        try:
            all_keys = es_store.list_keys()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to list Elasticsearch keys: {e}")
            )
            return

        if not all_keys:
            self.stdout.write(
                self.style.WARNING("No configuration keys found in Elasticsearch")
            )
            return

        self.stdout.write(f"Found {len(all_keys)} configuration key(s)")

        # Migrate each key
        migrated = 0
        failed = 0
        skipped = 0

        for key in all_keys:
            # Check if already exists in SQLite
            if sqlite_store.exists(key):
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(f"  ⊘ {key} - already exists in SQLite")
                    )
                skipped += 1
                continue

            # Get data from Elasticsearch
            data, status = es_store.get(key)
            if status != 200:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ {key} - failed to read from Elasticsearch (status {status})"
                    )
                )
                failed += 1
                continue

            if verbose:
                self.stdout.write(f"  → {key} - read from Elasticsearch")

            # Write to SQLite (unless dry run)
            if not dry_run:
                try:
                    _, write_status = sqlite_store.set(key, data)
                    if write_status not in (200, 201):
                        self.stdout.write(
                            self.style.ERROR(
                                f"  ✗ {key} - failed to write to SQLite (status {write_status})"
                            )
                        )
                        failed += 1
                        continue
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ {key} - error writing to SQLite: {e}")
                    )
                    failed += 1
                    continue

            if verbose:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ {key} - migrated successfully")
                )
            migrated += 1

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"Migration Summary:"))
        self.stdout.write(f"  Total keys found:    {len(all_keys)}")
        self.stdout.write(self.style.SUCCESS(f"  Migrated:            {migrated}"))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f"  Skipped (existing):  {skipped}"))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f"  Failed:              {failed}"))

        if dry_run:
            self.stdout.write(
                "\n"
                + self.style.WARNING(
                    "DRY RUN completed - run without --dry-run to perform migration"
                )
            )
        elif failed == 0:
            self.stdout.write(
                "\n" + self.style.SUCCESS("✓ Migration completed successfully!")
            )
            self.stdout.write(
                "\nTo use SQLite for config storage, set environment variable:"
            )
            self.stdout.write("  CONFIG_STORE_BACKEND=sqlite")
        else:
            self.stdout.write(
                "\n"
                + self.style.ERROR(
                    f"⚠ Migration completed with {failed} error(s)"
                )
            )
