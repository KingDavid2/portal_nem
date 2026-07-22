import uuid

from django.conf import settings
from django.db import models

from workspaces.managers import ScopedManager


class Workspace(models.Model):
    """Tenant boundary. Every scoped resource belongs to exactly one Workspace."""

    class Type(models.TextChoices):
        PERSONAL = "personal", "Personal"
        GROUP = "group", "Group"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=Type.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workspaces_workspace"

    def __str__(self) -> str:
        return f"{self.type}:{self.id}"


class Membership(models.Model):
    """Links a user to a workspace with a capability-matrix role."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    # CharField + choices (not TextChoices-typed column) so future roles
    # (e.g. tutor/viewer) are a one-line addition — design Interfaces.
    role = models.CharField(max_length=20, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workspaces_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "workspace"], name="unique_user_workspace_membership"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id}@{self.workspace_id}:{self.role}"


class ScopedModel(models.Model):
    """Abstract base for domain models isolated to a single Workspace.

    Concrete subclasses get a `workspace` FK (`workspace_id` column), which
    both the D5 scoped manager and the D8 RLS policy key on.
    """

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    objects = ScopedManager()

    class Meta:
        abstract = True


class WorkspaceResource(ScopedModel):
    """Minimal concrete `ScopedModel`, added only to exercise RLS (D8/D9).

    M2a ships no real NEM domain models yet (those land in M2b+). Without at
    least one concrete `ScopedModel` subclass there would be no table for
    the RLS backstop (tenancy-isolation spec) to protect, and the D9
    cross-tenant leak test would have nothing to query. This model carries
    no product meaning — replace/remove once real scoped domain models
    exist.
    """

    name = models.CharField(max_length=200)

    class Meta:
        db_table = "workspaces_workspaceresource"

    def __str__(self) -> str:
        return f"{self.workspace_id}:{self.name}"


class WorkspaceInvitation(models.Model):
    """Pending/terminal invite to join a Workspace by email.

    Deliberately a plain `ForeignKey(Workspace)`, NOT a `ScopedModel`: an
    invitee has no `Membership`-derived active workspace yet, so RLS/
    `ScopedManager` would hide their own invite (invitations spec —
    RLS Exclusion). Authorization is enforced explicitly in services.py:
    inviter-side by `workspace=` filter + `has_permission`, invitee-side by
    token + email ownership. Uses the default `Manager` (NOT `ScopedManager`).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=Membership.Role.choices)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_invitations",
    )
    token = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Computed by the invite service (now() + 7 days), not a model default —
    # invitations spec: "Expiry computed at creation".
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "workspaces_workspaceinvitation"
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["email", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.email}@{self.workspace_id}:{self.status}"
