import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from indicators.models import RawFile, Source
from indicators.schedule_model import ScheduleAudit, ScheduleConfig
from indicators.schedule_views import schedule_update
from indicators.source_admin_views import admin_source_archive, admin_source_delete
from indicators.source_status import InactiveSourceError
from indicators.sync_history_model import SyncRun
from indicators.sync_history_service import begin_sync_run


@skipUnlessDBFeature("has_select_for_update")
class SourceLifecyclePostgresTests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.user = get_user_model().objects.create_user(username="fixture-lifecycle-admin", is_staff=True)
        self.source = Source.objects.create(
            source_id="PG_FIXTURE", source_name="Fixture source", institution="Fixture institution",
            primary_url="https://example.test/", acquisition_method="file_xlsx",
            data_format="xlsx", frequency="monthly",
        )

    def _request(self, view):
        request = RequestFactory().post("/", json.dumps({"expectedRevision": 0}), content_type="application/json")
        request.user = self.user
        return view(request, self.source.source_id).status_code

    def _blocked_worker(self, fn):
        started = threading.Event()
        pid = []

        def run():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pid.append(cursor.fetchone()[0])
                started.set()
                return fn()
            finally:
                close_old_connections()

        return started, pid, run

    def _assert_blocked(self, started, pid):
        self.assertTrue(started.wait(10), "Worker failed to start")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_blocking_pids(%s)", [pid[0]])
                if cursor.fetchone()[0]:
                    return
            time.sleep(0.05)
        self.fail("Worker did not wait on a PostgreSQL lock")

    def test_archive_waits_for_start_and_rejects_running_sync(self):
        started, pid, worker = self._blocked_worker(lambda: self._request(admin_source_archive))
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                source = Source.objects.select_for_update().get(pk=self.source.pk)
                future = pool.submit(worker)
                self._assert_blocked(started, pid)
                SyncRun.objects.create(source=source, status="running", started_at=timezone.now())
            self.assertEqual(future.result(timeout=10), 409)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, "active")
        self.assertEqual(SyncRun.objects.filter(source=self.source).count(), 1)

    def test_delete_waits_and_rejects_new_related_raw(self):
        started, pid, worker = self._blocked_worker(lambda: self._request(admin_source_delete))
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                source = Source.objects.select_for_update().get(pk=self.source.pk)
                future = pool.submit(worker)
                self._assert_blocked(started, pid)
                raw = RawFile.objects.create(source=source, document_name="fixture", checksum_sha256="a" * 64)
            self.assertEqual(future.result(timeout=10), 409)
        self.assertTrue(Source.objects.filter(pk=self.source.pk).exists())
        self.assertTrue(RawFile.objects.filter(pk=raw.pk).exists())

    def test_start_waits_for_archive_then_rejects_inactive_source(self):
        def start():
            try:
                begin_sync_run(source=self.source)
            except InactiveSourceError:
                return "blocked"
            return "started"

        started, pid, worker = self._blocked_worker(start)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                Source.objects.select_for_update().get(pk=self.source.pk)
                future = pool.submit(worker)
                self._assert_blocked(started, pid)
                self.assertEqual(self._request(admin_source_archive), 200)
            self.assertEqual(future.result(timeout=10), "blocked")
        self.assertFalse(SyncRun.objects.filter(source=self.source).exists())

    def test_schedule_update_waiting_for_archive_does_not_change_schedule(self):
        config = ScheduleConfig.objects.create(source=self.source, interval_days=30, enabled=True)

        def update_schedule():
            request = RequestFactory().put(
                "/", json.dumps({"intervalDays": 7, "enabled": True}), content_type="application/json"
            )
            request.user = self.user
            return schedule_update(request, self.source.source_id).status_code

        started, pid, worker = self._blocked_worker(update_schedule)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                Source.objects.select_for_update().get(pk=self.source.pk)
                future = pool.submit(worker)
                self._assert_blocked(started, pid)
                self.assertEqual(self._request(admin_source_archive), 200)
            self.assertEqual(future.result(timeout=10), 400)
        config.refresh_from_db()
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, "archived")
        self.assertEqual(config.interval_days, 30)
        self.assertEqual(self.source.update_schedule, "")
        self.assertFalse(ScheduleAudit.objects.filter(source_id_snapshot=self.source.source_id).exists())


@skipUnlessDBFeature("has_select_for_update")
class SourceArchiveMigrationPostgresTests(TransactionTestCase):
    def test_existing_source_raw_and_revision_survive_upgrade(self):
        self.assertEqual(connection.vendor, "postgresql")
        previous = ("indicators", "0020_merge_analysis_schedule")
        target = ("indicators", "0021_source_archived")
        executor = MigrationExecutor(connection)
        executor.migrate([previous])
        old = executor.loader.project_state([previous]).apps
        source_old = old.get_model("indicators", "Source")
        raw_old = old.get_model("indicators", "RawFile")
        revision_old = old.get_model("indicators", "SourceRevision")
        source = source_old.objects.create(source_id="PG_UPGRADE", source_name="Fixture", institution="Fixture")
        raw = raw_old.objects.create(source=source, document_name="preserve", checksum_sha256="c" * 64)
        revision = revision_old.objects.create(source=source, version=1, action="tambah", before={}, after={})
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([target])
            new = executor.loader.project_state([target]).apps
            source_new = new.get_model("indicators", "Source")
            raw_new = new.get_model("indicators", "RawFile")
            revision_new = new.get_model("indicators", "SourceRevision")
            self.assertEqual(source_new.objects.get(pk=source.pk).source_name, "Fixture")
            self.assertTrue(raw_new.objects.filter(pk=raw.pk, source_id=source.pk).exists())
            self.assertTrue(revision_new.objects.filter(pk=revision.pk, source_id=source.pk).exists())
        finally:
            MigrationExecutor(connection).migrate([target])
