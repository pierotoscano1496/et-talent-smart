from .base import *  # noqa: F403
from django.core.exceptions import ImproperlyConfigured

if len(SECRET_KEY) < 50 or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("qa necesita una SECRET_KEY aleatoria y hosts explícitos.")
for value in (SECRET_KEY, RFID_API_KEY, TALENTOSITO_SERVICE_KEY, MINIO_SECRET_KEY):
    if value.startswith("change-") or value.startswith("replace-"):
        raise ImproperlyConfigured("Reemplaza las credenciales de ejemplo antes de desplegar.")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^api/health/live/$", r"^api/health/ready/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
# Do not preload or force HTTPS on unrelated subdomains of the shared host.
# Enable these only after the actual QA domain and its subdomains are reviewed.
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
