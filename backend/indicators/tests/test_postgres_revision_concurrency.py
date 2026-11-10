"""PostgreSQL-only cross-connection source revision controls."""
import json
import threading
import time
import unittest
from queue import Queue

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, transaction
from django.test import Client, TransactionTestCase

from indicators.models import Source, SourceRevision


@unittest.skipUnless(connection.vendor == 'postgresql', 'Requires disposable PostgreSQL fixture')
class PostgresRevisionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.source = Source.objects.create(
            source_id='PG_FIXTURE', source_name='Synthetic', institution='Synthetic',
            primary_url='https://example.test/', acquisition_method='file_xlsx',
            data_format='xlsx', frequency='monthly',
        )
        staff = get_user_model().objects.create_user(username='synthetic-pg-admin', is_staff=True)
        self.clients = []
        for _ in range(2):
            client = Client(enforce_csrf_checks=True)
            client.force_login(staff)
            token = client.get('/api/auth/csrf/').json()['csrfToken']
            self.clients.append((client, token))

    def patch_status(self, client, token, status):
        return client.patch(
            '/api/admin/sources/PG_FIXTURE/update/',
            json.dumps({'status': status, 'expectedRevision': 0}),
            content_type='application/json', HTTP_X_CSRFTOKEN=token,
        )

    def test_two_simultaneous_stale_updates_do_not_both_succeed(self):
        barrier = threading.Barrier(2, timeout=5)
        results = Queue()

        def worker(client, token, status):
            close_old_connections()
            try:
                barrier.wait()
                results.put(self.patch_status(client, token, status).status_code)
            except Exception as error:
                results.put(error)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(*self.clients[0], 'inactive'), daemon=True),
                   threading.Thread(target=worker, args=(*self.clients[1], 'inactive'), daemon=True)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=12)
        self.assertTrue(all(not thread.is_alive() for thread in threads), 'Concurrent requests did not finish')
        values = [results.get_nowait(), results.get_nowait()]
        self.assertEqual(sorted(values, key=str), [200, 409])
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, 'inactive')
        self.assertEqual(SourceRevision.objects.filter(source=self.source).count(), 1)

    def test_update_waits_for_existing_source_row_lock(self):
        ready = threading.Event()
        result = Queue()
        pid = Queue()
        client, token = self.clients[0]

        def worker():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    pid.put(cursor.fetchone()[0])
                ready.set()
                result.put(self.patch_status(client, token, 'inactive').status_code)
            except Exception as error:
                result.put(error)
            finally:
                connection.close()

        thread = threading.Thread(target=worker, daemon=True)
        try:
            with transaction.atomic():
                Source.objects.select_for_update().get(pk=self.source.pk)
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    holder_pid = cursor.fetchone()[0]
                thread.start()
                self.assertTrue(ready.wait(5), 'Second connection did not start')
                worker_pid = pid.get(timeout=5)
                deadline = time.monotonic() + 6
                blocked = False
                while time.monotonic() < deadline:
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT pg_blocking_pids(%s)', [worker_pid])
                        if holder_pid in cursor.fetchone()[0]:
                            blocked = True
                            break
                    time.sleep(0.05)
                self.assertTrue(blocked, 'Update did not wait on the owned row lock')
        finally:
            if thread.ident is not None:
                thread.join(timeout=12)
        self.assertFalse(thread.is_alive(), 'Update did not finish after lock release')
        self.assertEqual(result.get_nowait(), 200)
        self.assertEqual(SourceRevision.objects.filter(source=self.source).count(), 1)
