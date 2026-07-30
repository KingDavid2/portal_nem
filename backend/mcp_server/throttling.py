"""Per-token throttle for the Streamable-HTTP MCP mount (Quizzy P6 Slice 1b).

Keyed on ``sha256(bearer)`` so counters follow the token identity, not the IP.
Rate comes from ``settings.MCP_HTTP_THROTTLE_RATE`` (override-friendly in tests).
"""

from __future__ import annotations

import hashlib

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class McpHttpTokenThrottle(SimpleRateThrottle):
    scope = "mcp_http"

    def get_rate(self) -> str:
        return settings.MCP_HTTP_THROTTLE_RATE

    def get_cache_key(self, request, view) -> str | None:
        # Deferred: http.py imports this module after auth, so avoid a cycle
        # with parse_bearer living on the transport module.
        from mcp_server.http import parse_bearer

        authorization = request.META.get("HTTP_AUTHORIZATION")
        if not authorization and hasattr(request, "headers"):
            authorization = request.headers.get("Authorization")
        raw = parse_bearer(authorization)
        if raw is None:
            return None
        ident = hashlib.sha256(raw.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}
