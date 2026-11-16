import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.contrib.sessions.models import Session
from django.test import Client
from django.utils import timezone

from indicators.lifecycle import stage_observation
from indicators.models import Observation, ObservationCandidate, RawFile
from indicators.tests.support import IndicatorCase


class CandidateReviewApiTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        self.reviewer.is_superuser = True
        self.reviewer.save(update_fields=['is_superuser'])
        candidate = stage_observation(indicator_id=self.indicator.pk, source_id=self.source.pk,
            observation_date=date(2024, 1, 31), period_label='UJI 2024', frequency='monthly',
            data_type='yoy', value=Decimal('3.250000'), unit='%')
        assert candidate is not None
        self.candidate = candidate
        self.url = '/api/admin/sources/TEST_ONLY/candidates/'
        self.review_url = f'{self.url}{self.candidate.pk}/review/'

    def test_authorized_list_exposes_exact_candidate_and_anonymous_is_denied(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.client.force_login(self.reviewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        item = response.json()['items'][0]
        self.assertEqual(item['id'], self.candidate.pk)
        self.assertEqual(item['value'], '3.250000')
        self.assertEqual(item['fingerprint'], self.candidate.fingerprint)
        self.assertEqual(Observation.objects.count(), 0)
        detail = self.client.get(f'{self.url}{self.candidate.pk}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['candidate']['id'], self.candidate.pk)
        self.assertEqual(self.client.get(f'/api/admin/sources/OTHER/candidates/{self.candidate.pk}/').status_code, 404)

    def test_evidence_uses_candidate_snapshot_and_does_not_expose_source_url(self):
        raw = RawFile.objects.create(source=self.source, document_name='Bukti sintetis',
            source_url='https://example.test/key/SYNTHETIC-PRIVATE', period_label='UJI',
            checksum_sha256='a' * 64, file_size_bytes=12)
        candidate = stage_observation(indicator_id=self.indicator.pk, source_id=self.source.pk,
            observation_date=date(2024, 3, 31), period_label='UJI RAW', frequency='monthly',
            data_type='yoy', value=Decimal('1.25'), unit='%', raw_file_id=raw.pk)
        assert candidate is not None
        raw.document_name = 'Diubah kemudian'
        raw.save(update_fields=['document_name'])
        self.client.force_login(self.reviewer)
        response = self.client.get(f'{self.url}{candidate.pk}/')
        self.assertEqual(response.status_code, 200)
        evidence = response.json()['candidate']['rawEvidence']
        self.assertEqual(evidence['documentName'], 'Bukti sintetis')
        self.assertEqual(evidence['checksumSha256'], 'a' * 64)
        self.assertNotIn('SYNTHETIC-PRIVATE', response.content.decode())
        self.assertIsNone(self.client.get(f'{self.url}{self.candidate.pk}/').json()['candidate']['rawEvidence'])

    def test_source_identity_comes_from_staging_snapshot_after_source_edit(self):
        original_name = self.source.source_name
        original_url = self.source.primary_url
        self.source.source_name = 'Nama sumber berubah'
        self.source.primary_url = 'https://changed.example.test/'
        self.source.save(update_fields=['source_name', 'primary_url'])
        self.client.force_login(self.reviewer)
        for url in (self.url, f'{self.url}{self.candidate.pk}/'):
            data = self.client.get(url).json()
            item = data['items'][0] if 'items' in data else data['candidate']
            self.assertEqual(item['sourceName'], original_name)
            self.assertEqual(item['sourceUrl'], original_url)
        body = {'decision': 'publish', 'fingerprint': self.candidate.fingerprint, 'notes': ''}
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Observation.objects.count(), 0)
        body.update(decision='reject', notes='Bukti tidak sesuai')
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        detail = self.client.get(f'{self.url}{self.candidate.pk}/').json()['candidate']
        self.assertEqual(detail['sourceName'], original_name)
        ObservationCandidate.objects.filter(pk=self.candidate.pk).update(
            base_snapshot={**self.candidate.base_snapshot, 'source': None})
        missing = self.client.get(f'{self.url}{self.candidate.pk}/').json()['candidate']
        self.assertIsNone(missing['sourceName'])
        self.assertIsNone(missing['sourceUrl'])

    def test_indicator_identity_comes_from_staging_snapshot_after_indicator_edit(self):
        original_name = self.indicator.name
        original_code = self.indicator.code
        self.indicator.name = 'Indikator berubah'
        self.indicator.code = 'indicator_changed'
        self.indicator.save(update_fields=['name', 'code'])
        self.client.force_login(self.reviewer)
        for url in (self.url, f'{self.url}{self.candidate.pk}/'):
            data = self.client.get(url).json()
            item = data['items'][0] if 'items' in data else data['candidate']
            self.assertEqual(item['indicatorName'], original_name)
            self.assertEqual(item['indicator'], original_code)
        body = {'decision': 'publish', 'fingerprint': self.candidate.fingerprint, 'notes': ''}
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Observation.objects.count(), 0)
        body.update(decision='reject', notes='Bukti tidak sesuai')
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        ObservationCandidate.objects.filter(pk=self.candidate.pk).update(
            base_snapshot={**self.candidate.base_snapshot, 'indicator': None})
        missing = self.client.get(f'{self.url}{self.candidate.pk}/').json()['candidate']
        self.assertIsNone(missing['indicatorName'])
        self.assertIsNone(missing['indicator'])

    def test_publish_requires_permission_csrf_and_matching_fingerprint(self):
        self.client.force_login(self.reviewer)
        body = {'decision': 'publish', 'fingerprint': self.candidate.fingerprint, 'notes': ''}
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.reviewer)
        response = csrf_client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        wrong = {**body, 'fingerprint': '0' * 64}
        response = self.client.post(self.review_url, json.dumps(wrong), content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Observation.objects.count(), 0)
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.status, ObservationCandidate.Status.PUBLISHED)
        self.assertEqual(self.candidate.reviewed_by_id, self.reviewer.pk)
        self.assertEqual(Observation.objects.count(), 1)
        self.assertEqual(self.client.get(f'{self.url}{self.candidate.pk}/').json()['candidate']['status'], 'published')
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 409)

    def test_reject_requires_reason_and_no_publication(self):
        self.client.force_login(self.reviewer)
        body = {'decision': 'reject', 'fingerprint': self.candidate.fingerprint, 'notes': ''}
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        body['notes'] = 'Tidak cocok dengan sumber'
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.status, 'rejected')
        self.assertEqual(Observation.objects.count(), 0)

    def test_staff_without_review_permission_is_denied(self):
        self.reviewer.is_superuser = False
        self.reviewer.save(update_fields=['is_superuser'])
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        body = {'decision': 'publish', 'fingerprint': self.candidate.fingerprint, 'notes': ''}
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Observation.objects.count(), 0)

    def test_session_reports_review_capability_without_granting_access(self):
        self.assertFalse(self.client.get('/api/admin/session/').json()['canReviewCandidates'])
        self.reviewer.is_superuser = False
        self.reviewer.save(update_fields=['is_superuser'])
        self.client.force_login(self.reviewer)
        self.assertFalse(self.client.get('/api/admin/session/').json()['canReviewCandidates'])
        self.assertEqual(self.client.get(self.url).status_code, 403)
        permission = Permission.objects.get(
            content_type__app_label='indicators', codename='change_observationcandidate')
        self.reviewer.user_permissions.add(permission)
        self.assertTrue(self.client.get('/api/admin/session/').json()['canReviewCandidates'])
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_expired_session_cannot_read_or_review(self):
        self.client.force_login(self.reviewer)
        session_key = self.client.session.session_key
        Session.objects.filter(session_key=session_key).update(expire_date=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get(self.url).status_code, 401)
        body = {'decision': 'publish', 'fingerprint': self.candidate.fingerprint, 'notes': ''}
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Observation.objects.count(), 0)

    def test_list_paginates_and_rejects_invalid_parameters(self):
        for day in range(1, 26):
            stage_observation(indicator_id=self.indicator.pk, source_id=self.source.pk,
                observation_date=date(2024, 2, day), period_label=f'UJI {day}', frequency='monthly',
                data_type='yoy', value=Decimal('1.25'), unit='%')
        self.client.force_login(self.reviewer)
        first = self.client.get(self.url).json()
        second = self.client.get(self.url, {'page': 2}).json()
        self.assertEqual(first['total'], 26)
        self.assertEqual(len(first['items']), 20)
        self.assertTrue(first['hasNext'])
        self.assertEqual(len(second['items']), 6)
        self.assertFalse(second['hasNext'])
        self.assertEqual(self.client.get(self.url, {'page': 0}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {'status': 'bogus'}).status_code, 400)

    def test_tampered_candidate_does_not_publish(self):
        self.client.force_login(self.reviewer)
        body = {'decision': 'publish', 'fingerprint': self.candidate.fingerprint, 'notes': ''}
        ObservationCandidate.objects.filter(pk=self.candidate.pk).update(
            payload={**self.candidate.payload, 'value': '99.000000'})
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Observation.objects.count(), 0)
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.status, 'pending')

    def test_changed_base_does_not_publish(self):
        self.client.force_login(self.reviewer)
        body = {'decision': 'publish', 'fingerprint': self.candidate.fingerprint, 'notes': ''}
        self.indicator.name = 'Indikator berubah'
        self.indicator.save(update_fields=['name'])
        response = self.client.post(self.review_url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Observation.objects.count(), 0)

    def test_candidate_is_not_reviewable_from_another_source(self):
        self.client.force_login(self.reviewer)
        body = {'decision': 'publish', 'fingerprint': self.candidate.fingerprint, 'notes': ''}
        url = f'/api/admin/sources/OTHER/candidates/{self.candidate.pk}/review/'
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Observation.objects.count(), 0)
