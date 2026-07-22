"""Capability matrix authorization (design D-3 Interfaces, authorization spec).

`has_permission` is the sole source of truth for "can-do-X" decisions. It is
architecturally separate from tenancy isolation ("can-see-workspace-Y"),
which is decided by `ScopedManager` (D5) and Postgres RLS (D8). No caller —
views, serializers, or this DRF permission class — may substitute an inline
comparison of the membership role against a literal string for a call
through this matrix.
"""

from rest_framework.permissions import BasePermission

CAPABILITIES: dict[str, frozenset[str]] = {
    "owner": frozenset(
        {
            "delete_workspace",
            "manage_members",
            "manage_billing",
            "view_workspace",
            "edit_content",
        }
    ),
    "admin": frozenset(
        {
            "manage_members",
            "view_workspace",
            "edit_content",
        }
    ),
    "member": frozenset(
        {
            "view_workspace",
            "edit_content",
        }
    ),
}


def has_permission(membership, action: str) -> bool:
    """Return whether `membership.role` grants `action`, per the matrix."""
    role = getattr(membership, "role", None)
    return action in CAPABILITIES.get(role, frozenset())


class WorkspacePermission(BasePermission):
    """DRF permission class delegating every decision to `has_permission`.

    Never compares `membership.role` against a literal string itself —
    that would defeat the single-source-of-truth guarantee (authorization
    spec, gate: no inline role-string comparisons).
    """

    def has_object_permission(self, request, view, obj) -> bool:
        membership = getattr(request, "membership", None)
        action = getattr(view, "action", None)
        return has_permission(membership, action)
