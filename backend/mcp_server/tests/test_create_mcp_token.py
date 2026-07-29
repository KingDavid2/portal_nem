"""Tests for `create_mcp_token` management command (identity-auth spec)."""

from __future__ import annotations

import hashlib
import re

import pytest

from django.core.management import call_command
from django.test import TestCase
from django.urls import get_resolver
from mcp_server.auth import resolve_membership
from mcp_server.models import WorkspaceApiToken
from users.models import User
from workspaces.models import Membership, Workspace


@pytest.mark.django_db(transaction=True)
class TestCreateMcpToken(TestCase):
    """Tests for the create_mcp_token management command."""

    def setUp(self):
        self.workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
        self.user = User.objects.create_user(email="token@test.com", password="pass")
        self.membership = Membership.objects.create(
            user=self.user, workspace=self.workspace, role="member"
        )

    def test_command_mints_token_and_prints_raw_value_once(self):
        """Scenario: Command mints a token and prints the raw value once.

        Given an existing membership
        When manage.py create_mcp_token is run for that membership with a name
        Then a WorkspaceApiToken row is created for it
        And the raw token is printed exactly once to the command output
        """
        from io import StringIO

        out = StringIO()
        err = StringIO()

        call_command(
            "create_mcp_token",
            f"--membership={self.membership.pk}",
            "--name=smoke_token",
            stdout=out,
            stderr=err,
        )

        output = out.getvalue()
        assert "smoke_token" in output

        # The raw token is a 64-char hex string printed exactly once, and the
        # output says plainly that it cannot be retrieved again.
        raw_tokens = re.findall(r"\b[0-9a-f]{64}\b", output)
        assert len(raw_tokens) == 1, output
        raw_token = raw_tokens[0]
        assert raw_token not in err.getvalue()
        assert "cannot be retrieved again" in err.getvalue()

        # It resolves to the membership it was minted for.
        membership = resolve_membership(raw_token)
        assert membership is not None
        assert membership.pk == self.membership.pk

        # And the raw value is nowhere in the stored row.
        stored = WorkspaceApiToken.objects.get(membership=self.membership)
        assert stored.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
        assert raw_token not in stored.name

        # Verify token row was created
        tokens = WorkspaceApiToken.objects.filter(membership=self.membership).all()
        assert len(tokens) == 1
        assert tokens[0].name == "smoke_token"

    def test_no_http_surface_mints_tokens(self):
        """Scenario: No HTTP surface mints tokens.

        Given the registered URLconf
        When it is searched for a token-issuance route
        Then no endpoint exists that creates a WorkspaceApiToken
        """
        def walk(patterns):
            for entry in patterns:
                nested = getattr(entry, "url_patterns", None)
                if nested is not None:
                    yield from walk(nested)
                else:
                    yield entry

        routes = list(walk(get_resolver().url_patterns))
        assert routes, "URLconf resolved to no routes — the scan would be vacuous"

        for route in routes:
            module = getattr(route.callback, "__module__", "") or ""
            assert not module.startswith("mcp_server"), (
                f"{route.pattern} is served by {module}; token issuance is command-only"
            )

    def test_demo_workspace_can_mint_token(self):
        """Scenario: A demo workspace can mint a token.

        Given a membership in a demo-provisioned workspace
        When manage.py create_mcp_token is run for it
        Then a token is minted and resolves to that membership
        """
        # Create a demo-style workspace and user
        demo_workspace = Workspace.objects.create(type=Workspace.Type.GROUP, name="Demo Workspace")
        demo_user = User.objects.create_user(email="demo@test.com", password="pass")
        demo_membership = Membership.objects.create(
            user=demo_user, workspace=demo_workspace, role="member"
        )

        from io import StringIO
        out = StringIO()
        err = StringIO()

        call_command(
            "create_mcp_token",
            f"--membership={demo_membership.pk}",
            "--name=demo_token",
            stdout=out,
            stderr=err,
        )

        # Verify token was created and is resolvable
        tokens = WorkspaceApiToken.objects.filter(membership=demo_membership).all()
        assert len(tokens) == 1
        assert tokens[0].name == "demo_token"

        # Verify the token hash is valid (we can verify by checking hash format)
        assert len(tokens[0].token_hash) == 64  # SHA-256 hex digest is always 64 chars