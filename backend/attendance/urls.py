from django.urls import path

from attendance.views import AttendanceBulkView, AttendanceRosterView

urlpatterns = [
    path("attendance/roster/", AttendanceRosterView.as_view(), name="attendance-roster"),
    path("attendance/bulk/", AttendanceBulkView.as_view(), name="attendance-bulk"),
]
