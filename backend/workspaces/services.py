"""Signup provisioning (workspaces spec — Transactional Signup Provisioning).

A single atomic transaction creates the new User, a personal Workspace for
them, and an owner Membership linking the two. Any failure mid-transaction
(e.g. a duplicate email) rolls back every record created in this attempt —
no orphaned User, Workspace, or Membership is left behind.
"""

import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from workspaces.models import Membership, Workspace, WorkspaceInvitation
from workspaces.permissions import has_permission

User = get_user_model()

INVITATION_TOKEN_BYTES = 32
INVITATION_EXPIRY = timedelta(days=7)


def provision_signup(*, email: str, password: str) -> "User":
    """Create a User, personal Workspace, and owner Membership atomically."""
    with transaction.atomic():
        workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
        user = User.objects.create_user(email=email, password=password)
        Membership.objects.create(
            user=user, workspace=workspace, role=Membership.Role.OWNER
        )
    return user


def invite_member(
    *, inviter_membership: Membership, email: str, role: str
) -> WorkspaceInvitation:
    """Create a `pending` invite for `email` in the inviter's workspace.

    Requires `has_permission(inviter_membership, "manage_members")`
    (owner/admin) — invitations spec, Invite Creation Authorization.
    """
    if not has_permission(inviter_membership, "manage_members"):
        raise PermissionDenied("Only owners and admins may invite members.")

    return WorkspaceInvitation.objects.create(
        workspace=inviter_membership.workspace,
        email=email,
        role=role,
        invited_by=inviter_membership.user,
        token=secrets.token_urlsafe(INVITATION_TOKEN_BYTES),
        expires_at=timezone.now() + INVITATION_EXPIRY,
        status=WorkspaceInvitation.Status.PENDING,
    )


def accept_invitation(*, user: "User", token: str) -> Membership:
    """Accept a pending, non-expired invite whose email matches `user`.

    Atomically creates `Membership(user, invite.workspace, invite.role)` and
    flips `invite.status = accepted` (invitations spec — Accept Flow). Lazy
    expiry is evaluated first: a `pending` row past `expires_at` is persisted
    as `expired` and rejected before the terminal-state check. If the user
    already holds a Membership in the workspace, accept is an idempotent
    no-op (invitations spec — Idempotent Accept for Existing Members).
    """
    invite = WorkspaceInvitation.objects.get(token=token)

    if (
        invite.status == WorkspaceInvitation.Status.PENDING
        and invite.expires_at < timezone.now()
    ):
        invite.status = WorkspaceInvitation.Status.EXPIRED
        invite.save(update_fields=["status"])
        raise ValueError("Invitation has expired.")

    if invite.status != WorkspaceInvitation.Status.PENDING:
        raise ValueError(f"Invitation is not pending (status={invite.status}).")

    if invite.email != user.email:
        raise PermissionDenied("This invitation was sent to a different email.")

    with transaction.atomic():
        membership, _ = Membership.objects.get_or_create(
            user=user,
            workspace=invite.workspace,
            defaults={"role": invite.role},
        )
        invite.status = WorkspaceInvitation.Status.ACCEPTED
        invite.save(update_fields=["status"])

    return membership
