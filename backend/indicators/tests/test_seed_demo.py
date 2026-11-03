from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from indicators.management.commands.seed_demo import is_isolated_demo_database
from indicators.models import Indicator, Observation, Source


class SeedDemoTests(TestCase):
    def test_guard_requires_exact_demo_settings_and_database(self):
        from django.db import connection

        with patch.dict("os.environ", {"DJANGO_SETTINGS_MODULE": "backend.settings_demo"}):
            with patch.dict(
                connection.settings_dict, {"ENGINE": "django.db.backends.sqlite3", "NAME": "/data/deksi-demo.sqlite3"}
            ):
                self.assertTrue(is_isolated_demo_database())
            with patch.dict(
                connection.settings_dict, {"ENGINE": "django.db.backends.sqlite3", "NAME": "/data/db.sqlite3"}
            ):
                self.assertFalse(is_isolated_demo_database())

    def test_seed_is_refused_outside_explicit_demo_database(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Indicator.objects.count(), 0)

    @override_settings(DEBUG=True, DEKSI_SYNTHETIC_DEMO=True)
    @patch("indicators.management.commands.seed_demo.is_isolated_demo_database", return_value=True)
    def test_seed_creates_labeled_simulation_and_refuses_second_run(self, _guard):
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Indicator.objects.count(), 6)
        self.assertEqual(Observation.objects.count(), 48)
        self.assertTrue(all("SIMULASI" in name for name in Indicator.objects.values_list("name", flat=True)))
        self.assertTrue(all("SIMULASI" in value for value in Source.objects.values_list("institution", flat=True)))
        self.assertFalse(Observation.objects.exclude(reviewed_by__username="demo-simulation-not-human-review").exists())
        self.assertFalse(Observation.objects.filter(reviewed_by__is_active=True).exists())
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Observation.objects.count(), 48)
