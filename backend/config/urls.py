from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from school import views
from school import rfid as rfid_views

router = DefaultRouter()
for prefix, view in [
    ("users", views.UserViewSet), ("classrooms", views.ClassroomViewSet),
    ("courses", views.CourseViewSet), ("schedules", views.ScheduleViewSet),
    ("attendance", views.AttendanceViewSet), ("incidents", views.IncidentViewSet),
    ("files", views.FileViewSet),
]:
    router.register(prefix, view, basename=prefix)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/live/", views.live),
    path("api/health/ready/", views.ready),
    path("api/auth/login/", views.Login.as_view()),
    path("api/auth/me/", views.me),
    path("api/auth/logout/", views.logout),
    path("api/my-schedule/", views.my_schedule),
    path("api/directory/", views.DirectoryList.as_view()),
    path("api/talentosito/context/", views.assistant_context),
    path("api/rfid/registro", rfid_views.register_reading),
    path("api/rfid/readings/", rfid_views.ReadingList.as_view()),
    path("api/rfid/summary/", rfid_views.summary),
    path("api/rfid/devices/", rfid_views.devices),
    path("api/puerta/estado", rfid_views.report_door),
    path("api/puerta/cerrar", rfid_views.report_closed),
    path("api/", include(router.urls)),
]
