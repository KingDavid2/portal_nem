"""RED/GREEN for the stdio MCP transport (Slice 4 — mcp-tool-surface).

Identity comes from PORTAL_NEM_MCP_TOKEN via resolve_membership. Handlers
dispatch through dispatch_async; ToolError subclasses render as MCP tool
errors (isError=True). Unset and garbage tokens share one denied outcome
with no workspace rows returned.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import connections
from lesson_plans.models import LessonPlan
from mcp.types import CallToolResult
from mcp_server.models import WorkspaceApiToken
from schools.models import Group, School, SchoolYear
from workspaces.models import Membership, Workspace
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db(transaction=True)
User = get_user_model()

TOKEN_ENV = "PORTAL_NEM_MCP_TOKEN"


def _mint_token(membership: Membership, *, raw: str, name: str = "stdio") -> str:
    WorkspaceApiToken.objects.create(
        membership=membership,
        name=name,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
    )
    return raw


def _membership_with_plan(*, theme: str = "A-plan") -> tuple[Membership, LessonPlan, str]:
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    user = User.objects.create_user(
        email=f"stdio-{Membership.objects.count()}@example.com",
        password="s3cret-pass",
    )
    membership = Membership.objects.create(
        user=user, workspace=workspace, role=Membership.Role.MEMBER
    )
    school = School.objects.create(
        workspace=workspace,
        name="Escuela Stdio",
        level=School.Level.SECUNDARIA,
        cct="15DES0099Z",
    )
    year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2025-2026"
    )
    group = Group.objects.create(
        workspace=workspace, school_year=year, grado=2, grupo="A"
    )
    with workspace_scope(workspace.id):
        plan = LessonPlan.objects.create(
            workspace=workspace,
            group=group,
            campo="Lenguajes",
            grade="SEGUNDO",
            theme=theme,
        )
    raw = _mint_token(membership, raw=f"raw-stdio-{membership.pk}")
    return membership, plan, raw


async def _call_and_release(name: str, arguments: dict) -> CallToolResult:
    """Await the stdio call_tool handler, then close the bridge connection."""
    from mcp_server.server import handle_call_tool

    try:
        return await handle_call_tool(name, arguments)
    finally:
        await sync_to_async(connections.close_all, thread_sensitive=True)()


def _call_tool_in_cold_thread(name: str, arguments: dict) -> CallToolResult:
    """Run handle_call_tool on a fresh thread (no inherited workspace scope)."""

    def _call():
        try:
            return asyncio.run(_call_and_release(name, arguments))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_call).result(timeout=10)


def _result_payload(result: CallToolResult) -> dict | None:
    """Parse structuredContent or JSON text content into a dict, if present."""
    if result.structuredContent is not None:
        return result.structuredContent
    if not result.content:
        return None
    text = result.content[0].text
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def test_stdio_list_lesson_plans_with_valid_token():
    """4.2 — valid PORTAL_NEM_MCP_TOKEN returns workspace A's plans over stdio."""
    membership, plan, raw = _membership_with_plan(theme="workspace-a-theme")
    # A second workspace's plan must not leak into the response.
    _membership_with_plan(theme="workspace-b-theme")

    previous = os.environ.get(TOKEN_ENV)
    os.environ[TOKEN_ENV] = raw
    try:
        result = _call_tool_in_cold_thread("list_lesson_plans", {})
    finally:
        if previous is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous

    assert result.isError is False
    payload = _result_payload(result)
    assert payload is not None
    plans = payload["lesson_plans"]
    assert len(plans) == 1
    assert plans[0]["id"] == plan.pk
    assert plans[0]["theme"] == "workspace-a-theme"


def test_stdio_denied_when_token_unset_and_garbage_are_identical():
    """4.3 — unset and garbage tokens are denied identically, with no rows."""
    _membership, plan, _raw = _membership_with_plan(theme="should-not-leak")

    previous = os.environ.get(TOKEN_ENV)
    outcomes: list[tuple[bool, str, dict | None]] = []
    try:
        # Unset
        os.environ.pop(TOKEN_ENV, None)
        unset_result = _call_tool_in_cold_thread("list_lesson_plans", {})
        outcomes.append(
            (
                unset_result.isError,
                unset_result.content[0].text if unset_result.content else "",
                _result_payload(unset_result),
            )
        )

        # Garbage
        os.environ[TOKEN_ENV] = "not-a-real-token-value"
        garbage_result = _call_tool_in_cold_thread("list_lesson_plans", {})
        outcomes.append(
            (
                garbage_result.isError,
                garbage_result.content[0].text if garbage_result.content else "",
                _result_payload(garbage_result),
            )
        )
    finally:
        if previous is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous

    unset_outcome, garbage_outcome = outcomes
    assert unset_outcome == garbage_outcome
    assert unset_outcome[0] is True  # isError
    payload = unset_outcome[2]
    # Denied response must not carry workspace rows.
    if payload is not None:
        assert "lesson_plans" not in payload
        assert plan.pk not in json.dumps(payload)


def test_stdio_tool_not_found_renders_fixed_message():
    """Triangulation: ToolNotFoundError always carries its fixed message."""
    _membership, plan, raw = _membership_with_plan()
    previous = os.environ.get(TOKEN_ENV)
    os.environ[TOKEN_ENV] = raw
    try:
        result = _call_tool_in_cold_thread(
            "get_lesson_plan", {"id": plan.pk + 999_999}
        )
    finally:
        if previous is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous

    assert result.isError is True
    assert result.content[0].text == "Lesson plan not found."
