"""RED HTTP tests for the students DRF surface (school-structure spec — DRF
CRUD Endpoints Are Workspace-Scoped and Isolated).
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

User = get_user_model()


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
def group_for(api_client_for):
    def make(membership):
        client = api_client_for(membership)
        school_resp = client.post(
            "/api/schools/", {"name": "Escuela Uno", "cct": "", "level": "primaria"}
        )
        school_year_resp = client.post(
            "/api/school-years/",
            {"school": school_resp.data["id"], "label": "2024-2025"},
        )
        group_resp = client.post(
            "/api/groups/",
            {"school_year": school_year_resp.data["id"], "grado": 1, "grupo": "A"},
        )
        return group_resp.data["id"]

    return make


def test_create_student_scopes_to_membership_workspace(
    membership_factory, api_client_for, group_for
):
    membership = membership_factory("member")
    group_id = group_for(membership)
    client = api_client_for(membership)

    response = client.post(
        "/api/students/",
        {"group": group_id, "first_name": "Ana", "last_name_paternal": "Perez"},
    )

    assert response.status_code == 201
    assert response.data["workspace"] == membership.workspace_id


def test_list_students_is_isolated_per_workspace(
    membership_factory, api_client_for, group_for
):
    membership_a = membership_factory("member")
    membership_b = membership_factory("member")
    group_a = group_for(membership_a)
    group_b = group_for(membership_b)
    client_a = api_client_for(membership_a)
    client_b = api_client_for(membership_b)

    client_a.post(
        "/api/students/",
        {"group": group_a, "first_name": "Mine", "last_name_paternal": "A"},
    )
    client_b.post(
        "/api/students/",
        {"group": group_b, "first_name": "NotMine", "last_name_paternal": "B"},
    )

    response = client_a.get("/api/students/")

    names = [row["first_name"] for row in response.data]
    assert names == ["Mine"]


def test_retrieve_foreign_workspace_student_returns_404(
    membership_factory, api_client_for, group_for
):
    membership_a = membership_factory("member")
    membership_b = membership_factory("member")
    group_b = group_for(membership_b)
    client_a = api_client_for(membership_a)
    client_b = api_client_for(membership_b)

    create_response = client_b.post(
        "/api/students/",
        {"group": group_b, "first_name": "Ajena", "last_name_paternal": "B"},
    )
    student_id = create_response.data["id"]

    response = client_a.get(f"/api/students/{student_id}/")

    assert response.status_code == 404


def test_write_denied_without_edit_content_returns_403(
    membership_factory, api_client_for, group_for
):
    membership = membership_factory("member")
    group_id = group_for(membership)
    membership.role = "no-capabilities-role"
    membership.save(update_fields=["role"])
    client = api_client_for(membership)

    response = client.post(
        "/api/students/",
        {"group": group_id, "first_name": "Ana", "last_name_paternal": "Perez"},
    )

    assert response.status_code == 403


def test_update_student_success(membership_factory, api_client_for, group_for):
    membership = membership_factory("member")
    group_id = group_for(membership)
    client = api_client_for(membership)

    create_response = client.post(
        "/api/students/",
        {"group": group_id, "first_name": "Ana", "last_name_paternal": "Perez"},
    )
    student_id = create_response.data["id"]

    response = client.patch(f"/api/students/{student_id}/", {"first_name": "Ana Maria"})

    assert response.status_code == 200
    assert response.data["first_name"] == "Ana Maria"


def test_destroy_student_success(membership_factory, api_client_for, group_for):
    membership = membership_factory("member")
    group_id = group_for(membership)
    client = api_client_for(membership)

    create_response = client.post(
        "/api/students/",
        {"group": group_id, "first_name": "Ana", "last_name_paternal": "Perez"},
    )
    student_id = create_response.data["id"]

    response = client.delete(f"/api/students/{student_id}/")

    assert response.status_code == 204
