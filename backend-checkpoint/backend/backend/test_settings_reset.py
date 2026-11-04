"""Reset tests use only disposable databases and an in-process mail outbox."""

from . import test_settings_auth as baseline

globals().update({key: getattr(baseline, key) for key in dir(baseline) if key.isupper()})
ADMIN_PASSWORD_RESET_ENABLED = True
ADMIN_PASSWORD_RESET_FRONTEND_ORIGIN = "http://127.0.0.1:62944"
PASSWORD_RESET_TIMEOUT = 1800
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
DEFAULT_FROM_EMAIL = "DEKSI <no-reply@example.test>"
CORS_ALLOWED_ORIGINS = [*baseline.CORS_ALLOWED_ORIGINS, ADMIN_PASSWORD_RESET_FRONTEND_ORIGIN]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
