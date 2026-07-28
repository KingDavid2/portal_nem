"""RED HTTP tests for the lesson_plans export action (ai-planeaciones spec —
Ready LessonPlan Can Be Exported as Docx or Markdown).

Export is a synchronous view over the stored `proyecto` — no live LLM/Celery
infra is needed, so these tests build a `ready` row directly rather than
going through the generate/task path.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from docx import Document
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


CONTENT = "Recursos lingüísticos y textuales para la comprensión y producción de textos."
OFFICIAL_PDA = (
    "Emplea las reglas de acentuación de palabras agudas, graves, esdrújulas y "
    "sobresdrújulas para escribir con corrección."
)
INVENTED_PDA = "Inventa un proceso de desarrollo de aprendizaje que no existe."


def _canned_proyecto(pdas: list[str] | None = None) -> Proyecto:
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
            ContentPda(content=CONTENT, pdas=pdas or [OFFICIAL_PDA]),
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


def _extract_docx_paragraphs(docx_bytes: bytes) -> list[str]:
    """Return every paragraph's text from a docx buffer."""
    doc = Document(BytesIO(docx_bytes))
    return [p.text for p in doc.paragraphs]


def _grounded_plan(membership, group, *, pdas, selections, invented):
    """A ready plan whose grounding audit columns are populated as the task would."""
    plan = _make_lesson_plan(
        membership, group, status="ready", proyecto=_canned_proyecto(pdas)
    )
    plan.grounding_selections = selections
    plan.invented_pda_texts = invented
    plan.save()
    return plan


def test_export_docx_marks_official_and_invented_pdas(
    membership_factory, api_client_for, group_factory
):
    """The exported document names the offending PDA rather than only carrying a
    document-wide warning — the teacher has to know which line to fix."""
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)
    plan = _grounded_plan(
        membership,
        group,
        pdas=[OFFICIAL_PDA, INVENTED_PDA],
        selections=[{"content": CONTENT, "pdas": [OFFICIAL_PDA]}],
        invented=[INVENTED_PDA],
    )

    response = client.get(f"/api/lesson-plans/{plan.pk}/export/?format=docx")

    assert response.status_code == 200
    paragraphs = _extract_docx_paragraphs(response.content)
    assert f"✓ {OFFICIAL_PDA}" in paragraphs
    assert f"⚠ FUERA DE TU SELECCIÓN — {INVENTED_PDA}" in paragraphs


def test_export_docx_includes_the_official_basis_it_was_checked_against(
    membership_factory, api_client_for, group_factory
):
    """The other half of the audit trail: the verbatim SEP text the plan was
    checked against, so a reader can confirm the verdict instead of trusting it."""
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)
    plan = _grounded_plan(
        membership,
        group,
        pdas=[OFFICIAL_PDA],
        selections=[{"content": CONTENT, "pdas": [OFFICIAL_PDA]}],
        invented=[],
    )

    response = client.get(f"/api/lesson-plans/{plan.pk}/export/?format=docx")

    paragraphs = _extract_docx_paragraphs(response.content)
    heading = paragraphs.index("Fundamentación oficial (SEP)")
    assert paragraphs[heading + 1] == CONTENT
    assert paragraphs[heading + 2] == OFFICIAL_PDA


def test_export_docx_of_a_legacy_plan_carries_no_marks(
    membership_factory, api_client_for, group_factory
):
    """Plans generated before the audit columns existed were never checked against
    anything. Marking every PDA ⚠ — or claiming an empty official basis — would
    invent a verdict the data does not support, so they render exactly as before."""
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)
    plan = _make_lesson_plan(
        membership, group, status="ready", proyecto=_canned_proyecto()
    )
    assert plan.grounding_selections == []
    assert plan.invented_pda_texts == []

    response = client.get(f"/api/lesson-plans/{plan.pk}/export/?format=docx")

    paragraphs = _extract_docx_paragraphs(response.content)
    assert OFFICIAL_PDA in paragraphs
    assert not any("✓ " in p or "⚠" in p for p in paragraphs)
    assert not any("Fundamentación oficial" in p for p in paragraphs)


def test_export_markdown_marks_official_and_invented_pdas(
    membership_factory, api_client_for, group_factory
):
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)
    plan = _grounded_plan(
        membership,
        group,
        pdas=[OFFICIAL_PDA, INVENTED_PDA],
        selections=[{"content": CONTENT, "pdas": [OFFICIAL_PDA]}],
        invented=[INVENTED_PDA],
    )

    body = client.get(f"/api/lesson-plans/{plan.pk}/export/?format=md").content.decode()

    assert f"  - ✓ {OFFICIAL_PDA}" in body
    assert f"  - ⚠ FUERA DE TU SELECCIÓN — {INVENTED_PDA}" in body


def test_export_markdown_includes_the_official_basis_it_was_checked_against(
    membership_factory, api_client_for, group_factory
):
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)
    plan = _grounded_plan(
        membership,
        group,
        pdas=[OFFICIAL_PDA],
        selections=[{"content": CONTENT, "pdas": [OFFICIAL_PDA]}],
        invented=[],
    )

    body = client.get(f"/api/lesson-plans/{plan.pk}/export/?format=md").content.decode()

    assert f"## Fundamentación oficial (SEP)\n- {CONTENT}\n  - {OFFICIAL_PDA}" in body


def test_export_markdown_of_a_legacy_plan_carries_no_marks(
    membership_factory, api_client_for, group_factory
):
    membership = membership_factory("member")
    client = api_client_for(membership)
    group = group_factory(membership)
    plan = _make_lesson_plan(
        membership, group, status="ready", proyecto=_canned_proyecto()
    )

    body = client.get(f"/api/lesson-plans/{plan.pk}/export/?format=md").content.decode()

    assert f"  - {OFFICIAL_PDA}" in body
    assert "✓" not in body
    assert "⚠" not in body
    assert "Fundamentación oficial" not in body
