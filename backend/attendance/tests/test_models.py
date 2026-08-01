"""RED tests for AttendanceRecord model shape (attendance spec — AttendanceRecord
Invariants).
"""

import datetime

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace():
    from workspaces.models import Workspace

    return Workspace.objects.create(type=Workspace.Type.GROUP)


@pytest.fixture
def group(workspace):
    from schools.models import Group, School, SchoolYear

    school = School.objects.create(
        workspace=workspace, name="Escuela", level=School.Level.PRIMARIA
    )
    school_year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2024-2025"
    )
    return Group.objects.create(
        workspace=workspace, school_year=school_year, grado=1, grupo="A"
    )


@pytest.fixture
def student(workspace, group):
    from students.models import Student

    return Student.objects.create(
        workspace=workspace,
        group=group,
        first_name="Ana",
        last_name_paternal="Perez",
    )


def test_attendance_record_subclasses_scoped_model():
    from attendance.models import AttendanceRecord
    from workspaces.models import ScopedModel

    assert issubclass(AttendanceRecord, ScopedModel)


def test_attendance_record_db_table():
    from attendance.models import AttendanceRecord

    assert AttendanceRecord._meta.db_table == "attendance_attendancerecord"


def test_attendance_record_has_no_group_fk():
    from attendance.models import AttendanceRecord

    field_names = {f.name for f in AttendanceRecord._meta.get_fields()}
    assert "group" not in field_names


def test_attendance_record_field_shapes(student, workspace):
    from attendance.models import AttendanceRecord

    record = AttendanceRecord(
        workspace=workspace,
        student=student,
        date=datetime.date(2026, 8, 1),
        status=AttendanceRecord.Status.PRESENT,
    )
    record.full_clean()
    record.save()

    assert record.student_id == student.pk
    assert record.date == datetime.date(2026, 8, 1)
    assert record.status == "present"
    assert record.notes == ""


def test_attendance_record_status_enum_values():
    from attendance.models import AttendanceRecord

    assert set(AttendanceRecord.Status.values) == {
        "present",
        "absent",
        "late",
        "excused",
    }


def test_attendance_record_notes_max_length(student, workspace):
    from django.core.exceptions import ValidationError

    from attendance.models import AttendanceRecord

    record = AttendanceRecord(
        workspace=workspace,
        student=student,
        date=datetime.date(2026, 8, 1),
        status=AttendanceRecord.Status.PRESENT,
        notes="x" * 501,
    )
    with pytest.raises(ValidationError):
        record.full_clean()


def test_duplicate_student_date_raises(student, workspace):
    from attendance.models import AttendanceRecord

    AttendanceRecord.objects.create(
        workspace=workspace,
        student=student,
        date=datetime.date(2026, 8, 1),
        status=AttendanceRecord.Status.ABSENT,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AttendanceRecord.objects.create(
                workspace=workspace,
                student=student,
                date=datetime.date(2026, 8, 1),
                status=AttendanceRecord.Status.PRESENT,
            )


def test_deleting_student_with_attendance_records_is_protected(student, workspace):
    from attendance.models import AttendanceRecord

    AttendanceRecord.objects.create(
        workspace=workspace,
        student=student,
        date=datetime.date(2026, 8, 1),
        status=AttendanceRecord.Status.PRESENT,
    )

    with pytest.raises(ProtectedError):
        student.delete()
