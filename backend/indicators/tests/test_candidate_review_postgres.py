"""Real PostgreSQL lock/race tests; run only with test_settings_candidate_pg."""
import json
import threading
import time
from datetime import date
from decimal import Decimal
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management.color import no_style
from django.db import close_old_connections, connection, connections, transaction
from django.test import Client, TransactionTestCase

from indicators.lifecycle import stage_observation
from indicators.models import DataUpdateLog, Indicator, Observation, ObservationCandidate, Source


@skipUnless(connection.vendor == "postgresql", "requires the disposable PostgreSQL test settings")
class CandidateReviewPostgresConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        super().setUp()
        # TransactionTestCase resets sequences; restore the migrated seed row's sequence in this fixture DB.
        with connection.cursor() as cursor:
            for statement in connection.ops.sequence_reset_sql(no_style(), [DataUpdateLog]):
                cursor.execute(statement)
        user_model = get_user_model()
        self.reviewers = [
            user_model.objects.create_user(username=f"pg-reviewer-{i}", password="synthetic-not-a-real-secret",
                                     is_staff=True, is_superuser=True)
            for i in (1, 2)
        ]
        self.indicator = Indicator.objects.create(code="pg_race", name="Indikator Uji Race", category="Uji", unit="%")
        self.source = Source.objects.create(source_id="PG_TEST_ONLY", source_name="Sumber Uji Race",
                                            institution="Institusi Sintetis", primary_url="https://example.test/pg-race")
        self.observation = Observation.objects.create(
            indicator=self.indicator, source=self.source, observation_date=date(2024, 1, 31),
            period_label="Januari 2024", frequency="monthly", data_type="yoy", value=Decimal("2.000000"),
            unit="%", validation_status=Observation.Status.PUBLISHED, reviewed_by=self.reviewers[0],
        )
        candidate = stage_observation(
            indicator_id=self.indicator.pk, source_id=self.source.pk, observation_date=date(2024, 1, 31),
            period_label="Januari 2024", frequency="monthly", data_type="yoy", value=Decimal("3.250000"), unit="%",
        )
        self.assertIsNotNone(candidate)
        self.candidate = candidate
        self.url = f"/api/admin/sources/{self.source.source_id}/candidates/{candidate.pk}/review/"

    def _post(self, reviewer, body, results, index, ready=None):
        close_old_connections()
        try:
            client = Client()
            client.force_login(reviewer)
            if ready is not None:
                ready.wait(timeout=15)
            response = client.post(self.url, json.dumps(body), content_type="application/json")
            results[index] = (response.status_code, response.json())
        except BaseException as exc:
            results[index] = exc
        finally:
            connections.close_all()

    def test_two_reviewers_race_same_fingerprint_publishes_exactly_once(self):
        body = {"decision": "publish", "fingerprint": self.candidate.fingerprint, "notes": ""}
        parsed = threading.Barrier(2)
        original_parse = __import__("indicators.source_admin_views", fromlist=["_parse_json_body"])._parse_json_body

        def parse_then_release(request):
            parsed_body = original_parse(request)
            parsed.wait(timeout=15)
            return parsed_body

        results = [None, None]
        threads = [threading.Thread(target=self._post, args=(reviewer, body, results, i))
                   for i, reviewer in enumerate(self.reviewers)]
        # Both requests reach the pre-transaction boundary before either can lock the candidate.
        with patch("indicators.candidate_views._parse_json_body", side_effect=parse_then_release):
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)

        self.assertTrue(all(not thread.is_alive() for thread in threads), "review requests did not finish")
        self.assertFalse(any(isinstance(result, BaseException) for result in results), repr(results))
        statuses = sorted(result[0] for result in results)
        self.assertEqual(statuses, [200, 409], results)
        self.candidate.refresh_from_db()
        self.observation.refresh_from_db()
        self.assertEqual(self.candidate.status, ObservationCandidate.Status.PUBLISHED)
        self.assertEqual(self.candidate.reviewed_by_id, self.observation.reviewed_by_id)
        self.assertIn(self.candidate.reviewed_by_id, [reviewer.pk for reviewer in self.reviewers])
        self.assertIsNotNone(self.candidate.reviewed_at)
        self.assertEqual(self.observation.value, Decimal("3.250000"))
        self.assertEqual(self.observation.validation_status, Observation.Status.PUBLISHED)
        self.assertEqual(self.observation.reviewed_by_id, self.candidate.reviewed_by_id)
        self.assertEqual(self.observation.reviewed_at, self.candidate.reviewed_at)
        logs = DataUpdateLog.objects.filter(event_kind=DataUpdateLog.EventKind.PUBLICATION)
        self.assertEqual(logs.count(), 1)
        audit = logs.get()
        self.assertEqual(audit.updated_by_id, self.candidate.reviewed_by_id)
        self.assertEqual(audit.observation_count, 1)
        self.assertEqual(audit.status, DataUpdateLog.Status.SUCCESS)
        self.assertEqual(ObservationCandidate.objects.filter(status="published").count(), 1)

    def test_bps_stage_and_candidate_review_do_not_deadlock_on_master_row_locks(self):
        """Exercise the real staging and HTTP review paths with an inverted lock order."""
        body = {"decision": "publish", "fingerprint": self.candidate.fingerprint, "notes": ""}
        stage_has_indicator = threading.Event()
        review_candidate_query_done = threading.Event()
        stage_result = [None]
        review_result = [None]
        stage_sql = []
        review_sql = []
        deadlock_states = []

        def sqlstate(exc):
            current = exc
            while current is not None:
                state = getattr(current, "sqlstate", None) or getattr(current, "pgcode", None)
                if state:
                    return state
                current = current.__cause__
            return None

        def stage_worker():
            close_old_connections()
            try:
                conn = connections["default"]

                def pause_after_indicator(execute, sql, params, many, context):
                    if 'FROM "indicators_indicator"' in sql and "FOR UPDATE" in sql.upper():
                        stage_sql.append(sql)
                        result = execute(sql, params, many, context)
                        stage_has_indicator.set()
                        if not review_candidate_query_done.wait(timeout=15):
                            raise TimeoutError("review did not lock/read its candidate row")
                        return result
                    if "FOR UPDATE" in sql.upper():
                        stage_sql.append(sql)
                    return execute(sql, params, many, context)

                with conn.execute_wrapper(pause_after_indicator):
                    stage_result[0] = stage_observation(
                        indicator_id=self.indicator.pk, source_id=self.source.pk,
                        observation_date=date(2024, 2, 29), period_label="Februari 2024",
                        frequency="monthly", data_type="yoy", value=Decimal("3.500000"), unit="%",
                    )
            except BaseException as exc:
                stage_result[0] = exc
                if sqlstate(exc):
                    deadlock_states.append(sqlstate(exc))
            finally:
                connections.close_all()

        def review_worker():
            close_old_connections()
            try:
                client = Client()
                client.force_login(self.reviewers[1])
                conn = connections["default"]

                def observe_candidate_lock(execute, sql, params, many, context):
                    result = execute(sql, params, many, context)
                    if ('FROM "indicators_observationcandidate"' in sql
                            and "FOR UPDATE" in sql.upper()):
                        review_sql.append(sql)
                        review_candidate_query_done.set()
                    return result

                with conn.execute_wrapper(observe_candidate_lock):
                    response = client.post(self.url, json.dumps(body), content_type="application/json")
                review_result[0] = (response.status_code, response.json())
            except BaseException as exc:
                review_result[0] = exc
                if sqlstate(exc):
                    deadlock_states.append(sqlstate(exc))
            finally:
                connections.close_all()

        stage = threading.Thread(target=stage_worker)
        review = threading.Thread(target=review_worker)
        stage.start()
        self.assertTrue(stage_has_indicator.wait(timeout=10), "stage did not acquire the indicator row lock")
        review.start()
        stage.join(timeout=25)
        review.join(timeout=25)

        self.assertFalse(stage.is_alive(), "staging thread did not finish")
        self.assertFalse(review.is_alive(), "review thread did not finish")
        self.assertTrue(review_candidate_query_done.is_set(), "review never executed its candidate lock query")
        self.assertNotIn("40P01", deadlock_states,
                         f"PostgreSQL detected a deadlock; stage lock SQL={stage_sql!r}; "
                         f"review lock SQL={review_sql!r}; stage={stage_result[0]!r}; "
                         f"review={review_result[0]!r}")
        self.assertIsInstance(review_result[0], tuple, repr(review_result[0]))
        self.assertEqual(review_result[0][0], 200, review_result[0])
        self.assertTrue(any('FOR UPDATE OF "indicators_observationcandidate"' in sql
                            for sql in review_sql), review_sql)
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.status, ObservationCandidate.Status.PUBLISHED)
        self.assertIsNotNone(stage_result[0], repr(stage_result[0]))
        self.assertFalse(isinstance(stage_result[0], BaseException), repr(stage_result[0]))
        self.assertEqual(DataUpdateLog.objects.filter(event_kind=DataUpdateLog.EventKind.PUBLICATION).count(), 1)
        self.assertEqual(Observation.objects.get(pk=self.observation.pk).value, Decimal("3.250000"))
        self.assertEqual(ObservationCandidate.objects.filter(status="pending").count(), 1)

    def test_review_rechecks_source_binding_after_candidate_lock(self):
        candidate_query_done = threading.Event()
        allow_review = threading.Event()
        source_update_done = threading.Event()
        results = [None]
        update_errors = []
        body = {"decision": "publish", "fingerprint": self.candidate.fingerprint, "notes": ""}

        def review_worker():
            close_old_connections()
            try:
                client = Client()
                client.force_login(self.reviewers[1])
                conn = connections["default"]

                def pause_after_candidate(execute, sql, params, many, context):
                    result = execute(sql, params, many, context)
                    if ('FROM "indicators_observationcandidate"' in sql
                            and "FOR UPDATE" in sql.upper()):
                        candidate_query_done.set()
                        if not allow_review.wait(timeout=15):
                            raise TimeoutError("test did not release candidate review")
                    return result

                with conn.execute_wrapper(pause_after_candidate):
                    response = client.post(self.url, json.dumps(body), content_type="application/json")
                results[0] = (response.status_code, response.json())
            except BaseException as exc:
                results[0] = exc
            finally:
                connections.close_all()

        def change_source_id():
            close_old_connections()
            try:
                if not candidate_query_done.wait(timeout=10):
                    raise TimeoutError("review did not execute its candidate query")
                changed = Source.objects.filter(pk=self.source.pk).update(source_id="PG_TEST_RENAMED")
                if changed != 1:
                    raise AssertionError(f"expected to rename one source, changed={changed}")
            except BaseException as exc:
                update_errors.append(exc)
            finally:
                source_update_done.set()
                connections.close_all()

        reviewer = threading.Thread(target=review_worker)
        updater = threading.Thread(target=change_source_id)
        reviewer.start()
        updater.start()
        try:
            self.assertTrue(candidate_query_done.wait(timeout=10), "review candidate query did not run")
            # With only the candidate locked, this source rename commits before the
            # route-binding recheck; a joined-row lock would hold the rename until review ends.
            self.assertTrue(source_update_done.wait(timeout=5), "source rename stayed blocked by the joined read")
        finally:
            allow_review.set()
            reviewer.join(timeout=20)
            updater.join(timeout=10)

        self.assertFalse(reviewer.is_alive(), "review request did not finish")
        self.assertFalse(updater.is_alive(), "source rename did not finish")
        self.assertFalse(update_errors, repr(update_errors))
        self.assertEqual(results[0][0], 404, results[0])
        self.candidate.refresh_from_db()
        self.source.refresh_from_db()
        self.assertEqual(self.source.source_id, "PG_TEST_RENAMED")
        self.assertEqual(self.candidate.status, ObservationCandidate.Status.PENDING)
        self.assertEqual(DataUpdateLog.objects.filter(event_kind=DataUpdateLog.EventKind.PUBLICATION).count(), 0)

    def test_review_waits_on_candidate_row_lock_and_pg_reports_blocker(self):
        body = {"decision": "publish", "fingerprint": self.candidate.fingerprint, "notes": ""}
        locked = threading.Event()
        release = threading.Event()
        results = [None]

        def hold_lock():
            close_old_connections()
            try:
                with transaction.atomic():
                    ObservationCandidate.objects.select_for_update().get(pk=self.candidate.pk)
                    locked.set()
                    if not release.wait(timeout=20):
                        raise TimeoutError("test did not release candidate row lock")
            except BaseException as exc:
                results[0] = exc
            finally:
                connections.close_all()

        holder = threading.Thread(target=hold_lock)
        holder.start()
        self.assertTrue(locked.wait(timeout=10), "lock holder did not acquire row lock")

        reviewer = self.reviewers[1]
        review_results = [None]
        request = threading.Thread(target=self._post, args=(reviewer, body, review_results, 0))
        request.start()
        try:
            deadline = time.monotonic() + 10
            blocking_pids = []
            while time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pid, pg_blocking_pids(pid) FROM pg_stat_activity "
                                   "WHERE application_name = 'deksi_candidate_pg_test' AND state = 'active' "
                                   "AND cardinality(pg_blocking_pids(pid)) > 0")
                    row = cursor.fetchone()
                if row:
                    blocking_pids = row[1]
                    break
                time.sleep(0.05)
            self.assertTrue(blocking_pids, "pg_blocking_pids did not show the review blocked by the held row lock")
        finally:
            release.set()
            request.join(timeout=25)
            holder.join(timeout=10)
        self.assertFalse(request.is_alive(), "blocked review did not finish after lock release")
        self.assertFalse(holder.is_alive(), "lock holder did not finish")
        self.assertFalse(isinstance(results[0], BaseException), repr(results[0]))
        self.assertFalse(isinstance(review_results[0], BaseException), repr(review_results[0]))
        self.assertEqual(review_results[0][0], 200, review_results)
        self.candidate.refresh_from_db()
        self.observation.refresh_from_db()
        self.assertEqual(self.candidate.status, "published")
        self.assertEqual(self.observation.value, Decimal("3.250000"))
        self.assertEqual(DataUpdateLog.objects.filter(event_kind="publication").count(), 1)
