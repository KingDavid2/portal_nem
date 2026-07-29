"""Token resolution for MCP tools (identity-auth spec, design D4)."""

from __future__ import annotations

import hashlib

from django.utils import timezone
from workspaces.models import Membership

from .models import WorkspaceApiToken


def resolve_membership(raw_token: str) -> Membership | None:
    """Resolve a raw API token to its Membership.

    D4: `revoked_at__isnull=True` goes INSIDE the filter, structurally
    preventing any code path on which a revoked row can be touched.

    Unknown and revoked tokens are byte-identical outcomes: both return None,
    neither touches last_used_at, neither raises a distinguishing error.
    """
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    row = (
        WorkspaceApiToken.objects.filter(
            token_hash=token_hash, revoked_at__isnull=True
        )
        .select_related("membership__workspace")
        .first()
    )
    if row is None:
        return None

    # Touch via a targeted UPDATE, not save() — only after a successful resolution.
    WorkspaceApiToken.objects.filter(pk=row.pk).update(last_used_at=timezone.now())

    return row.membership
