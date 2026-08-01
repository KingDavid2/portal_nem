"""Services layer for AttendanceRecord (attendance spec — Roster Read Endpoint,
Bulk Upsert Endpoint).
"""

from __future__ import annotations

import datetime

from django.core.exceptions import ValidationError
from django.db import transaction

from attendance.models import AttendanceRecord
from students.models import Student
from workspaces.scope import workspace_scope


def _validate_group_workspace(*, membership, group) -> None:
    if group.workspace_id != membership.workspace_id:
        raise ValueError("Group does not belong to the caller's workspace.")


def get_roster(*, membership, group, date: datetime.date) -> list[dict]:
    """Return every student in `group` merged with saved attendance for `date`.

    Students without a saved row default to status ``present`` and empty notes.
    """
    _validate_group_workspace(membership=membership, group=group)

    with workspace_scope(membership.workspace_id):
        students = list(
            Student.objects.filter(group=group).order_by("last_name_paternal", "first_name")
        )
        if not students:
            return []

        records_by_student = {
            record.student_id: record
            for record in AttendanceRecord.objects.filter(
                student__in=students,
                date=date,
            )
        }

    roster: list[dict] = []
    for student in students:
        record = records_by_student.get(student.pk)
        if record is None:
            roster.append(
                {
                    "student": student,
                    "status": AttendanceRecord.Status.PRESENT,
                    "notes": "",
                }
            )
        else:
            roster.append(
                {
                    "student": student,
                    "status": record.status,
                    "notes": record.notes,
                }
            )
    return roster


def bulk_upsert(*, membership, group, date: datetime.date, entries: list[dict]) -> None:
    """Atomically upsert attendance rows for every entry in `entries`.

    Every `student` must belong to `group` and the caller's workspace.
    Workspace is always taken from `membership`, never from client input.
    """
    _validate_group_workspace(membership=membership, group=group)

    with workspace_scope(membership.workspace_id):
        group_student_ids = set(
            Student.objects.filter(group=group).values_list("pk", flat=True)
        )

        validated: list[AttendanceRecord] = []
        valid_statuses = set(AttendanceRecord.Status.values)
        for entry in entries:
            student = entry["student"]
            if student.pk not in group_student_ids:
                raise ValueError("Student does not belong to the supplied group.")
            if student.workspace_id != membership.workspace_id:
                raise ValueError("Student does not belong to the caller's workspace.")
            if entry["status"] not in valid_statuses:
                raise ValueError(f"Invalid status: {entry['status']!r}")

            record = AttendanceRecord(
                workspace=membership.workspace,
                student=student,
                date=date,
                status=entry["status"],
                notes=entry.get("notes", ""),
            )
            record.full_clean()
            validated.append(record)

        with transaction.atomic():
            for record in validated:
                AttendanceRecord.objects.update_or_create(
                    student=record.student,
                    date=record.date,
                    defaults={
                        "workspace": membership.workspace,
                        "status": record.status,
                        "notes": record.notes,
                    },
                )
