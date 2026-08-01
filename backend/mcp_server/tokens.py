"""Ephemeral WorkspaceApiToken mint/revoke for Quizzy → MCP wiring."""

from __future__ import annotations

import hashlib
import secrets

from django.utils import timezone
from workspaces.models import Membership

from mcp_server.models import WorkspaceApiToken


def mint_ephemeral_token(
    membership: Membership, *, name: str = "quizzy-ephemeral"
) -> tuple[str, WorkspaceApiToken]:
    """Create a hashed token row and return ``(raw_token, row)``.

    The raw value is returned only to the caller and MUST NOT be persisted.
    """
    raw_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    row = WorkspaceApiToken.objects.create(
        membership=membership,
        name=name,
        token_hash=token_hash,
    )
    return raw_token, row


def revoke_token(row: WorkspaceApiToken) -> None:
    """Set ``revoked_at`` so subsequent ``resolve_membership`` returns None."""
    WorkspaceApiToken.objects.filter(pk=row.pk, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )
