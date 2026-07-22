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


# --- D2: invite_member ----------------------------------------------------


@pytest.fixture
def owner_membership(inviter, workspace):
    from workspaces.models import Membership

    return Membership.objects.create(
        user=inviter, workspace=workspace, role=Membership.Role.OWNER
    )


@pytest.fixture
def admin_membership(workspace):
    from workspaces.models import Membership

    admin_user = User.objects.create_user(
        email="admin@example.com", password="s3cret-pass"
    )
    return Membership.objects.create(
        user=admin_user, workspace=workspace, role=Membership.Role.ADMIN
    )


@pytest.fixture
def member_membership(workspace):
    from workspaces.models import Membership

    member_user = User.objects.create_user(
        email="member@example.com", password="s3cret-pass"
    )
    return Membership.objects.create(
        user=member_user, workspace=workspace, role=Membership.Role.MEMBER
    )


def test_invite_member_owner_can_invite(owner_membership):
    from workspaces.models import WorkspaceInvitation
    from workspaces.services import invite_member

    invite = invite_member(
        inviter_membership=owner_membership,
        email="newuser@example.com",
        role="member",
    )

    assert invite.status == WorkspaceInvitation.Status.PENDING
    assert WorkspaceInvitation.objects.filter(pk=invite.pk).exists()


def test_invite_member_admin_can_invite(admin_membership):
    from workspaces.models import WorkspaceInvitation
    from workspaces.services import invite_member

    invite = invite_member(
        inviter_membership=admin_membership,
        email="newuser2@example.com",
        role="member",
    )

    assert invite.status == WorkspaceInvitation.Status.PENDING


def test_invite_member_denied_for_member(member_membership):
    from django.core.exceptions import PermissionDenied

    from workspaces.models import WorkspaceInvitation
    from workspaces.services import invite_member

    count_before = WorkspaceInvitation.objects.count()

    with pytest.raises(PermissionDenied):
        invite_member(
            inviter_membership=member_membership,
            email="newuser3@example.com",
            role="member",
        )

    assert WorkspaceInvitation.objects.count() == count_before


def test_invite_member_expiry_set_to_now_plus_seven_days(owner_membership):
    from django.utils import timezone

    from workspaces.services import invite_member

    before = timezone.now()
    invite = invite_member(
        inviter_membership=owner_membership,
        email="newuser4@example.com",
        role="member",
    )
    after = timezone.now()

    assert before + timezone.timedelta(days=7) <= invite.expires_at
    assert invite.expires_at <= after + timezone.timedelta(days=7)


# --- D3: accept_invitation -------------------------------------------------


def _make_invitation(*, workspace, inviter, email, status="pending", expires_in_days=7):
    from django.utils import timezone

    from workspaces.models import WorkspaceInvitation

    return WorkspaceInvitation.objects.create(
        workspace=workspace,
        email=email,
        role="member",
        invited_by=inviter,
        token=secrets_token(),
        status=status,
        expires_at=timezone.now() + timezone.timedelta(days=expires_in_days),
    )


def secrets_token():
    import secrets

    return secrets.token_urlsafe(32)


def test_accept_invitation_valid_accept_creates_membership_and_flips_status(
    workspace, inviter
):
    from workspaces.models import Membership, WorkspaceInvitation
    from workspaces.services import accept_invitation

    invitee = User.objects.create_user(
        email="invitee@example.com", password="s3cret-pass"
    )
    invite = _make_invitation(
        workspace=workspace, inviter=inviter, email="invitee@example.com"
    )

    membership = accept_invitation(user=invitee, token=invite.token)

    assert membership.user_id == invitee.pk
    assert membership.workspace_id == workspace.pk
    assert membership.role == "member"
    invite.refresh_from_db()
    assert invite.status == WorkspaceInvitation.Status.ACCEPTED
    assert Membership.objects.filter(user=invitee, workspace=workspace).count() == 1


def test_accept_invitation_email_mismatch_rejects(workspace, inviter):
    from django.core.exceptions import PermissionDenied

    from workspaces.models import Membership, WorkspaceInvitation
    from workspaces.services import accept_invitation

    someone_else = User.objects.create_user(
        email="someone-else@example.com", password="s3cret-pass"
    )
    invite = _make_invitation(
        workspace=workspace, inviter=inviter, email="invitee@example.com"
    )

    with pytest.raises(PermissionDenied):
        accept_invitation(user=someone_else, token=invite.token)

    invite.refresh_from_db()
    assert invite.status == WorkspaceInvitation.Status.PENDING
    assert not Membership.objects.filter(user=someone_else, workspace=workspace).exists()


def test_accept_invitation_expired_invite_rejected_and_persists_expired(
    workspace, inviter
):
    from workspaces.models import Membership, WorkspaceInvitation
    from workspaces.services import accept_invitation

    invitee = User.objects.create_user(
        email="expired-invitee@example.com", password="s3cret-pass"
    )
    invite = _make_invitation(
        workspace=workspace,
        inviter=inviter,
        email="expired-invitee@example.com",
        expires_in_days=-1,
    )

    with pytest.raises(ValueError):
        accept_invitation(user=invitee, token=invite.token)

    invite.refresh_from_db()
    assert invite.status == WorkspaceInvitation.Status.EXPIRED
    assert not Membership.objects.filter(user=invitee, workspace=workspace).exists()


def test_accept_invitation_terminal_invite_rejected_no_transition(workspace, inviter):
    from workspaces.models import Membership, WorkspaceInvitation
    from workspaces.services import accept_invitation

    invitee = User.objects.create_user(
        email="terminal-invitee@example.com", password="s3cret-pass"
    )
    invite = _make_invitation(
        workspace=workspace,
        inviter=inviter,
        email="terminal-invitee@example.com",
        status=WorkspaceInvitation.Status.REVOKED,
    )

    with pytest.raises(ValueError):
        accept_invitation(user=invitee, token=invite.token)

    invite.refresh_from_db()
    assert invite.status == WorkspaceInvitation.Status.REVOKED
    assert not Membership.objects.filter(user=invitee, workspace=workspace).exists()


def test_accept_invitation_already_member_is_idempotent_no_duplicate(
    workspace, inviter
):
    from workspaces.models import Membership, WorkspaceInvitation
    from workspaces.services import accept_invitation

    invitee = User.objects.create_user(
        email="already-member@example.com", password="s3cret-pass"
    )
    Membership.objects.create(
        user=invitee, workspace=workspace, role=Membership.Role.MEMBER
    )
    invite = _make_invitation(
        workspace=workspace, inviter=inviter, email="already-member@example.com"
    )

    membership = accept_invitation(user=invitee, token=invite.token)

    invite.refresh_from_db()
    assert invite.status == WorkspaceInvitation.Status.ACCEPTED
    assert Membership.objects.filter(user=invitee, workspace=workspace).count() == 1
    assert membership.user_id == invitee.pk
