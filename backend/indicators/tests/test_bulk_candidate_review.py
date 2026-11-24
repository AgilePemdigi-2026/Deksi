import json
import os
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client, override_settings
from django.utils import timezone

from indicators.lifecycle import _digest, stage_observation
from indicators.models import BulkCandidateReview, Observation, ObservationCandidate, RawFile, Source
from indicators.storage import save_raw
from indicators.tests.support import IndicatorCase

_DEFAULT_PUBLICATION_DATE = object()


class BulkCandidateReviewApiTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        self.reviewer.is_superuser = True
        self.reviewer.save(update_fields=["is_superuser"])
        self.client.force_login(self.reviewer)
        self.base = "/api/admin/sources/TEST_ONLY/candidates/"
        self.raw_dir = tempfile.TemporaryDirectory(dir=os.environ.get("HERMES_TEST_SCRATCH"))
        self.addCleanup(self.raw_dir.cleanup)
        settings_override = override_settings(DEKSI_RAW_DIR=self.raw_dir.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def stage(self, *, day, raw=True, publication_date=_DEFAULT_PUBLICATION_DATE):
        if publication_date is _DEFAULT_PUBLICATION_DATE:
            publication_date = date(2024, 1, 1)
        raw_file = None
        if raw:
            if self.source.source_id in ("BPS", "BKPM", "BI"):
                raw_file, _ = save_raw(self.source, f"BPS synthetic {day}".encode(), f"Evidence {day}")
            else:
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

    def test_bps_missing_release_is_eligible_with_explicit_warning_and_confirmed_review(self):
        self.source = Source.objects.get(source_id="BPS")
        self.base = "/api/admin/sources/BPS/candidates/"
        candidate = self.stage(day=1, publication_date=None)
        preview = self.preview().json()
        self.assertEqual((preview["eligible"], preview["excluded"]), (1, 0))
        self.assertIsNone(preview["items"][0]["publicationDate"])
        self.assertEqual(preview["items"][0]["observationDate"], "2024-01-01")
        self.assertFalse(Observation.objects.exists())
        response = self.client.post(self.base + f"bulk-review/{preview['id']}/confirm/",
                                    data=json.dumps({"confirmed": True}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["counts"]["published"], 1)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, "published")
        self.assertIsNone(Observation.objects.get().publication_date)

    def test_bps_missing_raw_or_invalid_observation_period_is_excluded(self):
        self.source = Source.objects.get(source_id="BPS")
        self.base = "/api/admin/sources/BPS/candidates/"
        no_raw = self.stage(day=1, raw=False, publication_date=None)
        invalid_date = self.stage(day=2, publication_date=None)
        invalid_date.payload["observation_date"] = "2024-99-99"
        invalid_date.save(update_fields=["payload"])
        missing_period = self.stage(day=3, publication_date=None)
        missing_period.payload["period_label"] = ""
        missing_period.save(update_fields=["payload"])
        items = {item["id"]: item for item in self.preview().json()["items"]}
        self.assertEqual(items[no_raw.pk]["exclusionReason"], "missing_raw_file")
        self.assertEqual(items[invalid_date.pk]["exclusionReason"], "invalid_observation_date")
        self.assertEqual(items[missing_period.pk]["exclusionReason"], "missing_period_label")

    def test_bps_missing_and_corrupt_raw_are_excluded_before_preview(self):
        self.source = Source.objects.get(source_id="BPS")
        self.base = "/api/admin/sources/BPS/candidates/"
        missing = self.stage(day=1, publication_date=None)
        corrupt = self.stage(day=2, publication_date=None)
        Path(RawFile.objects.get(pk=missing.payload["raw_file_id"]).stored_path).unlink()
        Path(RawFile.objects.get(pk=corrupt.payload["raw_file_id"]).stored_path).write_bytes(b"tampered")
        items = {item["id"]: item for item in self.preview().json()["items"]}
        self.assertEqual(items[missing.pk]["exclusionReason"], "raw_file_unavailable")
        self.assertEqual(items[corrupt.pk]["exclusionReason"], "raw_file_invalid")
        self.assertFalse(Observation.objects.exists())

    def test_bps_raw_corrupted_after_preview_is_not_published(self):
        self.source = Source.objects.get(source_id="BPS")
        self.base = "/api/admin/sources/BPS/candidates/"
        candidate = self.stage(day=1, publication_date=None)
        preview = self.preview().json()
        self.assertEqual(preview["eligible"], 1)
        Path(RawFile.objects.get(pk=candidate.payload["raw_file_id"]).stored_path).write_bytes(b"tampered")
        response = self.client.post(self.base + f"bulk-review/{preview['id']}/confirm/",
                                    data=json.dumps({"confirmed": True}), content_type="application/json")
        self.assertEqual(response.json()["counts"]["published"], 0)
        self.assertEqual(response.json()["items"][0]["status"], "skipped")
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, "pending")
        self.assertFalse(Observation.objects.exists())

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

    def test_bkpm_missing_raw_after_preview_is_not_published(self):
        self._assert_missing_raw_after_preview_is_not_published("BKPM")

    def test_bi_missing_raw_after_preview_is_not_published(self):
        self._assert_missing_raw_after_preview_is_not_published("BI")

    def _assert_missing_raw_after_preview_is_not_published(self, source_id):
        self.source = Source.objects.get(source_id=source_id)
        self.base = f"/api/admin/sources/{source_id}/candidates/"
        raw, _ = save_raw(self.source, b"BKPM SYNTHETIC", "synthetic.json")
        candidate = stage_observation(indicator_id=self.indicator.pk, source_id=self.source.pk,
            observation_date=date(2024, 1, 1), period_label="UJI", frequency="monthly",
            data_type="yoy", value=Decimal("2.5"), unit="%", publication_date=None, raw_file_id=raw.pk)
        assert candidate is not None
        preview = self.preview().json()
        self.assertEqual(preview["eligible"], 1)
        Path(raw.stored_path).unlink()
        response = self.client.post(self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, "pending")
        self.assertEqual(response.json()["counts"]["published"], 0)

    def test_excluded_first_batch_does_not_starve_later_candidates(self):
        self.stage(day=1, raw=False)
        self.stage(day=2, raw=False)
        later = self.stage(day=3)
        with patch("indicators.bulk_candidate_views.MAX_PREVIEW_ITEMS", 2):
            first = self.preview().json()
            self.assertTrue(first["hasMore"])
            response = self.client.post(self.base + f"bulk-review/{first['id']}/confirm/",
                data=json.dumps({"confirmed": True}), content_type="application/json")
            self.assertEqual(response.status_code, 200)
            second = self.preview().json()
        self.assertIn(later.pk, [item["id"] for item in second["items"]])

    def test_bkpm_corrupt_or_missing_raw_is_excluded_before_preview(self):
        self.source = Source.objects.get(source_id="BKPM")
        self.base = "/api/admin/sources/BKPM/candidates/"
        missing = self.stage(day=1, publication_date=None)
        corrupt = self.stage(day=2, publication_date=None)
        Path(RawFile.objects.get(pk=missing.payload["raw_file_id"]).stored_path).unlink()
        Path(RawFile.objects.get(pk=corrupt.payload["raw_file_id"]).stored_path).write_bytes(b"tampered")
        items = {item["id"]: item for item in self.preview().json()["items"]}
        self.assertEqual(items[missing.pk]["exclusionReason"], "raw_file_unavailable")
        self.assertEqual(items[corrupt.pk]["exclusionReason"], "raw_file_invalid")

    def test_bkpm_valid_raw_without_release_can_still_be_bulk_published(self):
        self._assert_valid_raw_without_release_can_be_published("BKPM")

    def test_bi_valid_raw_without_release_can_still_be_bulk_published(self):
        self._assert_valid_raw_without_release_can_be_published("BI")

    def _assert_valid_raw_without_release_can_be_published(self, source_id):
        self.source = Source.objects.get(source_id=source_id)
        self.base = f"/api/admin/sources/{source_id}/candidates/"
        candidate = self.stage(day=1, publication_date=None)
        preview = self.preview().json()
        self.assertEqual(preview["eligible"], 1)
        response = self.client.post(self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json")
        self.assertEqual(response.json()["counts"]["published"], 1)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, "published")
        self.assertIsNone(Observation.objects.get().publication_date)

    def test_bkpm_raw_corrupted_after_preview_is_not_published(self):
        self.source = Source.objects.get(source_id="BKPM")
        self.base = "/api/admin/sources/BKPM/candidates/"
        candidate = self.stage(day=1, publication_date=None)
        preview = self.preview().json()
        Path(RawFile.objects.get(pk=candidate.payload["raw_file_id"]).stored_path).write_bytes(b"tampered")
        response = self.client.post(self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json")
        self.assertEqual(response.json()["counts"]["published"], 0)
        self.assertEqual(response.json()["items"][0]["reason"], "raw_file_invalid")
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, "pending")

    def test_batch_progress_wraps_to_excluded_candidates_without_changing_status(self):
        early = [self.stage(day=day, raw=False) for day in (1, 2)]
        later = self.stage(day=3)
        with patch("indicators.bulk_candidate_views.MAX_PREVIEW_ITEMS", 2):
            first = self.preview().json()
            self.client.post(self.base + f"bulk-review/{first['id']}/confirm/",
                data=json.dumps({"confirmed": True}), content_type="application/json")
            second = self.preview().json()
            self.assertEqual([item["id"] for item in second["items"]], [later.pk])
            self.client.post(self.base + f"bulk-review/{second['id']}/confirm/",
                data=json.dumps({"confirmed": True}), content_type="application/json")
            third = self.preview().json()
        self.assertEqual([item["id"] for item in third["items"]], [item.pk for item in early])
        self.assertEqual(ObservationCandidate.objects.filter(pk__in=[item.pk for item in early],
            status="pending").count(), 2)

    def test_unconfirmed_preview_does_not_advance_or_share_progress_with_other_reviewers(self):
        first = self.stage(day=1, raw=False)
        self.stage(day=2)
        with patch("indicators.bulk_candidate_views.MAX_PREVIEW_ITEMS", 1):
            preview = self.preview().json()
            self.assertEqual(self.preview().json()["items"][0]["id"], first.pk)
            self.client.post(self.base + f"bulk-review/{preview['id']}/confirm/",
                data=json.dumps({"confirmed": True}), content_type="application/json")
            from django.contrib.auth import get_user_model
            other = get_user_model().objects.create_user(username="other-bulk-reviewer", is_staff=True,
                is_superuser=True)
            self.client.force_login(other)
            self.assertEqual(self.preview().json()["items"][0]["id"], first.pk)

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

    def test_unresolved_batch_requires_explicit_review_before_new_confirmation(self):
        self.stage(day=14)
        first = self.preview().json()
        BulkCandidateReview.objects.filter(pk=first["id"]).update(status=BulkCandidateReview.Status.RUNNING)
        second = self.preview().json()
        url = self.base + f"bulk-review/{first['id']}/reconcile/"
        rejected = self.client.post(url, data=json.dumps({"reason": "", "acknowledged": True}),
                                    content_type="application/json")
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(self.client.post(self.base + f"bulk-review/{second['id']}/confirm/",
                          data=json.dumps({"confirmed": True}), content_type="application/json").status_code, 409)
        resolved = self.client.post(url, data=json.dumps({"reason": "Diperiksa manual; hentikan batch lama",
                                                       "acknowledged": True}), content_type="application/json")
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["status"], "unknown")
        self.assertEqual(resolved.json()["counts"]["unknown"], 1)
        self.assertIsNotNone(resolved.json()["resolvedAt"])
        self.assertEqual(resolved.json()["resolvedBy"], self.reviewer.get_username())
        self.assertEqual(resolved.json()["resolutionReason"], "Diperiksa manual; hentikan batch lama")
        self.assertEqual(self.client.post(url, data=json.dumps({"reason": "Lain", "acknowledged": True}),
                          content_type="application/json").json(), resolved.json())
        repeated = self.client.post(self.base + f"bulk-review/{first['id']}/confirm/",
                                    data=json.dumps({"confirmed": True}), content_type="application/json")
        self.assertEqual(repeated.json(), resolved.json())
        self.assertEqual(Observation.objects.count(), 0)
        next_batch = self.client.post(self.base + f"bulk-review/{second['id']}/confirm/",
                                      data=json.dumps({"confirmed": True}), content_type="application/json")
        self.assertEqual(next_batch.status_code, 200)
        self.assertEqual(next_batch.json()["counts"]["published"], 1)
        self.assertEqual(Observation.objects.count(), 1)

    def test_reconcile_requires_reviewer_and_csrf(self):
        self.stage(day=15)
        preview = self.preview().json()
        BulkCandidateReview.objects.filter(pk=preview["id"]).update(status=BulkCandidateReview.Status.UNKNOWN)
        url = self.base + f"bulk-review/{preview['id']}/reconcile/"
        payload = json.dumps({"reason": "Ditinjau manual", "acknowledged": True})
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.reviewer)
        self.assertEqual(csrf_client.post(url, data=payload, content_type="application/json").status_code, 403)
        other = type(self.reviewer).objects.create_user(username="unrelated-reviewer", is_staff=True)
        other.user_permissions.add(Permission.objects.get(codename="change_observationcandidate",
                                                          content_type__app_label="indicators"))
        self.client.force_login(other)
        self.assertEqual(self.client.post(url, data=payload, content_type="application/json").status_code, 404)
        self.client.force_login(self.reviewer)
        self.assertFalse(BulkCandidateReview.objects.get(pk=preview["id"]).resolved_at)

    def test_admin_can_find_and_close_unresolved_batch_left_by_another_reviewer(self):
        self.stage(day=16)
        preview = self.preview().json()
        BulkCandidateReview.objects.filter(pk=preview["id"]).update(status=BulkCandidateReview.Status.RUNNING)
        admin = type(self.reviewer).objects.create_user(username="recovery-admin", is_staff=True, is_superuser=True)
        self.client.force_login(admin)
        active = self.client.get(self.base + "bulk-review/active/")
        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.json()["batch"]["id"], preview["id"])
        url = self.base + f"bulk-review/{preview['id']}/reconcile/"
        resolved = self.client.post(url, data=json.dumps({"reason": "Pemeriksaan oleh Admin pengganti",
                                                       "acknowledged": True}), content_type="application/json")
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["resolvedBy"], admin.get_username())
        self.assertEqual(self.client.get(self.base + f"bulk-review/{preview['id']}/").json(), resolved.json())
        self.assertEqual(self.client.get(self.base + "bulk-review/active/").json()["batch"], resolved.json())

    def test_active_readback_is_read_only_and_scoped_to_reviewer(self):
        self.stage(day=7)
        preview = self.preview().json()
        confirmed = self.client.post(
            self.base + f"bulk-review/{preview['id']}/confirm/",
            data=json.dumps({"confirmed": True}), content_type="application/json",
        ).json()
        self.assertEqual(self.client.get(self.base + "bulk-review/active/").json(), {"batch": confirmed})
        self.assertEqual(confirmed["status"], "completed")
