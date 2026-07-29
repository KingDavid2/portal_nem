"""MCP server data model — API token storage and resolution (identity-auth spec)."""

from __future__ import annotations

from django.db import models

from workspaces.models import Membership


class WorkspaceApiToken(models.Model):
    """Hashed per-membership API token.

    Deliberately a plain `models.Model`, NOT a `ScopedModel`: the token row
    must be readable *before* any workspace scope exists — it is the row that
    establishes scope — so a `ScopedManager` would fail closed on the very lookup
    that resolves identity. This mirrors the documented-exclusion precedent carried
    by `WorkspaceInvitation` and `WorkspaceHistory` in `workspaces.models`, which
    are also plain `models.Model` for the same reason. Uses the default `Manager`
    (NOT `ScopedManager`).
    """

    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="api_tokens",
    )
    name = models.CharField(max_length=200)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True)
    revoked_at = models.DateTimeField(null=True)