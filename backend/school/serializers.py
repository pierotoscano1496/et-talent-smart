from datetime import time
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import User, Classroom, Course, Schedule, Attendance, Incident, StoredFile


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "classroom", "children", "rfid_uid", "is_active", "password"]
        read_only_fields = ["classroom"]

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return value

    def validate_rfid_uid(self, value):
        value = value.strip().upper() if value else None
        if value and User.objects.filter(rfid_uid=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("La llave ya está asignada.")
        return value

    def validate(self, attrs):
        if "classroom" in self.initial_data:
            raise serializers.ValidationError({"classroom": "La asignación de grado y sección corresponde al coordinador."})
        role = attrs.get("role", getattr(self.instance, "role", None))
        if attrs.get("children") and role != User.Role.PARENT:
            raise serializers.ValidationError({"children": "Solo los padres de familia pueden vincular hijos."})
        if any(child.role != User.Role.STUDENT for child in attrs.get("children", [])):
            raise serializers.ValidationError({"children": "Selecciona únicamente estudiantes."})
        if self.instance and role != self.instance.role:
            if self.instance.is_superuser:
                raise serializers.ValidationError("El rol del superusuario se gestiona desde Django admin.")
            if role != User.Role.STUDENT:
                attrs["rfid_uid"] = None
                attrs["classroom"] = None
            if role != User.Role.PARENT:
                attrs["children"] = []
        if attrs.get("rfid_uid") and attrs.get("role", getattr(self.instance, "role", None)) != User.Role.STUDENT:
            raise serializers.ValidationError("Las llaves de asistencia se asignan a estudiantes.")
        return attrs

    def create(self, validated_data):
        children = validated_data.pop("children", [])
        password = validated_data.pop("password")
        user = User.objects.create_user(username=validated_data["email"], password=password, **validated_data)
        user.children.set(children)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if "email" in validated_data:
            validated_data["username"] = validated_data["email"]
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class ClassroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = "__all__"


class DirectorySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="get_full_name", read_only=True)
    grade = serializers.CharField(source="classroom.grade", default="", read_only=True)
    section = serializers.CharField(source="classroom.section", default="", read_only=True)
    year = serializers.IntegerField(source="classroom.year", default=None, read_only=True)

    class Meta:
        model = User
        fields = ["id", "name", "role", "classroom", "grade", "section", "year", "is_active"]


class EventInput(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2200)
    all_classrooms = serializers.BooleanField(default=False)
    classroom_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)
    day = serializers.IntegerField(min_value=0, max_value=6)
    start = serializers.TimeField(format="%H:%M")
    end = serializers.TimeField(format="%H:%M")
    title = serializers.CharField(max_length=120)
    room = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate(self, data):
        if not time(7, 30) <= data["start"] < data["end"] <= time(16, 30):
            raise serializers.ValidationError("El evento debe estar entre 07:30 y 16:30.")
        if bool(data["all_classrooms"]) == bool(data.get("classroom_ids")):
            raise serializers.ValidationError("Selecciona algunos grupos o todos los del año, no ambos.")
        return data


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"

    def validate_teacher(self, value):
        if value.role != User.Role.TEACHER:
            raise serializers.ValidationError("Selecciona un docente.")
        return value


class BlockSerializer(serializers.Serializer):
    day = serializers.IntegerField(min_value=0, max_value=6)
    start = serializers.TimeField(format="%H:%M")
    end = serializers.TimeField(format="%H:%M")
    kind = serializers.ChoiceField(choices=["curso", "receso", "almuerzo", "evento"])
    course_id = serializers.IntegerField(required=False, allow_null=True)
    title = serializers.CharField(max_length=120, required=False, allow_blank=True)
    room = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate(self, data):
        if not time(7, 30) <= data["start"] < data["end"] <= time(16, 30):
            raise serializers.ValidationError("El bloque debe estar entre 07:30 y 16:30, con fin posterior al inicio.")
        if data["kind"] == "curso" and not data.get("course_id"):
            raise serializers.ValidationError("Selecciona un curso.")
        if data["kind"] != "curso" and data.get("course_id"):
            raise serializers.ValidationError("Solo los bloques académicos llevan curso.")
        return data


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = "__all__"
        read_only_fields = ["published", "published_at"]

    def validate(self, attrs):
        classroom = attrs.get("classroom", getattr(self.instance, "classroom", None))
        blocks = attrs.get("draft", getattr(self.instance, "draft", []))
        if not isinstance(blocks, list):
            raise serializers.ValidationError({"draft": "Se espera una lista de bloques."})
        parsed = BlockSerializer(data=blocks, many=True)
        parsed.is_valid(raise_exception=True)
        for block in parsed.validated_data:
            if block.get("course_id") and not Course.objects.filter(pk=block["course_id"], classroom=classroom).exists():
                raise serializers.ValidationError({"draft": "El curso no pertenece al grado y sección."})
        attrs["draft"] = list(parsed.data)
        return attrs


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    class Meta:
        model = Attendance
        fields = "__all__"


class IncidentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    class Meta:
        model = Incident
        fields = "__all__"
        read_only_fields = ["created_by", "created_at"]
        # Validate uniqueness explicitly; created_by is server-owned.
        validators = []

    def validate(self, attrs):
        role = self.context["request"].user.role
        if attrs["student"].role != User.Role.STUDENT:
            raise serializers.ValidationError("Selecciona un estudiante.")
        allowed = {User.Role.TEACHER: Incident.Kind.JUSTIFIED, User.Role.AUXILIARY: Incident.Kind.EARLY_EXIT}
        if allowed.get(role) != attrs["kind"]:
            raise serializers.ValidationError("Tu rol no puede registrar esta incidencia.")
        if attrs["kind"] == Incident.Kind.EARLY_EXIT and not attrs.get("exit_time"):
            raise serializers.ValidationError({"exit_time": "La hora de salida es obligatoria."})
        if Incident.objects.filter(student=attrs["student"], date=attrs["date"], kind=attrs["kind"]).exists():
            raise serializers.ValidationError("Ya existe esta incidencia para el estudiante y día.")
        return attrs


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredFile
        fields = ["id", "filename", "size", "content_type", "created_at"]
