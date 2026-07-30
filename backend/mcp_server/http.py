"""Streamable-HTTP MCP transport (mcp-tool-surface — Slice 5).

Identity from ``Authorization: Bearer`` → ``resolve_membership`` →
``dispatch_async``. Mounted only when ``settings.MCP_HTTP_ENABLED``.
"""

from __future__ import annotations

from contextvars import ContextVar

from asgiref.sync import async_to_sync, sync_to_async
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from mcp.server.lowlevel.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from workspaces.models import Membership

from mcp_server.auth import resolve_membership
from mcp_server.registry import ToolError, dispatch_async
from mcp_server.server import _error_result, _success_result, handle_list_tools

MCP_HTTP_PATH = "mcp/"

_http_membership: ContextVar[Membership | None] = ContextVar(
    "mcp_http_membership", default=None
)


def parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, remainder = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    raw = remainder.strip()
    return raw or None


def resolve_bearer_membership(authorization: str | None) -> Membership | None:
    raw = parse_bearer(authorization)
    if raw is None:
        return None
    return resolve_membership(raw)


async def handle_http_call_tool(
    authorization: str | None, name: str, arguments: dict | None
):
    """Bearer identity → dispatch_async → MCP result (no transport-local tools).

    Order: (1) resolve identity, (2) dispatch_async, (3) ToolError→isError,
    (4) success payload.
    """
    membership = await sync_to_async(
        resolve_bearer_membership, thread_sensitive=True
    )(authorization)
    try:
        payload = await dispatch_async(name, arguments or {}, membership)
    except ToolError as exc:
        return _error_result(str(exc))
    return _success_result(payload)


def build_http_server() -> Server:
    """MCP Server; call_tool reads membership from the request ContextVar."""
    server = Server("portal-nem-http")

    @server.list_tools()
    async def list_tools():
        return await handle_list_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict | None):
        membership = _http_membership.get()
        try:
            payload = await dispatch_async(name, arguments or {}, membership)
        except ToolError as exc:
            return _error_result(str(exc))
        return _success_result(payload)

    return server


async def _asgi_response_for_django(
    request: HttpRequest, membership: Membership
) -> HttpResponse:
    """One-shot Streamable-HTTP (stateless JSON) for a Django request."""
    manager = StreamableHTTPSessionManager(
        app=build_http_server(),
        json_response=True,
        stateless=True,
    )
    status_code = 500
    raw_headers: list[tuple[bytes, bytes]] = []
    body_chunks: list[bytes] = []

    async def send(message: dict) -> None:
        nonlocal status_code, raw_headers
        if message["type"] == "http.response.start":
            status_code = message["status"]
            raw_headers = list(message.get("headers", []))
        elif message["type"] == "http.response.body":
            chunk = message.get("body", b"")
            if chunk:
                body_chunks.append(chunk)

    body = request.body
    seen = False

    async def receive() -> dict:
        nonlocal seen
        if not seen:
            seen = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    asgi_headers = [
        (n.lower().encode("latin-1"), v.encode("latin-1"))
        for n, v in request.headers.items()
    ]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": request.method,
        "scheme": "http",
        "path": request.path,
        "raw_path": request.path.encode("utf-8"),
        "query_string": request.META.get("QUERY_STRING", "").encode("latin-1"),
        "root_path": "",
        "headers": asgi_headers,
        "client": ("127.0.0.1", 0),
        "server": ("testserver", 80),
    }

    token = _http_membership.set(membership)
    try:
        async with manager.run():
            await manager.handle_request(scope, receive, send)
    finally:
        _http_membership.reset(token)

    header_map = {k.decode("latin-1"): v.decode("latin-1") for k, v in raw_headers}
    return HttpResponse(
        b"".join(body_chunks),
        status=status_code,
        content_type=header_map.get("content-type", "application/json"),
    )


@csrf_exempt
@require_http_methods(["GET", "POST", "DELETE"])
def mcp_http_view(request: HttpRequest) -> HttpResponse:
    """Django mount: Bearer gate first (401, no tool), then Streamable-HTTP ASGI."""
    membership = resolve_bearer_membership(request.headers.get("Authorization"))
    if membership is None:
        return HttpResponse(status=401)
    return async_to_sync(_asgi_response_for_django)(request, membership)
