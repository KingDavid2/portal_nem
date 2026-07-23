"""RED tests for lesson_plans/services.py (ai-planeaciones spec — Generation
Request Is Gated, Workspace-Bound, and Schema-Validated; CRUD Endpoints Are
Workspace-Scoped).

`generate_lesson_plan` creates a `pending` row synchronously and enqueues
`generate_lesson_plan_task.delay(...)`. Under pytest, Celery runs eagerly
(`CELERY_TASK_ALWAYS_EAGER`, see `config/settings.py`), so the enqueued task
resolves inline — every test that reaches the enqueue step mocks
`lesson_plans.tasks.build_provider` to avoid a live LLM call (see
`test_tasks.py`'s `_FakeProvider` pattern).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied

from lesson_plans.core.ports.llm import GenerationResult, Usage
from lesson_plans.core.schema import (
    ArticulatingAxis,
    ContentPda,
    Datos,
    Proyecto,
    Rubric,
    RubricCriterion,
)
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db


def _read_plan(workspace_id, plan_id):
    from lesson_plans.models import LessonPlan

    with workspace_scope(workspace_id):
        return LessonPlan.objects.get(pk=plan_id)


def _canned_proyecto(*, extra_pda: str | None = None) -> Proyecto:
    pdas = [
        "Emplea las reglas de acentuación de palabras agudas, graves, "
        "esdrújulas y sobresdrújulas para escribir con corrección.",
    ]
    if extra_pda:
        pdas.append(extra_pda)
    return Proyecto(
        datos=Datos(
            school_name="Escuela Uno",
            grade="SEGUNDO",
            campo_formativo="Lenguajes",
            date="2026-01-01",
        ),
        title="Héroes y Gestas",
        purpose="Comprender la independencia.",
        articulating_axes=[ArticulatingAxis(name="Vida saludable", justification="x")],
        problem_or_theme="La independencia",
        contents_and_pdas=[
            ContentPda(
                content="Recursos lingüísticos y textuales para la comprensión y "
                "producción de textos.",
                pdas=pdas,
            )
        ],
        stages=[],
        rubric=Rubric(
            criteria=[RubricCriterion(criterion="Participación", levels=["a", "b", "c", "d"])]
        ),
    )


class _FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    def generate(self, request, pdas):
        if self._error is not None:
            raise self._error
        return self._result


def _fake_provider_returning(proyecto, invented_pdas=None):
    return _FakeProvider(
        result=GenerationResult(
            proyecto=proyecto,
            usage=Usage(input_tokens=10, output_tokens=20),
            invented_pdas=invented_pdas or [],
        )
    )


@pytest.fixture
def membership_factory():
    from django.contrib.auth import get_user_model

    from workspaces.models import Membership, Workspace

    User = get_user_model()

    def make(role="member", workspace=None):
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
def viewer_membership(membership_factory):
    """A membership whose role only carries view_workspace, not edit_content."""
    from django.contrib.auth import get_user_model

    from workspaces.models import Membership, Workspace

    User = get_user_model()
    user = User.objects.create_user(email="viewer@example.com", password="s3cret-pass")
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    membership = Membership.objects.create(user=user, workspace=workspace, role="member")
    membership.role = "no-capabilities-role"
    return membership


@pytest.fixture
def group_factory(membership_factory):
    from schools.models import Group, School, SchoolYear

    def make(membership):
        school = School.objects.create(
            workspace=membership.workspace, name="Escuela Uno", level=School.Level.SECUNDARIA
        )
        school_year = SchoolYear.objects.create(
            workspace=membership.workspace, school=school, label="2024-2025"
        )
        return Group.objects.create(
            workspace=membership.workspace, school_year=school_year, grado=1, grupo="A"
        )

    return make


def test_create_denied_without_edit_content(viewer_membership, group_factory):
    from lesson_plans.models import LessonPlan
    from lesson_plans.services import generate_lesson_plan

    group = group_factory(viewer_membership)

    with pytest.raises(PermissionDenied):
        generate_lesson_plan(
            membership=viewer_membership,
            group=group,
            campo="Lenguajes",
            grade="SEGUNDO",
            theme="La independencia",
        )

    assert not LessonPlan.objects.filter(group=group).exists()


def test_generate_assigns_membership_workspace_not_client_input(
    member_membership, group_factory
):
    """Scenario: Client-supplied workspace_id is ignored on generation.

    The service signature does not even accept a `workspace_id` kwarg — the
    row is always assigned `membership.workspace`, proven here by asserting
    the created row's workspace matches the membership regardless of any
    other workspace that might exist.
    """
    from workspaces.models import Workspace

    from lesson_plans.services import generate_lesson_plan

    Workspace.objects.create(type=Workspace.Type.GROUP)  # an unrelated "other" workspace
    group = group_factory(member_membership)

    with patch(
        "lesson_plans.tasks.build_provider",
        return_value=_fake_provider_returning(_canned_proyecto()),
    ):
        plan = generate_lesson_plan(
            membership=member_membership,
            group=group,
            campo="Lenguajes",
            grade="SEGUNDO",
            theme="La independencia",
        )

    assert plan.workspace_id == member_membership.workspace_id


def test_generate_denied_cross_workspace_group(member_membership, membership_factory, group_factory):
    from lesson_plans.services import generate_lesson_plan

    other_membership = membership_factory("member")
    foreign_group = group_factory(other_membership)

    with pytest.raises(ValueError):
        generate_lesson_plan(
            membership=member_membership,
            group=foreign_group,
            campo="Lenguajes",
            grade="SEGUNDO",
            theme="La independencia",
        )


def test_generate_creates_pending_row_and_enqueues_task(member_membership, group_factory):
    """Scenario: POST generate returns a pending LessonPlan immediately.

    Under eager Celery the task resolves inline by the time `.delay()`
    returns, so this asserts the row transitioned to `ready` once the (fake,
    mocked) provider succeeds — proving the create path enqueues correctly
    without asserting anything about the pending->ready ordering (that
    ordering is proven at the DRF layer in test_viewsets.py where the
    initial response body is inspected before the task can run).
    """
    from lesson_plans.models import LessonPlan
    from lesson_plans.services import generate_lesson_plan

    group = group_factory(member_membership)

    with patch(
        "lesson_plans.tasks.build_provider",
        return_value=_fake_provider_returning(_canned_proyecto()),
    ):
        plan = generate_lesson_plan(
            membership=member_membership,
            group=group,
            campo="Lenguajes",
            grade="SEGUNDO",
            theme="La independencia",
        )

    updated = _read_plan(member_membership.workspace_id, plan.pk)
    assert updated.status == LessonPlan.Status.READY
    assert updated.proyecto["title"] == "Héroes y Gestas"


def test_generate_surfaces_invented_pda_flag_without_blocking_ready(
    member_membership, group_factory
):
    """Scenario: Generated proyecto invents a PDA not in the source set.

    The guard flags the invented PDA on the row (`invented_pdas=True`); the
    design's literal task contract does not withhold `status=ready` for
    this — it surfaces the flag alongside `ready` rather than silently
    blocking it.
    """
    from lesson_plans.models import LessonPlan
    from lesson_plans.services import generate_lesson_plan

    group = group_factory(member_membership)
    invented = "Un PDA que no existe en el fixture."
    proyecto = _canned_proyecto(extra_pda=invented)

    with patch(
        "lesson_plans.tasks.build_provider",
        return_value=_fake_provider_returning(proyecto, invented_pdas=[invented]),
    ):
        plan = generate_lesson_plan(
            membership=member_membership,
            group=group,
            campo="Lenguajes",
            grade="SEGUNDO",
            theme="La independencia",
        )

    updated = _read_plan(member_membership.workspace_id, plan.pk)
    assert updated.invented_pdas is True
    assert updated.status == LessonPlan.Status.READY


def test_delete_denied_without_edit_content(member_membership, viewer_membership, group_factory):
    from lesson_plans.services import delete_lesson_plan, generate_lesson_plan

    group = group_factory(member_membership)
    with patch(
        "lesson_plans.tasks.build_provider",
        return_value=_fake_provider_returning(_canned_proyecto()),
    ):
        plan = generate_lesson_plan(
            membership=member_membership,
            group=group,
            campo="Lenguajes",
            grade="SEGUNDO",
            theme="La independencia",
        )

    with pytest.raises(PermissionDenied):
        delete_lesson_plan(membership=viewer_membership, lesson_plan=plan)


def test_delete_success(member_membership, group_factory):
    from lesson_plans.models import LessonPlan
    from lesson_plans.services import delete_lesson_plan, generate_lesson_plan

    group = group_factory(member_membership)
    with patch(
        "lesson_plans.tasks.build_provider",
        return_value=_fake_provider_returning(_canned_proyecto()),
    ):
        plan = generate_lesson_plan(
            membership=member_membership,
            group=group,
            campo="Lenguajes",
            grade="SEGUNDO",
            theme="La independencia",
        )

    delete_lesson_plan(membership=member_membership, lesson_plan=plan)

    assert not LessonPlan.objects.filter(pk=plan.pk).exists()
