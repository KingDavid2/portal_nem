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

Tool = Callable[..., dict]

# Tool name → capability mapping. Mirrors viewset capability maps:
# reads → view_workspace; school-structure mutations → edit_content.
CAPABILITY_MAP: dict[str, str] = {
    "list_groups": "view_workspace",
    "list_lesson_plans": "view_workspace",
    "get_lesson_plan": "view_workspace",
    "get_quota": "view_workspace",
    "search_catalog": "view_workspace",
    "get_teaching_context": "view_workspace",
    "list_school_years": "view_workspace",
    "list_students": "view_workspace",
    "create_school": "edit_content",
    "create_school_year": "edit_content",
    "create_group": "edit_content",
    "create_student": "edit_content",
    "update_school": "edit_content",
    "update_school_year": "edit_content",
    "update_group": "edit_content",
    "update_student": "edit_content",
    "delete_school": "edit_content",
    "delete_school_year": "edit_content",
    "delete_group": "edit_content",
    "delete_student": "edit_content",
}


class ToolError(Exception):
    """Base class for MCP tool dispatch errors."""


class UnknownToolError(ToolError):
    """Tool name is not in the registry."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Unknown tool: {name}")


class ToolNotFoundError(ToolError):
    """A requested resource was not found.

    Indistinguishable by payload from a malformed id or a cross-workspace miss:
    one message, one shape. Callers pass the fixed message explicitly; this
    class holds no default, so a per-resource message can never drift into a
    distinguishing signal.
    """


class ToolInputError(ToolError):
    """Tool input validation failed."""


class ToolDenied(ToolError):
    """Access denied.

    Covers both unresolved identity and authorization failure — one shape,
    no distinguishable outcome between "unknown token" and "token valid but
    role insufficient".
    """


# ---------------------------------------------------------------------------
# Tool callables — bodies live in tools.py / tools_school.py.
# ---------------------------------------------------------------------------

from mcp_server.tools import (  # noqa: E402
    get_lesson_plan,
    get_quota,
    list_groups,
    list_lesson_plans,
    search_catalog,
)
from mcp_server.tools_school import (  # noqa: E402
    create_group,
    create_school,
    create_school_year,
    create_student,
    delete_group,
    delete_school,
    delete_school_year,
    delete_student,
    get_teaching_context,
    list_school_years,
    list_students,
    update_group,
    update_school,
    update_school_year,
    update_student,
)

# Single registry mapping name → tool callable.
_TOOLS: dict[str, Tool] = {
    "list_groups": list_groups,
    "list_lesson_plans": list_lesson_plans,
    "get_lesson_plan": get_lesson_plan,
    "get_quota": get_quota,
    "search_catalog": search_catalog,
    "get_teaching_context": get_teaching_context,
    "list_school_years": list_school_years,
    "list_students": list_students,
    "create_school": create_school,
    "create_school_year": create_school_year,
    "create_group": create_group,
    "create_student": create_student,
    "update_school": update_school,
    "update_school_year": update_school_year,
    "update_group": update_group,
    "update_student": update_student,
    "delete_school": delete_school,
    "delete_school_year": delete_school_year,
    "delete_group": delete_group,
    "delete_student": delete_student,
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
