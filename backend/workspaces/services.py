"""Signup provisioning (workspaces spec — Transactional Signup Provisioning).

A single atomic transaction creates the new User, a personal Workspace for
them, and an owner Membership linking the two. Any failure mid-transaction
(e.g. a duplicate email) rolls back every record created in this attempt —
no orphaned User, Workspace, or Membership is left behind.
"""

import secrets
from dataclasses import dataclass, field
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from workspaces.models import Membership, Workspace, WorkspaceInvitation
from workspaces.permissions import has_permission

User = get_user_model()

INVITATION_TOKEN_BYTES = 32
INVITATION_EXPIRY = timedelta(days=7)


@dataclass
class SignupResult:
    """Result of `provision_signup`: the new user plus discovery-only data.

    `pending_invites` never implies Membership — joining an invited
    workspace always requires a separate `accept_invitation` call
    (workspaces spec — Signup-Time Invite Discovery).
    """

    user: "User"
    pending_invites: list[WorkspaceInvitation] = field(default_factory=list)


def provision_signup(*, email: str, password: str) -> SignupResult:
    """Create a User, personal Workspace, and owner Membership atomically.

    After the atomic block, discover (read-only) any pending invitations
    matching the new user's email and attach them to the result — this
    NEVER creates a Membership for the invited workspace.
    """
    with transaction.atomic():
        workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
        user = User.objects.create_user(email=email, password=password)
        Membership.objects.create(
            user=user, workspace=workspace, role=Membership.Role.OWNER
        )

    pending_invites = list(discover_pending_invites(user=user))
    return SignupResult(user=user, pending_invites=pending_invites)


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


def revoke_invitation(
    *, actor_membership: Membership, invitation: WorkspaceInvitation
) -> WorkspaceInvitation:
    """Revoke a `pending` invite, setting `status = revoked`.

    Requires `has_permission(actor_membership, "manage_members")` and that
    the invitation belongs to the actor's own workspace (explicit filter,
    not RLS — invitations spec, RLS Exclusion). Revoking a terminal invite
    is rejected without changing its status.
    """
    if not has_permission(actor_membership, "manage_members"):
        raise PermissionDenied("Only owners and admins may revoke invitations.")

    if invitation.workspace_id != actor_membership.workspace_id:
        raise PermissionDenied("Invitation does not belong to this workspace.")

    if invitation.status != WorkspaceInvitation.Status.PENDING:
        raise ValueError(f"Invitation is not pending (status={invitation.status}).")

    invitation.status = WorkspaceInvitation.Status.REVOKED
    invitation.save(update_fields=["status"])
    return invitation


def list_invitations(*, membership: Membership) -> "QuerySet[WorkspaceInvitation]":
    """List pending invites for `membership`'s workspace (inviter-side).

    Requires `has_permission(membership, "manage_members")` (owner/admin).
    Filtered by an explicit `workspace=` clause scoped to the caller's own
    membership — never RLS or `ScopedManager` (invitations spec — RLS
    Exclusion, "Inviter-side access is filtered explicitly, not by RLS").
    """
    if not has_permission(membership, "manage_members"):
        raise PermissionDenied("Only owners and admins may list invitations.")

    return WorkspaceInvitation.objects.filter(
        workspace=membership.workspace,
        status=WorkspaceInvitation.Status.PENDING,
    )


def discover_pending_invites(*, user: "User") -> "QuerySet[WorkspaceInvitation]":
    """Read-only lookup of actionable pending invites for `user`'s email.

    Only non-expired `pending` rows are actionable; this never persists a
    lazy `expired` transition and never creates a Membership (invitations
    spec / workspaces spec — Signup-Time Invite Discovery).
    """
    return WorkspaceInvitation.objects.filter(
        email=user.email,
        status=WorkspaceInvitation.Status.PENDING,
        expires_at__gte=timezone.now(),
    )
