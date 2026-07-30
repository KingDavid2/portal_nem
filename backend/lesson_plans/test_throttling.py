"""Generation create rate limits — demo guest vs teacher scopes (Quizzy P6 Slice 1b).

Design rates: demo guest 3/hour (`lesson_plan_generate_demo`), teacher 30/hour
(`lesson_plan_generate`). Rate-limit 429 must not create a LessonPlan or move
monthly quota `used`. Scopes are independent.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from demo.models import DemoSession
from lesson_plans.core.ports.llm import GenerationResult, Usage
from lesson_plans.core.schema import (
    ArticulatingAxis,
    ContentPda,
    Datos,
    Proyecto,
    Rubric,
    RubricCriterion,
)
from lesson_plans.models import LessonPlan
from schools.models import Group, School, SchoolYear
from workspaces.models import Membership, Workspace
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


def _membership(*, email: str) -> Membership:
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    user = User.objects.create_user(email=email, password="s3cret-pass")
    return Membership.objects.create(
        user=user, workspace=workspace, role=Membership.Role.MEMBER
    )


def _group_for(membership: Membership) -> Group:
    school = School.objects.create(
        workspace=membership.workspace,
        name="Escuela Uno",
        level=School.Level.SECUNDARIA,
        cct="15DES0001A",
    )
    year = SchoolYear.objects.create(
        workspace=membership.workspace, school=school, label="2025-2026"
    )
    return Group.objects.create(
        workspace=membership.workspace, school_year=year, grado=1, grupo="A"
    )


def _client_for(membership: Membership) -> APIClient:
    client = APIClient()
    client.force_login(membership.user)
    client.credentials(HTTP_X_WORKSPACE_ID=str(membership.workspace_id))
    return client


def _demo_guest_membership() -> Membership:
    membership = _membership(email="demo+guest@example.com")
    DemoSession.objects.create(
        persona="teacher_minimal",
        status=DemoSession.Status.READY,
        user=membership.user,
        workspace=membership.workspace,
    )
    return membership


def test_demo_guest_429_at_request_4_creates_no_plan_and_leaves_quota_used():
    membership = _demo_guest_membership()
    client = _client_for(membership)
    group = _group_for(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_FakeProvider()):
        for i in range(3):
            response = client.post(
                "/api/lesson-plans/", _payload(group), format="json"
            )
            assert response.status_code == 202, f"expected 202 on request {i + 1}"

        used_before = client.get("/api/lesson-plans/quota/").data["used"]
        with workspace_scope(membership.workspace_id):
            plans_before = LessonPlan.objects.count()

        limited = client.post("/api/lesson-plans/", _payload(group), format="json")

    assert limited.status_code == 429
    with workspace_scope(membership.workspace_id):
        assert LessonPlan.objects.count() == plans_before
    assert client.get("/api/lesson-plans/quota/").data["used"] == used_before


def test_teacher_allows_up_to_30_generations():
    membership = _membership(email="teacher@example.com")
    client = _client_for(membership)
    group = _group_for(membership)

    with patch("lesson_plans.tasks.build_provider", return_value=_FakeProvider()):
        for i in range(30):
            response = client.post(
                "/api/lesson-plans/", _payload(group), format="json"
            )
            assert response.status_code == 202, f"expected 202 on request {i + 1}"


def test_demo_and_teacher_rate_counters_are_independent():
    demo = _demo_guest_membership()
    teacher = _membership(email="teacher-independent@example.com")
    demo_client = _client_for(demo)
    teacher_client = _client_for(teacher)
    demo_group = _group_for(demo)
    teacher_group = _group_for(teacher)

    with patch("lesson_plans.tasks.build_provider", return_value=_FakeProvider()):
        for _ in range(3):
            assert (
                demo_client.post(
                    "/api/lesson-plans/", _payload(demo_group), format="json"
                ).status_code
                == 202
            )
        assert (
            demo_client.post(
                "/api/lesson-plans/", _payload(demo_group), format="json"
            ).status_code
            == 429
        )

        # Exhausting the demo-guest counter must not consume the teacher scope.
        teacher_ok = teacher_client.post(
            "/api/lesson-plans/", _payload(teacher_group), format="json"
        )

    assert teacher_ok.status_code == 202
