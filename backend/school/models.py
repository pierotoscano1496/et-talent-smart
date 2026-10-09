import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


class Classroom(models.Model):
    year = models.PositiveIntegerField()
    grade = models.CharField(max_length=40)
    section = models.CharField(max_length=40)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["year", "grade", "section"], name="unique_classroom")]

    def __str__(self):
        return f"{self.year} / {self.grade} / {self.section}"


class SchoolUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "administrador")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "administrador", "Administrador"
        AUXILIARY = "auxiliar", "Auxiliar"
        COORDINATOR = "coordinador", "Coordinador"
        TEACHER = "docente", "Docente"
        STUDENT = "estudiante", "Estudiante"
        PARENT = "padre", "Padre de familia"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    classroom = models.ForeignKey(Classroom, null=True, blank=True, on_delete=models.PROTECT)
    children = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="guardians")
    rfid_uid = models.CharField(max_length=64, unique=True, null=True, blank=True)
    objects = SchoolUserManager()


class AccessToken(models.Model):
    digest = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    expires_at = models.DateTimeField()

    @classmethod
    def issue(cls, user):
        raw = secrets.token_urlsafe(48)
        cls.objects.create(digest=hashlib.sha256(raw.encode()).hexdigest(), user=user,
                           expires_at=timezone.now() + timedelta(hours=settings.TOKEN_HOURS))
        return raw


class Course(models.Model):
    name = models.CharField(max_length=120)
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT)
    teacher = models.ForeignKey(User, on_delete=models.PROTECT, limit_choices_to={"role": "docente"})

    def __str__(self):
        return self.name


class Schedule(models.Model):
    classroom = models.OneToOneField(Classroom, on_delete=models.PROTECT)
    draft = models.JSONField(default=list)
    published = models.JSONField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)


class RFIDReading(models.Model):
    uid = models.CharField(max_length=64)
    student = models.ForeignKey(User, null=True, on_delete=models.PROTECT)
    device_id = models.CharField(max_length=100)
    location_id = models.CharField(max_length=100)
    authorized = models.BooleanField()
    recorded_at = models.DateTimeField(default=timezone.now)
    event_id = models.CharField(max_length=128, null=True, blank=True)
    wifi_rssi = models.SmallIntegerField(null=True, blank=True)
    uptime_ms = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["device_id", "event_id"], name="unique_rfid_device_event")]


class RFIDDeviceState(models.Model):
    device_id = models.CharField(max_length=100, primary_key=True)
    location_id = models.CharField(max_length=100)
    state = models.CharField(max_length=16, choices=[("abierta", "Abierta"), ("cerrada", "Cerrada")])
    reported_at = models.DateTimeField(default=timezone.now)


class Attendance(models.Model):
    student = models.ForeignKey(User, on_delete=models.PROTECT)
    date = models.DateField()
    first_seen = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "date"], name="one_attendance_per_day")]


class Incident(models.Model):
    class Kind(models.TextChoices):
        JUSTIFIED = "falta_justificada", "Falta justificada"
        EARLY_EXIT = "retiro_temprano", "Retiro temprano"
    student = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidents")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    date = models.DateField()
    exit_time = models.TimeField(null=True, blank=True)
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "date", "kind"], name="unique_daily_incident")]


class StoredFile(models.Model):
    owner = models.ForeignKey(User, on_delete=models.PROTECT)
    object_name = models.CharField(max_length=200, unique=True)
    filename = models.CharField(max_length=200)
    size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
