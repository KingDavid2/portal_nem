"""RED tests for Workspace/Membership models (workspaces spec)."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(email="teacher@example.com", password="s3cret-pass")


def test_workspace_type_restricted_to_allowed_values():
    from workspaces.models import Workspace

    workspace = Workspace(type="enterprise")
    with pytest.raises(ValidationError):
        workspace.full_clean()


def test_workspace_type_accepts_personal_and_group():
    from workspaces.models import Workspace

    personal = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    group = Workspace.objects.create(type=Workspace.Type.GROUP)
    assert personal.type == "personal"
    assert group.type == "group"


def test_membership_role_restricted_to_allowed_values(user):
    from workspaces.models import Membership, Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    membership = Membership(user=user, workspace=workspace, role="superadmin")
    with pytest.raises(ValidationError):
        membership.full_clean()


def test_membership_role_is_charfield_with_choices():
    from workspaces.models import Membership

    role_field = Membership._meta.get_field("role")
    assert isinstance(role_field, models.CharField)
    assert role_field.choices is not None
    assert {"owner", "admin", "member"} == {value for value, _ in role_field.choices}


def test_membership_accepts_valid_roles(user):
    from workspaces.models import Membership, Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    membership = Membership.objects.create(
        user=user, workspace=workspace, role=Membership.Role.OWNER
    )
    assert membership.role == "owner"


def test_scoped_model_provides_workspace_fk():
    from workspaces.models import ScopedModel, Workspace

    assert ScopedModel._meta.abstract is True
    workspace_field = ScopedModel._meta.get_field("workspace")
    assert workspace_field.remote_field.model is Workspace
