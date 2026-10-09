from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import User, Classroom, Course, Schedule, AccessToken, Attendance, RFIDReading, Incident, StoredFile


@override_settings(RFID_API_KEY="test-rfid", TALENTOSITO_SERVICE_KEY="test-service")
class APITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.group = Classroom.objects.create(year=2026, grade="4", section="A")
        self.other_group = Classroom.objects.create(year=2026, grade="5", section="B")
        self.student = self.user("student", "estudiante", classroom=self.group, rfid_uid="AABB")
        self.other = self.user("other", "estudiante", classroom=self.other_group)
        self.teacher = self.user("teacher", "docente")
        self.coordinator = self.user("coord", "coordinador")
        self.auxiliary = self.user("aux", "auxiliar")
        self.course = Course.objects.create(name="Robótica", classroom=self.group, teacher=self.teacher)

    def user(self, name, role, **kwargs):
        return User.objects.create_user(username=name, email=f"{name}@example.org",
                                        password="a-strong-test-password", role=role, **kwargs)

    def login_as(self, user):
        token = AccessToken.issue(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return token

    def test_login_rejects_invalid_or_inactive_account_and_logout_revokes_token(self):
        result = self.client.post("/api/auth/login/", {"email": self.student.email, "password": "wrong"})
        self.assertEqual(result.status_code, 401)
        result = self.client.post("/api/auth/login/", {"email": self.student.email, "password": "a-strong-test-password"})
        self.assertEqual(result.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + result.data["token"])
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)
        self.client.post("/api/auth/logout/")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        self.student.is_active = False
        self.student.save()
        self.client.credentials()
        self.assertEqual(self.client.post("/api/auth/login/", {
            "email": self.student.email, "password": "a-strong-test-password",
        }).status_code, 401)

    def test_expired_token_is_rejected(self):
        self.login_as(self.student)
        AccessToken.objects.update(expires_at=timezone.now())
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_student_cannot_create_users_or_read_other_student_records(self):
        self.login_as(self.student)
        self.assertEqual(self.client.post("/api/users/", {}).status_code, 403)
        self.assertEqual(self.client.get(f"/api/attendance/?student={self.other.pk}").status_code, 403)

    def test_rfid_authentication_daily_deduplication_and_lima_date(self):
        self.assertEqual(self.client.post("/api/rfid/registro", {"uid": "AABB"}).status_code, 403)
        now = datetime(2026, 10, 9, 2, 0, tzinfo=dt_timezone.utc)
        with patch("school.views.timezone.now", return_value=now):
            for _ in range(2):
                response = self.client.post("/api/rfid/registro", {"uid": "aabb"}, HTTP_X_API_KEY="test-rfid")
                self.assertTrue(response.data["authorized"])
        self.assertEqual(Attendance.objects.count(), 1)
        self.assertEqual(RFIDReading.objects.count(), 2)
        self.assertEqual(Attendance.objects.get().date.isoformat(), "2026-10-08")

    def test_unknown_rfid_does_not_create_attendance(self):
        result = self.client.post("/api/rfid/registro", {"uid": "UNKNOWN"}, HTTP_X_API_KEY="test-rfid")
        self.assertFalse(result.data["authorized"])
        self.assertFalse(Attendance.objects.exists())

    def test_teacher_is_scoped_and_exports_same_filters(self):
        now = timezone.now()
        for student in (self.student, self.other):
            Attendance.objects.create(student=student, date="2026-10-08", first_seen=now)
        self.login_as(self.teacher)
        result = self.client.get("/api/attendance/?start=2026-10-08&end=2026-10-08")
        self.assertEqual(result.data["count"], 1)
        result = self.client.get("/api/attendance/export/?grade=5")
        self.assertEqual(len(result.content.decode("utf-8-sig").splitlines()), 1)
        self.assertEqual(self.client.get("/api/attendance/?start=2026-10-09&end=2026-10-08").status_code, 400)

    def test_incident_roles_and_preservation_of_original_readings(self):
        payload = {"student": self.student.pk, "date": "2026-10-08", "kind": "retiro_temprano", "exit_time": "12:00"}
        self.login_as(self.teacher)
        self.assertEqual(self.client.post("/api/incidents/", payload).status_code, 400)
        self.login_as(self.auxiliary)
        self.assertEqual(self.client.post("/api/incidents/", payload).status_code, 201)
        self.assertEqual(self.client.post("/api/incidents/", payload).status_code, 400)
        self.assertEqual(Incident.objects.count(), 1)

    def test_schedule_publication_is_validated_and_draft_does_not_leak(self):
        self.login_as(self.coordinator)
        block = {"day": 0, "start": "08:00", "end": "09:00", "kind": "curso", "course_id": self.course.pk}
        result = self.client.post("/api/schedules/", {"classroom": self.group.pk, "draft": [block]}, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        pk = result.data["id"]
        self.assertEqual(self.client.post(f"/api/schedules/{pk}/publish/").status_code, 200)
        self.client.patch(f"/api/schedules/{pk}/", {"draft": [block, block]}, format="json")
        self.assertEqual(self.client.post(f"/api/schedules/{pk}/publish/").status_code, 400)
        self.login_as(self.student)
        result = self.client.get("/api/my-schedule/")
        self.assertEqual(len(result.data[0]["blocks"]), 1)
        self.login_as(self.other)
        self.assertEqual(self.client.get("/api/my-schedule/").data, [])

    def test_file_access_is_owner_scoped(self):
        file = StoredFile.objects.create(owner=self.other, object_name="other/object", filename="private.txt", size=1)
        self.login_as(self.student)
        self.assertEqual(self.client.get(f"/api/files/{file.pk}/download/").status_code, 404)

    def test_assistant_requires_both_user_session_and_service_key(self):
        self.assertEqual(self.client.get("/api/talentosito/context/", HTTP_X_SERVICE_KEY="test-service").status_code, 401)
        self.login_as(self.student)
        self.assertEqual(self.client.get("/api/talentosito/context/").status_code, 403)
        result = self.client.get("/api/talentosito/context/", HTTP_X_SERVICE_KEY="test-service")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["user"]["id"], self.student.pk)
