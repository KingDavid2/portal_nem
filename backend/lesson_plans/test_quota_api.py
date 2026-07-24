"""Tests for `GET /api/lesson-plans/quota/` (the "Generaciones de este mes"
card).

`test_quota.py` covers the ledger and its enforcement inside `create`; this
file covers only the read endpoint's HTTP contract, mirroring how
`test_catalog_api.py` isolates the `catalog` action.
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
from lesson_plans.models import GenerationUsage
from lesson_plans.quota import current_period, format_period
from schools.models import Group, School, SchoolYear
from workspaces.models import Membership, Workspace
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db

User = get_user_model()

QUOTA_URL = "/api/lesson-plans/quota/"


@pytest.fixture
def membership_factory():
    def make(*, role="member", workspace=None):
        workspace = workspace or Workspace.objects.create(type=Workspace.Type.GROUP)
        user = User.objects.create_user(
            email=f"user-{Membership.objects.count()}@example.com",
            password="s3cret-pass",
        )
        return Membership.objects.create(user=user, workspace=workspace, role=role)

    return make


@pytest.fixture
def client_for():
    def make(membership):
        client = APIClient()
        client.force_login(membership.user)
        client.credentials(HTTP_X_WORKSPACE_ID=str(membership.workspace_id))
        return client

    return make


@pytest.fixture
def group_factory():
    def make(membership):
        school = School.objects.create(
            workspace=membership.workspace,
            name="Escuela Uno",
            level=School.Level.SECUNDARIA,
            cct="15DES0001A",
        )
        school_year = SchoolYear.objects.create(
            workspace=membership.workspace, school=school, label="2025-2026"
        )
        return Group.objects.create(
            workspace=membership.workspace,
            school_year=school_year,
            grado=2,
            grupo="A",
        )

    return make


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
            criteria=[
                RubricCriterion(criterion="Participación", levels=["a", "b", "c", "d"])
            ]
        ),
    )


class _FakeProvider:
    name = "fake"
    model = "fake-model"

    def generate(self, request, pdas):
        return GenerationResult(
            proyecto=_canned_proyecto(),
            usage=Usage(input_tokens=10, output_tokens=20),
            invented_pdas=[],
        )


def _payload(group):
    return {
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


def _usage_row_count(workspace) -> int:
    with workspace_scope(workspace.pk):
        return GenerationUsage.objects.filter(workspace=workspace).count()


def test_quota_reports_a_full_allowance_before_the_first_generation(
    settings, membership_factory, client_for
):
    settings.LESSON_PLAN_MONTHLY_GENERATION_LIMIT = 30
    membership = membership_factory()

    response = client_for(membership).get(QUOTA_URL)

    assert response.status_code == 200
    assert response.data == {
        "period": format_period(current_period()),
        "used": 0,
        "limit": 30,
        "remaining": 30,
    }


def test_reading_the_quota_does_not_seed_a_ledger_row(
    membership_factory, client_for
):
    """Opening the planning form must not charge — or even materialize — a
    period the workspace has not generated in."""
    membership = membership_factory()

    assert client_for(membership).get(QUOTA_URL).status_code == 200

    assert _usage_row_count(membership.workspace) == 0


def test_quota_counts_the_generations_already_accepted_this_month(
    settings, membership_factory, client_for, group_factory
):
    settings.LESSON_PLAN_MONTHLY_GENERATION_LIMIT = 30
    membership = membership_factory()
    client = client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_FakeProvider()):
        for _ in range(3):
            assert (
                client.post(
                    "/api/lesson-plans/", _payload(group), format="json"
                ).status_code
                == 202
            )

    response = client.get(QUOTA_URL)

    assert response.status_code == 200
    assert response.data["used"] == 3
    assert response.data["remaining"] == 27


def test_quota_reports_the_same_period_as_the_429_body(
    settings, membership_factory, client_for, group_factory
):
    """The card and the rejection label the same window; asserting them equal
    here is what keeps the two formatters from drifting apart."""
    settings.LESSON_PLAN_MONTHLY_GENERATION_LIMIT = 1
    membership = membership_factory()
    client = client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_FakeProvider()):
        assert (
            client.post("/api/lesson-plans/", _payload(group), format="json").status_code
            == 202
        )
        rejected = client.post("/api/lesson-plans/", _payload(group), format="json")

    quota = client.get(QUOTA_URL)

    assert rejected.status_code == 429
    assert quota.status_code == 200
    assert quota.data["period"] == rejected.data["period"]
    assert quota.data["remaining"] == 0


def test_quota_is_scoped_to_the_active_workspace(
    settings, membership_factory, client_for, group_factory
):
    settings.LESSON_PLAN_MONTHLY_GENERATION_LIMIT = 30
    caller = membership_factory()
    other = membership_factory()
    other_group = group_factory(other)

    with patch("lesson_plans.tasks.build_provider", return_value=_FakeProvider()):
        assert (
            client_for(other)
            .post("/api/lesson-plans/", _payload(other_group), format="json")
            .status_code
            == 202
        )

    assert client_for(caller).get(QUOTA_URL).data["used"] == 0
    assert client_for(other).get(QUOTA_URL).data["used"] == 1


def test_quota_requires_authentication():
    response = APIClient().get(QUOTA_URL)

    assert response.status_code in {401, 403}


def test_quota_requires_view_workspace_permission(membership_factory, client_for):
    membership = membership_factory(role="no-capabilities-role")

    response = client_for(membership).get(QUOTA_URL)

    assert response.status_code == 403
