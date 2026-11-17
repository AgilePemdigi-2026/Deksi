"""Opt-in settings restricted to the disposable PostgreSQL fixture."""
import os
import re

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_SECRET = "DEKSI_CANDIDATE_PG_TEST_ONLY"
if os.environ.get("DEKSI_CANDIDATE_PG_OPT_IN") != _SECRET:
    raise RuntimeError("Candidate PostgreSQL tests require explicit opt-in")

_host = os.environ.get("DEKSI_CANDIDATE_PG_HOST", "")
_port = os.environ.get("DEKSI_CANDIDATE_PG_PORT", "")
_name = os.environ.get("DEKSI_CANDIDATE_PG_NAME", "")
_user = os.environ.get("DEKSI_CANDIDATE_PG_USER", "")
_password = os.environ.get("DEKSI_CANDIDATE_PG_PASSWORD", "")
if _host not in {"127.0.0.1", "candidate-pg"} or not _port.isdecimal() or not (1 <= int(_port) <= 65535):
    raise RuntimeError("Candidate PostgreSQL host must be the loopback address or the isolated fixture alias")
if not re.fullmatch(r"dksi_cand_pg_[a-f0-9]{8}", _name):
    raise RuntimeError("Candidate PostgreSQL database name is outside the disposable-test allowlist")
if not re.fullmatch(r"dksi_test_[a-f0-9]{8}", _user) or not _password.startswith("synthetic-"):
    raise RuntimeError("Candidate PostgreSQL credentials must be synthetic and uniquely scoped")

SECRET_KEY = "synthetic-candidate-postgres-test-key"
DEBUG = False
ALLOWED_HOSTS = ["testserver"]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "corsheaders", "indicators", "axes", "admin_auth",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware", "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]
ROOT_URLCONF = "backend.urls"
AUTHENTICATION_BACKENDS = ["axes.backends.AxesStandaloneBackend", "admin_auth.backends.AdminBackend"]
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request",
              "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": _name,
    "USER": _user,
    "PASSWORD": _password,
    "HOST": _host,
    "PORT": _port,
    "CONN_MAX_AGE": 0,
    "TEST": {"NAME": f"test_{_name}"},
    "OPTIONS": {"connect_timeout": 5, "application_name": "deksi_candidate_pg_test"},
}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "Asia/Jakarta"
STATIC_URL = "/static/"
CORS_ALLOWED_ORIGINS = []
CSRF_TRUSTED_ORIGINS = []
DEKSI_RAW_DIR = BASE_DIR / ".artifacts" / "candidate-pg-test-raw"
BPS_API_KEY = ""
BPS_API_BASE_URL = "https://webapi.bps.go.id/v1"
