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
