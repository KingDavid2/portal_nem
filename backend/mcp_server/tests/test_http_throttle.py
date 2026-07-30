"""Per-token rate limit on the Streamable-HTTP MCP arm (Quizzy P6 Slice 1b).

Design rate: `mcp_http` 60/min keyed on sha256(bearer). Auth runs first (401
unchanged); throttle runs after identity resolves. A 429 must not execute a
tool. Distinct bearer tokens have independent counters.
"""

from __future__ import annotations

import hashlib
import importlib
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import Client, override_settings
from django.urls import clear_url_caches
from mcp_server.models import WorkspaceApiToken
from schools.models import Group, School, SchoolYear
from workspaces.models import Membership, Workspace

import config.urls

pytestmark = pytest.mark.django_db(transaction=True)
User = get_user_model()

MCP_PATH = "/mcp/"


def _mint_token(membership: Membership, *, raw: str, name: str = "http") -> str:
    WorkspaceApiToken.objects.create(
        membership=membership,
        name=name,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
    )
    return raw


def _membership_with_token(*, raw: str, grupo: str = "A") -> tuple[Membership, str]:
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    user = User.objects.create_user(
        email=f"throttle-{Membership.objects.count()}@example.com",
        password="s3cret-pass",
    )
    membership = Membership.objects.create(
        user=user, workspace=workspace, role=Membership.Role.MEMBER
    )
    school = School.objects.create(
        workspace=workspace,
        name="Escuela HTTP",
        level=School.Level.SECUNDARIA,
        cct="15DES0088Z",
    )
    year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2025-2026"
    )
    Group.objects.create(workspace=workspace, school_year=year, grado=1, grupo=grupo)
    return membership, _mint_token(membership, raw=raw)


def _reload_urls():
    clear_url_caches()
    return importlib.reload(config.urls)


@pytest.fixture(autouse=True)
def restore_urlconf():
    yield
    _reload_urls()


def _post_mcp(client: Client, raw: str) -> HttpResponse:
    return client.post(
        MCP_PATH,
        data=b"{}",
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {raw}",
    )


@override_settings(MCP_HTTP_ENABLED=True, MCP_HTTP_THROTTLE_RATE="3/min")
def test_token_returns_429_after_rate_ceiling_without_tool():
    _membership, raw = _membership_with_token(raw="raw-throttle-a")
    _reload_urls()
    client = Client()

    with patch(
        "mcp_server.http._asgi_response_for_django",
        return_value=HttpResponse(b"ok", status=200),
    ) as mock_asgi:
        for i in range(3):
            response = _post_mcp(client, raw)
            assert response.status_code == 200, f"expected 200 on request {i + 1}"

        limited = _post_mcp(client, raw)

        assert limited.status_code == 429
        assert "Retry-After" in limited.headers
        assert mock_asgi.call_count == 3


@override_settings(MCP_HTTP_ENABLED=True, MCP_HTTP_THROTTLE_RATE="3/min")
def test_distinct_bearer_tokens_have_independent_counters():
    _m1, raw_a = _membership_with_token(raw="raw-token-a", grupo="A")
    _m2, raw_b = _membership_with_token(raw="raw-token-b", grupo="B")
    _reload_urls()
    client = Client()

    with patch(
        "mcp_server.http._asgi_response_for_django",
        return_value=HttpResponse(b"ok", status=200),
    ):
        for _ in range(3):
            assert _post_mcp(client, raw_a).status_code == 200
        assert _post_mcp(client, raw_a).status_code == 429

        # Exhausting token A must leave token B's budget intact.
        assert _post_mcp(client, raw_b).status_code == 200
