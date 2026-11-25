"""Real concurrent connections on a disposable PostgreSQL, never production."""
import json
import os
import threading
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless

import httpx
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import close_old_connections, connection, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone

from indicators import ai_narrative as service
from indicators.models import AINarrativeDraft, AINarrativeReview, Indicator, Observation, Source
from indicators.storage import save_raw


@skipUnless(connection.vendor == 'postgresql', 'Requires the owned PostgreSQL runner')
class NarrativePostgresTests(TransactionTestCase):
    def setUp(self):
        super().setUp()
        directory = self.enterContext(TemporaryDirectory(dir=os.environ['HERMES_TEST_SCRATCH']))
        self.enterContext(override_settings(DEKSI_RAW_DIR=Path(directory),
            DEKSI_AI_NARRATIVES_ENABLED=True, LLM_BASE_URL='http://127.0.0.1:11434/v1',
            LLM_MODEL='synthetic:1', LLM_API_KEY=''))
        self.users = [get_user_model().objects.create_user(username=f'ai-pg-{i}', is_staff=True) for i in range(2)]
        permissions = Permission.objects.filter(content_type__app_label='indicators', codename__in=(
            'generate_ainarrativedraft', 'review_ainarrativedraft', 'view_ainarrativedraft'))
        for user in self.users:
            user.user_permissions.set(permissions)
        self.source, _ = Source.objects.get_or_create(source_id='BPS', defaults={
            'source_name': 'SYNTHETIC BPS', 'institution': 'SYNTHETIC', 'primary_url': 'https://www.bps.go.id/'})
        self.indicator = Indicator.objects.create(code='pdb', name='PDB SYNTHETIC', category='Test', unit='%')
        raw, _ = save_raw(self.source, b'PG SYNTHETIC', 'synthetic.json')
        self.row = Observation.objects.create(indicator=self.indicator, source=self.source,
            raw_file=raw, observation_date=date(2025, 6, 30), period_label='Q2 2025', frequency='quarterly',
            data_type='yoy', value=Decimal('5'), unit='%', validation_status='published',
            reviewed_by=self.users[0], reviewed_at=timezone.now())

    def payload(self):
        return {'summary': 'Kegiatan ekonomi dibandingkan dengan periode tahunan sebelumnya.',
                'meaning': 'PDB adalah ukuran kegiatan ekonomi, bukan pendapatan tiap keluarga.',
                'comparison': None, 'limitations': 'Angka ini belum menjelaskan penyebab perubahan.',
                'factRefs': ['facts.current']}

    def ready(self):
        draft = service.request_draft(self.users[0], request_key=uuid.uuid4(), observation_id=self.row.pk)
        response = {'model': 'synthetic:1', 'choices': [{'finish_reason': 'stop',
            'message': {'content': json.dumps(self.payload())}}]}
        service.run_once(transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=response)))
        draft.refresh_from_db()
        self.assertEqual(draft.generation_status, 'ready')
        return draft

    def race(self, action):
        barrier = threading.Barrier(2)
        results = [None, None]
        def run(index):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                barrier.wait(timeout=10)
                results[index] = action(index)
            except BaseException as error:
                results[index] = error
            finally:
                connections.close_all()
        threads = [threading.Thread(target=run, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertFalse(any(isinstance(value, BaseException) for value in results), repr(results))
        return results

    def test_same_request_key_concurrently_returns_one_row(self):
        key = uuid.uuid4()
        results = self.race(lambda _index: service.request_draft(
            self.users[0], request_key=key, observation_id=self.row.pk).pk)
        self.assertEqual(results[0], results[1])
        self.assertEqual(AINarrativeDraft.objects.count(), 1)

    def test_distinct_keys_compete_for_one_database_slot(self):
        def request(index):
            try:
                service.request_draft(self.users[index], request_key=uuid.uuid4(), observation_id=self.row.pk)
                return 'queued'
            except service.NarrativeError as error:
                return error.code
        self.assertEqual(sorted(self.race(request)), ['busy', 'queued'])
        self.assertEqual(AINarrativeDraft.objects.count(), 1)

    def test_two_real_review_endpoints_append_one_decision_only(self):
        draft = self.ready()
        body = {'contentDigest': draft.content_digest, 'decision': 'approved', 'notes': ''}
        def post(index):
            client = Client()
            client.force_login(self.users[index])
            return client.post(f'/api/admin/ai-narratives/{draft.pk}/review/',
                json.dumps(body), content_type='application/json').status_code
        self.assertEqual(sorted(self.race(post)), [200, 409])
        self.assertEqual(AINarrativeReview.objects.filter(draft=draft).count(), 1)
        self.row.refresh_from_db()
        self.assertEqual(self.row.value, Decimal('5'))

    def test_two_workers_send_exactly_one_completion_for_one_queued_request(self):
        draft = service.request_draft(self.users[0], request_key=uuid.uuid4(), observation_id=self.row.pk)
        calls = []
        lock = threading.Lock()
        def handle(request):
            with lock:
                calls.append(str(request.url))
            return httpx.Response(200, json={'model': 'synthetic:1', 'choices': [
                {'finish_reason': 'stop', 'message': {'content': json.dumps(self.payload())}}]})
        def worker(_index):
            row = service.run_once(transport=httpx.MockTransport(handle))
            return row.pk if row else None
        self.race(worker)
        self.assertEqual(len(calls), 1)
        draft.refresh_from_db()
        self.assertEqual(draft.generation_status, 'ready')

    def test_source_writer_finishes_before_approval_then_stale_input_is_refused(self):
        draft = self.ready()
        writer_holds_master = threading.Event()
        release_writer = threading.Event()
        result = []
        def writer():
            close_old_connections()
            try:
                with transaction.atomic():
                    Indicator.objects.select_for_update().get(pk=self.indicator.pk)
                    writer_holds_master.set()
                    if not release_writer.wait(10):
                        raise RuntimeError('Writer deadline')
                    Observation.objects.filter(pk=self.row.pk).update(value=Decimal('8'))
            except BaseException as error:
                result.append(error)
            finally:
                connections.close_all()
        thread = threading.Thread(target=writer)
        thread.start()
        try:
            self.assertTrue(writer_holds_master.wait(10))
            release_writer.set()
            with self.assertRaises(service.NarrativeError) as error:
                service.review_draft(self.users[0], draft.pk, content_digest=draft.content_digest,
                                     decision='approved', notes='')
            self.assertEqual(error.exception.code, 'stale_input')
        finally:
            release_writer.set()
            thread.join(timeout=15)
        self.assertFalse(thread.is_alive())
        self.assertFalse(result, repr(result))
        self.assertEqual(AINarrativeReview.objects.count(), 0)


@skipUnless(connection.vendor == 'postgresql', 'Requires the owned PostgreSQL runner')
class NarrativeMigrationPostgresTests(TransactionTestCase):
    def test_upgrade_and_rollback_preserve_existing_observation_tables(self):
        executor = MigrationExecutor(connection)
        final_targets = executor.loader.graph.leaf_nodes()
        old = [('indicators', '0024_kemenkeu_online_choice')]
        executor.migrate(old)
        try:
            apps = executor.loader.project_state(old).apps
            source = apps.get_model('indicators', 'Source').objects.create(source_id='MIGRATION_AI_TEST',
                source_name='SYNTHETIC', institution='SYNTHETIC', primary_url='https://example.test')
            indicator = apps.get_model('indicators', 'Indicator').objects.create(
                code='migration_ai_test', name='SYNTHETIC', category='Test', unit='%')
            row = apps.get_model('indicators', 'Observation').objects.create(
                indicator_id=indicator.pk, source_id=source.pk, observation_date=date(2025, 6, 30),
                period_label='Q2 2025', frequency='quarterly', data_type='yoy', unit='%', value=Decimal('0'))
            MigrationExecutor(connection).migrate(final_targets)
            self.assertEqual(Observation.objects.get(pk=row.pk).value, Decimal('0'))
            MigrationExecutor(connection).migrate(old)
            old_apps = MigrationExecutor(connection).loader.project_state(old).apps
            self.assertEqual(old_apps.get_model('indicators', 'Observation').objects.get(pk=row.pk).value, Decimal('0'))
        finally:
            MigrationExecutor(connection).migrate(final_targets)
