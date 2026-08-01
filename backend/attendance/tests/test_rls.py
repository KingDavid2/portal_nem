"""RLS backstop tests for attendance_attendancerecord (tenancy-isolation spec —
RLS Coverage Extends to Attendance Records).
"""

import datetime

import psycopg
import pytest
from django.db import connection

pytestmark = pytest.mark.django_db(transaction=True)


def _portal_app_connection():
    db_settings = connection.settings_dict
    return psycopg.connect(
        dbname=db_settings["NAME"],
        host=db_settings["HOST"] or None,
        port=db_settings["PORT"] or None,
        user="portal_app",
    )


def _make_group(workspace):
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


def test_rls_enabled_with_ws_isolation_nullif_policy():
    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.relrowsecurity, p.polname, pg_get_expr(p.polqual, p.polrelid)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_policy p ON p.polrelid = c.oid AND p.polname = 'ws_isolation'
            WHERE c.relname = 'attendance_attendancerecord'
              AND n.nspname = 'public'
            """
        )
        row = cur.fetchone()

    assert row is not None
    relrowsecurity, polname, polqual = row
    assert relrowsecurity is True
    assert polname == "ws_isolation"
    assert "NULLIF(current_setting('app.workspace_id'" in polqual


def test_rls_denies_attendance_rows_with_no_workspace_context_set():
    from attendance.models import AttendanceRecord
    from students.models import Student
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    student = Student.objects.create(
        workspace=workspace, group=group, first_name="Ana", last_name_paternal="Perez"
    )
    AttendanceRecord.objects.create(
        workspace=workspace,
        student=student,
        date=datetime.date(2026, 8, 1),
        status=AttendanceRecord.Status.PRESENT,
    )

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM attendance_attendancerecord")
        (count,) = cur.fetchone()

    assert count == 0


def test_rls_blocks_foreign_workspace_attendance_row():
    from attendance.models import AttendanceRecord
    from students.models import Student
    from workspaces.models import Workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    group_a = _make_group(workspace_a)
    group_b = _make_group(workspace_b)
    student_a = Student.objects.create(
        workspace=workspace_a, group=group_a, first_name="Mine", last_name_paternal="A"
    )
    student_b = Student.objects.create(
        workspace=workspace_b, group=group_b, first_name="NotMine", last_name_paternal="B"
    )
    AttendanceRecord.objects.create(
        workspace=workspace_a,
        student=student_a,
        date=datetime.date(2026, 8, 1),
        status=AttendanceRecord.Status.ABSENT,
    )
    AttendanceRecord.objects.create(
        workspace=workspace_b,
        student=student_b,
        date=datetime.date(2026, 8, 1),
        status=AttendanceRecord.Status.ABSENT,
    )

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.workspace_id', %s, false)", [str(workspace_a.id)]
        )
        cur.execute(
            "SELECT s.first_name FROM attendance_attendancerecord ar "
            "JOIN students_student s ON s.id = ar.student_id "
            "ORDER BY s.first_name"
        )
        rows = [row[0] for row in cur.fetchall()]

    assert rows == ["Mine"]
