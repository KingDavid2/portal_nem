"""Typed MCP tool dispatch errors (mcp-tool-surface).

Kept in a dedicated module so tool bodies can raise them without importing
`registry` (which loads the tool callables).
"""

from __future__ import annotations


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
