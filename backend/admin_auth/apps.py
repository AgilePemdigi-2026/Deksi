from importlib import import_module

from django.apps import AppConfig


class AdminAuthConfig(AppConfig):
    name = "admin_auth"

    def ready(self):
        import_module("admin_auth.signals")
