"""RLS backstop tests for schools_school / schools_schoolyear / schools_group
(tenancy-isolation spec — RLS Coverage Extends to School Structure Tables).

Mirrors the `_portal_app_connection()` pattern from
`workspaces/tests/test_rls.py`.
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


def test_rls_denies_school_rows_with_no_workspace_context_set():
    from schools.models import School
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    School.objects.create(workspace=workspace, name="Secreta", level=School.Level.PRIMARIA)

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM schools_school")
        (count,) = cur.fetchone()

    assert count == 0


def test_rls_blocks_foreign_workspace_school_row():
    from schools.models import School
    from workspaces.models import Workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    School.objects.create(workspace=workspace_a, name="Mine", level=School.Level.PRIMARIA)
    School.objects.create(workspace=workspace_b, name="NotMine", level=School.Level.PRIMARIA)

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.workspace_id', %s, false)", [str(workspace_a.id)]
        )
        cur.execute("SELECT name FROM schools_school ORDER BY name")
        rows = [row[0] for row in cur.fetchall()]

    assert rows == ["Mine"]


def test_rls_denies_school_year_rows_with_no_workspace_context_set():
    from schools.models import School, SchoolYear
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    school = School.objects.create(
        workspace=workspace, name="Escuela", level=School.Level.PRIMARIA
    )
    SchoolYear.objects.create(workspace=workspace, school=school, label="2024-2025")

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM schools_schoolyear")
        (count,) = cur.fetchone()

    assert count == 0


def test_rls_blocks_foreign_workspace_school_year_row():
    from schools.models import School, SchoolYear
    from workspaces.models import Workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    school_a = School.objects.create(
        workspace=workspace_a, name="Escuela A", level=School.Level.PRIMARIA
    )
    school_b = School.objects.create(
        workspace=workspace_b, name="Escuela B", level=School.Level.PRIMARIA
    )
    SchoolYear.objects.create(workspace=workspace_a, school=school_a, label="mine")
    SchoolYear.objects.create(workspace=workspace_b, school=school_b, label="not-mine")

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.workspace_id', %s, false)", [str(workspace_a.id)]
        )
        cur.execute("SELECT label FROM schools_schoolyear ORDER BY label")
        rows = [row[0] for row in cur.fetchall()]

    assert rows == ["mine"]


def test_rls_denies_group_rows_with_no_workspace_context_set():
    from schools.models import Group, School, SchoolYear
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    school = School.objects.create(
        workspace=workspace, name="Escuela", level=School.Level.PRIMARIA
    )
    school_year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2024-2025"
    )
    Group.objects.create(workspace=workspace, school_year=school_year, grado=1, grupo="A")

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM schools_group")
        (count,) = cur.fetchone()

    assert count == 0


def test_rls_blocks_foreign_workspace_group_row():
    from schools.models import Group, School, SchoolYear
    from workspaces.models import Workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    school_a = School.objects.create(
        workspace=workspace_a, name="Escuela A", level=School.Level.PRIMARIA
    )
    school_b = School.objects.create(
        workspace=workspace_b, name="Escuela B", level=School.Level.PRIMARIA
    )
    school_year_a = SchoolYear.objects.create(
        workspace=workspace_a, school=school_a, label="2024-2025"
    )
    school_year_b = SchoolYear.objects.create(
        workspace=workspace_b, school=school_b, label="2024-2025"
    )
    Group.objects.create(workspace=workspace_a, school_year=school_year_a, grado=1, grupo="A")
    Group.objects.create(workspace=workspace_b, school_year=school_year_b, grado=1, grupo="A")

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.workspace_id', %s, false)", [str(workspace_a.id)]
        )
        cur.execute("SELECT grupo FROM schools_group")
        rows = [row[0] for row in cur.fetchall()]

    assert rows == ["A"]
