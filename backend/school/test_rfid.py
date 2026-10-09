from datetime import datetime, timezone as utc
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Attendance, RFIDDeviceState, RFIDReading, User


@override_settings(RFID_API_KEY="test-device-key")
class RFIDIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(username="student", email="student@example.org",
                                                role="estudiante", rfid_uid="AABB")
        self.admin = User.objects.create_user(username="admin", email="admin@example.org", role="administrador")
        self.auxiliary = User.objects.create_user(username="aux", email="aux@example.org", role="auxiliar")
        self.event = {"uid": "aabb", "device_id": "gate-1", "location_id": "entrance", "event_id": "boot-1-1"}

    def reading(self, **changes):
        return self.client.post("/api/rfid/registro", {**self.event, **changes}, format="json",
                                HTTP_X_API_KEY="test-device-key")

    def test_retry_retains_original_day_and_single_reading(self):
        with patch("school.rfid.timezone.now", return_value=datetime(2026, 10, 9, 2, tzinfo=utc.utc)):
            first = self.reading()
        with patch("school.rfid.timezone.now", return_value=datetime(2026, 10, 10, 2, tzinfo=utc.utc)):
            replay = self.reading()
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.data["attendance_created"])
        self.assertTrue(replay.data["replayed"])
        self.assertFalse(replay.data["attendance_created"])
        self.assertEqual(first.data["reading_id"], replay.data["reading_id"])
        self.assertEqual(RFIDReading.objects.count(), 1)
        self.assertEqual(Attendance.objects.get().date.isoformat(), "2026-10-08")

    def test_event_conflict_does_not_change_saved_reading(self):
        self.reading()
        self.assertEqual(self.reading(uid="CCDD").status_code, 409)
        self.assertEqual(self.reading(location_id="elsewhere").status_code, 409)
        self.assertEqual(RFIDReading.objects.get().uid, "AABB")

    def test_revoked_and_reassigned_keys_do_not_reauthorize_old_event(self):
        self.reading()
        self.student.rfid_uid = None
        self.student.save()
        self.assertFalse(self.reading().data["authorized"])
        User.objects.create_user(username="other", email="other@example.org", role="estudiante", rfid_uid="AABB")
        self.assertFalse(self.reading().data["authorized"])
        self.assertEqual(Attendance.objects.count(), 1)

    def test_inactive_student_is_denied(self):
        self.student.is_active = False
        self.student.save()
        self.assertFalse(self.reading().data["authorized"])
        self.assertFalse(Attendance.objects.exists())

    def test_bad_device_auth_or_payload_does_not_store_reading(self):
        self.assertEqual(self.client.post("/api/rfid/registro", self.event).status_code, 403)
        self.assertEqual(self.reading(wifi_rssi=1).status_code, 400)
        self.assertEqual(self.reading(uid="").status_code, 400)
        self.assertFalse(RFIDReading.objects.exists())

    def test_monitoring_is_auxiliary_only(self):
        self.reading()
        for user in (self.student, self.admin):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get("/api/rfid/readings/").status_code, 403)
            self.assertEqual(self.client.get("/api/rfid/summary/").status_code, 403)
        self.client.force_authenticate(self.auxiliary)
        self.assertEqual(self.client.get("/api/rfid/readings/").data["count"], 1)
        self.assertEqual(self.client.get("/api/rfid/readings/?device_id=unknown").data["count"], 0)
        self.assertEqual(self.client.get("/api/rfid/summary/").data["attendance"], 1)

    def test_door_telemetry_needs_device_key_and_never_marks_attendance(self):
        body = {"device_id": "gate-1", "location_id": "entrance", "state": "abierta"}
        self.assertEqual(self.client.post("/api/puerta/estado", body).status_code, 403)
        response = self.client.post("/api/puerta/estado", body, HTTP_X_API_KEY="test-device-key")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RFIDDeviceState.objects.get().state, "abierta")
        response = self.client.post("/api/puerta/cerrar", body, HTTP_X_API_KEY="test-device-key")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RFIDDeviceState.objects.get().state, "cerrada")
        self.assertFalse(RFIDReading.objects.exists())
        self.assertFalse(Attendance.objects.exists())
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get("/api/rfid/devices/").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/rfid/devices/").status_code, 200)

    def test_only_admin_assigns_unique_normalized_keys(self):
        path = f"/api/users/{self.student.pk}/"
        self.client.force_authenticate(self.auxiliary)
        self.assertEqual(self.client.patch(path, {"rfid_uid": "ccdd"}).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(path, {"rfid_uid": "ccdd"}).status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.rfid_uid, "CCDD")
        other = User.objects.create_user(username="other", email="other@example.org", role="estudiante")
        self.assertEqual(self.client.patch(f"/api/users/{other.pk}/", {"rfid_uid": "ccdd"}).status_code, 400)
        self.assertEqual(self.client.get("/api/users/?role=estudiante&search=student@").data["count"], 1)
        self.assertEqual(self.client.patch(path, {"rfid_uid": None}, format="json").status_code, 200)
