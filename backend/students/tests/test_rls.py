"""RLS backstop tests for students_student (tenancy-isolation spec — RLS
Coverage Extends to School Structure Tables).
"""

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


def test_rls_denies_student_rows_with_no_workspace_context_set():
    from students.models import Student
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    Student.objects.create(
        workspace=workspace, group=group, first_name="Ana", last_name_paternal="Perez"
    )

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM students_student")
        (count,) = cur.fetchone()

    assert count == 0


def test_rls_blocks_foreign_workspace_student_row():
    from students.models import Student
    from workspaces.models import Workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    group_a = _make_group(workspace_a)
    group_b = _make_group(workspace_b)
    Student.objects.create(
        workspace=workspace_a, group=group_a, first_name="Mine", last_name_paternal="A"
    )
    Student.objects.create(
        workspace=workspace_b, group=group_b, first_name="NotMine", last_name_paternal="B"
    )

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.workspace_id', %s, false)", [str(workspace_a.id)]
        )
        cur.execute("SELECT first_name FROM students_student ORDER BY first_name")
        rows = [row[0] for row in cur.fetchall()]

    assert rows == ["Mine"]
