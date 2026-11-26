import json
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TransactionTestCase, override_settings


@override_settings(DEKSI_PUBLIC_ENGINE_AI_ENABLED=True, DEKSI_ENGINE_AI_DAILY_LIMIT=3)
class PublicEngineAITests(TransactionTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.admin = get_user_model().objects.create_user(username='engine-ai-admin', is_staff=True)
        permission = Permission.objects.get(codename='review_publicengineairequest')
        self.admin.user_permissions.add(permission)
        self.csrf = self.client.get('/api/auth/csrf/').json()['csrfToken']

    def post(self, body):
        return self.client.post('/api/public-engine-ai/requests/', json.dumps(body), content_type='application/json',
                                HTTP_X_CSRFTOKEN=self.csrf)

    def test_public_click_queues_idempotently_but_never_generates_in_request(self):
        with patch('indicators.public_engine_ai.calculate_snapshot', return_value={
                'availableMetrics': {'pmtb_share': {'value': '20.00', 'resultDigest': 'a' * 64}},
                'inputDigest': 'b' * 64, 'period': 'Q1 2025', 'resultDigest': 'a' * 64}) as snapshot, \
             patch('indicators.public_engine_ai.call_provider') as provider:
            body = {'requestKey': str(uuid.uuid4()), 'quarter': '2025-03-31'}
            first = self.post(body)
            again = self.post(body)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(first.json()['request']['status'], 'queued')
        self.assertEqual(again.json()['request']['requestKey'], first.json()['request']['requestKey'])
        provider.assert_not_called()
        self.assertEqual(snapshot.call_count, 1)

    def test_public_read_hides_unapproved_and_requires_exact_metric_digest(self):
        from indicators.public_engine_ai import create_request
        from indicators.models import PublicEngineAIRequest
        with patch('indicators.public_engine_ai.calculate_snapshot', return_value={
                'availableMetrics': {'pmtb_share': {'value': '20.00', 'resultDigest': 'a' * 64, 'inputDigest': 'c' * 64}},
                'inputDigest': 'b' * 64, 'period': 'Q1 2025', 'resultDigest': 'a' * 64}):
            row, _ = create_request(uuid.uuid4(), '2025-03-31')
        with patch('indicators.public_engine_ai.calculate_snapshot', return_value={
                'inputDigest': row.input_digest, 'resultDigest': row.result_digest}):
            response = self.client.get(f'/api/public-engine-ai/requests/{row.request_key}/')
        self.assertEqual(response.json()['request']['status'], 'queued')
        self.assertNotIn('narrative', response.json()['request'])
        row.status = PublicEngineAIRequest.Status.APPROVED
        row.approved_result_digest = 'a' * 64
        row.narrative = {'summary': '<script>alert(1)</script>'}
        from indicators.public_engine_ai import _review_digest
        row.approved_content_digest = _review_digest(row)
        row.save(update_fields=['status', 'approved_result_digest', 'approved_content_digest', 'narrative'])
        with patch('indicators.public_engine_ai.calculate_snapshot', return_value={
                'inputDigest': row.input_digest, 'resultDigest': row.result_digest}):
            response = self.client.get(f'/api/public-engine-ai/requests/{row.request_key}/')
        self.assertNotIn('<script>', response.content.decode())
        self.assertEqual(response.json()['request']['resultDigest'], 'a' * 64)
        self.assertEqual(response.json()['request']['metricsBinding'], {
            'pmtb_share': {'inputDigest': 'c' * 64, 'resultDigest': 'a' * 64}})

    def test_worker_is_disabled_by_default_and_does_not_claim_or_send(self):
        with override_settings(DEKSI_PUBLIC_ENGINE_AI_ENABLED=False):
            from indicators.public_engine_ai import run_once
            with patch('indicators.public_engine_ai.call_provider') as provider:
                self.assertIsNone(run_once())
            provider.assert_not_called()

    def test_daily_hard_cap_is_enforced(self):
        from indicators.public_engine_ai import create_request
        from indicators.models import PublicEngineAIRequest
        snapshots = [{'availableMetrics': {'pmtb_share': {'value': '20.00', 'resultDigest': str(i) * 64}},
                      'inputDigest': str(i + 1) * 64, 'period': 'Q1 2025', 'resultDigest': str(i) * 64}
                     for i in range(1, 5)]
        with patch('indicators.public_engine_ai.calculate_snapshot', side_effect=snapshots):
            for _ in range(3):
                create_request(uuid.uuid4(), '2025-03-31')
            with self.assertRaises(Exception):
                create_request(uuid.uuid4(), '2025-03-31')
        self.assertEqual(PublicEngineAIRequest.objects.count(), 3)

    def test_admin_review_requires_staff_and_csrf(self):
        response = self.client.post('/api/admin/public-engine-ai/1/review/', '{}', content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.post('/api/admin/public-engine-ai/1/review/',
            json.dumps({'contentDigest': 'a' * 64, 'decision': 'approved', 'notes': ''}),
            content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 404)

    def test_worker_marks_abandoned_claim_unknown_without_retry(self):
        from datetime import timedelta
        from django.utils import timezone
        from indicators.public_engine_ai import create_request, run_once
        from indicators.models import PublicEngineAIRequest
        with patch('indicators.public_engine_ai.calculate_snapshot', return_value={
                'availableMetrics': {'pmtb_share': {'value': '20.00', 'resultDigest': 'a' * 64}},
                'inputDigest': 'b' * 64, 'period': 'Q1 2025', 'resultDigest': 'a' * 64}):
            row, _ = create_request(uuid.uuid4(), '2025-03-31')
        row.status = PublicEngineAIRequest.Status.RUNNING
        row.claimed_at = timezone.now() - timedelta(minutes=4)
        row.save(update_fields=['status', 'claimed_at'])
        with patch('indicators.public_engine_ai.call_provider') as provider:
            result = run_once()
        row.refresh_from_db()
        self.assertIsNone(result)
        self.assertEqual(row.status, PublicEngineAIRequest.Status.UNKNOWN)
        provider.assert_not_called()

    def test_staff_without_review_permission_cannot_read_admin_queue(self):
        staff = get_user_model().objects.create_user(username='staff-no-review', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get('/api/admin/public-engine-ai/').status_code, 403)

    @override_settings(DEKSI_PUBLIC_ENGINE_AI_MODEL='gemini-synthetic-test')
    def test_partial_metric_queue_worker_review_and_public_read(self):
        from pathlib import Path
        import httpx
        from indicators.public_engine_ai import run_once
        packet = json.loads((Path(__file__).parent / 'fixtures/engine_gdp_preview.json').read_text())
        metrics = {'pmtb_share': packet['metrics']['pmtb_share']}
        output = {'summary': 'Porsi komponen dalam PDB.', 'meaning': 'PMTB dibandingkan total PDB.',
                  'comparison': None, 'limitations': 'Status revisi dan tanggal rilis belum diketahui.',
                  'factRefs': ['metrics.pmtb_share']}
        calls = []
        def handle(request):
            calls.append(json.loads(request.content))
            return httpx.Response(200, json={'model': 'gemini-synthetic-test', 'choices': [
                {'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': json.dumps(output)}}]})
        with patch('indicators.public_engine_ai.calculate_gdp_shares', return_value=metrics), \
             patch.dict('os.environ', {'GEMINI_API_KEY': 'synthetic-test-key'}):
            response = self.post({'requestKey': str(uuid.uuid4()), 'quarter': '2025-03-31'})
            self.assertEqual(response.status_code, 202)
            key = response.json()['request']['requestKey']
            worker = run_once(transport=httpx.MockTransport(handle))
            self.assertIsNotNone(worker)
            self.assertEqual(worker.status, 'ready')
            public = self.client.get(f'/api/public-engine-ai/requests/{key}/').json()['request']
            self.assertEqual(public['status'], 'ready')
            self.assertNotIn('narrative', public)
            self.client.force_login(self.admin)
            queue = self.client.get('/api/admin/public-engine-ai/').json()['items']
            self.assertEqual(len(queue), 1)
            review = self.client.post(f'/api/admin/public-engine-ai/{worker.pk}/review/',
                json.dumps({'contentDigest': queue[0]['contentDigest'], 'decision': 'approved', 'notes': ''}),
                content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf)
            self.assertEqual(review.status_code, 200)
            public = self.client.get(f'/api/public-engine-ai/requests/{key}/').json()['request']
            self.assertEqual(public['narrative'], output)
            self.assertEqual(set(public['metricsBinding']), {'pmtb_share'})
            self.assertEqual(len(calls), 1)
