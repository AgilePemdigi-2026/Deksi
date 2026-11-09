from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.admin.sites import site
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory

from indicators.admin import ObservationAdmin
from indicators.lifecycle import review_candidate, stage_observation
from indicators.models import DataUpdateLog, Observation, ObservationCandidate
from indicators.tests.support import IndicatorCase


class CandidateReviewTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        self.reviewer.is_superuser = True
        self.reviewer.save(update_fields=["is_superuser"])
        self.row = self.observation(observation_date=date(2020, 1, 31), period_label="Januari 2020",
                                    value=Decimal("5"))

    def stage(self, value="6", **changes):
        fields = {"indicator_id": self.indicator.pk, "source_id": self.source.pk,
            "observation_date": self.row.observation_date, "period_label": self.row.period_label,
            "frequency": self.row.frequency, "data_type": self.row.data_type, "value": Decimal(value), "unit": "%"}
        fields.update(changes)
        candidate = stage_observation(**fields)
        assert candidate is not None
        return candidate

    def test_real_admin_action_reviews_selected_candidate_before_replacing_public_value(self):
        candidate = self.stage()
        self.client.force_login(self.reviewer)
        response = self.client.post("/admin/indicators/observationcandidate/", {
            "action": "action_publish", "_selected_action": [candidate.pk], "select_across": "0"})
        self.assertEqual(response.status_code, 302)
        self.row.refresh_from_db()
        candidate.refresh_from_db()
        self.assertEqual(self.row.value, Decimal("6"))
        self.assertEqual(candidate.status, ObservationCandidate.Status.PUBLISHED)
        self.assertEqual(candidate.reviewed_by_id, self.reviewer.pk)
        self.assertEqual(self.row.reviewed_at, candidate.reviewed_at)
        self.assertEqual(candidate.base_snapshot["observation"]["value"], "5.000000")
        self.assertEqual(DataUpdateLog.objects.first().updated_by_id, self.reviewer.pk)
        self.assertEqual(self.client.get("/api/indicators/?code=inflasi").json()["indicators"][0]["value"], "6")

    def test_rejection_preserves_public_value_and_records_distinct_review(self):
        candidate = self.stage()
        before = self.client.get("/api/indicators/?code=inflasi").content
        review_candidate(candidate.pk, self.reviewer, publish=False, notes="UJI ditolak")
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, "rejected")
        self.assertEqual(candidate.review_notes, "UJI ditolak")
        self.assertEqual(self.client.get("/api/indicators/?code=inflasi").content, before)

    def test_permission_is_rechecked_after_user_is_deactivated(self):
        candidate = self.stage()
        self.reviewer.has_perm("indicators.change_observationcandidate")
        type(self.reviewer).objects.filter(pk=self.reviewer.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            review_candidate(candidate.pk, self.reviewer)
        self.row.refresh_from_db()
        self.assertEqual(self.row.value, Decimal("5"))

    def test_competing_candidate_becomes_stale_after_first_review(self):
        first, second = self.stage("6"), self.stage("7")
        review_candidate(first.pk, self.reviewer)
        with self.assertRaises(ValidationError):
            review_candidate(second.pk, self.reviewer)
        self.row.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.row.value, Decimal("6"))
        self.assertEqual(second.status, "pending")

    def test_payload_tampering_cannot_inherit_original_review(self):
        candidate = self.stage()
        ObservationCandidate.objects.filter(pk=candidate.pk).update(payload={**candidate.payload, "value": "99.000000"})
        with self.assertRaises(ValidationError):
            review_candidate(candidate.pk, self.reviewer)
        self.row.refresh_from_db()
        self.assertEqual(self.row.value, Decimal("5"))

    def test_logging_failure_rolls_back_observation_and_candidate_review(self):
        candidate = self.stage()
        with patch("indicators.lifecycle.record_update_success", side_effect=RuntimeError("UJI log gagal")):
            with self.assertRaises(RuntimeError):
                review_candidate(candidate.pk, self.reviewer)
        self.row.refresh_from_db()
        candidate.refresh_from_db()
        self.assertEqual(self.row.value, Decimal("5"))
        self.assertEqual(candidate.status, "pending")
        self.assertIsNone(candidate.reviewed_at)

    def test_review_rejects_invalid_domain_value_without_replacing_valid_old_value(self):
        self.indicator.code = "investasi"
        self.indicator.save(update_fields=["code"])
        candidate = self.stage("1900")
        with self.assertRaises(ValidationError):
            review_candidate(candidate.pk, self.reviewer)
        self.row.refresh_from_db()
        self.assertEqual(self.row.value, Decimal("5"))

    def test_new_observation_is_created_only_after_review(self):
        candidate = self.stage(observation_date=date(2020, 2, 29), period_label="Februari 2020")
        self.assertEqual(Observation.objects.count(), 1)
        review_candidate(candidate.pk, self.reviewer)
        self.assertEqual(Observation.objects.count(), 2)
        self.assertEqual(self.client.get("/api/indicators/?code=inflasi").json()["indicators"][0]["value"], "6")

    def test_processed_candidate_cannot_be_published_twice(self):
        candidate = self.stage()
        review_candidate(candidate.pk, self.reviewer)
        count = DataUpdateLog.objects.count()
        with self.assertRaises(ValidationError):
            review_candidate(candidate.pk, self.reviewer)
        self.assertEqual(DataUpdateLog.objects.count(), count)

    def test_master_metadata_change_invalidates_pending_review_basis(self):
        candidate = self.stage()
        self.source.institution = "INSTANSI UJI BERUBAH"
        self.source.save(update_fields=["institution"])
        with self.assertRaises(ValidationError):
            review_candidate(candidate.pk, self.reviewer)
        self.row.refresh_from_db()
        self.assertEqual(self.row.value, Decimal("5"))

    def test_published_admin_form_does_not_allow_fact_edits_without_new_review(self):
        request = RequestFactory().get("/admin/indicators/observation/")
        request.user = self.reviewer
        model_admin = ObservationAdmin(Observation, site)
        self.assertIn("value", model_admin.get_readonly_fields(request, self.row))
        self.assertFalse(model_admin.has_delete_permission(request, self.row))

    def test_publication_command_requires_explicit_selected_candidate_ids(self):
        self.row.validation_status = "validated"
        self.row.save(update_fields=["validation_status"])
        with self.assertRaises(CommandError):
            call_command("publish_observations", username=self.reviewer.get_username())
        self.row.refresh_from_db()
        self.assertEqual(self.row.validation_status, "validated")

    def test_publication_command_publishes_only_explicit_selection(self):
        first, second = self.stage("6"), self.stage("7")
        call_command("publish_observations", username=self.reviewer.get_username(), candidate_ids=[first.pk],
                     stdout=StringIO())
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, "published")
        self.assertEqual(second.status, "pending")

    def test_publication_command_rolls_back_all_selections_if_one_is_stale(self):
        first, second = self.stage("6"), self.stage("7")
        with self.assertRaises(CommandError):
            call_command("publish_observations", username=self.reviewer.get_username(),
                         candidate_ids=[first.pk, second.pk], stdout=StringIO())
        self.row.refresh_from_db()
        self.assertEqual(self.row.value, Decimal("5"))
        self.assertEqual(ObservationCandidate.objects.filter(status="pending").count(), 2)

    def test_legacy_observation_publication_action_is_unavailable_even_to_superuser(self):
        before_logs = DataUpdateLog.objects.count()
        Observation.objects.filter(pk=self.row.pk).update(validation_status="validated", reviewed_by=None,
                                                         reviewed_at=None)
        self.client.force_login(self.reviewer)
        self.client.post("/admin/indicators/observation/", {
            "action": "action_publish", "_selected_action": [self.row.pk], "select_across": "0"})
        self.row.refresh_from_db()
        self.assertEqual(self.row.validation_status, "validated")
        self.assertEqual(DataUpdateLog.objects.count(), before_logs)
        request = RequestFactory().get("/admin/indicators/observation/")
        request.user = self.reviewer
        self.assertNotIn("action_publish", ObservationAdmin(Observation, site).get_actions(request))

    def test_identical_unreviewed_legacy_facts_still_require_a_candidate(self):
        for status in ["pending", "validated", "published"]:
            with self.subTest(status=status):
                Observation.objects.filter(pk=self.row.pk).update(validation_status=status,
                                                                 reviewed_by=None, reviewed_at=None)
                candidate = self.stage("5")
                self.assertEqual(candidate.status, "pending")
                self.assertIsNone(candidate.reviewed_by_id)
