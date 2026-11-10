"""Production settings for Coolify deployments."""

from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from . import settings as baseline

globals().update({key: getattr(baseline, key) for key in dir(baseline) if key.isupper()})

env = baseline.env
BASE_DIR = baseline.BASE_DIR
MIDDLEWARE = list(baseline.MIDDLEWARE)
DEBUG = False
SECRET_KEY = env("SECRET_KEY", default="")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY must be configured for production.")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must include the public application domain.")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="deksi"),
        "USER": env("POSTGRES_USER", default="deksi"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "HOST": env("EMAIL_HOST", default="localhost"),
        "PORT": env.int("EMAIL_PORT", default=25),
        "USERNAME": env("EMAIL_HOST_USER", default=""),
        "PASSWORD": env("EMAIL_HOST_PASSWORD", default=""),
        "USE_TLS": env.bool("EMAIL_USE_TLS", default=False),
        "USE_SSL": env.bool("EMAIL_USE_SSL", default=False),
    }
}

MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEKSI_RAW_DIR = Path("/data/raw_storage")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31_536_000)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
