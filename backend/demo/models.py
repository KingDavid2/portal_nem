"""Provisioning-receipt model for demo sessions.

DemoSession is a platform-level record: it tracks the lifecycle of a demo
workspace provisioning (pending -> ready / failed). It is deliberately a
plain `models.Model`, NOT a `ScopedModel`, because it must be readable
before any workspace is provisioned — a guest creates a session and polls
it via an unauthenticated endpoint. Inheriting from `ScopedModel` would
require a `workspace_id` at creation time, which is precisely the value
being produced by the provisioning task. No RLS migration is needed for
this table; the demo endpoints only expose session status to the caller
who owns the session id.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class DemoSession(models.Model):
    """A provisioning receipt for a demo workspace.

    One row per demo session. Created as ``pending``, moved to ``ready``
    once the provisioning task finishes (user + workspace are backfilled),
    or to ``failed`` if the task errors out. After sign-in, nothing reads
    this row again — it is a receipt, not a mode marker.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    persona = models.CharField(max_length=64)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="demo_sessions",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "demo_sessions"
        ordering = ["-created_at"]

    @property
    def provisioned(self) -> bool:
        """True only when the session is READY and both FKs are populated.

        Mirrors ``AccountDemoSession#provisioned?``: a READY status alone is
        not enough — the user and workspace must have been backfilled by the
        provisioning task.
        """
        return (
            self.status == self.Status.READY
            and self.user_id is not None
            and self.workspace_id is not None
        )

    def __str__(self) -> str:
        return f"{self.persona}:{self.status}"