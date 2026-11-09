"""Isolated test settings; never open the application's existing SQLite database."""

from . import settings as baseline

globals().update({key: getattr(baseline, key) for key in dir(baseline) if key.isupper()})
SECRET_KEY = "test-only-deksi-auth-fixture-key-not-for-production"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CORS_ALLOWED_ORIGINS = ["http://127.0.0.1:62942", "http://localhost:5173"]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {"axes": {"handlers": ["null"], "propagate": False}},
}
