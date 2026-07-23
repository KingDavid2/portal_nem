"""RED HTTP tests for the lesson_plans DRF surface (ai-planeaciones spec —
CRUD Endpoints Are Workspace-Scoped; Generation Runs Asynchronously via a
Celery Task; Generation Request Is Gated, Workspace-Bound, and
Schema-Validated).

Under pytest, Celery runs eagerly (`CELERY_TASK_ALWAYS_EAGER`), so by the
time `POST /api/lesson-plans/` returns, the (mocked) task has already
resolved the row to `ready` or `failed` — every test that reaches the
generate path mocks `lesson_plans.tasks.build_provider` so no live LLM call
happens, and assertions on status accept the post-eager outcome rather than
asserting a literal `pending` snapshot (per this run's explicit guidance).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from lesson_plans.core.ports.llm import GenerationResult, Usage
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


def _fake_provider():
    return _FakeProvider(
        result=GenerationResult(
            proyecto=_canned_proyecto(), usage=Usage(input_tokens=10, output_tokens=20), invented_pdas=[]
        )
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


def test_create_returns_202_with_lesson_plan_id(membership_factory, api_client_for, group_factory):
    """Scenario: POST generate returns a pending LessonPlan immediately."""
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_fake_provider()):
        response = client.post(
            "/api/lesson-plans/",
            {"group": group.pk, "campo": "Lenguajes", "grade": "SEGUNDO", "theme": "La independencia"},
        )

    assert response.status_code == 202
    assert "id" in response.data
    assert response.data["status"] in {"pending", "ready", "failed"}


def test_create_denied_without_edit_content(membership_factory, api_client_for, group_factory):
    membership = membership_factory("member")
    membership.role = "no-capabilities-role"
    membership.save(update_fields=["role"])
    client = api_client_for(membership)
    group = group_factory(membership)

    response = client.post(
        "/api/lesson-plans/",
        {"group": group.pk, "campo": "Lenguajes", "grade": "SEGUNDO", "theme": "La independencia"},
    )

    assert response.status_code == 403


def test_list_scoped_to_requested_group_and_workspace(
    membership_factory, api_client_for, group_factory
):
    """Scenario: List endpoint returns only the requested group's plans in
    the active workspace."""
    membership_a = membership_factory("member")
    membership_b = membership_factory("member")
    client_a = api_client_for(membership_a)
    client_b = api_client_for(membership_b)
    group_a = group_factory(membership_a)
    group_b = group_factory(membership_b)

    with patch("lesson_plans.tasks.build_provider", return_value=_fake_provider()):
        create_a = client_a.post(
            "/api/lesson-plans/",
            {"group": group_a.pk, "campo": "Lenguajes", "grade": "SEGUNDO", "theme": "Mine"},
        )
        client_b.post(
            "/api/lesson-plans/",
            {"group": group_b.pk, "campo": "Lenguajes", "grade": "SEGUNDO", "theme": "NotMine"},
        )

    response = client_a.get(f"/api/lesson-plans/?group={group_a.pk}")

    rows = response.data["results"] if "results" in response.data else response.data
    assert [row["id"] for row in rows] == [create_a.data["id"]]


def test_retrieve_foreign_workspace_lesson_plan_returns_404(
    membership_factory, api_client_for, group_factory
):
    """Scenario: Retrieve of a foreign-workspace LessonPlan returns 404."""
    membership_a = membership_factory("member")
    membership_b = membership_factory("member")
    client_a = api_client_for(membership_a)
    client_b = api_client_for(membership_b)
    group_b = group_factory(membership_b)

    with patch("lesson_plans.tasks.build_provider", return_value=_fake_provider()):
        create_b = client_b.post(
            "/api/lesson-plans/",
            {"group": group_b.pk, "campo": "Lenguajes", "grade": "SEGUNDO", "theme": "Ajena"},
        )

    response = client_a.get(f"/api/lesson-plans/{create_b.data['id']}/")

    assert response.status_code == 404


def test_retrieve_reflects_status_transitions(membership_factory, api_client_for, group_factory):
    """Scenario: Client polls until generation completes.

    With eager Celery, the (mocked) task has already resolved the row to
    `ready`/`failed` by the time the create response returns, so polling
    retrieve after create reflects the terminal status.
    """
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_fake_provider()):
        create_response = client.post(
            "/api/lesson-plans/",
            {"group": group.pk, "campo": "Lenguajes", "grade": "SEGUNDO", "theme": "La independencia"},
        )

    plan_id = create_response.data["id"]
    response = client.get(f"/api/lesson-plans/{plan_id}/")

    assert response.status_code == 200
    assert response.data["status"] == "ready"
    assert response.data["proyecto"]["title"] == "Héroes y Gestas"


def test_destroy_success(membership_factory, api_client_for, group_factory):
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_fake_provider()):
        create_response = client.post(
            "/api/lesson-plans/",
            {"group": group.pk, "campo": "Lenguajes", "grade": "SEGUNDO", "theme": "La independencia"},
        )

    response = client.delete(f"/api/lesson-plans/{create_response.data['id']}/")

    assert response.status_code == 204
