"""RED tests for GET /api/workspaces/ (workspaces spec — "Workspace-List
Endpoint Returns Only the Caller's Memberships"; tenancy-isolation spec —
"Workspace-List Read Exposes Only the Caller's Own Membership Rows").
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from workspaces.models import Membership, Workspace

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def user_factory():
    counter = {"n": 0}

    def make(email=None):
        counter["n"] += 1
        return User.objects.create_user(
            email=email or f"user{counter['n']}@example.com",
            password="s3cret-pass",
        )

    return make


def test_workspace_list_returns_only_the_callers_own_memberships(user_factory):
    user = user_factory()
    personal = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    Membership.objects.create(user=user, workspace=personal, role=Membership.Role.OWNER)

    group_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    Membership.objects.create(user=user, workspace=group_b, role=Membership.Role.MEMBER)

    client = APIClient()
    client.force_login(user)
    response = client.get("/api/workspaces/")

    assert response.status_code == 200
    workspace_ids = {entry["id"] for entry in response.json()}
    assert workspace_ids == {str(personal.id), str(group_b.id)}
    for entry in response.json():
        assert set(entry.keys()) == {"id", "name", "type", "role"}


def test_workspace_list_never_includes_another_users_workspace(user_factory):
    user = user_factory()
    personal = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    Membership.objects.create(user=user, workspace=personal, role=Membership.Role.OWNER)

    other_user = user_factory()
    other_workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    Membership.objects.create(
        user=other_user, workspace=other_workspace, role=Membership.Role.OWNER
    )

    client = APIClient()
    client.force_login(user)
    response = client.get("/api/workspaces/")

    assert response.status_code == 200
    workspace_ids = {entry["id"] for entry in response.json()}
    assert str(other_workspace.id) not in workspace_ids


def test_workspace_list_denies_anonymous_request():
    client = APIClient()
    response = client.get("/api/workspaces/")
    assert response.status_code in (401, 403)


def test_workspace_list_does_not_require_workspace_header(user_factory):
    """No X-Workspace-Id needed — the view reads the caller's own memberships
    directly, bypassing `WorkspacePermission`/`ScopedManager` entirely.
    (`TenancyMiddleware` still falls back to the personal workspace for any
    authenticated request with no header — that fallback is pre-existing,
    global middleware behavior, not something this endpoint opts into.)
    """
    user = user_factory()
    personal = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    Membership.objects.create(user=user, workspace=personal, role=Membership.Role.OWNER)
    group = Workspace.objects.create(type=Workspace.Type.GROUP)
    Membership.objects.create(user=user, workspace=group, role=Membership.Role.OWNER)

    client = APIClient()
    client.force_login(user)
    response = client.get("/api/workspaces/")

    assert response.status_code == 200
    workspace_ids = {entry["id"] for entry in response.json()}
    assert workspace_ids == {str(personal.id), str(group.id)}
