"""Synthetic narrative persistence; no real provider or user database."""
import importlib
import importlib.util
import json
import os
import threading
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import Client, override_settings
from django.utils import timezone

from indicators.models import AINarrativeDraft, AINarrativeReview, DataUpdateLog, Observation, Source
from indicators.storage import save_raw
from indicators.tests.support import IndicatorCase


class NarrativeTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        root = self.enterContext(TemporaryDirectory(dir=os.environ['HERMES_TEST_SCRATCH']))
        self.enterContext(override_settings(
            DEKSI_RAW_DIR=Path(root), DEKSI_AI_NARRATIVES_ENABLED=True,
            LLM_BASE_URL='http://127.0.0.1:11434/v1', LLM_MODEL='synthetic:1', LLM_API_KEY='',
        ))
        self.indicator.code = 'pdb'
        self.indicator.save()
        self.source = Source.objects.get(source_id='BPS')
        self.raw, _ = save_raw(self.source, b'SYNTHETIC NARRATIVE EVIDENCE', 'synthetic.json')
        self.current = self.observation(source=self.source, raw_file=self.raw,
            observation_date=date(2025, 6, 30), period_label='Q2 2025', frequency='quarterly',
            data_type='yoy', value=Decimal('5.123456'))
        self.reviewer.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='indicators', codename__in=(
                'view_ainarrativedraft', 'generate_ainarrativedraft', 'review_ainarrativedraft')))

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('indicators.ai_narrative'),
                             'Narrative persistence service is not implemented')
        return importlib.import_module('indicators.ai_narrative')

    def request(self, key=None, **changes):
        return self.api().request_draft(self.reviewer, request_key=key or uuid.uuid4(),
            observation_id=self.current.pk, comparison_id=None, parent_id=None, **changes)

    def test_persists_fact_snapshot_without_generation_and_replays_exact_request(self):
        api = self.api()
        key = uuid.uuid4()
        first = self.request(key)
        self.assertEqual(first.generation_status, 'queued')
        self.assertEqual(first.fact_package['facts']['current']['value'], '5.123456')
        self.assertEqual(self.request(key).pk, first.pk)
        self.current.value = Decimal('8')
        self.current.save(update_fields=['value'])
        first.refresh_from_db()
        self.assertEqual(first.fact_package['facts']['current']['value'], '5.123456')
        dto = api.serialize_draft(first)
        self.assertEqual(dto['generationStatus'], 'queued')
        self.assertIsNone(dto['narrative'])
        self.assertEqual(dto['reviewStatus'], 'pending')

    def output(self):
        return {'summary': 'Kegiatan ekonomi berubah dibanding periode pembanding tahunan.',
                'meaning': 'PDB menggambarkan ukuran kegiatan ekonomi, bukan pendapatan setiap keluarga.',
                'comparison': None, 'limitations': 'Penyebab perubahan belum dapat disimpulkan dari angka ini.',
                'factRefs': ['facts.current']}

    def transport(self, content=None):
        payload = self.output() if content is None else content
        def handle(request):
            self.assertEqual(str(request.url), 'http://127.0.0.1:11434/v1/chat/completions')
            body = json.loads(request.content)
            self.assertEqual(body['model'], 'synthetic:1')
            self.assertFalse(body['stream'])
            self.assertNotIn(self.reviewer.username, request.content.decode())
            return httpx.Response(200, json={'model': 'synthetic:1', 'choices': [
                {'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': json.dumps(payload)}}]})
        return httpx.MockTransport(handle)

    def test_worker_generates_exact_bound_draft_and_review_does_not_publish_numbers(self):
        api = self.api()
        self.assertTrue(callable(getattr(api, 'run_once', None)), 'Single-request generation is not implemented')
        draft = self.request()
        expected = self.current.value
        atomic_depth = len(connection.atomic_blocks)
        with patch('indicators.ai_narrative_provider.assert_outside_transaction',
                   side_effect=lambda: self.assertEqual(len(connection.atomic_blocks), atomic_depth)):
            api.run_once(transport=self.transport())
        draft.refresh_from_db()
        self.assertEqual(draft.generation_status, 'ready')
        self.assertEqual(draft.narrative, self.output())
        api.review_draft(self.reviewer, draft.pk, content_digest=draft.content_digest, decision='approved', notes='')
        dto = api.serialize_draft(draft)
        self.assertEqual(dto['reviewStatus'], 'approved')
        self.current.refresh_from_db()
        self.assertEqual(self.current.value, expected)
        self.assertEqual(self.current.validation_status, 'published')

    def test_private_api_capabilities_request_and_lookup_do_not_generate(self):
        self.client.force_login(self.reviewer)
        root = '/api/admin/ai-narratives/'
        capabilities = self.client.get(root + 'capabilities/')
        self.assertEqual(capabilities.status_code, 200)
        self.assertEqual(capabilities.json(), {'canRead': True, 'canGenerate': True,
                                             'canReview': True, 'generationConfigured': True})
        key = str(uuid.uuid4())
        body = {'requestKey': key, 'observationId': self.current.pk, 'comparisonId': None, 'parentId': None}
        response = self.client.post(root, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 202)
        draft = response.json()['draft']
        self.assertEqual(draft['generationStatus'], 'queued')
        self.assertEqual(self.client.get(root + 'lookup/', {'requestKey': key}).json()['draft']['id'], draft['id'])
        self.assertEqual(self.client.get(root).json()['total'], 1)
        self.assertEqual(self.client.get(root + 'observations/').json()['items'][0]['id'], self.current.pk)

    def ready(self):
        draft = self.request()
        with patch('indicators.ai_narrative_provider.assert_outside_transaction'):
            self.api().run_once(transport=self.transport())
        draft.refresh_from_db()
        self.assertEqual(draft.generation_status, 'ready')
        return draft

    def rejected(self, code, callback, *args, **kwargs):
        with self.assertRaises(self.api().NarrativeError) as error:
            callback(*args, **kwargs)
        self.assertEqual(error.exception.code, code)

    def test_permission_revocation_is_read_again_and_candidate_permission_is_not_narrative_permission(self):
        api = self.api()
        self.assertTrue(api.capabilities(self.reviewer)['canGenerate'])
        self.reviewer.user_permissions.clear()
        self.reviewer.user_permissions.add(Permission.objects.get(
            content_type__app_label='indicators', codename='change_observationcandidate'))
        self.assertFalse(api.capabilities(self.reviewer)['canGenerate'])
        with self.assertRaises(PermissionDenied):
            self.request()

    def test_invalid_literal_ids_keys_and_parent_are_not_normalized_or_guessed(self):
        api = self.api()
        for key in (None, True, str(uuid.uuid4()).upper(), 'not-a-uuid'):
            self.rejected('invalid_request', api.request_draft, self.reviewer,
                request_key=key, observation_id=self.current.pk)
        for value in (True, 0, -1, str(self.current.pk), 1.0):
            self.rejected('invalid_request', api.request_draft, self.reviewer,
                request_key=uuid.uuid4(), observation_id=value)
        self.rejected('conflict', api.request_draft, self.reviewer,
            request_key=uuid.uuid4(), observation_id=self.current.pk, parent_id=999999)

    def test_disabled_or_unsafe_configuration_does_not_queue_or_contact_model(self):
        for values in ({'DEKSI_AI_NARRATIVES_ENABLED': False}, {'DEKSI_AI_NARRATIVES_ENABLED': 'False'},
                       {'LLM_BASE_URL': 'https://@example.test/v1'},
                       {'LLM_BASE_URL': 'http://example.test/v1?key=PRIVATE'},
                       {'LLM_BASE_URL': ' http://127.0.0.1/v1'}, {'LLM_MODEL': 'bad model'},
                       {'DEKSI_AI_TIMEOUT_SECONDS': True}, {'DEKSI_AI_TIMEOUT_SECONDS': 1}):
            with override_settings(**values):
                self.rejected('unconfigured', self.request)
        self.assertEqual(AINarrativeDraft.objects.count(), 0)

    def test_missing_raw_or_unreviewed_primary_cannot_be_used_for_generation(self):
        self.current.raw_file = None
        self.current.save(update_fields=['raw_file'])
        self.rejected('unavailable_input', self.request)
        self.current.raw_file = self.raw
        self.current.reviewed_at = None
        self.current.save(update_fields=['raw_file', 'reviewed_at'])
        self.rejected('unavailable_input', self.request)
        self.assertEqual(AINarrativeDraft.objects.count(), 0)

    def test_idempotency_binds_actor_and_payload_and_single_slot_blocks_another_request(self):
        first = self.request()
        self.rejected('busy', self.request)
        previous = self.observation(source=self.source, raw_file=self.raw,
            observation_date=date(2025, 3, 31), period_label='Q1 2025', frequency='quarterly', data_type='yoy')
        self.rejected('conflict', self.api().request_draft, self.reviewer,
            request_key=first.request_key, observation_id=previous.pk)
        other = get_user_model().objects.create_user(username='other-narrative-test', is_staff=True)
        other.user_permissions.set(self.reviewer.user_permissions.all())
        self.rejected('conflict', self.api().request_draft, other,
            request_key=first.request_key, observation_id=self.current.pk)
        self.assertEqual(AINarrativeDraft.objects.count(), 1)

    def test_generation_timeout_is_unknown_until_explicit_acknowledgement_not_a_retry(self):
        draft = self.request()
        def timeout(_request):
            raise httpx.ReadTimeout('PRIVATE_TRANSPORT_ERROR')
        with patch('indicators.ai_narrative_provider.assert_outside_transaction'):
            self.api().run_once(transport=httpx.MockTransport(timeout))
        draft.refresh_from_db()
        self.assertEqual(draft.generation_status, 'unknown')
        self.assertEqual(draft.active_slot, 1)
        self.assertNotIn('PRIVATE_', json.dumps(self.api().serialize_draft(draft)))
        self.rejected('busy', self.request)
        self.rejected('invalid_request', self.api().reconcile_draft, self.reviewer, draft.pk,
                      acknowledged=False, notes='Checked synthetic provider')
        self.api().reconcile_draft(self.reviewer, draft.pk, acknowledged=True, notes='Checked synthetic provider')
        draft.refresh_from_db()
        self.assertEqual(draft.generation_status, 'unknown')
        self.assertIsNone(draft.narrative)
        self.assertEqual(self.request(draft.request_key).pk, draft.pk)
        new = self.request()
        self.assertNotEqual(new.pk, draft.pk)

    def test_late_provider_result_cannot_finish_a_reconciled_claim(self):
        draft = self.request()
        def delayed_result(*_args, **_kwargs):
            AINarrativeDraft.objects.filter(pk=draft.pk).update(deadline_at=timezone.now() - timedelta(seconds=1))
            self.api().reconcile_draft(self.reviewer, draft.pk, acknowledged=True, notes='Operator inspected outcome')
            return self.output(), 'synthetic:1'
        with patch('indicators.ai_narrative.generate', side_effect=delayed_result):
            self.api().run_once()
        draft.refresh_from_db()
        self.assertEqual(draft.generation_status, 'unknown')
        self.assertIsNone(draft.narrative)
        self.assertIsNone(draft.content_digest)

    def test_expired_running_read_is_nonmutating_and_requires_operator_reconciliation(self):
        draft = self.request()
        AINarrativeDraft.objects.filter(pk=draft.pk).update(generation_status='running', claim=uuid.uuid4(),
            deadline_at=timezone.now() - timedelta(seconds=1))
        draft.refresh_from_db()
        self.assertEqual(self.api().serialize_draft(draft)['generationStatus'], 'unknown')
        draft.refresh_from_db()
        self.assertEqual(draft.generation_status, 'running')
        self.api().reconcile_draft(self.reviewer, draft.pk, acknowledged=True, notes='Explicit release')

    def test_change_after_request_is_rejected_before_transport(self):
        draft = self.request()
        self.current.value = Decimal('8')
        self.current.save(update_fields=['value'])
        with patch('indicators.ai_narrative.generate',
                   side_effect=AssertionError('Must not contact provider')) as generate:
            self.api().run_once()
        generate.assert_not_called()
        draft.refresh_from_db()
        self.assertEqual(draft.error_code, 'stale_input')
        self.assertEqual(draft.generation_status, 'failed')

    def test_model_change_after_queue_does_not_switch_provider_or_model(self):
        draft = self.request()
        with override_settings(LLM_MODEL='other:1'), patch('indicators.ai_narrative.generate') as generate:
            self.api().run_once()
        generate.assert_not_called()
        draft.refresh_from_db()
        self.assertEqual(draft.error_code, 'config_changed')

    def test_stale_approval_is_blocked_but_rejection_can_record_historical_version(self):
        draft = self.ready()
        self.current.value = Decimal('8')
        self.current.save(update_fields=['value'])
        self.rejected('stale_input', self.api().review_draft, self.reviewer, draft.pk,
                      content_digest=draft.content_digest, decision='approved', notes='')
        self.api().review_draft(self.reviewer, draft.pk, content_digest=draft.content_digest,
                               decision='rejected', notes='Source changed')
        self.assertEqual(self.api().serialize_draft(draft)['factPackage']['facts']['current']['value'], '5.123456')
        self.assertEqual(AINarrativeReview.objects.get(draft=draft).decision, 'rejected')

    def test_exact_digest_required_and_decisions_cannot_be_overwritten(self):
        draft = self.ready()
        self.rejected('conflict', self.api().review_draft, self.reviewer, draft.pk,
                      content_digest='a' * 64, decision='approved', notes='')
        self.api().review_draft(self.reviewer, draft.pk, content_digest=draft.content_digest,
                               decision='needs_revision', notes='Please simplify the language')
        self.rejected('not_ready', self.api().review_draft, self.reviewer, draft.pk,
                      content_digest=draft.content_digest, decision='approved', notes='')
        self.assertEqual(AINarrativeReview.objects.filter(draft=draft).count(), 1)
        with self.assertRaises(ValidationError):
            draft.save()
        decision = AINarrativeReview.objects.get(draft=draft)
        with self.assertRaises(ValidationError):
            decision.save()

    def test_review_rejects_nonascii_digest_as_bad_request_instead_of_server_error(self):
        draft = self.ready()
        self.rejected('invalid_request', self.api().review_draft, self.reviewer, draft.pk,
                      content_digest='é' * 64, decision='approved', notes='')

    def test_existing_figures_raw_and_publication_logs_are_unchanged_by_generation_and_review(self):
        rows = list(Observation.objects.values())
        logs = list(DataUpdateLog.objects.values())
        raw = Path(self.raw.stored_path).read_bytes()
        draft = self.ready()
        self.api().review_draft(self.reviewer, draft.pk, content_digest=draft.content_digest,
                               decision='approved', notes='')
        self.assertEqual(rows, list(Observation.objects.values()))
        self.assertEqual(logs, list(DataUpdateLog.objects.values()))
        self.assertEqual(raw, Path(self.raw.stored_path).read_bytes())

    def test_malformed_outputs_cannot_become_ready_or_expose_raw_errors(self):
        for value in ({'summary': 'incomplete'}, {**self.output(), 'summary': 'Angka baru 999 persen'},
                      {**self.output(), 'meaning': '<script>bad</script>'},
                      {**self.output(), 'factRefs': ['facts.missing']},
                      {**self.output(), 'comparison': 'Pembanding palsu'}):
            draft = self.request()
            with patch('indicators.ai_narrative_provider.assert_outside_transaction'):
                self.api().run_once(transport=self.transport(value))
            draft.refresh_from_db()
            self.assertEqual(draft.generation_status, 'failed')
            self.assertEqual(draft.error_code, 'invalid_output')
            self.assertIsNone(draft.narrative)

    def test_anonymous_and_nonstaff_and_old_candidate_permission_cannot_access_drafts(self):
        root = '/api/admin/ai-narratives/'
        self.assertEqual(self.client.get(root).status_code, 401)
        self.reviewer.is_staff = False
        self.reviewer.save(update_fields=['is_staff'])
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(root).status_code, 403)

    def test_csrf_is_required_and_duplicate_or_unknown_json_fields_are_rejected(self):
        root = '/api/admin/ai-narratives/'
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.reviewer)
        key = str(uuid.uuid4())
        body = {'requestKey': key, 'observationId': self.current.pk, 'comparisonId': None, 'parentId': None}
        self.assertEqual(client.post(root, json.dumps(body), content_type='application/json').status_code, 403)
        token = client.get('/api/auth/csrf/').json()['csrfToken']
        for raw in (json.dumps({**body, 'arbitrary': 'bad'}), json.dumps(body)[:-1] + ',"parentId":null}',
                    '{"requestKey":NaN}', '[]'):
            response = client.post(root, raw, content_type='application/json', HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(client.post(root, json.dumps(body), content_type='application/json',
                                     HTTP_X_CSRFTOKEN=token).status_code, 202)

    def test_json_parser_rejects_duplicate_keys_and_total_deadline_returns_without_waiting_for_transport(self):
        from indicators.ai_narrative_provider import strict_json, within_deadline
        with self.assertRaises(ValueError):
            strict_json('{"x":1,"x":2}')
        release = threading.Event()
        try:
            self.rejected('outcome_unknown', within_deadline, lambda: release.wait(2), 0.01)
        finally:
            release.set()

    def test_comparison_requires_the_existing_comparison_and_all_declared_references(self):
        previous = self.observation(source=self.source, raw_file=self.raw,
            observation_date=date(2025, 3, 31), period_label='Q1 2025', frequency='quarterly', data_type='yoy')
        draft = self.api().request_draft(self.reviewer, request_key=uuid.uuid4(),
            observation_id=self.current.pk, comparison_id=previous.pk)
        value = {**self.output(), 'comparison': (
                    'Selisih ini membandingkan dua laju tahunan, bukan pertumbuhan antartriwulan.'),
                 'factRefs': ['facts.current', 'facts.comparison', 'comparisons.yoy_rate_difference']}
        with patch('indicators.ai_narrative_provider.assert_outside_transaction'):
            self.api().run_once(transport=self.transport(value))
        draft.refresh_from_db()
        self.assertEqual(draft.generation_status, 'ready')
        self.assertEqual(draft.fact_package['comparisons'][0]['value'], '5.12')

    def test_malformed_chat_envelopes_are_failed_not_unknown(self):
        for body in ({'choices': [{'finish_reason': 'stop', 'message': None}]},
                     {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]},
                     {'choices': []},
                     {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"x":1,"x":2}'}}]}):
            draft = self.request()
            transport = httpx.MockTransport(lambda _request, body=body: httpx.Response(200, json=body))
            with patch('indicators.ai_narrative_provider.assert_outside_transaction'):
                self.api().run_once(transport=transport)
            draft.refresh_from_db()
            self.assertEqual(draft.generation_status, 'failed')
            self.assertEqual(draft.error_code, 'invalid_output')

    def test_tampered_stored_content_is_not_approved_or_projected(self):
        draft = self.ready()
        AINarrativeDraft.objects.filter(pk=draft.pk).update(
            narrative={**self.output(), 'summary': 'Changed after generation'})
        draft.refresh_from_db()
        self.rejected('invalid_snapshot', self.api().serialize_draft, draft)
        self.rejected('invalid_snapshot', self.api().review_draft, self.reviewer, draft.pk,
                      content_digest=draft.content_digest, decision='approved', notes='')

    def test_raw_corruption_after_generation_blocks_approval_and_keeps_ready_history(self):
        draft = self.ready()
        Path(self.raw.stored_path).write_bytes(b'CORRUPT SYNTHETIC EVIDENCE')
        self.rejected('stale_input', self.api().review_draft, self.reviewer, draft.pk,
                      content_digest=draft.content_digest, decision='approved', notes='')
        self.assertEqual(self.api().serialize_draft(draft)['generationStatus'], 'ready')
        self.assertEqual(AINarrativeReview.objects.count(), 0)

    def test_previous_prompt_history_remains_readable_and_new_revision_needs_its_own_review(self):
        api = self.api()
        draft = self.ready()
        draft.prompt_version = 'pdb-plain-id.v1'
        original_digest = api.content_digest(draft, draft.narrative, draft.reported_model)
        AINarrativeDraft.objects.filter(pk=draft.pk).update(
            prompt_version=draft.prompt_version, content_digest=original_digest)
        draft.refresh_from_db()
        self.assertEqual(api.serialize_draft(draft)['promptVersion'], 'pdb-plain-id.v1')
        api.review_draft(self.reviewer, draft.pk, content_digest=original_digest, decision='approved', notes='')
        child = api.request_draft(self.reviewer, request_key=uuid.uuid4(),
            observation_id=self.current.pk, parent_id=draft.pk)
        self.assertEqual(child.prompt_version, 'pdb-plain-id.v2')
        self.assertEqual(api.serialize_draft(child)['reviewStatus'], 'pending')
        self.assertIsNone(api.serialize_draft(child)['review'])
        draft.refresh_from_db()
        self.assertEqual(draft.content_digest, original_digest)
        self.assertEqual(api.serialize_draft(draft)['reviewStatus'], 'approved')

    def test_old_queued_prompt_is_not_silently_run_with_new_request_contract(self):
        api = self.api()
        draft = self.request()
        AINarrativeDraft.objects.filter(pk=draft.pk).update(prompt_version='pdb-plain-id.v1')
        with patch('indicators.ai_narrative.generate', side_effect=AssertionError('No implicit upgrade')) as generate:
            api.run_once()
        generate.assert_not_called()
        draft.refresh_from_db()
        self.assertEqual(draft.generation_status, 'failed')
        self.assertEqual(draft.error_code, 'config_changed')
        self.assertEqual(draft.prompt_version, 'pdb-plain-id.v1')
        self.assertIsNone(draft.narrative)

    def test_unrecognized_prompt_identity_stays_unreadable_even_with_a_resealed_content_digest(self):
        api = self.api()
        draft = self.ready()
        draft.prompt_version = 'unrecognized-prompt'
        AINarrativeDraft.objects.filter(pk=draft.pk).update(prompt_version=draft.prompt_version,
            content_digest=api.content_digest(draft, draft.narrative, draft.reported_model))
        draft.refresh_from_db()
        self.rejected('invalid_snapshot', api.serialize_draft, draft)
