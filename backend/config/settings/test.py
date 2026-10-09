import os
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("RFID_API_KEY", "test-rfid")
os.environ.setdefault("TALENTOSITO_SERVICE_KEY", "test-service")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
from .base import *  # noqa: F403,E402
# Unit tests can run without Docker; CI also runs this suite against PostgreSQL.
if os.getenv("TEST_POSTGRES") != "1":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
if os.getenv("BUILD_STATIC") != "1":
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
