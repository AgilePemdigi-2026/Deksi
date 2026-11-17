import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import Client
from django.utils import timezone

from indicators.lifecycle import _digest, stage_observation
from indicators.models import BulkCandidateReview, Observation, ObservationCandidate, RawFile
from indicators.tests.support import IndicatorCase

_DEFAULT_PUBLICATION_DATE = object()


class BulkCandidateReviewApiTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        self.reviewer.is_superuser = True
        self.reviewer.save(update_fields=["is_superuser"])
        self.client.force_login(self.reviewer)
        self.base = "/api/admin/sources/TEST_ONLY/candidates/"

    def stage(self, *, day, raw=True, publication_date=_DEFAULT_PUBLICATION_DATE):
        if publication_date is _DEFAULT_PUBLICATION_DATE:
            publication_date = date(2024, 1, 1)
        raw_file = None
        if raw:
            raw_file = RawFile.objects.create(
                source=self.source, document_name=f"Evidence {day}",
                checksum_sha256=f"{day:064x}", file_size_bytes=1,
            )
        candidate = stage_observation(
            indicator_id=self.indicator.pk, source_id=self.source.pk,
            observation_date=date(2024, 1, day), period_label=f"UJI {day}",
            frequency="monthly", data_type="yoy", value=Decimal("2.5"), unit="%",
            publication_date=publication_date, raw_file_id=raw_file.pk if raw_file else None,
        )
        assert candidate is not None
        return candidate

    def preview(self):
        return self.client.post(self.base + "bulk-preview/", data="{}", content_type="application/json")

    def test_preview_freezes_eligible_and_excluded_candidate_metadata(self):
        eligible = self.stage(day=1)
        no_raw = self.stage(day=2, raw=False)
        missing_date = self.stage(day=3, publication_date=None)
        mismatched = self.stage(day=4)
        snapshot = dict(mismatched.base_snapshot)
        snapshot["candidate_raw"] = {**snapshot["candidate_raw"], "source_id": -1}
        ObservationCandidate.objects.filter(pk=mismatched.pk).update(base_snapshot=snapshot)
        response = self.preview()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["status"], body["total"], body["eligible"], body["excluded"]),
                         ("preview", 4, 1, 3))
        self.assertTrue(body["id"])
        self.assertTrue(body["expiresAt"])
        items = {item["id"]: item for item in body["items"]}
        self.assertTrue(items[eligible.pk]["eligible"])
        self.assertIsNone(items[eligible.pk]["exclusionReason"])
        self.assertFalse(items[no_raw.pk]["eligible"])
        self.assertTrue(items[no_raw.pk]["exclusionReason"])
        self.assertFalse(items[missing_date.pk]["eligible"])
        self.assertFalse(items[mismatched.pk]["eligible"])
        self.assertEqual(items[mismatched.pk]["exclusionReason"], "raw_snapshot_source_mismatch")
        self.assertEqual(Observation.objects.count(), 0)
        eligible.payload["value"] = "999.000000"
        eligible.save(update_fields=["payload"])
        refreshed = self.preview().json()
        self.assertNotEqual(refreshed["id"], body["id"])
        self.assertEqual(body["items"][0]["value"], "2.500000")

    def test_preview_covers_pending_candidates_beyond_first_page(self):
        for day in range(1, 23):
            self.stage(day=day)
        preview = self.preview().json()
        self.assertEqual(preview["total"], 22)
        self.assertEqual(preview["eligible"], 22)
        self.assertEqual(len({item["id"] for item in preview["items"]}), 22)

    def test_confirm_requires_csrf_and_preserves_pending_candidate(self):
        self.stage(day=12)
        preview = self.preview().json()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.reviewer)
        rejected = csrf_client.post(
            self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(Observation.objects.count(), 0)
        self.assertEqual(ObservationCandidate.objects.get().status, ObservationCandidate.Status.PENDING)

    def test_confirmation_persists_each_result_and_duplicate_confirm_never_replays(self):
        candidate = self.stage(day=4)
        preview = self.preview().json()
        url = self.base + f"bulk-review/{preview['id']}/confirm/"
        response = self.client.post(url, data=json.dumps({"confirmed": True}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["counts"]["published"], 1)
        self.assertEqual(Observation.objects.count(), 1)
        repeated = self.client.post(url, data=json.dumps({"confirmed": True}), content_type="application/json")
        self.assertEqual(repeated.json(), result)
        self.assertEqual(Observation.objects.count(), 1)
        status = self.client.get(self.base + f"bulk-review/{preview['id']}/").json()
        self.assertEqual(status, result)
        self.assertEqual(status["items"][0]["id"], candidate.pk)

    def test_excluded_items_stay_individually_reviewable_and_are_not_bulk_published(self):
        candidate = self.stage(day=5, raw=False)
        preview = self.preview().json()
        response = self.client.post(
            self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertEqual(item["status"], "excluded")
        self.assertEqual(Observation.objects.count(), 0)
        candidate.refresh_from_db()
        individual = self.client.post(
            self.base + f"{candidate.pk}/review/",
            data=json.dumps({"decision": "publish", "fingerprint": candidate.fingerprint, "notes": ""}),
            content_type="application/json",
        )
        self.assertEqual(individual.status_code, 200)
        self.assertEqual(Observation.objects.count(), 1)

    def test_preview_and_confirm_are_reviewer_bound_expiring_and_authorized(self):
        self.stage(day=6)
        preview = self.preview().json()
        malformed = self.client.post(
            self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": 1}), content_type="application/json",
        )
        self.assertEqual(malformed.status_code, 400)
        other = type(self.reviewer).objects.create_user(username="other-reviewer", is_staff=True, is_superuser=True)
        self.client.force_login(other)
        status_url = self.base + f"bulk-review/{preview['id']}/"
        self.assertEqual(self.client.get(status_url).status_code, 404)
        denied = self.client.post(
            self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json",
        )
        self.assertEqual(denied.status_code, 404)
        self.client.force_login(self.reviewer)
        from indicators.models import BulkCandidateReview
        BulkCandidateReview.objects.filter(pk=preview["id"]).update(expires_at=timezone.now())
        expired = self.client.post(
            self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json",
        )
        self.assertEqual(expired.status_code, 409)
        self.assertEqual(Observation.objects.count(), 0)

    def test_validation_conflict_is_skipped_without_failing_the_batch(self):
        self.stage(day=8)
        preview = self.preview().json()
        with patch("indicators.bulk_candidate_views.review_candidate", side_effect=ValidationError("stale")):
            response = self.client.post(
                self.base + f"bulk-review/{preview['id']}/confirm/",
                data=json.dumps({"confirmed": True}), content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["items"][0]["status"], "skipped")
        self.assertEqual(Observation.objects.count(), 0)

    def test_changed_candidate_after_preview_never_publishes_new_fingerprint(self):
        candidate = self.stage(day=10)
        preview = self.preview().json()
        candidate.payload["value"] = "999.000000"
        candidate.fingerprint = _digest(candidate.payload, candidate.base_snapshot)
        candidate.save(update_fields=["payload", "fingerprint"])
        response = self.client.post(
            self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["counts"]["published"], 0)
        self.assertEqual(response.json()["items"][0]["status"], "skipped")
        self.assertFalse(Observation.objects.exists())

    def test_metadata_removed_after_preview_is_not_bulk_published(self):
        candidate = self.stage(day=11)
        preview = self.preview().json()
        candidate.payload["publication_date"] = None
        candidate.fingerprint = _digest(candidate.payload, candidate.base_snapshot)
        candidate.save(update_fields=["payload", "fingerprint"])
        response = self.client.post(
            self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["counts"]["published"], 0)
        self.assertFalse(Observation.objects.exists())

    def test_systemic_failure_is_unknown_and_never_automatically_retried(self):
        self.stage(day=9)
        preview = self.preview().json()
        url = self.base + f"bulk-review/{preview['id']}/confirm/"
        with patch("indicators.bulk_candidate_views.review_candidate",
                   side_effect=RuntimeError("synthetic failure")) as review:
            first = self.client.post(url, data=json.dumps({"confirmed": True}), content_type="application/json")
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.json()["status"], "unknown")
            self.assertEqual(first.json()["items"][0]["status"], "unknown")
            second = self.client.post(url, data=json.dumps({"confirmed": True}), content_type="application/json")
            self.assertEqual(second.json(), first.json())
            self.assertEqual(review.call_count, 1)
        self.assertEqual(self.client.get(self.base + "bulk-review/active/").json()["batch"], first.json())
        self.assertEqual(Observation.objects.count(), 0)

    def test_unresolved_batch_blocks_confirmation_of_another_snapshot(self):
        self.stage(day=13)
        first = self.preview().json()
        BulkCandidateReview.objects.filter(pk=first["id"]).update(status=BulkCandidateReview.Status.UNKNOWN)
        second = self.preview().json()
        response = self.client.post(
            self.base + f"bulk-review/{second['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(Observation.objects.exists())

    def test_active_readback_is_read_only_and_scoped_to_reviewer(self):
        self.stage(day=7)
        preview = self.preview().json()
        confirmed = self.client.post(
            self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json",
        ).json()
        self.assertEqual(self.client.get(self.base + "bulk-review/active/").json(), {"batch": confirmed})
        self.assertEqual(confirmed["status"], "completed")
