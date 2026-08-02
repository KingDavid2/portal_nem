"""RLS backstop tests for grades tables (tenancy-isolation spec — RLS Coverage
Extends to Grades Tables).
"""

import datetime
from decimal import Decimal

import psycopg
import pytest
from django.db import connection

pytestmark = pytest.mark.django_db(transaction=True)

SCOPED_TABLES = ("grades_term", "grades_activity", "grades_activityscore")


def _portal_app_connection():
    db_settings = connection.settings_dict
    return psycopg.connect(
        dbname=db_settings["NAME"],
        host=db_settings["HOST"] or None,
        port=db_settings["PORT"] or None,
        user="portal_app",
    )


def _make_school_year(workspace):
    from schools.models import School, SchoolYear

    school = School.objects.create(
        workspace=workspace, name="Escuela", level=School.Level.SECUNDARIA
    )
    return SchoolYear.objects.create(
        workspace=workspace, school=school, label="2024-2025"
    )


def _make_group(workspace, school_year):
    from schools.models import Group

    return Group.objects.create(
        workspace=workspace, school_year=school_year, grado=1, grupo="A"
    )


@pytest.mark.parametrize("table", SCOPED_TABLES)
def test_rls_enabled_with_ws_isolation_nullif_policy(table):
    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.relrowsecurity, p.polname, pg_get_expr(p.polqual, p.polrelid)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_policy p ON p.polrelid = c.oid AND p.polname = 'ws_isolation'
            WHERE c.relname = %s
              AND n.nspname = 'public'
            """,
            [table],
        )
        row = cur.fetchone()

    assert row is not None
    relrowsecurity, polname, polqual = row
    assert relrowsecurity is True
    assert polname == "ws_isolation"
    assert "NULLIF(current_setting('app.workspace_id'" in polqual


def test_rls_denies_grades_rows_with_no_workspace_context_set():
    from grades.models import Activity, ActivityScore, Term
    from students.models import Student
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    school_year = _make_school_year(workspace)
    group = _make_group(workspace, school_year)
    term = Term.objects.create(workspace=workspace, school_year=school_year, number=1)
    student = Student.objects.create(
        workspace=workspace, group=group, first_name="Ana", last_name_paternal="Perez"
    )
    activity = Activity.objects.create(
        workspace=workspace,
        group=group,
        term=term,
        title="Tarea",
        activity_type=Activity.ActivityType.TASK,
        due_date=datetime.date(2026, 8, 15),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )
    ActivityScore.objects.create(
        workspace=workspace,
        activity=activity,
        student=student,
        score=Decimal("8.0"),
    )

    with _portal_app_connection() as conn, conn.cursor() as cur:
        for table in SCOPED_TABLES:
            cur.execute(f"SELECT count(*) FROM {table}")
            (count,) = cur.fetchone()
            assert count == 0, f"{table} visible without workspace context"


def test_rls_blocks_foreign_workspace_activity_and_score():
    from grades.models import Activity, ActivityScore, Term
    from students.models import Student
    from workspaces.models import Workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    year_a = _make_school_year(workspace_a)
    year_b = _make_school_year(workspace_b)
    group_a = _make_group(workspace_a, year_a)
    group_b = _make_group(workspace_b, year_b)
    term_a = Term.objects.create(workspace=workspace_a, school_year=year_a, number=1)
    term_b = Term.objects.create(workspace=workspace_b, school_year=year_b, number=1)
    student_a = Student.objects.create(
        workspace=workspace_a, group=group_a, first_name="Mine", last_name_paternal="A"
    )
    student_b = Student.objects.create(
        workspace=workspace_b, group=group_b, first_name="NotMine", last_name_paternal="B"
    )
    activity_a = Activity.objects.create(
        workspace=workspace_a,
        group=group_a,
        term=term_a,
        title="MineAct",
        activity_type=Activity.ActivityType.TASK,
        due_date=datetime.date(2026, 8, 15),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )
    activity_b = Activity.objects.create(
        workspace=workspace_b,
        group=group_b,
        term=term_b,
        title="OtherAct",
        activity_type=Activity.ActivityType.EXAM,
        due_date=datetime.date(2026, 8, 20),
        formative_field_id="languages",
        subject_ids=["english"],
    )
    ActivityScore.objects.create(
        workspace=workspace_a,
        activity=activity_a,
        student=student_a,
        score=Decimal("9.0"),
    )
    ActivityScore.objects.create(
        workspace=workspace_b,
        activity=activity_b,
        student=student_b,
        score=Decimal("7.0"),
    )

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.workspace_id', %s, false)", [str(workspace_a.id)]
        )
        cur.execute("SELECT title FROM grades_activity ORDER BY title")
        activity_titles = [row[0] for row in cur.fetchall()]
        cur.execute(
            "SELECT s.first_name FROM grades_activityscore sc "
            "JOIN students_student s ON s.id = sc.student_id "
            "ORDER BY s.first_name"
        )
        score_names = [row[0] for row in cur.fetchall()]

    assert activity_titles == ["MineAct"]
    assert score_names == ["Mine"]
