from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Classroom, Course, Schedule, RFIDReading, Attendance, Incident, StoredFile


@admin.register(User)
class SchoolUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Talent Smart", {"fields": ("role", "classroom", "children", "rfid_uid")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Talent Smart", {"fields": ("email", "role")}),)
    list_display = ("username", "email", "role", "is_active")


for model in (Classroom, Course, Schedule, RFIDReading, Attendance, Incident, StoredFile):
    admin.site.register(model)

