"""RLS backstop tests for lesson_plans_lessonplan (tenancy-isolation spec —
RLS coverage extends to the LessonPlan table). Mirrors the
`_portal_app_connection()` pattern from `workspaces/tests/test_rls.py` and
`schools/tests/test_rls.py`.
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
        workspace=workspace, name="Escuela", level=School.Level.SECUNDARIA
    )
    school_year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2024-2025"
    )
    return Group.objects.create(workspace=workspace, school_year=school_year, grado=1, grupo="A")


def test_rls_denies_lesson_plan_rows_with_no_workspace_context_set():
    from lesson_plans.models import LessonPlan
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    LessonPlan.objects.create(
        workspace=workspace, group=group, campo="Lenguajes", grade="SEGUNDO", theme="Secreto"
    )

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM lesson_plans_lessonplan")
        (count,) = cur.fetchone()

    assert count == 0


def test_rls_blocks_foreign_workspace_lesson_plan_row():
    from lesson_plans.models import LessonPlan
    from workspaces.models import Workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    group_a = _make_group(workspace_a)
    group_b = _make_group(workspace_b)
    LessonPlan.objects.create(
        workspace=workspace_a, group=group_a, campo="Lenguajes", grade="SEGUNDO", theme="Mine"
    )
    LessonPlan.objects.create(
        workspace=workspace_b, group=group_b, campo="Lenguajes", grade="SEGUNDO", theme="NotMine"
    )

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.workspace_id', %s, false)", [str(workspace_a.id)]
        )
        cur.execute("SELECT theme FROM lesson_plans_lessonplan ORDER BY theme")
        rows = [row[0] for row in cur.fetchall()]

    assert rows == ["Mine"]


def test_scoped_manager_denies_lesson_plan_rows_with_no_active_workspace():
    """ORM-level gate, independent of RLS (design Data Flow — ScopedManager
    is the primary mechanism, RLS the backstop)."""
    from lesson_plans.models import LessonPlan
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    LessonPlan.objects.create(
        workspace=workspace, group=group, campo="Lenguajes", grade="SEGUNDO", theme="Secreto"
    )

    assert list(LessonPlan.objects.all()) == []


def test_scoped_manager_returns_only_the_active_workspace_lesson_plans():
    from lesson_plans.models import LessonPlan
    from workspaces.context import active_workspace
    from workspaces.models import Workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    group_a = _make_group(workspace_a)
    group_b = _make_group(workspace_b)
    LessonPlan.objects.create(
        workspace=workspace_a, group=group_a, campo="Lenguajes", grade="SEGUNDO", theme="Mine"
    )
    LessonPlan.objects.create(
        workspace=workspace_b, group=group_b, campo="Lenguajes", grade="SEGUNDO", theme="NotMine"
    )

    token = active_workspace.set(workspace_a.id)
    try:
        themes = list(LessonPlan.objects.values_list("theme", flat=True))
    finally:
        active_workspace.reset(token)

    assert themes == ["Mine"]
