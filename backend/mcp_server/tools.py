"""Five read-only MCP tool bodies (mcp-tool-surface + design D1–D3).

Each tool enters `workspace_scope(membership.workspace_id)` itself. Payloads
reuse the existing HTTP serializer shapes.

`search_catalog` is stubbed here — deferred to feat/quizzy-p4-s3b-search-catalog
(tasks.md 400-line headroom). The four workspace-scoped tools and
`catalog_group_payload` land together in this slice.
"""

from __future__ import annotations

from lesson_plans.models import LessonPlan
from lesson_plans.quota import current_period, current_usage, format_period
from lesson_plans.serializers import (
    GenerationQuotaSerializer,
    LessonPlanSerializer,
    catalog_group_payload,
)
from schools.models import Group
from workspaces.scope import workspace_scope


def list_groups(membership, **_kwargs) -> dict:
    with workspace_scope(membership.workspace_id):
        groups = list(
            Group.objects.select_related("school_year__school").order_by("pk")
        )
        return {"groups": [catalog_group_payload(group) for group in groups]}


def list_lesson_plans(membership, **_kwargs) -> dict:
    with workspace_scope(membership.workspace_id):
        plans = list(LessonPlan.objects.order_by("pk"))
        return {
            "lesson_plans": [LessonPlanSerializer(plan).data for plan in plans]
        }


def get_lesson_plan(membership, *, id, **_kwargs) -> dict:
    """Indistinguishable not-found for cross-workspace, nowhere, and malformed ids."""
    from mcp_server.registry import ToolNotFoundError

    with workspace_scope(membership.workspace_id):
        try:
            plan = LessonPlan.objects.get(pk=int(id))
        except (LessonPlan.DoesNotExist, ValueError, TypeError):
            raise ToolNotFoundError("Lesson plan not found.")
        return LessonPlanSerializer(plan).data


def get_quota(membership, **_kwargs) -> dict:
    with workspace_scope(membership.workspace_id):
        used, limit = current_usage(membership.workspace)
        payload = {
            "period": format_period(current_period()),
            "used": used,
            "limit": limit,
            "remaining": max(limit - used, 0),
        }
        return GenerationQuotaSerializer(payload).data


def search_catalog(membership, **_kwargs) -> dict:
    """Deferred to feat/quizzy-p4-s3b-search-catalog (400-line headroom)."""
    from mcp_server.registry import ToolInputError

    raise ToolInputError(
        "search_catalog deferred to feat/quizzy-p4-s3b-search-catalog"
    )
