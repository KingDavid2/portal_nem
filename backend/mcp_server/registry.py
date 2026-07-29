"""Sync tool registry and dispatcher (mcp-tool-surface + authorization specs).

A single registry maps tool names to synchronous callables. All transports
dispatch through it; no transport holds its own copy of a tool body.

Authorization flows through `workspaces.permissions.has_permission` via an
explicit `CAPABILITY_MAP` — the raw tool name never reaches the authorization
layer, and no module compares `membership.role` to a literal string.
"""

from __future__ import annotations

from workspaces.permissions import has_permission

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
    one message, one shape.
    """

    message = "Not found."


class ToolInputError(ToolError):
    """Tool input validation failed."""


class ToolDenied(ToolError):
    """Access denied.

    Covers both unresolved identity and authorization failure — one shape,
    no distinguishable outcome between "unknown token" and "token valid but
    role insufficient".
    """


# ---------------------------------------------------------------------------
# Placeholder tool stubs — replaced by `tools.py` in Slice 3.
# ---------------------------------------------------------------------------

def _list_groups(_membership, **_kwargs: dict) -> dict:
    raise ToolInputError("list_groups tool not yet implemented")


def _list_lesson_plans(_membership, **_kwargs: dict) -> dict:
    raise ToolInputError("list_lesson_plans tool not yet implemented")


def _get_lesson_plan(_membership, **_kwargs: dict) -> dict:
    raise ToolInputError("get_lesson_plan tool not yet implemented")


def _get_quota(_membership, **_kwargs: dict) -> dict:
    raise ToolInputError("get_quota tool not yet implemented")


def _search_catalog(_membership, **_kwargs: dict) -> dict:
    raise ToolInputError("search_catalog tool not yet implemented")


# Single registry mapping name → (tool_callable).
_TOOLS: dict[str, callable] = {
    "list_groups": _list_groups,
    "list_lesson_plans": _list_lesson_plans,
    "get_lesson_plan": _get_lesson_plan,
    "get_quota": _get_quota,
    "search_catalog": _search_catalog,
}


def register(name: str, func: callable) -> None:
    """Register a tool callable under `name`.

    Raises `KeyError` if the name is already registered.
    """
    if name in _TOOLS:
        raise KeyError(f"Tool already registered: {name}")
    _TOOLS[name] = func


def dispatch(name: str, arguments: dict, membership) -> dict:
    """Dispatch a tool call synchronously.

    Order:
    1. Resolve capability from `CAPABILITY_MAP[name]` (miss → `UnknownToolError`).
    2. Check `has_permission(membership, capability)` (false → `ToolDenied`).
    3. Call the registered tool body → return its dict result.

    The raw tool name never reaches `has_permission`; no module compares
    `membership.role` to a literal string.
    """
    # Step 1: capability map — miss means unknown tool, not a raw KeyError.
    if name not in CAPABILITY_MAP:
        raise UnknownToolError(name)

    capability = CAPABILITY_MAP[name]

    # Step 2: authorization via the capability matrix.
    if not has_permission(membership, capability):
        raise ToolDenied()

    # Step 3: call the tool body.
    tool = _TOOLS.get(name)
    if tool is None:
        raise UnknownToolError(name)

    return tool(membership, **arguments)