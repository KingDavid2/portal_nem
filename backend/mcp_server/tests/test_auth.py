"""Tests for token resolution (identity-auth spec — resolve_membership)."""

from __future__ import annotations

import hashlib

import pytest

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from mcp_server.auth import resolve_membership
from mcp_server.models import WorkspaceApiToken
from users.models import User
from workspaces.models import Membership, Workspace


@pytest.mark.django_db(transaction=True)
def test_resolve_membership_valid_token():
    """Scenario: Valid token resolves to its membership.

    Given an unrevoked token minted for a membership in workspace A
    When resolve_membership is called with the raw token
    Then it returns that Membership
    And last_used_at is updated
    """
    workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    user = User.objects.create_user(email="valid@test.com", password="pass")
    membership = Membership.objects.create(user=user, workspace=workspace, role="member")

    raw_token = "valid-token-value"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    token_row = WorkspaceApiToken.objects.create(
        membership=membership,
        name="valid_token",
        token_hash=token_hash,
        last_used_at=None,
        revoked_at=None,
    )

    # Before resolution, last_used_at should be None
    assert token_row.last_used_at is None

    # Resolve with valid token
    result = resolve_membership(raw_token)
    assert result is not None
    assert result.pk == membership.pk
    assert result.workspace.pk == workspace.pk

    # After resolution, last_used_at should be updated
    token_row = WorkspaceApiToken.objects.get(pk=token_row.pk)
    assert token_row.last_used_at is not None
    assert timezone.now() - token_row.last_used_at < timezone.timedelta(seconds=2)


@pytest.mark.django_db(transaction=True)
def test_resolve_membership_unknown_token():
    """Scenario: Revoked and unknown tokens are indistinguishable.

    Given a raw token matching no stored row
    When resolve_membership is called
    Then it returns None
    And it does not raise a distinguishing error
    """
    raw_token = "unknown-token-value"
    result = resolve_membership(raw_token)
    assert result is None


@pytest.mark.django_db(transaction=True)
def test_resolve_membership_revoked_token():
    """Scenario: Revoked token returns None and doesn't touch last_used_at.

    Given a token whose revoked_at is set
    When resolve_membership is called
    Then it returns None
    And last_used_at is NOT updated (byte-identical to before)
    """
    workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    user = User.objects.create_user(email="revoked@test.com", password="pass")
    membership = Membership.objects.create(user=user, workspace=workspace, role="member")

    raw_token = "revoked-token-value"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    old_last_used_at = timezone.datetime(2024, 1, 1, tzinfo=timezone.UTC)

    token_row = WorkspaceApiToken.objects.create(
        membership=membership,
        name="revoked_token",
        token_hash=token_hash,
        last_used_at=old_last_used_at,
        revoked_at=timezone.now(),  # Token is revoked
    )

    # Verify token is revoked
    assert token_row.revoked_at is not None

    # Resolve with revoked token
    result = resolve_membership(raw_token)
    assert result is None

    # Verify last_used_at was NOT updated
    token_row = WorkspaceApiToken.objects.get(pk=token_row.pk)
    assert token_row.last_used_at == old_last_used_at


@pytest.mark.django_db(transaction=True)
def test_resolve_membership_unknown_and_revoked_byte_identical():
    """Unknown and revoked tokens produce byte-identical outcomes.

    Both return None, neither touches last_used_at, no distinguishing errors.
    """
    workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    user = User.objects.create_user(email="identical@test.com", password="pass")
    membership = Membership.objects.create(user=user, workspace=workspace, role="member")

    # Create a revoked token
    revoked_raw = "revoked-token"
    revoked_hash = hashlib.sha256(revoked_raw.encode()).hexdigest()
    old_last_used = timezone.datetime(2024, 6, 1, tzinfo=timezone.UTC)
    WorkspaceApiToken.objects.create(
        membership=membership,
        name="revoked",
        token_hash=revoked_hash,
        last_used_at=old_last_used,
        revoked_at=timezone.now(),
    )

    # Unknown token
    unknown_result = resolve_membership("unknown-token")
    assert unknown_result is None

    # Revoked token
    revoked_result = resolve_membership(revoked_raw)
    assert revoked_result is None

    # Both should return None, no exceptions
    # Verify last_used_at was NOT updated for the revoked token
    token = WorkspaceApiToken.objects.get(token_hash=revoked_hash)
    assert token.last_used_at == old_last_used


@pytest.mark.django_db(transaction=True)
def test_resolve_membership_failed_does_not_read_workspace_data():
    """Scenario: A failed resolution touches no workspace data.

    Given a raw token that resolves to no membership
    When resolve_membership is called
    Then no workspace-scoped ORM read or write occurs
    And no tool body is executed
    """
    with CaptureQueriesContext(connection) as captured:
        assert resolve_membership("unknown-token") is None

    statements = [q["sql"] for q in captured.captured_queries]

    # The only table touched is the token table itself.
    token_table = WorkspaceApiToken._meta.db_table
    for sql in statements:
        assert token_table in sql, sql

    # And nothing was written.
    for sql in statements:
        assert not sql.lstrip().upper().startswith(("UPDATE", "INSERT", "DELETE")), sql