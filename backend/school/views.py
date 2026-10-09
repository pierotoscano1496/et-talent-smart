import csv
import hmac
import uuid
from datetime import date

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import connection, transaction, IntegrityError
from django.db.models import Q
from django.http import FileResponse, HttpResponse, JsonResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes, authentication_classes, action, throttle_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from minio.error import S3Error
from urllib3.exceptions import HTTPError
from .models import User, AccessToken, Classroom, Course, Schedule, Attendance, RFIDReading, Incident, StoredFile
from .serializers import (UserSerializer, ClassroomSerializer, CourseSerializer, ScheduleSerializer,
                          AttendanceSerializer, IncidentSerializer, FileSerializer)
from .storage import client as storage_client


class Administrator(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and (request.user.is_superuser or request.user.role == User.Role.ADMIN))


class Coordinator(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == User.Role.COORDINATOR)


def visible_students(user):
    students = User.objects.filter(role=User.Role.STUDENT)
    if user.role == User.Role.AUXILIARY:
        return students
    if user.role == User.Role.TEACHER:
        return students.filter(classroom__course__teacher=user).distinct()
    if user.role == User.Role.STUDENT:
        return students.filter(pk=user.pk)
    if user.role == User.Role.PARENT:
        return students.filter(guardians=user)
    return students.none()


def public_user(user):
    return {"id": user.pk, "email": user.email, "name": user.get_full_name() or user.email, "role": user.role}


def live(request):
    return JsonResponse({"status": "ok"})


def ready(request):
    try:
        connection.ensure_connection()
        # Read a migrated table, so an unmigrated database cannot be marked ready.
        User.objects.exists()
        if not storage_client().bucket_exists(settings.MINIO_BUCKET):
            raise RuntimeError("Storage not initialized")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


class Login(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        if not isinstance(email, str) or not isinstance(password, str):
            raise ValidationError("Credenciales inválidas.")
        candidate = User.objects.filter(email__iexact=email.strip()).first()
        user = authenticate(username=candidate.username if candidate else email, password=password)
        if user is None:
            return Response({"detail": "Credenciales inválidas o cuenta no disponible."}, status=401)
        return Response({"token": AccessToken.issue(user), "user": public_user(user)})


@api_view(["GET"])
def me(request):
    return Response(public_user(request.user))


@api_view(["POST"])
def logout(request):
    request.auth.delete()
    return Response(status=204)


class UserViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    permission_classes = [Administrator]

    def get_queryset(self):
        result = super().get_queryset()
        if self.request.query_params.get("role"):
            result = result.filter(role=self.request.query_params["role"])
        search = self.request.query_params.get("search", "").strip()
        if search:
            result = result.filter(Q(email__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search))
        return result


class ClassroomViewSet(viewsets.ModelViewSet):
    queryset = Classroom.objects.all().order_by("year", "grade", "section")
    serializer_class = ClassroomSerializer
    permission_classes = [Coordinator]

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        classroom = self.get_object()
        student = User.objects.filter(pk=request.data.get("student_id"), role=User.Role.STUDENT).first()
        if not student:
            raise ValidationError("Estudiante no encontrado.")
        student.classroom = classroom
        student.save(update_fields=["classroom"])
        return Response({"student_id": student.pk, "classroom": classroom.pk})


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by("id")
    serializer_class = CourseSerializer
    permission_classes = [Coordinator]


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all().order_by("id")
    serializer_class = ScheduleSerializer
    permission_classes = [Coordinator]

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        with transaction.atomic():
            schedule = Schedule.objects.select_for_update().get(pk=self.get_object().pk)
            validation = ScheduleSerializer(schedule, data={"draft": schedule.draft}, partial=True)
            validation.is_valid(raise_exception=True)
            blocks = validation.validated_data["draft"]
            for i, block in enumerate(blocks):
                if any(block["day"] == other["day"] and block["start"] < other["end"] and other["start"] < block["end"]
                       for other in blocks[i + 1:]):
                    raise ValidationError("Hay bloques superpuestos. Corrige el borrador antes de publicar.")
            schedule.published = blocks
            schedule.published_at = timezone.now()
            schedule.save(update_fields=["published", "published_at"])
        return Response(ScheduleSerializer(schedule).data)


def personal_schedules(user):
    if user.role == User.Role.STUDENT:
        qs = Schedule.objects.filter(classroom_id=user.classroom_id)
    elif user.role == User.Role.TEACHER:
        qs = Schedule.objects.filter(classroom__course__teacher=user).distinct()
    else:
        qs = Schedule.objects.none()
    result = []
    own_courses = set(Course.objects.filter(teacher=user).values_list("id", flat=True))
    for schedule in qs.exclude(published=None).select_related("classroom"):
        blocks = schedule.published
        if user.role == User.Role.TEACHER:
            blocks = [b for b in blocks if b.get("course_id") in own_courses or b["kind"] != "curso"]
        course_names = dict(Course.objects.filter(classroom=schedule.classroom).values_list("id", "name"))
        blocks = [{**b, "title": b.get("title") or course_names.get(b.get("course_id"), b["kind"])} for b in blocks]
        result.append({"classroom": str(schedule.classroom), "blocks": blocks, "published_at": schedule.published_at})
    return result


@api_view(["GET"])
def my_schedule(request):
    return Response(personal_schedules(request.user))


def filtered_records(request, model):
    allowed = visible_students(request.user)
    qs = model.objects.filter(student__in=allowed)
    student_id = request.query_params.get("student")
    if student_id:
        if not student_id.isdigit() or not allowed.filter(pk=student_id).exists():
            raise PermissionDenied("No tienes acceso a este estudiante.")
        qs = qs.filter(student_id=student_id)
    for key in ("grade", "section"):
        if request.query_params.get(key):
            qs = qs.filter(**{f"student__classroom__{key}": request.query_params[key]})
    start, end = request.query_params.get("start"), request.query_params.get("end")
    try:
        start = date.fromisoformat(start) if start else None
        end = date.fromisoformat(end) if end else None
    except ValueError:
        raise ValidationError("Las fechas deben tener formato AAAA-MM-DD.")
    if start and end and start > end:
        raise ValidationError("El fin debe ser posterior o igual al inicio.")
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)
    return qs.select_related("student").order_by("-date", "student_id")


class AttendanceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        return filtered_records(self.request, Attendance)

    @action(detail=False, methods=["get"])
    def export(self, request):
        if request.user.role not in (User.Role.AUXILIARY, User.Role.TEACHER):
            raise PermissionDenied()
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="asistencias.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["Fecha", "Estudiante ID", "Estudiante", "Primera marcación", "Incidencias"])
        def safe(value):
            text = str(value)
            return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
        incidents = {}
        for incident in filtered_records(request, Incident):
            incidents.setdefault((incident.student_id, incident.date), []).append(incident.kind)
        for row in self.get_queryset():
            writer.writerow([row.date, row.student_id, safe(row.student.get_full_name()),
                             timezone.localtime(row.first_seen).isoformat(),
                             ", ".join(incidents.get((row.student_id, row.date), []))])
        # Justified absences have no RFID attendance but still belong in the report.
        recorded = set(self.get_queryset().values_list("student_id", "date"))
        for incident in filtered_records(request, Incident):
            key = (incident.student_id, incident.date)
            if key not in recorded:
                writer.writerow([incident.date, incident.student_id, safe(incident.student.get_full_name()),
                                 "", ", ".join(incidents[key])])
                recorded.add(key)
        return response


class IncidentViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = IncidentSerializer

    def get_queryset(self):
        return filtered_records(self.request, Incident)

    def perform_create(self, serializer):
        if not visible_students(self.request.user).filter(pk=serializer.validated_data["student"].pk).exists():
            raise PermissionDenied()
        try:
            with transaction.atomic():
                serializer.save(created_by=self.request.user)
        except IntegrityError:
            raise ValidationError("La incidencia ya existe.")


def check_key(request, setting, header):
    expected = getattr(settings, setting)
    if not expected or not hmac.compare_digest(request.headers.get(header, ""), expected):
        raise PermissionDenied("Credencial de servicio inválida.")


@api_view(["GET"])
def assistant_context(request):
    check_key(request, "TALENTOSITO_SERVICE_KEY", "X-Service-Key")
    return Response({"user": public_user(request.user), "schedules": personal_schedules(request.user)})


class FileViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = FileSerializer

    def get_queryset(self):
        return StoredFile.objects.filter(owner=self.request.user).order_by("-created_at")

    def create(self, request):
        upload = request.FILES.get("file")
        if not upload or upload.size > settings.MAX_FILE_SIZE:
            raise ValidationError("Adjunta un archivo de hasta 10 MiB.")
        name = upload.name[:200]
        object_name = f"{request.user.pk}/{uuid.uuid4().hex}"
        try:
            storage_client().put_object(settings.MINIO_BUCKET, object_name, upload, upload.size,
                                        content_type="application/octet-stream")
        except (S3Error, HTTPError):
            return Response({"detail": "No se pudo guardar el archivo."}, status=503)
        record = StoredFile.objects.create(owner=request.user, object_name=object_name,
                                           filename=name, size=upload.size, content_type="application/octet-stream")
        return Response(FileSerializer(record).data, status=201)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        record = self.get_object()
        try:
            stream = storage_client().get_object(settings.MINIO_BUCKET, record.object_name)
        except (S3Error, HTTPError):
            return Response({"detail": "Archivo no disponible."}, status=503)
        def chunks():
            try:
                yield from stream.stream(64 * 1024)
            finally:
                stream.close()
                stream.release_conn()
        return FileResponse(chunks(), as_attachment=True, filename=record.filename,
                            content_type="application/octet-stream")
