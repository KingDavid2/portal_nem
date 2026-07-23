"""RED tests for the `LessonPlan` model shape (design D3, Interfaces/Contracts —
`LessonPlan (ScopedModel)`; tenancy-isolation spec — LessonPlan is a
workspace-scoped entity carrying its own `workspace_id`).
"""

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
        workspace=workspace, name="Escuela Uno", level=School.Level.SECUNDARIA
    )
    school_year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2024-2025"
    )
    return Group.objects.create(workspace=workspace, school_year=school_year, grado=1, grupo="A")


def test_lesson_plan_workspace_id_is_populated_directly_on_the_row(workspace, group):
    """The `workspace` FK lives on the row itself — it is never derived by
    joining through `Group` (Scenario: LessonPlan row carries its own
    workspace FK)."""
    from lesson_plans.models import LessonPlan

    plan = LessonPlan.objects.create(
        workspace=workspace,
        group=group,
        campo="Lenguajes",
        grade="SEGUNDO",
        theme="La independencia",
    )

    from workspaces.context import active_workspace

    token = active_workspace.set(workspace.id)
    try:
        raw = LessonPlan.objects.filter(pk=plan.pk).values("workspace_id").first()
    finally:
        active_workspace.reset(token)
    assert raw["workspace_id"] == workspace.id


def test_deleting_a_group_with_lesson_plans_is_blocked(workspace, group):
    """Scenario: Deleting a Group with lesson plans is blocked — `group` is
    `PROTECT`, mirroring `Student.group`."""
    from lesson_plans.models import LessonPlan

    LessonPlan.objects.create(
        workspace=workspace,
        group=group,
        campo="Lenguajes",
        grade="SEGUNDO",
        theme="La independencia",
    )

    with pytest.raises(ProtectedError):
        group.delete()


def test_lesson_plan_defaults_to_pending_status(workspace, group):
    from lesson_plans.models import LessonPlan

    plan = LessonPlan.objects.create(
        workspace=workspace,
        group=group,
        campo="Lenguajes",
        grade="SEGUNDO",
        theme="La independencia",
    )

    assert plan.status == LessonPlan.Status.PENDING
    assert plan.proyecto is None
    assert plan.failure_reason == ""
    assert plan.invented_pdas is False
    assert plan.generated_at is None


def test_lesson_plan_status_restricted_to_enum(workspace, group):
    from django.core.exceptions import ValidationError

    from lesson_plans.models import LessonPlan

    plan = LessonPlan(
        workspace=workspace,
        group=group,
        campo="Lenguajes",
        grade="SEGUNDO",
        theme="La independencia",
        status="not-a-real-status",
    )
    with pytest.raises(ValidationError):
        plan.full_clean()


def test_lesson_plan_can_transition_to_ready_with_provenance(workspace, group):
    from lesson_plans.models import LessonPlan

    plan = LessonPlan.objects.create(
        workspace=workspace,
        group=group,
        campo="Lenguajes",
        grade="SEGUNDO",
        theme="La independencia",
    )

    plan.status = LessonPlan.Status.READY
    plan.proyecto = {"title": "Héroes y Gestas"}
    plan.provider = "qwen"
    plan.model_name = "test-model"
    plan.prompt_tokens = 100
    plan.completion_tokens = 200
    plan.save()
    plan.refresh_from_db()

    assert plan.status == LessonPlan.Status.READY
    assert plan.proyecto == {"title": "Héroes y Gestas"}
    assert plan.provider == "qwen"
    assert plan.prompt_tokens == 100
    assert plan.completion_tokens == 200


def test_lesson_plan_can_transition_to_failed_with_reason(workspace, group):
    from lesson_plans.models import LessonPlan

    plan = LessonPlan.objects.create(
        workspace=workspace,
        group=group,
        campo="Lenguajes",
        grade="SEGUNDO",
        theme="La independencia",
    )

    plan.status = LessonPlan.Status.FAILED
    plan.failure_reason = "Schema parse error"
    plan.save()
    plan.refresh_from_db()

    assert plan.status == LessonPlan.Status.FAILED
    assert plan.failure_reason == "Schema parse error"
