"""Tests for the WorkspaceApiToken model (identity-auth spec)."""

from __future__ import annotations

import hashlib

import pytest

from django.db import connection

from mcp_server.models import WorkspaceApiToken
from users.models import User
from workspaces.context import WORKSPACE_UNSET, active_workspace
from workspaces.models import Membership, Workspace


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("raw_token", ["super-secret-token-123", "another-token-value"])
def test_minting_stores_sha256_hash(raw_token: str) -> None:
    """Scenario: Only the hash is persisted.

    Given a token is minted for a membership
    When the stored WorkspaceApiToken row is inspected
    Then token_hash equals sha256(raw).hexdigest()
    And the raw token string does NOT appear in any field of the row
    """
    workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    user = User.objects.create_user(email="test@example.com", password="pass")
    membership = Membership.objects.create(user=user, workspace=workspace, role="member")

    # Create token
    token_row = WorkspaceApiToken.objects.create(
        membership=membership,
        name="test_token",
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
    )

    # Inspect the row
    stored_row = WorkspaceApiToken.objects.get(pk=token_row.pk)

    # Assert hash is correct
    expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    assert stored_row.token_hash == expected_hash

    # Assert raw token is NOT in any field
    assert raw_token not in stored_row.name
    assert raw_token not in stored_row.token_hash
    assert raw_token not in stored_row.__str__()


@pytest.mark.django_db(transaction=True)
def test_token_readable_without_workspace_scope():
    """Scenario: Token row is readable with no workspace scope active.

    Given no workspace contextvar is set and no app.workspace_id is active
    When a WorkspaceApiToken is looked up by token_hash
    Then the row is returned
    And the lookup does NOT fail closed the way a ScopedModel read would
    """
    workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    user = User.objects.create_user(email="test2@example.com", password="pass")
    membership = Membership.objects.create(user=user, workspace=workspace, role="member")

    raw_token = "no-scope-token"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # Create token
    token_row = WorkspaceApiToken.objects.create(
        membership=membership,
        name="no_scope_token",
        token_hash=token_hash,
    )

    # Explicitly unset the workspace context. The sentinel — not None — is what
    # `ScopedQuerySet._scoped` checks; setting None would filter on
    # `workspace_id=None` instead of taking the fail-closed path, so this test
    # would prove nothing about a scope-free read.
    active_workspace.set(WORKSPACE_UNSET)

    # And no RLS GUC is active either.
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.workspace_id', true)")
        assert cursor.fetchone()[0] in (None, "")

    # Lookup should work WITHOUT workspace scope active
    found = WorkspaceApiToken.objects.filter(token_hash=token_hash).first()
    assert found is not None
    assert found.pk == token_row.pk
    assert found.token_hash == token_hash