from django.urls import path

from attendance.views import (
    AttendanceBulkView,
    AttendanceRosterView,
    AttendanceWeekBulkView,
    AttendanceWeekView,
)

urlpatterns = [
    path("attendance/roster/", AttendanceRosterView.as_view(), name="attendance-roster"),
    path("attendance/bulk/", AttendanceBulkView.as_view(), name="attendance-bulk"),
    path("attendance/week/", AttendanceWeekView.as_view(), name="attendance-week"),
    path(
        "attendance/week/bulk/",
        AttendanceWeekBulkView.as_view(),
        name="attendance-week-bulk",
    ),
]
