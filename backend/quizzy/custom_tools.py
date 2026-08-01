"""In-process Quizzy tools over the MCP registry (reliable vs stdio MCP).

Composer was inventing create_student successes without calling tools. Binding
the same ``dispatch`` callables as ``LocalAgentOptions.custom_tools`` makes
mutations execute in the Django process under the chat membership.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from cursor_sdk import CustomTool, CustomToolContext
from django.core.serializers.json import DjangoJSONEncoder

from mcp_server.registry import CAPABILITY_MAP, ToolError, dispatch
from mcp_server.tool_meta import TOOL_DESCRIPTIONS, TOOL_SCHEMAS


def _json_safe(value: Any) -> Any:
    """cursor_sdk tool callbacks use stdlib json.dumps — UUIDs must be strings."""
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def build_portal_custom_tools(membership) -> dict[str, CustomTool]:
    """Build CustomTool entries for every registered MCP tool name."""
    tools: dict[str, CustomTool] = {}
    for name in CAPABILITY_MAP:

        def _execute(
            arguments: Mapping[str, Any],
            _ctx: CustomToolContext,
            *,
            tool_name: str = name,
        ) -> dict:
            try:
                result = dispatch(tool_name, dict(arguments or {}), membership)
                if isinstance(result, dict) and result.get("status") in (
                    "needs_confirmation",
                    "needs_orthography_clarification",
                ):
                    return _json_safe(
                        {
                            "ok": False,
                            "needs_clarification": True,
                            "result": result,
                        }
                    )
                return _json_safe({"ok": True, "result": result})
            except ToolError as exc:
                return {"ok": False, "error": str(exc)}

        tools[name] = CustomTool(
            execute=_execute,
            description=TOOL_DESCRIPTIONS.get(name, name),
            input_schema=TOOL_SCHEMAS.get(
                name,
                {"type": "object", "properties": {}, "additionalProperties": True},
            ),
        )
    return tools
