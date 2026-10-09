import sys
import tarfile
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from school.storage import client


class Command(BaseCommand):
    help = "Restore object contents from a tar stream. Does not delete other objects or extract to disk."

    def handle(self, *args, **options):
        storage = client()
        with tarfile.open(fileobj=sys.stdin.buffer, mode="r|*") as archive:
            for member in archive:
                if not member.isfile() or member.name.startswith("/") or ".." in member.name.split("/"):
                    raise CommandError("Entrada de respaldo no válida.")
                storage.put_object(settings.MINIO_BUCKET, member.name, archive.extractfile(member), member.size,
                                   content_type="application/octet-stream")

