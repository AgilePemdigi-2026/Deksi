import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from indicators import bps
from indicators.models import Observation, ObservationCandidate
from indicators.resync_model import ResyncJob
from indicators.sync_history_model import SyncRun
from indicators.tests.support import IndicatorCase


class ResyncWorkerTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_user(username="resync-worker-staff", is_staff=True)
        self.source = bps._get_or_create_source()
        self.job = ResyncJob.objects.create(source=self.source, requested_by=self.actor, request_key=uuid.uuid4())
        self.series = {
            "code": "resync_test", "var_id": 123, "name": "Synthetic indicator", "category": "Synthetic",
            "unit": "%", "aggregation_kind": "avg", "sort_order": 1,
            "frequency": "annual", "data_type": "level", "subperiods": {1: 1},
        }
        self.point = {
            "observation_date": date(2020, 12, 31), "period_label": "2020", "frequency": "annual",
            "data_type": "level", "value": Decimal("6"), "unit": "%",
        }

    def test_worker_processes_one_job_and_creates_one_run_and_candidate(self):
        with patch.object(bps, "BPS_SERIES", [self.series]), \
             patch.object(bps, "fetch_series", return_value=[self.point]):
            call_command("process_resync", once=True)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "success")
        self.assertEqual(SyncRun.objects.count(), 1)
        self.assertEqual(self.job.run.actor, self.actor)
        self.assertEqual(self.job.run.status, "success")
        self.assertEqual(ObservationCandidate.objects.count(), 1)
        self.assertFalse(Observation.objects.exists())

    def test_worker_rechecks_source_status_before_claim(self):
        self.source.status = "inactive"
        self.source.save(update_fields=["status"])
        with patch.object(bps, "fetch_series", side_effect=AssertionError("unexpected provider call")):
            call_command("process_resync", once=True)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "cancelled")
        self.assertFalse(SyncRun.objects.exists())

    def test_modified_bps_master_metadata_is_not_silently_used(self):
        self.source.institution = "Different institution"
        self.source.save(update_fields=["institution"])
        with patch.object(bps, "fetch_series", side_effect=AssertionError("unexpected provider call")) as fetch:
            call_command("process_resync", once=True)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "failed")
        fetch.assert_not_called()

    def test_partial_failure_is_failed_without_exposing_provider_error(self):
        with patch.object(bps, "_sync_bps_started", return_value={"errors": ["private fixture"]}):
            call_command("process_resync", once=True)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "failed")
        self.assertEqual(self.job.run.status, "failed")
        self.assertNotIn("private fixture", self.job.safe_message)
        self.assertIsNone(self.job.run.item_count)

    def test_unexpected_exception_is_failed_without_exposing_details(self):
        with patch.object(bps, "_sync_bps_started", side_effect=RuntimeError("private fixture")):
            call_command("process_resync", once=True)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "failed")
        self.assertEqual(self.job.run.status, "failed")
        self.assertNotIn("private fixture", self.job.safe_message)

    def test_worker_interruption_remains_unknown_and_is_not_retried(self):
        with patch.object(bps, "_sync_bps_started", side_effect=SystemExit("synthetic crash")):
            with self.assertRaises(SystemExit):
                call_command("process_resync", once=True)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "running")
        self.assertEqual(self.job.run.status, "running")
        with patch.object(bps, "_sync_bps_started", side_effect=AssertionError("must not rerun")) as handler:
            call_command("process_resync", once=True)
        handler.assert_not_called()
        self.assertEqual(SyncRun.objects.count(), 1)


class ResyncPublishedDataTests(IndicatorCase):
    def test_partial_failure_preserves_published_data_and_stages_candidate(self):
        source = bps._get_or_create_source()
        series = {"code": "bps_resync_synthetic", "var_id": 9999, "name": "Synthetic",
                  "category": "Uji", "unit": "%", "aggregation_kind": "avg", "sort_order": 1,
                  "frequency": "annual", "data_type": "level", "subperiods": {1: 1}}
        indicator = bps._get_or_create_indicator(series)
        observed = date(2020, 12, 31)
        row = self.observation(indicator=indicator, source=source, observation_date=observed,
                               period_label="2020", frequency="annual", data_type="level", value=Decimal("5"))
        previous = self.client.get(f"/api/indicators/?code={indicator.code}").json()
        job = ResyncJob.objects.create(source=source, requested_by=self.reviewer, request_key=uuid.uuid4())
        point = {"observation_date": observed, "period_label": "2020", "frequency": "annual",
                 "data_type": "level", "value": Decimal("6"), "unit": "%"}
        second = {**series, "code": "bps_resync_other"}
        with patch.object(bps, "BPS_SERIES", [series, second]), \
             patch.object(bps, "fetch_series", side_effect=[[point], bps.BpsError("synthetic error")]):
            call_command("process_resync", once=True)
        job.refresh_from_db()
        row.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertEqual(row.value, Decimal("5"))
        self.assertEqual(row.validation_status, Observation.Status.PUBLISHED)
        self.assertEqual(self.client.get(f"/api/indicators/?code={indicator.code}").json(), previous)
        candidate = ObservationCandidate.objects.get(indicator=indicator)
        self.assertEqual(candidate.payload["value"], "6.000000")
        self.assertEqual(candidate.status, ObservationCandidate.Status.PENDING)
