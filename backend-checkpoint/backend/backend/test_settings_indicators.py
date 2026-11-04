"""Isolated test/loopback settings; never loads .env or an existing database."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "synthetic-indicator-test-key-not-for-deployment"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "corsheaders", "indicators",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware", "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "backend.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request",
              "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
# The test runner uses memory; a loopback integration runner may supply its own owned scratch file.
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3", "NAME": os.environ.get("DEKSI_TEST_DATABASE", ":memory:")}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "Asia/Jakarta"
STATIC_URL = "/static/"
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
if os.environ.get("DEKSI_TEST_FE_ORIGIN"):
    CORS_ALLOWED_ORIGINS.append(os.environ["DEKSI_TEST_FE_ORIGIN"])
DEKSI_RAW_DIR = Path(os.environ.get("DEKSI_TEST_RAW_ROOT", BASE_DIR / ".artifacts" / "raw"))
DEKSI_MAX_RAW_BYTES = 32 * 1024 * 1024
BPS_API_KEY = ""
BPS_API_BASE_URL = "https://webapi.bps.go.id/v1"
