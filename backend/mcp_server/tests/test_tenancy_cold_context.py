"""Cold-context tenancy harness for the MCP async bridge (tenancy-isolation spec).

Why a fresh thread is mandatory here: `asgiref.sync.sync_to_async` copies the caller's
contextvars into the executor thread. A test whose calling context already holds
`active_workspace` would leak it across the bridge and pass **even with `workspace_scope`
stripped from the tool body** — a green test that proves nothing.

Every test in this module therefore runs the entire `asyncio.run(...)` inside a fresh
`ThreadPoolExecutor(max_workers=1)` thread, mirroring
`lesson_plans/test_tasks.py::_run_task_in_cold_thread` (`:174`, `:186`). The cold thread
starts with its own default `contextvars.Context`, so there is no inherited
`active_workspace` for a tool body to accidentally rely on.

`@pytest.mark.django_db(transaction=True)` is required alongside the cold-thread pattern:
the second thread opens its own DB connection, which only sees rows committed to the
database, not rows sitting inside another connection's uncommitted transaction.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from django.db import connections
from mcp_server.registry import (
    CAPABILITY_MAP,
    ToolInputError,
    _TOOLS,
    dispatch,
    dispatch_async,
)
from users.models import User
from workspaces.context import WORKSPACE_UNSET, active_workspace
from workspaces.models import Membership, Workspace, WorkspaceResource


# ---------------------------------------------------------------------------
# Cold-thread dispatcher (task 2b.2)
# ---------------------------------------------------------------------------


def _dispatch_in_cold_thread(name: str, arguments: dict, membership) -> dict:
    """Run `asyncio.run(dispatch_async(...))` on a fresh thread with no inherited
    `active_workspace` contextvar, then close that thread's DB connection so
    pytest-django's teardown doesn't race a still-open connection."""

    def _call():
        try:
            return asyncio.run(dispatch_async(name, arguments, membership))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_call).result(timeout=10)


# ---------------------------------------------------------------------------
# Helpers (2b.3 / 2b.4)
# ---------------------------------------------------------------------------


def _make_membership(workspace: Workspace) -> Membership:
    user = User.objects.create_user(email=f"user@{workspace.id}.test", password="pass")
    return Membership.objects.create(user=user, workspace=workspace, role="member")


def _make_probe(use_scope: bool = True):
    """Build a probe tool callable that reads `WorkspaceResource` rows.

    If `use_scope` is True, the tool enters `workspace_scope` before reading
    (task 2b.3). If False, it reads without entering scope (task 2b.4).
    """
    from workspaces.scope import workspace_scope

    def _probe_scoped(membership, **_kwargs):
        with workspace_scope(membership.workspace_id):
            rows = list(
                WorkspaceResource.objects.values_list("name", flat=True)
            )
        return {"rows": rows}

    def _probe_unscoped(membership, **_kwargs):
        rows = list(
            WorkspaceResource.objects.values_list("name", flat=True)
        )
        return {"rows": rows}

    return _probe_scoped if use_scope else _probe_unscoped


@contextlib.contextmanager
def _probe_patch(name: str, use_scope: bool = True):
    """Context manager that temporarily registers a probe tool without
    mutating global state (avoids breaking test_registry.py expectations).
    """
    probe = _make_probe(use_scope=use_scope)
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.dict(_TOOLS, {name: probe}))
        stack.enter_context(patch.dict(CAPABILITY_MAP, {name: "view_workspace"}))
        yield name


# ---------------------------------------------------------------------------
# Tests: RED phase (2b.3–2b.6)
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_probe_via_cold_thread_scoped_read_returns_workspace_rows():
    """Scenario: Tool sets its own workspace context before reading (tenancy-isolation spec).

    Given a probe tool that enters `workspace_scope(membership.workspace_id)`
    When invoked through the async bridge on a cold thread (no inherited active_workspace)
    Then it returns workspace A's rows
    And no scope was active in the calling context.
    """
    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    membership_a = _make_membership(workspace_a)

    WorkspaceResource.objects.create(workspace=workspace_a, name="resource-a-1")
    WorkspaceResource.objects.create(workspace=workspace_a, name="resource-a-2")

    # Sanity: caller thread has no workspace scope set
    assert active_workspace.get() is WORKSPACE_UNSET

    with _probe_patch("probe_scoped", use_scope=True) as probe_name:
        result = _dispatch_in_cold_thread(probe_name, {}, membership_a)

    rows = result["rows"]
    assert sorted(rows) == ["resource-a-1", "resource-a-2"]


@pytest.mark.django_db(transaction=True)
def test_probe_without_scope_fails_closed_zero_rows():
    """Scenario: Tool without established context fails closed, not cross-tenant (tenancy-isolation spec).

    Given an MCP tool stripped of its `workspace_scope` entry (simulating a regression)
    And rows exist in more than one workspace
    When that tool attempts to read
    Then it MUST return zero rows
    And MUST NOT return rows from any workspace as a fallback.

    If this test passes before the cold-thread harness exists, the harness is wrong
    (it would mean `active_workspace` is leaking into the cold thread).
    """
    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)

    membership_a = _make_membership(workspace_a)

    WorkspaceResource.objects.create(workspace=workspace_a, name="a-only")
    WorkspaceResource.objects.create(workspace=workspace_b, name="b-only")

    with _probe_patch("probe_unscoped", use_scope=False) as probe_name:
        result = _dispatch_in_cold_thread(probe_name, {}, membership_a)

    assert result["rows"] == []


@pytest.mark.django_db(transaction=True)
def test_dispatch_is_sync():
    """Assert that `dispatch` and every registered tool are plain sync callables.

    Per-task wrapping of sync_to_async was rejected: the bridge sits at
    `dispatch` only. This test catches a regression where a tool or
    dispatch itself drifts to coroutine form.
    """
    import asyncio
    from mcp_server import registry

    assert not asyncio.iscoroutinefunction(dispatch)

    for tool in registry._TOOLS.values():
        assert not asyncio.iscoroutinefunction(tool)


@pytest.mark.django_db(transaction=True)
def test_async_handler_does_not_raise_synchronous_only_operation():
    """A sync test calling `asyncio.run(dispatch_async(...))` must not trigger
    `SynchronousOnlyOperation`.

    Removing the bridge would make Django raise this exception because
    `dispatch` touches the ORM synchronously. This test proves the bridge
    actually wraps `dispatch` in `sync_to_async`.

    `DJANGO_ALLOW_ASYNC_UNSAFE` MUST be unset; that is what makes the failure
    reachable. No `pytest-asyncio` dependency.
    """
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    membership = _make_membership(workspace)

    # Assert the env var is unset — this is what makes SynchronousOnlyOperation reachable.
    assert os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE") is None

    # This call should NOT raise SynchronousOnlyOperation — the bridge must handle it.
    # The stub tools raise ToolInputError because they aren't implemented yet.
    with pytest.raises(ToolInputError):
        asyncio.run(dispatch_async("get_quota", {}, membership))