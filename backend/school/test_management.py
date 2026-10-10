import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Classroom, Course, Schedule, User


class ManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username="admin", email="admin@example.org", role="administrador")
        self.coord = User.objects.create_user(username="coord", email="coord@example.org", role="coordinador")
        self.teacher = User.objects.create_user(username="teacher", email="teacher@example.org", role="docente", first_name="Lucía")
        self.group = Classroom.objects.create(year=2026, grade="4", section="A")
        self.other = Classroom.objects.create(year=2026, grade="4", section="B")
        self.student = User.objects.create_user(username="student", email="student@example.org", role="estudiante", classroom=self.group, rfid_uid="PRIVATE")
        self.stranger = User.objects.create_user(username="stranger", email="stranger@example.org", role="estudiante", classroom=self.other)
        self.course = Course.objects.create(name="Matemática", classroom=self.group, teacher=self.teacher)
        self.block = {"day": 0, "start": "07:30", "end": "09:00", "kind": "curso", "course_id": self.course.pk}

    def test_coordinator_directory_is_minimal_and_cannot_manage_accounts(self):
        self.client.force_authenticate(self.coord)
        students = self.client.get("/api/directory/").data["results"]
        self.assertEqual(len(students), 2)
        self.assertNotIn("rfid_uid", students[0])
        self.assertNotIn("email", students[0])
        self.assertEqual(self.client.get("/api/directory/?role=docente").data["count"], 1)
        self.assertEqual(self.client.get("/api/directory/?role=administrador").status_code, 403)
        self.assertEqual(self.client.get("/api/users/").status_code, 403)
        self.assertEqual(self.client.post("/api/users/", {}).status_code, 403)

    def test_teacher_and_parent_directory_never_leaks_other_students(self):
        parent = User.objects.create_user(username="parent", email="parent@example.org", role="padre")
        parent.children.add(self.student)
        for user in (self.teacher, parent, self.student):
            self.client.force_authenticate(user)
            result = self.client.get("/api/directory/?role=docente")
            self.assertEqual([row["id"] for row in result.data["results"]], [self.student.pk])

    def test_admin_cannot_assign_classroom_and_coordinator_can(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f"/api/users/{self.student.pk}/", {"classroom": self.other.pk}).status_code, 400)
        self.assertEqual(self.client.post(f"/api/classrooms/{self.other.pk}/assign/", {"student_id": self.student.pk}).status_code, 403)
        self.client.force_authenticate(self.coord)
        self.assertEqual(self.client.post(f"/api/classrooms/{self.other.pk}/assign/", {"student_id": self.student.pk}).status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.classroom_id, self.other.pk)
        self.assertEqual(self.client.post(f"/api/classrooms/{self.other.pk}/assign/", {"student_id": "invalid"}).status_code, 400)

    def test_admin_creates_normal_account_and_rejects_duplicate_email(self):
        self.client.force_authenticate(self.admin)
        body = {"email": "NEW@example.org", "password": "Example-Strong-Password9!", "role": "coordinador", "is_superuser": True}
        result = self.client.post("/api/users/", body)
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data["email"], "new@example.org")
        self.assertNotIn("password", result.data)
        self.assertFalse(User.objects.get(pk=result.data["id"]).is_superuser)
        body["email"] = "New@example.org"
        self.assertEqual(self.client.post("/api/users/", body).status_code, 400)

    def test_parent_links_only_students_and_role_change_releases_key(self):
        self.client.force_authenticate(self.admin)
        result = self.client.patch(f"/api/users/{self.student.pk}/", {"role": "padre", "children": [self.teacher.pk]}, format="json")
        self.assertEqual(result.status_code, 400)
        result = self.client.patch(f"/api/users/{self.student.pk}/", {"role": "padre", "children": [self.stranger.pk]}, format="json")
        self.assertEqual(result.status_code, 200)
        self.student.refresh_from_db()
        self.assertIsNone(self.student.rfid_uid)
        self.assertIsNone(self.student.classroom)

    def test_event_targets_drafts_and_preserves_publication(self):
        existing = Schedule.objects.create(classroom=self.group, draft=[self.block], published=[self.block])
        self.client.force_authenticate(self.coord)
        payload = {"year": 2026, "all_classrooms": True, "title": "Feria", "day": 0, "start": "14:00", "end": "15:00"}
        result = self.client.post("/api/schedules/events/", payload, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(len(result.data), 2)
        existing.refresh_from_db()
        self.assertEqual(existing.published, [self.block])
        self.assertEqual(len(existing.draft), 2)
        self.client.post("/api/schedules/events/", payload, format="json")
        existing.refresh_from_db()
        self.assertEqual(len(existing.draft), 2)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post("/api/schedules/events/", payload, format="json").status_code, 403)

    def test_invalid_event_targets_or_hours_do_not_modify_schedules(self):
        self.client.force_authenticate(self.coord)
        payload = {"year": 2025, "classroom_ids": [self.group.pk], "title": "Feria", "day": 0, "start": "14:00", "end": "15:00"}
        self.assertEqual(self.client.post("/api/schedules/events/", payload, format="json").status_code, 400)
        payload.update(year=2026, start="07:00")
        self.assertEqual(self.client.post("/api/schedules/events/", payload, format="json").status_code, 400)
        self.assertFalse(Schedule.objects.exists())

    def test_teacher_cannot_have_overlapping_published_classes(self):
        Schedule.objects.create(classroom=self.group, draft=[self.block], published=[self.block])
        second = Course.objects.create(name="Otra clase", classroom=self.other, teacher=self.teacher)
        schedule = Schedule.objects.create(classroom=self.other, draft=[{**self.block, "course_id": second.pk}])
        self.client.force_authenticate(self.coord)
        result = self.client.post(f"/api/schedules/{schedule.pk}/publish/")
        self.assertEqual(result.status_code, 400)
        schedule.refresh_from_db()
        self.assertIsNone(schedule.published)


class DevSeedTests(TestCase):
    @override_settings(SETTINGS_MODULE="config.settings.qa", DEBUG=False)
    def test_seed_refuses_qa_even_with_dev_environment_variable(self):
        with patch.dict(os.environ, APP_ENV="dev"):
            with self.assertRaises(CommandError):
                call_command("seed_dev", stdout=StringIO())
        self.assertFalse(User.objects.exists())

    @override_settings(SETTINGS_MODULE="config.settings.dev", DEBUG=True)
    def test_seed_is_repeatable_and_preserves_passwords_and_schedule_changes(self):
        with patch.dict(os.environ, APP_ENV="dev"):
            call_command("seed_dev", stdout=StringIO())
            user = User.objects.get(email="admin@demo.talentsmart.test")
            self.assertTrue(user.check_password("TalentDev!2026"))
            self.assertFalse(user.is_superuser)
            user.set_password("changed-password")
            user.save()
            schedule = Schedule.objects.get()
            schedule.draft = []
            schedule.save()
            call_command("seed_dev", stdout=StringIO())
        user.refresh_from_db()
        schedule.refresh_from_db()
        self.assertTrue(user.check_password("changed-password"))
        self.assertEqual(schedule.draft, [])
        self.assertEqual(User.objects.count(), 7)
