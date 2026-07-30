"""RED/GREEN for the flag-gated Streamable-HTTP MCP arm (Slice 5).

Flag off ⇒ route absent from the URLconf (404 by absence). Flag on ⇒ Bearer
identity via resolve_membership; missing/unknown/revoked → 401 with no tool;
valid Bearer → list_groups for that workspace via dispatch_async.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import connections
from django.test import Client, override_settings
from django.urls import URLPattern, URLResolver, clear_url_caches, get_resolver
from django.utils import timezone
from mcp.types import CallToolResult
from mcp_server.models import WorkspaceApiToken
from schools.models import Group, School, SchoolYear
from workspaces.models import Membership, Workspace

import config.urls

pytestmark = pytest.mark.django_db(transaction=True)
User = get_user_model()

MCP_PATH = "/mcp/"
MCP_PATTERN = "mcp/"


def _mint_token(membership: Membership, *, raw: str, name: str = "http") -> str:
    WorkspaceApiToken.objects.create(
        membership=membership,
        name=name,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
    )
    return raw


def _membership_with_group(*, grupo: str = "A") -> tuple[Membership, Group, str]:
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    user = User.objects.create_user(
        email=f"http-{Membership.objects.count()}@example.com",
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
    group = Group.objects.create(
        workspace=workspace, school_year=year, grado=1, grupo=grupo
    )
    return membership, group, _mint_token(membership, raw=f"raw-http-{membership.pk}")


def _mcp_route_registered(module) -> bool:
    def walk(patterns):
        for entry in patterns:
            if isinstance(entry, URLResolver):
                if str(entry.pattern) == MCP_PATTERN or walk(entry.url_patterns):
                    return True
            elif isinstance(entry, URLPattern) and str(entry.pattern) == MCP_PATTERN:
                return True
        return False

    return walk(module.urlpatterns)


def _reload_urls():
    clear_url_caches()
    return importlib.reload(config.urls)


@pytest.fixture(autouse=True)
def restore_urlconf():
    yield
    _reload_urls()


def test_flag_off_route_absent_and_404():
    """5.1 — MCP_HTTP_ENABLED off ⇒ route absent and path 404s by absence."""
    with override_settings(MCP_HTTP_ENABLED=False):
        reloaded = _reload_urls()
        assert _mcp_route_registered(reloaded) is False
        assert MCP_PATTERN not in [str(p.pattern) for p in get_resolver().url_patterns]
        assert Client().get(MCP_PATH).status_code == 404


def test_flag_on_missing_unknown_revoked_bearer_return_401_without_tool():
    """5.2 — no Auth / unknown / revoked Bearer → 401; dispatch never runs."""
    membership, _group, raw = _membership_with_group()
    revoked_raw = _mint_token(
        membership, raw=f"revoked-http-{membership.pk}", name="revoked"
    )
    WorkspaceApiToken.objects.filter(
        token_hash=hashlib.sha256(revoked_raw.encode()).hexdigest()
    ).update(revoked_at=timezone.now())

    with override_settings(MCP_HTTP_ENABLED=True):
        _reload_urls()
        client = Client()
        cases = [
            {},
            {"HTTP_AUTHORIZATION": "Bearer not-a-real-token"},
            {"HTTP_AUTHORIZATION": f"Bearer {revoked_raw}"},
        ]
        for headers in cases:
            with patch("mcp_server.registry.dispatch", autospec=True) as mock_dispatch:
                response = client.post(
                    MCP_PATH, data=b"{}", content_type="application/json", **headers
                )
                assert response.status_code == 401, headers
                mock_dispatch.assert_not_called()


async def _call_and_release(authorization: str | None, name: str, arguments: dict):
    from mcp_server.http import handle_http_call_tool

    try:
        return await handle_http_call_tool(authorization, name, arguments)
    finally:
        await sync_to_async(connections.close_all, thread_sensitive=True)()


def _call_http_tool_in_cold_thread(authorization, name, arguments) -> CallToolResult:
    def _call():
        try:
            return asyncio.run(_call_and_release(authorization, name, arguments))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_call).result(timeout=10)


def test_flag_on_valid_bearer_list_groups_returns_workspace_a():
    """5.3 — valid Bearer for workspace A returns that workspace's groups."""
    membership_a, group_a, raw_a = _membership_with_group(grupo="A")
    _membership_with_group(grupo="B")

    with override_settings(MCP_HTTP_ENABLED=True):
        _reload_urls()
        assert _mcp_route_registered(config.urls) is True
        result = _call_http_tool_in_cold_thread(f"Bearer {raw_a}", "list_groups", {})

    assert result.isError is False
    payload = result.structuredContent
    if payload is None and result.content:
        payload = json.loads(result.content[0].text)
    assert payload is not None
    groups = payload["groups"]
    assert len(groups) == 1
    assert groups[0]["id"] == group_a.pk
    assert groups[0]["label"] == "1° A"
    assert membership_a.workspace_id == group_a.workspace_id
