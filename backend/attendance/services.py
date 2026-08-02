"""Services layer for AttendanceRecord (attendance spec — Roster Read Endpoint,
Bulk Upsert Endpoint, Week Roster Endpoint, Week Bulk Upsert Endpoint).
"""

from __future__ import annotations

import datetime

from django.db import transaction

from attendance.models import AttendanceRecord
from students.models import Student
from workspaces.scope import workspace_scope


def _validate_group_workspace(*, membership, group) -> None:
    if group.workspace_id != membership.workspace_id:
        raise ValueError("Group does not belong to the caller's workspace.")


def week_dates(week_start: datetime.date) -> list[datetime.date]:
    """Return Mon–Fri for a Monday ``week_start``. Raises if not Monday."""
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday.")
    return [week_start + datetime.timedelta(days=offset) for offset in range(5)]


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


def get_week_roster(*, membership, group, week_start: datetime.date) -> dict:
    """Return Mon–Fri matrix for ``group``: students with status per date.

    Students without a saved row default to status ``present`` for that date.
    Response carries no curp/notes.
    """
    _validate_group_workspace(membership=membership, group=group)
    dates = week_dates(week_start)

    with workspace_scope(membership.workspace_id):
        students = list(
            Student.objects.filter(group=group).order_by("last_name_paternal", "first_name")
        )
        if not students:
            return {"week_start": week_start, "dates": dates, "students": []}

        records = AttendanceRecord.objects.filter(
            student__in=students,
            date__in=dates,
        )
        status_by_student_date: dict[tuple[int, datetime.date], str] = {
            (record.student_id, record.date): record.status for record in records
        }

    rows: list[dict] = []
    for student in students:
        days = {
            date.isoformat(): status_by_student_date.get(
                (student.pk, date), AttendanceRecord.Status.PRESENT
            )
            for date in dates
        }
        rows.append(
            {
                "student": student,
                "days": days,
            }
        )

    return {"week_start": week_start, "dates": dates, "students": rows}


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


def bulk_upsert_week(
    *, membership, group, week_start: datetime.date, entries: list[dict]
) -> None:
    """Atomically upsert status for Mon–Fri entries; preserve existing notes.

    On create: notes default to empty. On update: only status + workspace change.
    Every entry date must fall in the Mon–Fri window for ``week_start``.
    """
    _validate_group_workspace(membership=membership, group=group)
    allowed_dates = set(week_dates(week_start))

    with workspace_scope(membership.workspace_id):
        group_student_ids = set(
            Student.objects.filter(group=group).values_list("pk", flat=True)
        )

        validated: list[tuple] = []
        valid_statuses = set(AttendanceRecord.Status.values)
        for entry in entries:
            student = entry["student"]
            date = entry["date"]
            status = entry["status"]
            if date not in allowed_dates:
                raise ValueError("Entry date is outside the Mon–Fri week window.")
            if student.pk not in group_student_ids:
                raise ValueError("Student does not belong to the supplied group.")
            if student.workspace_id != membership.workspace_id:
                raise ValueError("Student does not belong to the caller's workspace.")
            if status not in valid_statuses:
                raise ValueError(f"Invalid status: {status!r}")

            # Status already checked against Status.values; skip full_clean so an
            # existing (student, date) row does not trip unique-constraint validation.
            validated.append((student, date, status))

        with transaction.atomic():
            for student, date, status in validated:
                existing = AttendanceRecord.objects.filter(
                    student=student, date=date
                ).first()
                if existing is None:
                    AttendanceRecord.objects.create(
                        workspace=membership.workspace,
                        student=student,
                        date=date,
                        status=status,
                        notes="",
                    )
                else:
                    existing.status = status
                    existing.workspace = membership.workspace
                    existing.save(update_fields=["status", "workspace"])
