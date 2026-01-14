"""Tests for atomic queue operations with concurrent workers."""

import json
import threading
from datetime import datetime

import pytest
from common.models import DownloadQueueItem
from common.src.adapters.model.document_store import ModelDocumentStore
from django.test import TestCase


class TestAtomicQueueOperations(TestCase):
    """Test thread-safe queue operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.store = ModelDocumentStore(DownloadQueueItem)

        # Create test jobs
        self.jobs = []
        for i in range(10):
            job = {
                "youtube_id": f"test_vid_{i}",
                "status": "pending",
                "title": f"Test Video {i}",
                "channel_id": "test_channel",
                "timestamp": int(datetime.now().timestamp()) + i,
                "auto_start": i < 5,  # First 5 have auto_start
            }
            self.store.create(f"test_vid_{i}", job)
            self.jobs.append(job)

    def tearDown(self):
        """Clean up test data."""
        DownloadQueueItem.objects.all().delete()

    def test_claim_next_job_basic(self):
        """Test basic claim_next_job operation."""
        filters = {"status": "pending"}
        sort = [("timestamp", "asc")]
        claim_updates = {}

        job = self.store.claim_next_job(filters, sort, claim_updates)

        assert job is not None
        assert job["youtube_id"] == "test_vid_0"
        assert job["status"] == "pending"

    def test_claim_next_job_with_sort(self):
        """Test claiming with sorting."""
        filters = {"status": "pending"}
        sort = [("auto_start", "desc"), ("timestamp", "asc")]
        claim_updates = {}

        job = self.store.claim_next_job(filters, sort, claim_updates)

        # Should get first auto_start=True job
        assert job is not None
        assert job["auto_start"] is True
        assert job["youtube_id"] == "test_vid_0"

    def test_claim_next_job_no_matches(self):
        """Test claiming when no jobs match filters."""
        filters = {"status": "processing"}
        sort = [("timestamp", "asc")]
        claim_updates = {}

        job = self.store.claim_next_job(filters, sort, claim_updates)

        assert job is None

    def test_claim_next_job_with_updates(self):
        """Test claiming with status update."""
        filters = {"status": "pending"}
        sort = [("timestamp", "asc")]
        claim_updates = {"status": "processing"}

        job = self.store.claim_next_job(filters, sort, claim_updates)

        assert job is not None
        assert job["status"] == "processing"

        # Verify it was updated in DB
        updated = self.store.get("test_vid_0")
        assert updated["status"] == "processing"

    def test_concurrent_workers_no_duplicates(self):
        """
        Test that multiple workers don't claim the same job.

        This is the critical test for SELECT FOR UPDATE functionality.
        """
        claimed_jobs = []
        lock = threading.Lock()
        errors = []

        def worker():
            """Worker function that claims jobs."""
            try:
                for _ in range(3):  # Each worker tries to claim 3 jobs
                    filters = {"status": "pending"}
                    sort = [("timestamp", "asc")]
                    claim_updates = {"status": "processing"}

                    job = self.store.claim_next_job(filters, sort, claim_updates)
                    if job:
                        with lock:
                            claimed_jobs.append(job["youtube_id"])
            except Exception as e:
                errors.append(str(e))

        # Start 5 workers concurrently
        threads = []
        for _ in range(5):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        # Wait for all workers to complete
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify no duplicates were claimed
        assert len(claimed_jobs) == len(set(claimed_jobs)), (
            f"Duplicate jobs claimed: {claimed_jobs}"
        )

        # Verify all 10 jobs were claimed (5 workers * 3 jobs each = 15 attempts, but only 10 jobs)
        assert len(claimed_jobs) == 10

    def test_skip_locked_behavior(self):
        """
        Test that skip_locked prevents workers from waiting.

        When using SELECT FOR UPDATE with skip_locked=True, if a row is
        locked by another transaction, it should be skipped instead of blocking.
        """
        from django.db import transaction

        claimed_jobs = []
        lock = threading.Lock()

        def worker1():
            """First worker holds lock on first job."""
            with transaction.atomic():
                # Claim first job and hold the lock
                job = self.store.claim_next_job(
                    {"status": "pending"},
                    [("timestamp", "asc")],
                    {},
                )
                with lock:
                    claimed_jobs.append(("worker1", job["youtube_id"]))

                # Hold lock for a bit
                import time

                time.sleep(0.1)

        def worker2():
            """Second worker should skip locked job and get next one."""
            import time

            time.sleep(0.05)  # Start slightly after worker1

            with transaction.atomic():
                # Should skip the locked first job and get the second one
                job = self.store.claim_next_job(
                    {"status": "pending"},
                    [("timestamp", "asc")],
                    {},
                )
                if job:
                    with lock:
                        claimed_jobs.append(("worker2", job["youtube_id"]))

        t1 = threading.Thread(target=worker1)
        t2 = threading.Thread(target=worker2)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Both workers should have claimed jobs
        assert len(claimed_jobs) == 2

        # Worker 1 should have claimed test_vid_0
        worker1_jobs = [job for worker, job in claimed_jobs if worker == "worker1"]
        assert "test_vid_0" in worker1_jobs

        # Worker 2 should have skipped test_vid_0 and claimed a different one
        worker2_jobs = [job for worker, job in claimed_jobs if worker == "worker2"]
        assert len(worker2_jobs) == 1
        assert "test_vid_0" not in worker2_jobs

    def test_claim_respects_filters(self):
        """Test that claim_next_job respects all filters."""
        # Add a job with different channel
        job = {
            "youtube_id": "other_channel_vid",
            "status": "pending",
            "title": "Other Channel Video",
            "channel_id": "other_channel",
            "timestamp": 0,  # Lowest timestamp
            "auto_start": False,
        }
        self.store.create("other_channel_vid", job)

        # Claim with channel filter
        filters = {"status": "pending", "channel_id": "test_channel"}
        sort = [("timestamp", "asc")]

        claimed = self.store.claim_next_job(filters, sort, {})

        # Should not get the other_channel job even though it has lowest timestamp
        assert claimed is not None
        assert claimed["channel_id"] == "test_channel"
        assert claimed["youtube_id"] == "test_vid_0"

    def test_empty_queue(self):
        """Test behavior when queue is empty."""
        # Delete all jobs
        DownloadQueueItem.objects.all().delete()

        filters = {"status": "pending"}
        sort = [("timestamp", "asc")]

        job = self.store.claim_next_job(filters, sort, {})

        assert job is None
