from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.exceptions import APIException
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from .models import Attendance, RFIDReading, RFIDDeviceState, User
from .views import check_key


class EventConflict(APIException):
    status_code = 409
    default_detail = "El identificador de evento ya corresponde a otra lectura."


class Auxiliary(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == User.Role.AUXILIARY)


class RFIDOperator(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and (
            request.user.is_superuser or request.user.role in (User.Role.ADMIN, User.Role.AUXILIARY)))


class ReadingInput(serializers.Serializer):
    uid = serializers.CharField(max_length=64)
    device_id = serializers.CharField(max_length=100, default="unknown")
    location_id = serializers.CharField(max_length=100, default="unknown")
    event_id = serializers.CharField(max_length=128, required=False, allow_null=True)
    wifi_rssi = serializers.IntegerField(min_value=-127, max_value=0, required=False, allow_null=True)
    millis = serializers.IntegerField(min_value=0, max_value=4294967295, required=False, allow_null=True)

    def validate_uid(self, value):
        return value.strip().upper()


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def register_reading(request):
    check_key(request, "RFID_API_KEY", "X-API-KEY")
    payload = ReadingInput(data=request.data)
    payload.is_valid(raise_exception=True)
    data = payload.validated_data
    now = timezone.now()
    with transaction.atomic():
        student = User.objects.filter(rfid_uid=data["uid"], role=User.Role.STUDENT, is_active=True).first()
        values = dict(uid=data["uid"], student=student, authorized=bool(student),
                      location_id=data["location_id"], recorded_at=now,
                      wifi_rssi=data.get("wifi_rssi"), uptime_ms=data.get("millis"))
        event_id = data.get("event_id")
        if event_id:
            reading, created = RFIDReading.objects.get_or_create(
                device_id=data["device_id"], event_id=event_id, defaults=values)
            if reading.uid != data["uid"] or reading.location_id != data["location_id"]:
                raise EventConflict()
        else:
            reading = RFIDReading.objects.create(device_id=data["device_id"], **values)
            created = True
        # Replayed requests never create attendance on a different day, or reauthorize a revoked key.
        authorized = bool(reading.authorized and student and reading.student_id == student.pk)
        attendance_date = timezone.localtime(reading.recorded_at).date()
        attendance_created = False
        if created and authorized:
            _, attendance_created = Attendance.objects.get_or_create(
                student=student, date=attendance_date, defaults={"first_seen": reading.recorded_at})
    return Response({
        "ok": True, "authorized": authorized, "reading_id": reading.pk, "replayed": not created,
        "attendance_date": attendance_date if reading.authorized else None,
        "attendance_created": attendance_created,
        "usuario": {"nombre": student.get_full_name(), "rol": student.role} if authorized else None,
    })


class ReadingSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    def get_student_name(self, obj):
        return obj.student.get_full_name() if obj.student else "No identificado"

    class Meta:
        model = RFIDReading
        fields = ["id", "uid", "student", "student_name", "device_id", "location_id",
                  "authorized", "recorded_at", "event_id", "wifi_rssi", "uptime_ms"]


class ReadingList(ListAPIView):
    serializer_class = ReadingSerializer
    permission_classes = [Auxiliary]

    def get_queryset(self):
        rows = RFIDReading.objects.select_related("student").order_by("-recorded_at", "-id")
        if self.request.query_params.get("device_id"):
            rows = rows.filter(device_id=self.request.query_params["device_id"])
        return rows


@api_view(["GET"])
@permission_classes([Auxiliary])
def summary(request):
    today = timezone.localdate()
    readings = RFIDReading.objects.filter(recorded_at__date=today)
    return Response({
        "date": today, "readings": readings.count(),
        "allowed": readings.filter(authorized=True).count(),
        "denied": readings.filter(authorized=False).count(),
        "attendance": Attendance.objects.filter(date=today).count(),
    })


@api_view(["GET"])
@permission_classes([RFIDOperator])
def devices(request):
    return Response(list(RFIDDeviceState.objects.order_by("device_id").values(
        "device_id", "location_id", "state", "reported_at")))


class DoorInput(serializers.Serializer):
    device_id = serializers.CharField(max_length=100)
    location_id = serializers.CharField(max_length=100)
    state = serializers.ChoiceField(choices=["abierta", "cerrada"])


def save_report(request, closed=False):
    check_key(request, "RFID_API_KEY", "X-API-KEY")
    raw = request.data.copy()
    if closed:
        raw["state"] = "cerrada"
    serializer = DoorInput(data=raw)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    device, _ = RFIDDeviceState.objects.update_or_create(device_id=data.pop("device_id"),
                                                        defaults={**data, "reported_at": timezone.now()})
    return Response({"ok": True, "device_id": device.pk, "state": device.state, "reported_at": device.reported_at})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def report_door(request):
    return save_report(request)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def report_closed(request):
    return save_report(request, closed=True)

