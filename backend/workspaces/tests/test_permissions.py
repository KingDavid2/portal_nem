"""RED tests for the capability matrix + DRF permission (authorization spec)."""

import inspect

import pytest
from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def membership_factory():
    from workspaces.models import Membership, Workspace

    def make(role):
        user = User.objects.create_user(
            email=f"{role}@example.com", password="s3cret-pass"
        )
        workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
        return Membership.objects.create(user=user, workspace=workspace, role=role)

    return make


def test_owner_permitted_a_privileged_action(membership_factory):
    from workspaces.permissions import has_permission

    membership = membership_factory("owner")
    assert has_permission(membership, action="delete_workspace") is True


def test_member_denied_a_privileged_action(membership_factory):
    from workspaces.permissions import has_permission

    membership = membership_factory("member")
    assert has_permission(membership, action="delete_workspace") is False


def test_unknown_role_denied():
    from workspaces.permissions import has_permission

    class FakeMembership:
        role = "totally-unknown"

    assert has_permission(FakeMembership(), action="delete_workspace") is False


def test_drf_permission_class_delegates_to_has_permission(membership_factory, monkeypatch):
    from workspaces import permissions

    assert issubclass(permissions.WorkspacePermission, BasePermission)

    membership = membership_factory("member")
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeView:
        action = "destroy"
        capability_map = {"destroy": "edit_content"}

    class FakeRequest:
        pass

    permission = permissions.WorkspacePermission()
    request = FakeRequest()
    request.membership = membership

    assert (
        permission.has_object_permission(request, FakeView(), membership) is True
    )
    assert calls == [(membership, "edit_content")]


def test_has_permission_resolves_via_capability_map_for_read_actions(
    membership_factory, monkeypatch
):
    from workspaces import permissions

    membership = membership_factory("member")
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeView:
        action = "list"
        capability_map = {
            "list": "view_workspace",
            "retrieve": "view_workspace",
            "create": "edit_content",
            "update": "edit_content",
            "partial_update": "edit_content",
            "destroy": "edit_content",
        }

    class FakeRequest:
        pass

    permission = permissions.WorkspacePermission()
    request = FakeRequest()
    request.membership = membership

    assert permission.has_permission(request, FakeView()) is True
    assert calls == [(membership, "view_workspace")]


def test_has_permission_resolves_via_capability_map_for_write_actions(
    membership_factory, monkeypatch
):
    from workspaces import permissions

    membership = membership_factory("member")
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeView:
        action = "create"
        capability_map = {
            "list": "view_workspace",
            "retrieve": "view_workspace",
            "create": "edit_content",
            "update": "edit_content",
            "partial_update": "edit_content",
            "destroy": "edit_content",
        }

    class FakeRequest:
        pass

    permission = permissions.WorkspacePermission()
    request = FakeRequest()
    request.membership = membership

    assert permission.has_permission(request, FakeView()) is True
    assert calls == [(membership, "edit_content")]


def test_has_object_permission_also_resolves_via_capability_map(
    membership_factory, monkeypatch
):
    from workspaces import permissions

    membership = membership_factory("member")
    calls = []

    def fake_has_permission(passed_membership, action):
        calls.append((passed_membership, action))
        return True

    monkeypatch.setattr(permissions, "has_permission", fake_has_permission)

    class FakeView:
        action = "destroy"
        capability_map = {"destroy": "edit_content"}

    class FakeRequest:
        pass

    permission = permissions.WorkspacePermission()
    request = FakeRequest()
    request.membership = membership

    assert permission.has_object_permission(request, FakeView(), membership) is True
    assert calls == [(membership, "edit_content")]


def test_permissions_module_has_no_inline_role_string_comparisons():
    from workspaces import permissions

    # Gate #4 — no inline role-string comparison anywhere in the module.
    source = inspect.getsource(permissions)
    assert ".role ==" not in source
    assert ".role !=" not in source
