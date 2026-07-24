"""Tests for the monthly generation quota (`lesson_plans.quota`).

The quota is enforced inside `services.generate_lesson_plan`'s transaction, so
these tests drive it through the real HTTP surface wherever the assertion is
about the API contract (429 body, no row created) and through the quota module
directly where the assertion is about the ledger itself.

`timezone.localdate` is patched instead of waiting for a real month boundary;
the project has no `freezegun` dependency and `current_period()` reads exactly
that one function.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
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
from lesson_plans.models import GenerationUsage, LessonPlan
from lesson_plans.quota import (
    QuotaExceeded,
    consume_generation,
    current_period,
    current_usage,
)
from workspaces.scope import workspace_scope

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


def _payload(group, **overrides):
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
            workspace=membership.workspace,
            name="Escuela Uno",
            level=School.Level.SECUNDARIA,
        )
        school_year = SchoolYear.objects.create(
            workspace=membership.workspace, school=school, label="2024-2025"
        )
        return Group.objects.create(
            workspace=membership.workspace, school_year=school_year, grado=1, grupo="A"
        )

    return make


def _usage_rows(workspace):
    with workspace_scope(workspace.pk):
        return list(
            GenerationUsage.objects.filter(workspace=workspace).order_by("period")
        )


def _plan_count(workspace):
    with workspace_scope(workspace.pk):
        return LessonPlan.objects.count()


def test_first_create_seeds_the_period_row_at_one(
    membership_factory, api_client_for, group_factory
):
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_FakeProvider()):
        response = client.post("/api/lesson-plans/", _payload(group), format="json")

    assert response.status_code == 202
    rows = _usage_rows(membership.workspace)
    assert len(rows) == 1
    assert rows[0].period == current_period()
    assert rows[0].count == 1


def test_request_past_the_limit_returns_429_and_creates_no_lesson_plan(
    settings, membership_factory, api_client_for, group_factory
):
    settings.LESSON_PLAN_MONTHLY_GENERATION_LIMIT = 2
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_FakeProvider()):
        for _ in range(2):
            accepted = client.post(
                "/api/lesson-plans/", _payload(group), format="json"
            )
            assert accepted.status_code == 202

        rejected = client.post("/api/lesson-plans/", _payload(group), format="json")

    assert rejected.status_code == 429
    assert rejected.data == {
        "detail": "Monthly generation limit reached.",
        "code": "generation_quota_exceeded",
        "used": 2,
        "limit": 2,
        "period": f"{current_period():%Y-%m}",
    }
    assert _plan_count(membership.workspace) == 2
    rows = _usage_rows(membership.workspace)
    assert [row.count for row in rows] == [2]


def test_a_new_calendar_month_starts_a_fresh_period_row(
    settings, membership_factory
):
    settings.LESSON_PLAN_MONTHLY_GENERATION_LIMIT = 1
    membership = membership_factory("member")
    workspace = membership.workspace

    with patch("django.utils.timezone.localdate", return_value=date(2026, 7, 24)):
        consume_generation(workspace)
        with pytest.raises(QuotaExceeded):
            consume_generation(workspace)

    with patch("django.utils.timezone.localdate", return_value=date(2026, 8, 1)):
        august = consume_generation(workspace)
        assert current_usage(workspace) == (1, 1)

    assert august.period == date(2026, 8, 1)
    assert [(row.period, row.count) for row in _usage_rows(workspace)] == [
        (date(2026, 7, 1), 1),
        (date(2026, 8, 1), 1),
    ]


def test_two_workspaces_do_not_share_a_period_row(membership_factory):
    membership_a = membership_factory("member")
    membership_b = membership_factory("member")

    consume_generation(membership_a.workspace)
    consume_generation(membership_a.workspace)
    consume_generation(membership_b.workspace)

    assert current_usage(membership_a.workspace)[0] == 2
    assert current_usage(membership_b.workspace)[0] == 1
    assert len(_usage_rows(membership_a.workspace)) == 1
    assert len(_usage_rows(membership_b.workspace)) == 1


def test_unique_constraint_rejects_a_duplicate_period_row(membership_factory):
    """The ledger is one row per (workspace, period) — the constraint, not
    application code, is what makes a racing `get_or_create` safe."""
    membership = membership_factory("member")
    period = current_period()
    GenerationUsage.objects.create(workspace=membership.workspace, period=period)

    with pytest.raises(IntegrityError), transaction.atomic():
        GenerationUsage.objects.create(workspace=membership.workspace, period=period)


def test_consume_generation_raises_with_the_counters_the_api_reports(
    settings, membership_factory
):
    settings.LESSON_PLAN_MONTHLY_GENERATION_LIMIT = 1
    membership = membership_factory("member")
    consume_generation(membership.workspace)

    with pytest.raises(QuotaExceeded) as excinfo:
        consume_generation(membership.workspace)

    assert excinfo.value.used == 1
    assert excinfo.value.limit == 1
    assert excinfo.value.period == current_period()


def test_current_usage_reports_zero_before_the_first_generation(
    settings, membership_factory
):
    settings.LESSON_PLAN_MONTHLY_GENERATION_LIMIT = 30
    membership = membership_factory("member")

    assert current_usage(membership.workspace) == (0, 30)


def test_current_period_is_the_first_day_of_the_project_timezone_month():
    with patch("django.utils.timezone.localdate", return_value=date(2026, 7, 24)):
        assert current_period() == date(2026, 7, 1)
