"""Tests for the admin feedback list."""

from django.test import Client, TestCase

from indicators.feedback_model import Feedback
from indicators.models import Indicator


class AdminFeedbackListTests(TestCase):
    def setUp(self):
        self.client = Client()
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
