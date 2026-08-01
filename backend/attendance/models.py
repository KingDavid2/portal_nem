from django.db import models

from workspaces.models import ScopedModel


class AttendanceRecord(ScopedModel):
    """Daily attendance for one student on one calendar date (attendance spec).

    `student` is `PROTECT` — attendance history must not be silently destroyed
    by deleting the student. There is no `group` FK; group membership is
    derived from `student.group` and validated in the service layer.
    """

    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="attendance_records"
    )
    date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices)
    notes = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "attendance_attendancerecord"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "date"],
                name="unique_attendance_student_date",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student_id}@{self.date}:{self.status}"
