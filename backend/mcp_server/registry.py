"""Sync tool registry and dispatcher (mcp-tool-surface + authorization specs).

A single registry maps tool names to synchronous callables. All transports
dispatch through it; no transport holds its own copy of a tool body.

Authorization flows through `workspaces.permissions.has_permission` via an
explicit `CAPABILITY_MAP` — the raw tool name never reaches the authorization
layer, and no module compares `membership.role` to a literal string.
"""

from __future__ import annotations

from collections.abc import Callable

from asgiref.sync import sync_to_async
from workspaces.permissions import has_permission

from mcp_server.errors import (
    ToolDenied,
    ToolError,
    ToolInputError,
    ToolNotFoundError,
    UnknownToolError,
)
from mcp_server.tools import (
    get_lesson_plan,
    get_quota,
    list_groups,
    list_lesson_plans,
    search_catalog,
)

Tool = Callable[..., dict]

# Re-export error types so existing `from mcp_server.registry import …` keeps
# working; definitions live in `errors.py` to avoid a tools↔registry cycle.
__all__ = [
    "CAPABILITY_MAP",
    "Tool",
    "ToolDenied",
    "ToolError",
    "ToolInputError",
    "ToolNotFoundError",
    "UnknownToolError",
    "dispatch",
    "dispatch_async",
    "register",
]

# Tool name → capability mapping. Mirrors `lesson_plans/viewsets.py:64` for the
# same `view_workspace` / `edit_content` discipline: raw action verbs are never
# fed directly into `has_permission`.
CAPABILITY_MAP: dict[str, str] = {
    "list_groups": "view_workspace",
    "list_lesson_plans": "view_workspace",
    "get_lesson_plan": "view_workspace",
    "get_quota": "view_workspace",
    "search_catalog": "view_workspace",
}

# Single registry mapping name → tool callable.
_TOOLS: dict[str, Tool] = {
    "list_groups": list_groups,
    "list_lesson_plans": list_lesson_plans,
    "get_lesson_plan": get_lesson_plan,
    "get_quota": get_quota,
    "search_catalog": search_catalog,
}


def register(name: str, func: Tool, capability: str) -> None:
    """Register a tool callable under `name`, requiring its capability.

    The capability is not optional: a tool in `_TOOLS` with no `CAPABILITY_MAP`
    entry is undispatchable, because `dispatch` treats a capability miss as an
    unknown tool. Taking both here keeps the two tables populated together
    instead of leaving that invariant to whoever calls this next.

    Raises `KeyError` if the name is already registered.
    """
    if name in _TOOLS:
        raise KeyError(f"Tool already registered: {name}")
    _TOOLS[name] = func
    CAPABILITY_MAP[name] = capability


def dispatch(name: str, arguments: dict, membership) -> dict:
    """Dispatch a tool call synchronously.

    Order:
    1. Membership present (absent → `ToolDenied`).
    2. Resolve capability from `CAPABILITY_MAP[name]` (miss → `UnknownToolError`).
    3. Check `has_permission(membership, capability)` (false → `ToolDenied`).
    4. Call the registered tool body → return its dict result.

    Step 1 precedes step 2 deliberately. Resolving the tool name first would let
    an unresolved identity tell a registered name from an unregistered one by the
    error it gets back — enumeration of the tool surface before authentication.
    Unresolved identity and insufficient role share the one `ToolDenied` shape.

    The raw tool name never reaches `has_permission`; no module compares
    `membership.role` to a literal string.
    """
    # Step 1: identity before anything name-dependent, so an anonymous caller
    # learns nothing about which names exist.
    if membership is None:
        raise ToolDenied()

    # Step 2: capability map — miss means unknown tool, not a raw KeyError.
    if name not in CAPABILITY_MAP:
        raise UnknownToolError(name)

    capability = CAPABILITY_MAP[name]

    # Step 3: authorization via the capability matrix.
    if not has_permission(membership, capability):
        raise ToolDenied()

    # Step 4: call the tool body. Registry and capability map are populated
    # together, so a name past step 2 always resolves here.
    return _TOOLS[name](membership, **arguments)


async def dispatch_async(name: str, arguments: dict, membership) -> dict:
    """Async bridge to the sync dispatch path.

    The bridge sits **at dispatch only**, never per tool. Per-tool wrapping
    gives every future tool its own chance to forget it. All transports
    (stdio, Streamable-HTTP) call this function; the sync `dispatch` path is
    never exposed to async callers directly.

    `thread_sensitive=True` keeps the call on the same thread end-to-end so
    `workspace_scope`'s `transaction.atomic()` + `SET LOCAL app.workspace_id`
    are coherent — the same guarantee `TenancyMiddleware` relies on.
    """
    return await sync_to_async(dispatch, thread_sensitive=True)(
        name, arguments, membership
    )
