"""Tests for the admin feedback list."""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from indicators.feedback_model import Feedback, FeedbackAuditLog
from indicators.models import Indicator


class AdminFeedbackListTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="feedback-list-admin",
            password="test-password",
            is_staff=True,
        )
        self.client = Client()
        self.client.force_login(self.admin)
        self.indicator = Indicator.objects.create(
            code="pdb",
            name="Pertumbuhan PDB",
            category="PDB",
            unit="%",
            aggregation_kind="yoy",
            sort_order=1,
        )
        self.pending_feedback = Feedback.objects.create(
            category=Feedback.Category.DATA_ERROR,
            description="Nilai PDB kuartal 1 tidak sinkron dengan rilis BPS resmi.",
            sender_name="Budi Santoso",
            sender_email="budi@example.com",
            related_indicator_code="pdb",
            related_period="Q1 2024",
            status=Feedback.Status.PENDING,
        )
        Feedback.objects.create(
            category=Feedback.Category.VISUALIZATION,
            description="Grafik tren inflasi sulit dibaca pada layar perangkat mobile.",
            sender_name="Siti Rahma",
            status=Feedback.Status.IN_REVIEW,
        )

    def test_list_feedback_loads_and_includes_required_fields(self):
        response = self.client.get("/api/admin/feedback/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["feedbacks"]), 2)

        item = next(feedback for feedback in data["feedbacks"] if feedback["id"] == self.pending_feedback.pk)
        self.assertEqual(item["category"], Feedback.Category.DATA_ERROR)
        self.assertEqual(item["category_label"], "Kesalahan Data")
        self.assertIsNotNone(item["created_at"])
        self.assertEqual(item["status"], Feedback.Status.PENDING)
        self.assertEqual(item["status_label"], "Menunggu Ditinjau")

    def test_list_feedback_empty_handling(self):
        Feedback.objects.all().delete()

        response = self.client.get("/api/admin/feedback/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
        self.assertEqual(response.json()["feedbacks"], [])

    def test_list_feedback_can_filter_by_status_and_category(self):
        response = self.client.get("/api/admin/feedback/?status=pending&category=data_error")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["feedbacks"][0]["id"], self.pending_feedback.pk)

    def test_list_feedback_searches_across_report_fields(self):
        response = self.client.get("/api/admin/feedback/?search=BPS")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["search_query"], "BPS")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["feedbacks"][0]["id"], self.pending_feedback.pk)

    def test_list_feedback_search_returns_empty_list(self):
        response = self.client.get("/api/admin/feedback/?search=kata-tidak-ada-xyzz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
        self.assertEqual(response.json()["feedbacks"], [])

    def test_list_feedback_requires_admin_authentication(self):
        response = Client().get("/api/admin/feedback/")

        self.assertEqual(response.status_code, 401)

    def test_detail_feedback_requires_admin_authentication(self):
        response = Client().get(f"/api/admin/feedback/{self.pending_feedback.pk}/")

        self.assertEqual(response.status_code, 401)

    def test_list_and_detail_feedback_reject_non_staff_user(self):
        user = get_user_model().objects.create_user(
            username="feedback-regular-user",
            password="test-password",
            is_staff=False,
        )
        client = Client()
        client.force_login(user)

        list_response = client.get("/api/admin/feedback/")
        detail_response = client.get(f"/api/admin/feedback/{self.pending_feedback.pk}/")

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(detail_response.status_code, 403)

    def test_detail_feedback_includes_related_indicator_and_current_status(self):
        response = self.client.get(f"/api/admin/feedback/{self.pending_feedback.pk}/")

        self.assertEqual(response.status_code, 200)
        detail = response.json()["feedback"]
        self.assertEqual(detail["id"], self.pending_feedback.pk)
        self.assertEqual(detail["description"], self.pending_feedback.description)
        self.assertEqual(detail["status"], self.pending_feedback.status)
        self.assertEqual(detail["status_label"], self.pending_feedback.get_status_display())
        self.assertEqual(detail["related_indicator"], {
            "code": self.indicator.code,
            "name": self.indicator.name,
            "category": self.indicator.category,
            "unit": self.indicator.unit,
        })
        self.assertEqual(detail["related_period"], "Q1 2024")

    def test_detail_feedback_falls_back_when_indicator_is_unknown(self):
        feedback = Feedback.objects.create(
            category=Feedback.Category.SOURCE,
            description="Sumber data ini belum menjelaskan periode publikasinya.",
            related_indicator_code="inflasi",
        )

        response = self.client.get(f"/api/admin/feedback/{feedback.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["feedback"]["related_indicator"], {
            "code": "inflasi",
            "name": "INFLASI",
            "category": "-",
            "unit": "-",
        })

    def test_detail_feedback_returns_not_found_for_unknown_id(self):
        response = self.client.get("/api/admin/feedback/99999/")

        self.assertEqual(response.status_code, 404)


class AdminFeedbackStatusTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="feedback-admin",
            password="test-password",
            is_staff=True,
        )
        self.feedback = Feedback.objects.create(
            category=Feedback.Category.DATA_ERROR,
            description="Angka pada laporan perlu diverifikasi ulang.",
        )
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.admin)
        detail_response = self.client.get(f"/api/admin/feedback/{self.feedback.pk}/")
        self.csrf_token = detail_response.json()["csrfToken"]

    def test_status_update_saves_feedback_and_audit_log(self):
        notes = "Data telah diverifikasi dengan sumber resmi."
        response = self.client.post(
            f"/api/admin/feedback/{self.feedback.pk}/status/",
            data=json.dumps({"status": "resolved", "notes": notes}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()["feedback"]
        self.feedback.refresh_from_db()
        self.assertEqual(self.feedback.status, Feedback.Status.RESOLVED)
        self.assertEqual(self.feedback.admin_notes, notes)
        self.assertIsNotNone(self.feedback.updated_at)
        self.assertEqual(result["status"], Feedback.Status.RESOLVED)
        self.assertEqual(result["admin_notes"], notes)
        self.assertEqual(len(result["audit_logs"]), 1)

        audit = FeedbackAuditLog.objects.get(feedback=self.feedback)
        self.assertEqual(audit.old_status, Feedback.Status.PENDING)
        self.assertEqual(audit.new_status, Feedback.Status.RESOLVED)
        self.assertEqual(audit.notes, notes)
        self.assertEqual(audit.changed_by, self.admin.username)
        self.assertIsNotNone(audit.changed_at)

    def test_status_update_rejects_invalid_status(self):
        response = self.client.post(
            f"/api/admin/feedback/{self.feedback.pk}/status/",
            data=json.dumps({"status": "unknown", "notes": "Invalid"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 400)
        self.feedback.refresh_from_db()
        self.assertEqual(self.feedback.status, Feedback.Status.PENDING)
        self.assertFalse(FeedbackAuditLog.objects.exists())

    def test_status_update_rejects_notes_that_are_not_text(self):
        response = self.client.post(
            f"/api/admin/feedback/{self.feedback.pk}/status/",
            data=json.dumps({"status": "in_review", "notes": ["not", "text"]}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(FeedbackAuditLog.objects.exists())

    def test_status_update_rejects_overlong_notes(self):
        response = self.client.post(
            f"/api/admin/feedback/{self.feedback.pk}/status/",
            data=json.dumps({"status": "in_review", "notes": "x" * 2001}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(FeedbackAuditLog.objects.exists())

    def test_status_update_requires_staff_authentication(self):
        client = Client()
        response = client.post(
            f"/api/admin/feedback/{self.feedback.pk}/status/",
            data=json.dumps({"status": "resolved", "notes": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(FeedbackAuditLog.objects.exists())
