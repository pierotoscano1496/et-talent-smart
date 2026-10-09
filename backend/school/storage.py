from django.conf import settings
from minio import Minio
import urllib3


def client():
    return Minio(settings.MINIO_ENDPOINT, access_key=settings.MINIO_ACCESS_KEY,
                 secret_key=settings.MINIO_SECRET_KEY, secure=settings.MINIO_SECURE,
                 http_client=urllib3.PoolManager(timeout=urllib3.Timeout(connect=3, read=10), retries=1))
