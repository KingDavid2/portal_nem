"""Confirmation gate for MCP update/delete tools."""

from __future__ import annotations


def confirmation_required(*, action: str, preview: dict) -> dict:
    """Envelope returned when ``confirm`` is missing or not strictly True."""
    return {
        "status": "needs_confirmation",
        "action": action,
        "preview": preview,
    }


def is_confirmed(confirm) -> bool:
    """Strict True only — strings/1/\"true\" do not count."""
    return confirm is True
