"""RED tests for attendance/services.py (attendance spec — Roster Read Endpoint,
Bulk Upsert Endpoint).
"""

import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction

pytestmark = pytest.mark.django_db


@pytest.fixture
def membership_factory():
    from django.contrib.auth import get_user_model

    from workspaces.models import Membership, Workspace

    User = get_user_model()

    def make(role, workspace=None):
        user = User.objects.create_user(
            email=f"{role}-{Workspace.objects.count()}@example.com",
            password="s3cret-pass",
        )
        workspace = workspace or Workspace.objects.create(type=Workspace.Type.GROUP)
        return Membership.objects.create(user=user, workspace=workspace, role=role)

    return make


@pytest.fixture
def member_membership(membership_factory):
    return membership_factory("member")


@pytest.fixture
def group_factory(member_membership):
    from schools.services import create_group, create_school, create_school_year

    def make(membership=member_membership):
        school = create_school(
            membership=membership, name="Escuela Uno", cct="", level="primaria"
        )
        school_year = create_school_year(
            membership=membership, school=school, label="2024-2025"
        )
        return create_group(membership=membership, school_year=school_year, grado=1, grupo="A")

    return make


@pytest.fixture
def student_factory(member_membership, group_factory):
    from students.services import create_student

    def make(*, membership=member_membership, group=None, first_name="Ana", **kwargs):
        group = group or group_factory(membership=membership)
        return create_student(
            membership=membership,
            group=group,
            first_name=first_name,
            last_name_paternal=kwargs.get("last_name_paternal", "Perez"),
        )

    return make


def test_get_roster_merges_saved_and_unsaved_defaults_present(
    member_membership, group_factory, student_factory
):
    from attendance.models import AttendanceRecord
    from attendance.services import get_roster

    group = group_factory()
    student_a = student_factory(group=group, first_name="Ana")
    student_factory(group=group, first_name="Beto")
    AttendanceRecord.objects.create(
        workspace=member_membership.workspace,
        student=student_a,
        date=datetime.date(2026, 8, 1),
        status=AttendanceRecord.Status.ABSENT,
        notes="Enferma",
    )

    roster = get_roster(
        membership=member_membership,
        group=group,
        date=datetime.date(2026, 8, 1),
    )

    assert len(roster) == 2
    by_name = {entry["student"].first_name: entry for entry in roster}
    assert by_name["Ana"]["status"] == "absent"
    assert by_name["Ana"]["notes"] == "Enferma"
    assert by_name["Beto"]["status"] == "present"
    assert by_name["Beto"]["notes"] == ""


def test_get_roster_empty_group(member_membership, group_factory):
    from attendance.services import get_roster

    group = group_factory()
    roster = get_roster(
        membership=member_membership,
        group=group,
        date=datetime.date(2026, 8, 1),
    )

    assert roster == []


def test_bulk_upsert_atomic_all_or_nothing(
    member_membership, group_factory, student_factory
):
    from attendance.models import AttendanceRecord
    from attendance.services import bulk_upsert

    group = group_factory()
    student_a = student_factory(group=group, first_name="Ana")
    student_b = student_factory(group=group, first_name="Beto")

    with pytest.raises(ValueError):
        bulk_upsert(
            membership=member_membership,
            group=group,
            date=datetime.date(2026, 8, 1),
            entries=[
                {"student": student_a, "status": "present", "notes": ""},
                {"student": student_b, "status": "invalid-status", "notes": ""},
            ],
        )

    assert AttendanceRecord.objects.count() == 0


def test_bulk_upsert_rejects_student_not_in_group(
    member_membership, membership_factory, group_factory, student_factory
):
    from attendance.models import AttendanceRecord
    from attendance.services import bulk_upsert

    group = group_factory()
    student_in_group = student_factory(group=group, first_name="Ana")
    other_membership = membership_factory("member")
    other_group = group_factory(membership=other_membership)
    outsider = student_factory(
        membership=other_membership, group=other_group, first_name="Carla"
    )

    with pytest.raises(ValueError):
        bulk_upsert(
            membership=member_membership,
            group=group,
            date=datetime.date(2026, 8, 1),
            entries=[
                {"student": student_in_group, "status": "present", "notes": ""},
                {"student": outsider, "status": "absent", "notes": ""},
            ],
        )

    assert AttendanceRecord.objects.count() == 0


def test_bulk_upsert_rejects_notes_over_500_chars(
    member_membership, group_factory, student_factory
):
    from attendance.models import AttendanceRecord
    from attendance.services import bulk_upsert

    group = group_factory()
    student = student_factory(group=group)

    with pytest.raises(ValidationError):
        bulk_upsert(
            membership=member_membership,
            group=group,
            date=datetime.date(2026, 8, 1),
            entries=[
                {"student": student, "status": "present", "notes": "x" * 501},
            ],
        )

    assert AttendanceRecord.objects.count() == 0


def test_bulk_upsert_uses_membership_workspace_only(
    member_membership, membership_factory, group_factory, student_factory
):
    from attendance.models import AttendanceRecord
    from attendance.services import bulk_upsert
    from workspaces.context import active_workspace

    group = group_factory()
    student = student_factory(group=group)
    other_membership = membership_factory("member")

    bulk_upsert(
        membership=member_membership,
        group=group,
        date=datetime.date(2026, 8, 1),
        entries=[{"student": student, "status": "late", "notes": ""}],
    )

    token = active_workspace.set(member_membership.workspace_id)
    try:
        record = AttendanceRecord.objects.get(student=student)
    finally:
        active_workspace.reset(token)
    assert record.workspace_id == member_membership.workspace_id
    assert record.workspace_id != other_membership.workspace_id


def test_bulk_upsert_persists_all_entries(
    member_membership, group_factory, student_factory
):
    from attendance.models import AttendanceRecord
    from attendance.services import bulk_upsert, get_roster
    from workspaces.context import active_workspace

    group = group_factory()
    student_a = student_factory(group=group, first_name="Ana")
    student_b = student_factory(group=group, first_name="Beto")

    bulk_upsert(
        membership=member_membership,
        group=group,
        date=datetime.date(2026, 8, 1),
        entries=[
            {"student": student_a, "status": "absent", "notes": "A"},
            {"student": student_b, "status": "late", "notes": "B"},
        ],
    )

    token = active_workspace.set(member_membership.workspace_id)
    try:
        assert AttendanceRecord.objects.count() == 2
    finally:
        active_workspace.reset(token)
    roster = get_roster(
        membership=member_membership,
        group=group,
        date=datetime.date(2026, 8, 1),
    )
    by_name = {entry["student"].first_name: entry for entry in roster}
    assert by_name["Ana"]["status"] == "absent"
    assert by_name["Beto"]["status"] == "late"


def test_week_dates_requires_monday():
    from attendance.services import week_dates

    with pytest.raises(ValueError, match="Monday"):
        week_dates(datetime.date(2026, 8, 1))  # Saturday

    dates = week_dates(datetime.date(2026, 7, 27))  # Monday
    assert dates == [
        datetime.date(2026, 7, 27),
        datetime.date(2026, 7, 28),
        datetime.date(2026, 7, 29),
        datetime.date(2026, 7, 30),
        datetime.date(2026, 7, 31),
    ]


def test_get_week_roster_merges_saved_and_defaults_present(
    member_membership, group_factory, student_factory
):
    from attendance.models import AttendanceRecord
    from attendance.services import get_week_roster

    group = group_factory()
    student_a = student_factory(group=group, first_name="Ana")
    student_factory(group=group, first_name="Beto")
    monday = datetime.date(2026, 7, 27)
    AttendanceRecord.objects.create(
        workspace=member_membership.workspace,
        student=student_a,
        date=monday,
        status=AttendanceRecord.Status.ABSENT,
        notes="Enferma",
    )

    matrix = get_week_roster(
        membership=member_membership, group=group, week_start=monday
    )

    assert matrix["week_start"] == monday
    assert len(matrix["dates"]) == 5
    by_name = {row["student"].first_name: row for row in matrix["students"]}
    assert by_name["Ana"]["days"]["2026-07-27"] == "absent"
    assert by_name["Ana"]["days"]["2026-07-28"] == "present"
    assert by_name["Beto"]["days"]["2026-07-27"] == "present"


def test_bulk_upsert_week_preserves_notes(
    member_membership, group_factory, student_factory
):
    from attendance.models import AttendanceRecord
    from attendance.services import bulk_upsert_week
    from workspaces.context import active_workspace

    group = group_factory()
    student = student_factory(group=group)
    monday = datetime.date(2026, 7, 27)
    AttendanceRecord.objects.create(
        workspace=member_membership.workspace,
        student=student,
        date=monday,
        status=AttendanceRecord.Status.ABSENT,
        notes="Keep me",
    )

    bulk_upsert_week(
        membership=member_membership,
        group=group,
        week_start=monday,
        entries=[
            {"student": student, "date": monday, "status": "late"},
            {
                "student": student,
                "date": monday + datetime.timedelta(days=1),
                "status": "present",
            },
        ],
    )

    token = active_workspace.set(member_membership.workspace_id)
    try:
        monday_row = AttendanceRecord.objects.get(student=student, date=monday)
        tuesday_row = AttendanceRecord.objects.get(
            student=student, date=monday + datetime.timedelta(days=1)
        )
    finally:
        active_workspace.reset(token)

    assert monday_row.status == "late"
    assert monday_row.notes == "Keep me"
    assert tuesday_row.status == "present"
    assert tuesday_row.notes == ""


def test_bulk_upsert_week_rejects_date_outside_window(
    member_membership, group_factory, student_factory
):
    from attendance.models import AttendanceRecord
    from attendance.services import bulk_upsert_week

    group = group_factory()
    student = student_factory(group=group)
    monday = datetime.date(2026, 7, 27)

    with pytest.raises(ValueError, match="outside"):
        bulk_upsert_week(
            membership=member_membership,
            group=group,
            week_start=monday,
            entries=[
                {
                    "student": student,
                    "date": monday + datetime.timedelta(days=5),  # Saturday
                    "status": "present",
                },
            ],
        )

    assert AttendanceRecord.objects.count() == 0


def test_bulk_upsert_week_rejects_student_not_in_group(
    member_membership, membership_factory, group_factory, student_factory
):
    from attendance.models import AttendanceRecord
    from attendance.services import bulk_upsert_week

    group = group_factory()
    student_in_group = student_factory(group=group, first_name="Ana")
    other_membership = membership_factory("member")
    other_group = group_factory(membership=other_membership)
    outsider = student_factory(
        membership=other_membership, group=other_group, first_name="Carla"
    )
    monday = datetime.date(2026, 7, 27)

    with pytest.raises(ValueError):
        bulk_upsert_week(
            membership=member_membership,
            group=group,
            week_start=monday,
            entries=[
                {"student": student_in_group, "date": monday, "status": "present"},
                {"student": outsider, "date": monday, "status": "absent"},
            ],
        )

    assert AttendanceRecord.objects.count() == 0
