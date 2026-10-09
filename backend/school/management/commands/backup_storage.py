import sys
import tarfile
from django.conf import settings
from django.core.management.base import BaseCommand
from school.storage import client


class Command(BaseCommand):
    help = "Export the private bucket as a tar stream to stdout (redirect to a protected file)."

    def handle(self, *args, **options):
        storage = client()
        with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as archive:
            for obj in storage.list_objects(settings.MINIO_BUCKET, recursive=True):
                response = storage.get_object(settings.MINIO_BUCKET, obj.object_name)
                try:
                    info = tarfile.TarInfo(obj.object_name)
                    info.size = obj.size
                    archive.addfile(info, response)
                finally:
                    response.close()
                    response.release_conn()

