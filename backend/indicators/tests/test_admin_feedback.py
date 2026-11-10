"""Tests for the admin feedback list."""

from django.test import Client, TestCase

from indicators.feedback_model import Feedback


class AdminFeedbackListTests(TestCase):
    def setUp(self):
        self.client = Client()
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
