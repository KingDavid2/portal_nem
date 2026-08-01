"""stdio MCP transport (mcp-tool-surface).

Identity from PORTAL_NEM_MCP_TOKEN → resolve_membership → dispatch_async.
ToolError subclasses render as isError; ToolNotFoundError keeps its fixed message.
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
from mcp_server.tool_meta import TOOL_DESCRIPTIONS, TOOL_SCHEMAS

TOKEN_ENV = "PORTAL_NEM_MCP_TOKEN"


def _resolve_identity_from_env_sync():
    """Unset and garbage tokens both yield None."""
    raw = os.environ.get(TOKEN_ENV)
    if not raw:
        return None
    return resolve_membership(raw)


async def _resolve_identity_from_env():
    """Bridge resolve_membership with thread_sensitive=True (design: two ORM bridges)."""
    return await sync_to_async(
        _resolve_identity_from_env_sync, thread_sensitive=True
    )()


def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        isError=True,
    )


def _success_result(payload: dict) -> types.CallToolResult:
    text = json.dumps(payload, cls=DjangoJSONEncoder)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        structuredContent=json.loads(text),
        isError=False,
    )


async def handle_call_tool(
    name: str, arguments: dict | None
) -> types.CallToolResult:
    """Identity → dispatch_async → MCP result.

    Order (do not reorder):
    1. Resolve identity from PORTAL_NEM_MCP_TOKEN via resolve_membership.
    2. Await dispatch_async(name, arguments, membership).
    3. On ToolError → isError (ToolNotFoundError keeps its fixed message).
    4. On success → structured + text content.
    """
    # Step 1: identity before name-dependent work (anonymous callers learn nothing).
    membership = await _resolve_identity_from_env()

    # Step 2: single registry path — no transport-local tool copy.
    try:
        payload = await dispatch_async(name, arguments or {}, membership)
    except ToolError as exc:
        # Step 3: ToolError → isError; ToolNotFoundError message is str(exc).
        return _error_result(str(exc))

    # Step 4: success payload.
    return _success_result(payload)


async def handle_list_tools() -> list[types.Tool]:
    """Advertise registered tools from CAPABILITY_MAP."""
    return [
        types.Tool(
            name=name,
            description=TOOL_DESCRIPTIONS.get(name, name),
            inputSchema=TOOL_SCHEMAS.get(
                name, {"type": "object", "properties": {}, "additionalProperties": True}
            ),
        )
        for name in sorted(CAPABILITY_MAP)
    ]


def build_server() -> Server:
    """MCP Server with list_tools / call_tool handlers."""
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
    """stdio run loop — identity comes from the environment per call."""
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
