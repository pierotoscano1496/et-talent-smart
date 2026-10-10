import os
from datetime import datetime, time
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
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
        sql = (Path(__file__).resolve().parents[2] / "sql" / "dev_user.sql").read_text(encoding="utf-8")
        for name, email, role, first, last in [
            ("admin", "admin@demo.talentsmart.test", "administrador", "Administrador", "Demo"),
            ("coordinador", "coordinador@demo.talentsmart.test", "coordinador", "Pabel", "Valeriano"),
            ("docente", "elvisp@demo.talentsmart.test", "docente", "Elvis", "Perez"),
            ("docente2", "afachin@escuelatalentos.edu.pe", "docente", "Anthony", "Fachín"),
            ("auxiliar", "cesar@demo.talentsmart.test", "auxiliar", "César", ""),
            ("estudiante", "tliao@demo.talentsmart.test", "estudiante", "Tomiko", "Liao"),
            ("estudiante2", "mtinco@demo.talentsmart.test", "estudiante", "María", "Tinco"),
            ("estudiante3", "alopez@escuelatalentos.edu.pe", "estudiante", "Andrés", "López"),
            ("padre", "alopez@gmail.com", "padre", "Apoderado de Andrés", "López"),
        ]:
            user = User.objects.filter(email=email).first()
            if user:
                if user.role != role:
                    raise CommandError(f"La cuenta {email} existe con otro rol; no se modificó.")
                self.stdout.write(f"Se conserva {email}, incluida su contraseña.")
            else:
                if User.objects.filter(username=email).exists():
                    raise CommandError(f"El identificador {email} ya está ocupado.")
                with connection.cursor() as cursor:
                    cursor.execute(sql, {
                        "email": email, "password_hash": make_password("TalentDev!2026"),
                        "role": role, "first": first, "last": last,
                        "classroom_id": group.pk if role == "estudiante" else None,
                        "joined": timezone.now(),
                    })
                user = User.objects.get(email=email)
                if role == "padre":
                    user.children.add(accounts["estudiante3"])
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
