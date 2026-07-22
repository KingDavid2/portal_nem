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
