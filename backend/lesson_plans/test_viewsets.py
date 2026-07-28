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


def _payload(group, **overrides):
    """The catalog-backed POST body every create test submits."""
    payload = {
        "group": group.pk,
        "field_id": "languages",
        "subject_id": "spanish",
        "methodology_id": "community-based-project-learning",
        "theme": "La independencia",
        "context_diagnosis": "El grupo requiere fortalecer la producción escrita.",
        "scenario": "community",
        "duration_weeks": 4,
        "start_date": "2026-01-12",
        "end_date": "2026-02-06",
        "cross_cutting_theme_ids": ["critical-thinking", "inclusion"],
        "content_selections": [
            {
                "content_id": "languages-text-resources",
                "pda_ids": ["languages-accentuation", "languages-coherent-texts"],
            }
        ],
    }
    payload.update(overrides)
    return payload


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
            _payload(group),
            format="json",
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
        _payload(group),
        format="json",
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
            _payload(group_a, theme="Mine"),
            format="json",
        )
        client_b.post(
            "/api/lesson-plans/",
            _payload(group_b, theme="NotMine"),
            format="json",
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
            _payload(group_b, theme="Ajena"),
            format="json",
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
            _payload(group),
            format="json",
        )

    plan_id = create_response.data["id"]
    response = client.get(f"/api/lesson-plans/{plan_id}/")

    assert response.status_code == 200
    assert response.data["status"] == "ready"
    assert response.data["proyecto"]["title"] == "Héroes y Gestas"


def test_create_persists_every_project_context_column(
    membership_factory, api_client_for, group_factory
):
    """The catalog-backed body is stored verbatim on the row and echoed back
    by the read serializer."""
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_fake_provider()):
        create_response = client.post(
            "/api/lesson-plans/", _payload(group), format="json"
        )

    assert create_response.status_code == 202

    response = client.get(f"/api/lesson-plans/{create_response.data['id']}/")

    assert response.status_code == 200
    assert response.data["field_id"] == "languages"
    assert response.data["subject_id"] == "spanish"
    assert response.data["methodology_id"] == "community-based-project-learning"
    assert response.data["scenario"] == "community"
    assert response.data["context_diagnosis"] == (
        "El grupo requiere fortalecer la producción escrita."
    )
    assert response.data["duration_weeks"] == 4
    assert response.data["start_date"] == "2026-01-12"
    assert response.data["end_date"] == "2026-02-06"
    assert response.data["cross_cutting_theme_ids"] == ["critical-thinking", "inclusion"]
    assert response.data["content_selections"] == [
        {
            "content_id": "languages-text-resources",
            "pda_ids": ["languages-accentuation", "languages-coherent-texts"],
        }
    ]


def test_create_derives_campo_and_grade_ignoring_client_supplied_values(
    membership_factory, api_client_for, group_factory
):
    """`campo`/`grade` are server-derived from the resolved field and the
    group — a client that sends its own values is ignored, not obeyed."""
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_fake_provider()):
        create_response = client.post(
            "/api/lesson-plans/",
            _payload(group, campo="Matemáticas", grade="NOVENO"),
            format="json",
        )

    assert create_response.status_code == 202
    assert create_response.data["campo"] == "Lenguajes"
    assert create_response.data["grade"] == str(group.grado)


def test_create_rejects_a_body_that_is_not_catalog_backed(
    membership_factory, api_client_for, group_factory
):
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    response = client.post(
        "/api/lesson-plans/",
        _payload(group, field_id="astrology"),
        format="json",
    )

    assert response.status_code == 400
    assert response.data == {"field_id": ["Unsupported field id."]}


def test_destroy_success(membership_factory, api_client_for, group_factory):
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_fake_provider()):
        create_response = client.post(
            "/api/lesson-plans/",
            _payload(group),
            format="json",
        )

    response = client.delete(f"/api/lesson-plans/{create_response.data['id']}/")

    assert response.status_code == 204


def test_retrieve_exposes_grounding_audit_trail_fields(
    membership_factory, api_client_for, group_factory
):
    """A plan with populated `invented_pda_texts` and `grounding_selections`
    serializes both with the correct structure — nested snapshots keep their
    `{content, pdas}` shape, not stringified or flattened."""
    from lesson_plans.models import LessonPlan
    from workspaces.context import active_workspace

    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_fake_provider()):
        create_response = client.post(
            "/api/lesson-plans/",
            _payload(group),
            format="json",
        )

    plan_id = create_response.data["id"]
    token = active_workspace.set(membership.workspace_id)
    try:
        LessonPlan.objects.filter(id=plan_id).update(
            invented_pda_texts=["PDA inventada uno", "PDA inventada dos"],
            grounding_selections=[
                {
                    "content": "Recursos lingüísticos y textuales.",
                    "pdas": [
                        "Emplea las reglas de acentuación.",
                        "Produce textos coherentes.",
                    ],
                },
                {
                    "content": "Convenciones ortográficas.",
                    "pdas": ["Respeta los signos de puntuación."],
                },
            ],
        )
    finally:
        active_workspace.reset(token)

    response = client.get(f"/api/lesson-plans/{plan_id}/")

    assert response.status_code == 200
    assert response.data["invented_pda_texts"] == [
        "PDA inventada uno",
        "PDA inventada dos",
    ]
    assert response.data["grounding_selections"] == [
        {
            "content": "Recursos lingüísticos y textuales.",
            "pdas": [
                "Emplea las reglas de acentuación.",
                "Produce textos coherentes.",
            ],
        },
        {
            "content": "Convenciones ortográficas.",
            "pdas": ["Respeta los signos de puntuación."],
        },
    ]


def test_create_ignores_grounding_fields_sent_by_client(
    membership_factory, api_client_for, group_factory
):
    """Both fields are read-only: a client that POSTs values for them does not
    get them persisted. The create serializer does not declare these fields,
    so DRF drops them — the row keeps its defaults."""
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_fake_provider()):
        response = client.post(
            "/api/lesson-plans/",
            _payload(
                group,
                invented_pda_texts=["forged-pda"],
                grounding_selections=[
                    {"content": "fake", "pdas": ["fake-pda"]}
                ],
            ),
            format="json",
        )

    assert response.status_code == 202
    assert response.data["invented_pda_texts"] == []
    assert response.data["grounding_selections"] == []
