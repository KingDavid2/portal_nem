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
from asgiref.sync import sync_to_async
from django.db import connections
from mcp_server.registry import (
    CAPABILITY_MAP,
    _TOOLS,
    dispatch,
    dispatch_async,
)
from users.models import User
from workspaces.context import WORKSPACE_UNSET, active_workspace
from workspaces.models import Membership, Workspace, WorkspaceResource
from workspaces.scope import workspace_scope


# ---------------------------------------------------------------------------
# Cold-thread dispatcher (task 2b.2)
# ---------------------------------------------------------------------------


async def _dispatch_and_release(name: str, arguments: dict, membership) -> dict:
    """Await the bridge, then close the DB connection the tool opened.

    The close has to go back through `sync_to_async` rather than being called
    from the awaiting thread, and that differs from
    `lesson_plans/test_tasks.py::_run_task_in_cold_thread` for a reason: that
    helper runs the work ON the cold thread, so a plain
    `connections.close_all()` there closes the connection that was opened.
    `thread_sensitive=True` instead hands `dispatch` to asgiref's own shared
    executor thread, so the connection belongs to THAT thread — closing from
    the caller closes nothing and leaves a session open through pytest-django's
    test-database teardown.

    Every path that awaits `dispatch_async` in this module goes through here.
    """
    try:
        return await dispatch_async(name, arguments, membership)
    finally:
        await sync_to_async(connections.close_all, thread_sensitive=True)()


def _dispatch_in_cold_thread(name: str, arguments: dict, membership) -> dict:
    """Run `asyncio.run(dispatch_async(...))` on a fresh thread with no inherited
    `active_workspace` contextvar, releasing both threads' connections after."""

    def _call():
        try:
            return asyncio.run(_dispatch_and_release(name, arguments, membership))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_call).result(timeout=10)


# ---------------------------------------------------------------------------
# Helpers (2b.3 / 2b.4)
# ---------------------------------------------------------------------------


def _make_membership(workspace: Workspace) -> Membership:
    user = User.objects.create_user(email=f"user@{workspace.id}.test", password="pass")
    return Membership.objects.create(
        user=user, workspace=workspace, role=Membership.Role.MEMBER
    )


def _make_probe(use_scope: bool = True):
    """Build a probe tool callable that reads `WorkspaceResource` rows.

    If `use_scope` is True, the tool enters `workspace_scope` before reading
    (task 2b.3). If False, it reads without entering scope (task 2b.4).
    """

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
def test_cold_thread_is_what_makes_the_fail_closed_proof_real():
    """The harness itself is under test here, not the tool.

    The test above passes for two very different reasons, and only one of them
    is worth anything: the cold thread isolating the tool, or the calling
    context simply never having held a scope. Under pytest nothing sets
    `active_workspace`, so it passes either way — which means on its own it
    does not show the cold thread is load-bearing.

    This test holds `workspace_scope` in the CALLING context and dispatches the
    unscoped probe anyway. The rows must still be empty. Swap
    `_dispatch_in_cold_thread` for a plain `asyncio.run` and this returns
    `["a-only"]`, because `sync_to_async` copies the caller's contextvars into
    the executor thread — the exact leak the module docstring describes.

    Without this test, replacing the harness with a bare `asyncio.run` breaks
    the isolation and every other test in the file stays green.
    """
    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)

    membership_a = _make_membership(workspace_a)

    WorkspaceResource.objects.create(workspace=workspace_a, name="a-only")
    WorkspaceResource.objects.create(workspace=workspace_b, name="b-only")

    with _probe_patch("probe_unscoped", use_scope=False) as probe_name:
        with workspace_scope(workspace_a.id):
            assert active_workspace.get() == workspace_a.id
            result = _dispatch_in_cold_thread(probe_name, {}, membership_a)

    assert result["rows"] == [], (
        "The caller's workspace scope reached the tool body. The cold thread is "
        "not isolating the dispatch — see this module's docstring."
    )


def test_dispatch_is_sync():
    """Assert that `dispatch` and every registered tool are plain sync callables.

    Per-task wrapping of sync_to_async was rejected: the bridge sits at
    `dispatch` only. This test catches a regression where a tool or
    dispatch itself drifts to coroutine form.
    """
    assert not asyncio.iscoroutinefunction(dispatch)

    for tool in _TOOLS.values():
        assert not asyncio.iscoroutinefunction(tool)


@pytest.mark.django_db(transaction=True)
def test_async_handler_does_not_raise_synchronous_only_operation():
    """A sync test calling `asyncio.run(dispatch_async(...))` must not trigger
    `SynchronousOnlyOperation`.

    Removing the bridge would make Django raise this exception because
    `dispatch` touches the ORM synchronously. This test proves the bridge
    actually wraps `dispatch` in `sync_to_async`.

    The dispatched tool MUST reach the ORM for that to be true. Routing this at
    one of the Slice 2a placeholder stubs instead — they raise `ToolInputError`
    on their first line — makes the test pass with the bridge deleted, because
    no database call is ever attempted and `SynchronousOnlyOperation` is
    unreachable. The probe is the point.

    `DJANGO_ALLOW_ASYNC_UNSAFE` MUST be unset; that is what makes the failure
    reachable. No `pytest-asyncio` dependency.
    """
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    membership = _make_membership(workspace)
    WorkspaceResource.objects.create(workspace=workspace, name="reachable")

    # Assert the env var is unset — this is what makes SynchronousOnlyOperation reachable.
    assert os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE") is None

    # A plain sync test driving the coroutine on the main thread: the ORM call
    # inside the probe happens while an event loop is running, which is exactly
    # the condition Django refuses without the bridge.
    with _probe_patch("probe_scoped", use_scope=True) as probe_name:
        result = asyncio.run(_dispatch_and_release(probe_name, {}, membership))

    assert result["rows"] == ["reachable"]