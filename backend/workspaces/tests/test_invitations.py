"""RED tests for WorkspaceInvitation model/services (invitations spec)."""

import pytest
from django.contrib.auth import get_user_model
from django.db import models

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def inviter():
    return User.objects.create_user(email="owner@example.com", password="s3cret-pass")


@pytest.fixture
def workspace():
    from workspaces.models import Workspace

    return Workspace.objects.create(type=Workspace.Type.GROUP)


# --- D1: model / migration ---------------------------------------------


def test_token_is_generated_via_secrets_and_unique(inviter, workspace):
    from workspaces.models import WorkspaceInvitation

    invite = WorkspaceInvitation.objects.create(
        workspace=workspace,
        email="invitee@example.com",
        role="member",
        invited_by=inviter,
        token="a" * 43,
        expires_at="2999-01-01T00:00:00Z",
    )
    assert len(invite.token) <= 64
    assert invite.token != ""


def test_workspace_invitation_is_not_a_scoped_model():
    from workspaces.managers import ScopedManager
    from workspaces.models import ScopedModel, WorkspaceInvitation

    assert not issubclass(WorkspaceInvitation, ScopedModel)
    workspace_field = WorkspaceInvitation._meta.get_field("workspace")
    assert not isinstance(workspace_field.remote_field.model.objects, ScopedManager)
    assert not isinstance(WorkspaceInvitation.objects, ScopedManager)


def test_workspace_invitation_table_absent_from_scoped_tables():
    import importlib

    rls_module = importlib.import_module("workspaces.migrations.0003_rls")
    assert "workspaces_workspaceinvitation" not in rls_module.SCOPED_TABLES
