"""RED HTTP tests for the lesson_plans export action (ai-planeaciones spec —
Ready LessonPlan Can Be Exported as Docx or Markdown).

Export is a synchronous view over the stored `proyecto` — no live LLM/Celery
infra is needed, so these tests build a `ready` row directly rather than
going through the generate/task path.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from lesson_plans.core.schema import (
    ArticulatingAxis,
    ContentPda,
    Datos,
    Proyecto,
    Rubric,
    RubricCriterion,
)

pytestmark = pytest.mark.django_db

User = get_user_model()

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _canned_proyecto() -> Proyecto:
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
                pdas=[
                    "Emplea las reglas de acentuación de palabras agudas, graves, "
                    "esdrújulas y sobresdrújulas para escribir con corrección.",
                ],
            )
        ],
        stages=[],
        rubric=Rubric(
            criteria=[RubricCriterion(criterion="Participación", levels=["a", "b", "c", "d"])]
        ),
    )


@pytest.fixture
def membership_factory():
    from workspaces.models import Membership, Workspace

    def make(role="member", workspace=None):
        user = User.objects.create_user(
            email=f"{role}-{Workspace.objects.count()}@example.com",
            password="s3cret-pass",
        )
        workspace = workspace or Workspace.objects.create(type=Workspace.Type.GROUP)
        return Membership.objects.create(user=user, workspace=workspace, role=role)

    return make


@pytest.fixture
def api_client_for():
    def make(membership):
        client = APIClient()
        client.force_login(membership.user)
        client.credentials(HTTP_X_WORKSPACE_ID=str(membership.workspace_id))
        return client

    return make


@pytest.fixture
def group_factory():
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


def _make_lesson_plan(membership, group, *, status, proyecto=None):
    from workspaces.context import active_workspace

    from lesson_plans.models import LessonPlan

    token = active_workspace.set(membership.workspace_id)
    try:
        return LessonPlan.objects.create(
            workspace=membership.workspace,
            group=group,
            campo="Lenguajes",
            grade="SEGUNDO",
            theme="La independencia",
            status=status,
            proyecto=proyecto.model_dump(mode="json") if proyecto is not None else None,
            title=proyecto.title if proyecto is not None else "",
        )
    finally:
        active_workspace.reset(token)


def test_export_pending_plan_is_rejected(membership_factory, api_client_for, group_factory):
    """Scenario: Export of a pending plan is rejected."""
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)
    plan = _make_lesson_plan(membership, group, status="pending")

    response = client.get(f"/api/lesson-plans/{plan.pk}/export/?format=docx")

    assert 400 <= response.status_code < 500
    assert response.content == b"" or len(response.content) < 100


def test_export_ready_plan_as_docx(membership_factory, api_client_for, group_factory):
    """Scenario: Export ready plan as docx."""
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)
    plan = _make_lesson_plan(membership, group, status="ready", proyecto=_canned_proyecto())

    response = client.get(f"/api/lesson-plans/{plan.pk}/export/?format=docx")

    assert response.status_code == 200
    assert response["Content-Type"] == DOCX_CONTENT_TYPE
    assert "attachment" in response["Content-Disposition"]
    assert response.content[:2] == b"PK"  # docx is a zip archive


def test_export_ready_plan_as_markdown(membership_factory, api_client_for, group_factory):
    """Markdown export of a ready plan returns text reflecting the stored
    proyecto."""
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)
    plan = _make_lesson_plan(membership, group, status="ready", proyecto=_canned_proyecto())

    response = client.get(f"/api/lesson-plans/{plan.pk}/export/?format=md")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/markdown")
    body = response.content.decode("utf-8")
    assert "Héroes y Gestas" in body


def test_export_denied_cross_workspace(membership_factory, api_client_for, group_factory):
    membership_a = membership_factory("member")
    membership_b = membership_factory("member")
    client_a = api_client_for(membership_a)
    group_b = group_factory(membership_b)
    plan_b = _make_lesson_plan(membership_b, group_b, status="ready", proyecto=_canned_proyecto())

    response = client_a.get(f"/api/lesson-plans/{plan_b.pk}/export/?format=docx")

    assert response.status_code == 404
