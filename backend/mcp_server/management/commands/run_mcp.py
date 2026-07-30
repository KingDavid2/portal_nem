"""`manage.py run_mcp` — run the MCP server over stdio.

Identity comes from the PORTAL_NEM_MCP_TOKEN environment variable
(see mcp_server.server). Example:

    PORTAL_NEM_MCP_TOKEN=<raw> uv run manage.py run_mcp
"""

from __future__ import annotations

import asyncio

from django.core.management.base import BaseCommand

from mcp_server.server import run_stdio


class Command(BaseCommand):
    help = (
        "Run the Portal NEM MCP server over stdio. "
        "Set PORTAL_NEM_MCP_TOKEN to a raw API token before connecting a client."
    )

    def handle(self, *args, **options):
        asyncio.run(run_stdio())
