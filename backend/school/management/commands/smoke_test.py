import io
import secrets
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from rest_framework.test import APIClient
from school.models import User, StoredFile
from school.storage import client


class Command(BaseCommand):
    help = "Verify real MinIO write/read/delete with a unique temporary object."

    def handle(self, *args, **options):
        storage = client()
        key = "healthchecks/" + secrets.token_hex(16)
        payload = b"Talent Smart storage check"
        storage.put_object(settings.MINIO_BUCKET, key, io.BytesIO(payload), len(payload))
        try:
            response = storage.get_object(settings.MINIO_BUCKET, key)
            try:
                if response.read() != payload:
                    raise CommandError("El archivo recuperado no coincide.")
            finally:
                response.close()
                response.release_conn()
        finally:
            storage.remove_object(settings.MINIO_BUCKET, key)
        self.stdout.write(self.style.SUCCESS("MinIO: escritura, lectura y eliminación correctas."))
        # Exercise the API and PostgreSQL metadata, without leaving test accounts/files behind.
        object_name = None
        try:
            with transaction.atomic():
                suffix = secrets.token_hex(12)
                password = secrets.token_urlsafe(32)
                user = User.objects.create_user(username=suffix, email=suffix + "@example.invalid", password=password)
                api = APIClient(HTTP_HOST="localhost")
                login = api.post("/api/auth/login/", {"email": user.email, "password": password}, secure=True)
                if login.status_code != 200:
                    raise CommandError("Falló el login de integración.")
                api.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["token"])
                upload = api.post("/api/files/", {"file": SimpleUploadedFile("check.txt", payload)}, secure=True)
                if upload.status_code != 201:
                    raise CommandError("Falló la carga autenticada.")
                record = StoredFile.objects.get(pk=upload.data["id"])
                object_name = record.object_name
                download = api.get(f"/api/files/{record.pk}/download/", secure=True)
                if download.status_code != 200 or b"".join(download.streaming_content) != payload:
                    raise CommandError("Falló la descarga autenticada.")
                download.close()
                api.credentials()
                if api.get(f"/api/files/{record.pk}/download/", secure=True).status_code != 401:
                    raise CommandError("Un archivo privado fue accesible sin sesión.")
                transaction.set_rollback(True)
        finally:
            if object_name:
                storage.remove_object(settings.MINIO_BUCKET, object_name)
        self.stdout.write(self.style.SUCCESS("API: login y archivo privado verificados; datos de prueba revertidos."))
