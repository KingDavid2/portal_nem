"""stdio MCP transport (mcp-tool-surface — Slice 4).

Identity from PORTAL_NEM_MCP_TOKEN → resolve_membership → dispatch_async.
ToolError subclasses render as MCP tool errors (isError=True). ToolNotFoundError
always carries its fixed message — never a varying status or error type.
"""

from __future__ import annotations

import json
import os

import mcp.types as types
from asgiref.sync import sync_to_async
from django.core.serializers.json import DjangoJSONEncoder
from mcp.server.lowlevel.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from mcp_server.auth import resolve_membership
from mcp_server.registry import CAPABILITY_MAP, ToolError, dispatch_async

TOKEN_ENV = "PORTAL_NEM_MCP_TOKEN"

# Minimal JSON Schemas so the SDK's input validation accepts the known args.
_TOOL_SCHEMAS: dict[str, dict] = {
    "list_groups": {"type": "object", "properties": {}, "additionalProperties": False},
    "list_lesson_plans": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
    "get_lesson_plan": {
        "type": "object",
        "properties": {"id": {}},
        "required": ["id"],
        "additionalProperties": False,
    },
    "get_quota": {"type": "object", "properties": {}, "additionalProperties": False},
    "search_catalog": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "default": ""},
            "field": {"type": ["string", "null"], "default": None},
        },
        "additionalProperties": False,
    },
}

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "list_groups": "List groups in the authenticated workspace.",
    "list_lesson_plans": "List lesson plans in the authenticated workspace.",
    "get_lesson_plan": "Fetch one lesson plan by id (scoped to the workspace).",
    "get_quota": "Return the workspace generation quota card.",
    "search_catalog": "Search the frozen curriculum catalog by normalized substring.",
}


def _resolve_identity_from_env_sync():
    """Sync identity lookup — unset and garbage both yield None."""
    raw = os.environ.get(TOKEN_ENV)
    if not raw:
        return None
    return resolve_membership(raw)


async def _resolve_identity_from_env():
    """Bridge resolve_membership onto a sync thread (design: two ORM bridges).

    `resolve_membership` touches the ORM; calling it on the event loop raises
    SynchronousOnlyOperation. Same `thread_sensitive=True` discipline as
    `dispatch_async`.
    """
    return await sync_to_async(
        _resolve_identity_from_env_sync, thread_sensitive=True
    )()


def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        isError=True,
    )


def _success_result(payload: dict) -> types.CallToolResult:
    # DjangoJSONEncoder covers UUID / date values from DRF serializer `.data`.
    text = json.dumps(payload, cls=DjangoJSONEncoder)
    # Re-parse so structuredContent is plain JSON types (SDK-friendly).
    structured = json.loads(text)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        structuredContent=structured,
        isError=False,
    )


async def handle_call_tool(
    name: str, arguments: dict | None
) -> types.CallToolResult:
    """Async call_tool handler: identity → dispatch_async → MCP result.

    Order (enumerated — do not reorder):
    1. Resolve identity from PORTAL_NEM_MCP_TOKEN via resolve_membership.
    2. Await dispatch_async(name, arguments, membership).
    3. On ToolError, render as isError tool result (ToolNotFoundError keeps
       its fixed message via str(exc)).
    4. On success, return the tool payload as structured + text content.
    """
    # Step 1: identity from the environment — before any name-dependent work
    # that would distinguish registered vs unknown tools for an anonymous caller.
    # dispatch itself still checks membership first; this is the transport's
    # identity source.
    membership = await _resolve_identity_from_env()

    # Step 2: single registry path — no transport-local tool copy.
    try:
        payload = await dispatch_async(name, arguments or {}, membership)
    except ToolError as exc:
        # Step 3: all ToolError subclasses → isError. ToolNotFoundError's
        # message is whatever the tool raised (the fixed "Lesson plan not
        # found.") — never rewritten into a varying status or type.
        return _error_result(str(exc))

    # Step 4: success payload.
    return _success_result(payload)


async def handle_list_tools() -> list[types.Tool]:
    """Advertise the five registered tools from CAPABILITY_MAP."""
    return [
        types.Tool(
            name=name,
            description=_TOOL_DESCRIPTIONS.get(name, name),
            inputSchema=_TOOL_SCHEMAS.get(
                name, {"type": "object", "properties": {}, "additionalProperties": True}
            ),
        )
        for name in sorted(CAPABILITY_MAP)
    ]


def build_server() -> Server:
    """Construct the low-level MCP Server with list_tools / call_tool handlers."""
    server = Server("portal-nem")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return await handle_list_tools()

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict | None
    ) -> types.CallToolResult:
        return await handle_call_tool(name, arguments)

    return server


async def run_stdio() -> None:
    """stdio run loop — identity already comes from the environment per call."""
    server = build_server()
    init = InitializationOptions(
        server_name=server.name,
        server_version="0.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init)
