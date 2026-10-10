import os
from datetime import datetime, time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from school.models import Attendance, Classroom, Course, Schedule, User


class Command(BaseCommand):
    help = "Crea cuentas y datos ficticios solo en dev, sin sobrescribir registros existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        if (settings.SETTINGS_MODULE != "config.settings.dev" or not settings.DEBUG
                or os.getenv("APP_ENV") != "dev"):
            raise CommandError("Los datos de prueba solo pueden crearse en el ambiente dev.")
        group, _ = Classroom.objects.get_or_create(year=timezone.localdate().year, grade="4", section="A")
        Classroom.objects.get_or_create(year=timezone.localdate().year, grade="4", section="B")
        accounts = {}
        for name, role, first, last in [
            ("admin", "administrador", "Administrador", "Demo"),
            ("coordinador", "coordinador", "Coordinación", "Demo"),
            ("docente", "docente", "Lucía", "Docente Demo"),
            ("auxiliar", "auxiliar", "Daniel", "Auxiliar Demo"),
            ("estudiante", "estudiante", "Alex", "Estudiante Demo"),
            ("estudiante2", "estudiante", "Sam", "Estudiante Demo"),
            ("padre", "padre", "Andrea", "Familia Demo"),
        ]:
            email = f"{name}@demo.talentsmart.test"
            user = User.objects.filter(email=email).first()
            if user:
                if user.role != role:
                    raise CommandError(f"La cuenta {email} existe con otro rol; no se modificó.")
                self.stdout.write(f"Se conserva {email}, incluida su contraseña.")
            else:
                if User.objects.filter(username=email).exists():
                    raise CommandError(f"El identificador {email} ya está ocupado.")
                user = User.objects.create_user(
                    username=email, email=email, password="TalentDev!2026", role=role,
                    first_name=first, last_name=last,
                    classroom=group if role == "estudiante" else None,
                )
                if role == "padre":
                    user.children.add(accounts["estudiante"])
                self.stdout.write(self.style.SUCCESS(f"Creado: {email}"))
            accounts[name] = user
        course, _ = Course.objects.get_or_create(name="Matemática (demo)", classroom=group,
                                               teacher=accounts["docente"])
        blocks = [
            {"day": 0, "start": "07:30", "end": "09:00", "kind": "curso", "course_id": course.pk, "room": "Aula 4A"},
            {"day": 0, "start": "09:00", "end": "09:30", "kind": "receso"},
            {"day": 0, "start": "12:30", "end": "13:15", "kind": "almuerzo"},
        ]
        Schedule.objects.get_or_create(classroom=group, defaults={
            "draft": blocks, "published": blocks, "published_at": timezone.now(),
        })
        today = timezone.localdate()
        Attendance.objects.get_or_create(student=accounts["estudiante"], date=today, defaults={
            "first_seen": timezone.make_aware(datetime.combine(today, time(7, 25))),
        })
        self.stdout.write("Contraseña inicial de las cuentas NUEVAS: TalentDev!2026")
        self.stdout.write("Datos ficticios dev. No se asignaron llaves RFID reales ni permisos de superusuario.")
