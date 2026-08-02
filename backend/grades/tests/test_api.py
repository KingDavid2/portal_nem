"""RED HTTP tests for grades DRF surface (grades spec — Activities List and
Create, Scores Matrix Endpoint, Bulk Score Upsert; authorization spec —
Grades Endpoints Map Custom Actions to Capabilities).
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from workspaces.models import Membership

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def membership_factory():
    from workspaces.models import Workspace

    def make(role=Membership.Role.MEMBER, workspace=None):
        role_value = role if isinstance(role, Membership.Role) else Membership.Role(role)
        user = User.objects.create_user(
            email=f"{role_value}-{Workspace.objects.count()}@example.com",
            password="s3cret-pass",
        )
        workspace = workspace or Workspace.objects.create(type=Workspace.Type.GROUP)
        return Membership.objects.create(
            user=user, workspace=workspace, role=role_value
        )

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
def school_year_for():
    from schools.services import create_school, create_school_year

    def make(membership):
        school = create_school(
            membership=membership,
            name="Escuela Uno",
            cct="",
            level="secundaria",
        )
        return create_school_year(
            membership=membership, school=school, label="2024-2025"
        )

    return make


@pytest.fixture
def group_for(school_year_for):
    from schools.services import create_group

    def make(membership, school_year=None):
        school_year = school_year or school_year_for(membership)
        return create_group(
            membership=membership,
            school_year=school_year,
            grado=1,
            grupo="A",
        )

    return make


@pytest.fixture
def student_for(group_for):
    from students.services import create_student

    def make(membership, group=None, *, first_name="Ana", last_name_paternal="Perez"):
        group = group or group_for(membership)
        return create_student(
            membership=membership,
            group=group,
            first_name=first_name,
            last_name_paternal=last_name_paternal,
        )

    return make


@pytest.fixture
def term_for(school_year_for):
    from grades.services import ensure_terms

    def make(membership, school_year=None):
        school_year = school_year or school_year_for(membership)
        return ensure_terms(school_year=school_year)[0]

    return make


def _activity_payload(group_id, term_id, **overrides):
    payload = {
        "group": group_id,
        "term": term_id,
        "title": "Ensayo literario",
        "type": "task",
        "due_date": "2026-08-15",
        "field": "languages",
        "subject_ids": ["spanish"],
        "description": "Leer y escribir",
    }
    payload.update(overrides)
    return payload


def test_activities_require_group_and_term(
    membership_factory, api_client_for, group_for, term_for
):
    membership = membership_factory()
    group = group_for(membership)
    term = term_for(membership, school_year=group.school_year)
    client = api_client_for(membership)

    assert client.get("/api/grades/activities/").status_code == 400
    assert (
        client.get("/api/grades/activities/", {"group": group.pk}).status_code == 400
    )
    assert client.get("/api/grades/activities/", {"term": term.pk}).status_code == 400


def test_activities_require_workspace_header(membership_factory, group_for, term_for):
    membership = membership_factory()
    group = group_for(membership)
    term = term_for(membership, school_year=group.school_year)
    client = APIClient()
    client.force_login(membership.user)

    response = client.get(
        "/api/grades/activities/",
        {"group": group.pk, "term": term.pk},
    )

    assert response.status_code == 403


def test_create_then_list_activity(
    membership_factory, api_client_for, group_for, term_for
):
    membership = membership_factory()
    group = group_for(membership)
    term = term_for(membership, school_year=group.school_year)
    client = api_client_for(membership)

    create_resp = client.post(
        "/api/grades/activities/",
        _activity_payload(group.pk, term.pk),
        format="json",
    )
    assert create_resp.status_code == 201
    assert create_resp.data["title"] == "Ensayo literario"
    assert create_resp.data["type"] == "task"
    assert create_resp.data["field"] == "languages"
    assert create_resp.data["subject_ids"] == ["spanish"]

    list_resp = client.get(
        "/api/grades/activities/",
        {"group": group.pk, "term": term.pk},
    )
    assert list_resp.status_code == 200
    assert {t["number"] for t in list_resp.data["terms"]} == {1, 2, 3}
    assert len(list_resp.data["activities"]) == 1
    assert list_resp.data["activities"][0]["title"] == "Ensayo literario"
    assert list_resp.data["stats"]["total_activities"] == 1


def test_list_filters_by_type_and_q(
    membership_factory, api_client_for, group_for, term_for
):
    membership = membership_factory()
    group = group_for(membership)
    term = term_for(membership, school_year=group.school_year)
    client = api_client_for(membership)

    client.post(
        "/api/grades/activities/",
        _activity_payload(group.pk, term.pk, title="Tarea español", type="task"),
        format="json",
    )
    client.post(
        "/api/grades/activities/",
        _activity_payload(
            group.pk,
            term.pk,
            title="Examen mates",
            type="exam",
            field="scientific-thinking",
            subject_ids=["mathematics"],
        ),
        format="json",
    )

    filtered = client.get(
        "/api/grades/activities/",
        {"group": group.pk, "term": term.pk, "type": "task", "q": "español"},
    )
    assert filtered.status_code == 200
    assert len(filtered.data["activities"]) == 1
    assert filtered.data["activities"][0]["title"] == "Tarea español"


def test_list_foreign_group_denied(
    membership_factory, api_client_for, group_for, term_for
):
    membership_a = membership_factory()
    membership_b = membership_factory()
    foreign_group = group_for(membership_b)
    foreign_term = term_for(membership_b, school_year=foreign_group.school_year)
    client_a = api_client_for(membership_a)

    response = client_a.get(
        "/api/grades/activities/",
        {"group": foreign_group.pk, "term": foreign_term.pk},
    )

    assert response.status_code == 404


def test_matrix_mixed_cells_null_not_zero(
    membership_factory, api_client_for, group_for, term_for, student_for
):
    from grades.models import ActivityScore
    from grades.services import create_activity
    from workspaces.context import active_workspace

    membership = membership_factory()
    group = group_for(membership)
    term = term_for(membership, school_year=group.school_year)
    student_a = student_for(membership, group, first_name="Ana")
    student_for(membership, group, first_name="Beto")
    activity = create_activity(
        membership=membership,
        group=group,
        term=term,
        title="Quiz",
        activity_type="exam",
        due_date=datetime.date(2026, 8, 20),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )
    token = active_workspace.set(membership.workspace_id)
    try:
        ActivityScore.objects.create(
            workspace=membership.workspace,
            activity=activity,
            student=student_a,
            score=Decimal("8.5"),
        )
    finally:
        active_workspace.reset(token)

    client = api_client_for(membership)
    response = client.get(
        "/api/grades/scores/matrix/",
        {"group": group.pk, "term": term.pk},
    )

    assert response.status_code == 200
    assert {t["number"] for t in response.data["terms"]} == {1, 2, 3}
    assert len(response.data["students"]) == 2
    assert len(response.data["activities"]) == 1
    by_student = {
        (row["student"], row["activity"]): row["score"]
        for row in response.data["scores"]
    }
    assert by_student[(student_a.pk, activity.pk)] == Decimal("8.5")
    null_scores = [score for score in by_student.values() if score is None]
    assert len(null_scores) == 1
    assert Decimal("0.0") not in by_student.values()
    assert 0.0 not in by_student.values()


def test_bulk_upsert_persists_all_entries(
    membership_factory, api_client_for, group_for, term_for, student_for
):
    from grades.services import create_activity

    membership = membership_factory()
    group = group_for(membership)
    term = term_for(membership, school_year=group.school_year)
    student_a = student_for(membership, group, first_name="Ana")
    student_b = student_for(membership, group, first_name="Beto")
    activity = create_activity(
        membership=membership,
        group=group,
        term=term,
        title="Quiz",
        activity_type="exam",
        due_date=datetime.date(2026, 8, 20),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )
    client = api_client_for(membership)

    response = client.put(
        "/api/grades/scores/bulk/",
        {
            "group": group.pk,
            "entries": [
                {"student": student_a.pk, "activity": activity.pk, "score": "8.5"},
                {"student": student_b.pk, "activity": activity.pk, "score": None},
            ],
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["saved"] == 2

    matrix = client.get(
        "/api/grades/scores/matrix/",
        {"group": group.pk, "term": term.pk},
    )
    by_student = {
        (row["student"], row["activity"]): row["score"]
        for row in matrix.data["scores"]
    }
    assert by_student[(student_a.pk, activity.pk)] == Decimal("8.5")
    assert by_student[(student_b.pk, activity.pk)] is None


def test_bulk_rejects_wrong_student_no_partial_write(
    membership_factory, api_client_for, group_for, term_for, student_for
):
    from grades.models import ActivityScore
    from grades.services import create_activity
    from workspaces.context import active_workspace

    membership = membership_factory()
    other = membership_factory()
    group = group_for(membership)
    foreign_group = group_for(other)
    term = term_for(membership, school_year=group.school_year)
    student_in = student_for(membership, group, first_name="Ana")
    outsider = student_for(other, foreign_group, first_name="Carla")
    activity = create_activity(
        membership=membership,
        group=group,
        term=term,
        title="Quiz",
        activity_type="exam",
        due_date=datetime.date(2026, 8, 20),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )
    client = api_client_for(membership)

    response = client.put(
        "/api/grades/scores/bulk/",
        {
            "group": group.pk,
            "entries": [
                {"student": student_in.pk, "activity": activity.pk, "score": "7.0"},
                {"student": outsider.pk, "activity": activity.pk, "score": "6.0"},
            ],
        },
        format="json",
    )

    assert response.status_code == 400
    token = active_workspace.set(membership.workspace_id)
    try:
        assert ActivityScore.objects.count() == 0
    finally:
        active_workspace.reset(token)


def test_bulk_rejects_score_out_of_bounds_no_partial_write(
    membership_factory, api_client_for, group_for, term_for, student_for
):
    from grades.models import ActivityScore
    from grades.services import create_activity
    from workspaces.context import active_workspace

    membership = membership_factory()
    group = group_for(membership)
    term = term_for(membership, school_year=group.school_year)
    student = student_for(membership, group)
    activity = create_activity(
        membership=membership,
        group=group,
        term=term,
        title="Quiz",
        activity_type="exam",
        due_date=datetime.date(2026, 8, 20),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )
    client = api_client_for(membership)

    response = client.put(
        "/api/grades/scores/bulk/",
        {
            "group": group.pk,
            "entries": [
                {"student": student.pk, "activity": activity.pk, "score": "10.5"},
            ],
        },
        format="json",
    )

    assert response.status_code == 400
    token = active_workspace.set(membership.workspace_id)
    try:
        assert ActivityScore.objects.count() == 0
    finally:
        active_workspace.reset(token)


def test_list_capability_maps_to_view_workspace(membership_factory, monkeypatch):
    from grades.views import ActivitiesView
    from workspaces import permissions

    membership = membership_factory()
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeRequest:
        pass

    request = FakeRequest()
    request.membership = membership
    view = ActivitiesView()
    view.action = "list"

    assert permissions.WorkspacePermission().has_permission(request, view) is True
    assert calls == [(membership, "view_workspace")]


def test_create_capability_maps_to_edit_content(membership_factory, monkeypatch):
    from grades.views import ActivitiesView
    from workspaces import permissions

    membership = membership_factory()
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeRequest:
        pass

    request = FakeRequest()
    request.membership = membership
    view = ActivitiesView()
    view.action = "create"

    assert permissions.WorkspacePermission().has_permission(request, view) is True
    assert calls == [(membership, "edit_content")]


def test_matrix_capability_maps_to_view_workspace(membership_factory, monkeypatch):
    from grades.views import ScoresMatrixView
    from workspaces import permissions

    membership = membership_factory()
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeRequest:
        pass

    request = FakeRequest()
    request.membership = membership
    view = ScoresMatrixView()
    view.action = "matrix"

    assert permissions.WorkspacePermission().has_permission(request, view) is True
    assert calls == [(membership, "view_workspace")]


def test_bulk_capability_maps_to_edit_content(membership_factory, monkeypatch):
    from grades.views import ScoresBulkView
    from workspaces import permissions

    membership = membership_factory()
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeRequest:
        pass

    request = FakeRequest()
    request.membership = membership
    view = ScoresBulkView()
    view.action = "bulk"

    assert permissions.WorkspacePermission().has_permission(request, view) is True
    assert calls == [(membership, "edit_content")]


def test_write_denied_without_edit_content(
    membership_factory, api_client_for, group_for, term_for, student_for
):
    from grades.models import Activity, ActivityScore
    from grades.services import create_activity
    from workspaces.context import active_workspace

    membership = membership_factory()
    group = group_for(membership)
    term = term_for(membership, school_year=group.school_year)
    student = student_for(membership, group)
    activity = create_activity(
        membership=membership,
        group=group,
        term=term,
        title="Quiz",
        activity_type="exam",
        due_date=datetime.date(2026, 8, 20),
        formative_field_id="languages",
        subject_ids=["spanish"],
    )
    membership.role = "viewer-only"
    membership.save(update_fields=["role"])
    client = api_client_for(membership)

    create_resp = client.post(
        "/api/grades/activities/",
        _activity_payload(group.pk, term.pk, title="Blocked"),
        format="json",
    )
    bulk_resp = client.put(
        "/api/grades/scores/bulk/",
        {
            "group": group.pk,
            "entries": [
                {"student": student.pk, "activity": activity.pk, "score": "9.0"},
            ],
        },
        format="json",
    )

    assert create_resp.status_code == 403
    assert bulk_resp.status_code == 403
    token = active_workspace.set(membership.workspace_id)
    try:
        assert Activity.objects.filter(title="Blocked").count() == 0
        assert ActivityScore.objects.count() == 0
    finally:
        active_workspace.reset(token)


def test_read_denied_without_view_workspace(
    membership_factory, api_client_for, group_for, term_for
):
    membership = membership_factory()
    group = group_for(membership)
    term = term_for(membership, school_year=group.school_year)
    membership.role = "no-capabilities-role"
    membership.save(update_fields=["role"])
    client = api_client_for(membership)

    list_resp = client.get(
        "/api/grades/activities/",
        {"group": group.pk, "term": term.pk},
    )
    matrix_resp = client.get(
        "/api/grades/scores/matrix/",
        {"group": group.pk, "term": term.pk},
    )

    assert list_resp.status_code == 403
    assert matrix_resp.status_code == 403
