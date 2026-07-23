"""RED HTTP tests for the schools DRF surface (school-structure spec — DRF
CRUD Endpoints Are Workspace-Scoped and Isolated; PROTECT Surfaces a Clean
4xx on Group Delete With Students).
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
        membership = Membership.objects.create(user=user, workspace=workspace, role=role)
        return membership

    return make


@pytest.fixture
def api_client_for(membership_factory):
    def make(membership):
        client = APIClient()
        client.force_login(membership.user)
        client.credentials(HTTP_X_WORKSPACE_ID=str(membership.workspace_id))
        return client

    return make


def test_create_school_scopes_to_membership_workspace(membership_factory, api_client_for):
    membership = membership_factory("member")
    client = api_client_for(membership)

    response = client.post(
        "/api/schools/", {"name": "Escuela Uno", "cct": "", "level": "primaria"}
    )

    assert response.status_code == 201
    assert response.data["workspace"] == membership.workspace_id


def test_list_schools_is_isolated_per_workspace(membership_factory, api_client_for):
    membership_a = membership_factory("member")
    membership_b = membership_factory("member")
    client_a = api_client_for(membership_a)
    client_b = api_client_for(membership_b)

    client_a.post("/api/schools/", {"name": "Mine", "cct": "", "level": "primaria"})
    client_b.post("/api/schools/", {"name": "NotMine", "cct": "", "level": "primaria"})

    response = client_a.get("/api/schools/")

    names = [row["name"] for row in response.data["results"]] if "results" in response.data else [
        row["name"] for row in response.data
    ]
    assert names == ["Mine"]


def test_retrieve_foreign_workspace_school_returns_404(membership_factory, api_client_for):
    membership_a = membership_factory("member")
    membership_b = membership_factory("member")
    client_a = api_client_for(membership_a)
    client_b = api_client_for(membership_b)

    create_response = client_b.post(
        "/api/schools/", {"name": "Ajena", "cct": "", "level": "primaria"}
    )
    school_id = create_response.data["id"]

    response = client_a.get(f"/api/schools/{school_id}/")

    assert response.status_code == 404


def test_write_denied_without_edit_content_returns_403(membership_factory, api_client_for):
    membership = membership_factory("member")
    membership.role = "no-capabilities-role"
    membership.save(update_fields=["role"])
    client = api_client_for(membership)

    response = client.post(
        "/api/schools/", {"name": "Escuela Uno", "cct": "", "level": "primaria"}
    )

    assert response.status_code == 403


def test_update_school_success(membership_factory, api_client_for):
    membership = membership_factory("member")
    client = api_client_for(membership)

    create_response = client.post(
        "/api/schools/", {"name": "Escuela Uno", "cct": "", "level": "primaria"}
    )
    school_id = create_response.data["id"]

    response = client.patch(f"/api/schools/{school_id}/", {"name": "Nuevo Nombre"})

    assert response.status_code == 200
    assert response.data["name"] == "Nuevo Nombre"


def test_destroy_school_success(membership_factory, api_client_for):
    membership = membership_factory("member")
    client = api_client_for(membership)

    create_response = client.post(
        "/api/schools/", {"name": "Escuela Uno", "cct": "", "level": "primaria"}
    )
    school_id = create_response.data["id"]

    response = client.delete(f"/api/schools/{school_id}/")

    assert response.status_code == 204


def test_group_delete_with_students_returns_clean_4xx(membership_factory, api_client_for):
    membership = membership_factory("member")
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
    group_id = group_resp.data["id"]

    from schools.models import Group
    from students.models import Student
    from workspaces.context import active_workspace

    token = active_workspace.set(membership.workspace_id)
    try:
        group = Group.objects.get(pk=group_id)
        Student.objects.create(
            workspace_id=membership.workspace_id,
            group=group,
            first_name="Ana",
            last_name_paternal="Perez",
        )
    finally:
        active_workspace.reset(token)

    response = client.delete(f"/api/groups/{group_id}/")

    assert 400 <= response.status_code < 500
