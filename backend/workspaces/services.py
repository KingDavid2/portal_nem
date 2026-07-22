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

from workspaces.models import (
    Membership,
    Workspace,
    WorkspaceHistory,
    WorkspaceInvitation,
)
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


def move_member_to_workspace(
    *,
    actor_source_membership: Membership,
    actor_target_membership: Membership,
    member: Membership,
) -> Membership:
    """Atomically move `member` from its source workspace to the target.

    All validation runs before any write (authorization spec — Dual-
    Workspace Authorization for Member Moves; workspaces spec — Atomic
    Member Move Between Workspaces), in order:
    1. Same-actor-user guard: `actor_source_membership.user` MUST equal
       `actor_target_membership.user` — a caller may not combine two
       different people's memberships to authorize a move.
    2. `has_permission(..., "manage_members")` MUST hold on BOTH the source
       and target membership.
    3. `actor_source_membership.workspace` MUST match `member.workspace`.
    4. `member.role` MUST NOT be `owner`.
    5. The target workspace MUST be `type="group"` (rejects personal and
       any other non-group type).
    6. `member.user` MUST NOT already hold a Membership in the target
       workspace (honors `unique_user_workspace_membership`).

    Then inside one `transaction.atomic()`: delete the source `Membership`,
    create a target `Membership` (role forced to `member`, regardless of the
    member's source role), then write a `moved` `WorkspaceHistory` row
    (workspace-history spec). Any failure rolls back every step, leaving
    both sides unchanged (design — single transaction, ordered writes).

    Raises `PermissionDenied` for authorization failures (1-3) and
    `ValueError` for domain-rule violations (4-6).
    """
    # (1) Same-actor-user guard — CRITICAL security guard, do not remove:
    # without it a caller could pair their own manage_members membership in
    # one workspace with someone else's in another to authorize a move.
    if actor_source_membership.user_id != actor_target_membership.user_id:
        raise PermissionDenied(
            "Source and target authorizing memberships must belong to the "
            "same user."
        )

    # (2) Dual-workspace capability check — never inline role strings.
    if not has_permission(actor_source_membership, "manage_members") or not has_permission(
        actor_target_membership, "manage_members"
    ):
        raise PermissionDenied(
            "Only owners and admins may move members, in both workspaces."
        )

    # (3) The source authorizing membership must actually belong to the
    # workspace the moved member is currently in.
    if actor_source_membership.workspace_id != member.workspace_id:
        raise PermissionDenied(
            "Source membership does not belong to the member's workspace."
        )

    # (4) Owners are never movable.
    if member.role == Membership.Role.OWNER:
        raise ValueError("Cannot move a workspace owner.")

    # (5) Target must be a group workspace (rejects personal and any other
    # non-group type).
    if actor_target_membership.workspace.type != Workspace.Type.GROUP:
        raise ValueError("Target workspace must be a group workspace.")

    # (6) No duplicate membership in the target workspace.
    if Membership.objects.filter(
        user=member.user, workspace=actor_target_membership.workspace
    ).exists():
        raise ValueError("User already has a membership in the target workspace.")

    with transaction.atomic():
        source_workspace = member.workspace
        target_workspace = actor_target_membership.workspace
        moved_user = member.user

        member.delete()

        new_membership = Membership.objects.create(
            user=moved_user,
            workspace=target_workspace,
            role=Membership.Role.MEMBER,
        )

        WorkspaceHistory.objects.create(
            action=WorkspaceHistory.Action.MOVED,
            actor=actor_source_membership.user,
            target_user=moved_user,
            from_workspace=source_workspace,
            to_workspace=target_workspace,
        )

    return new_membership


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
