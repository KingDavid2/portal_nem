"""Read-only MCP tool bodies for lesson plans / catalog / groups.

Each tool enters `workspace_scope(membership.workspace_id)` itself. Payloads
reuse the existing HTTP serializer shapes. School-structure CRUD lives in
``tools_school.py``.
"""

from __future__ import annotations

from dataclasses import asdict

from lesson_plans.core.catalog import (
    CONTENTS,
    CROSS_CUTTING_THEMES,
    FIELDS,
    PDAS,
    SUBJECTS,
    _normalize,
    field_by_id,
)
from lesson_plans.models import LessonPlan
from lesson_plans.quota import current_period, current_usage, format_period
from lesson_plans.serializers import (
    CatalogContentSerializer,
    CatalogFieldSerializer,
    CatalogSubjectSerializer,
    CatalogThemeSerializer,
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


def _matches(needle: str, haystack: str) -> bool:
    return _normalize(needle) in _normalize(haystack)


def _content_dict(content) -> dict:
    pda_by_id = {pda.id: pda for pda in PDAS}
    return {
        "id": content.id,
        "text": content.text,
        "pdas": [
            {"id": pda_id, "text": pda_by_id[pda_id].text}
            for pda_id in content.pda_ids
        ],
    }


def search_catalog(membership, *, query: str = "", field: str | None = None, **_kwargs) -> dict:
    """Normalized substring search over the frozen curriculum catalog (design D1)."""
    from mcp_server.registry import ToolInputError

    with workspace_scope(membership.workspace_id):
        try:
            if field is not None:
                selected = field_by_id(field)
                fields = (selected,)
                subjects = tuple(
                    s for s in SUBJECTS if s.field_id == selected.id
                )
                contents = tuple(
                    c for c in CONTENTS if c.field_id == selected.id
                )
            else:
                fields = FIELDS
                subjects = SUBJECTS
                contents = CONTENTS
        except KeyError as exc:
            raise ToolInputError(str(exc)) from exc

        themes = CROSS_CUTTING_THEMES
        matched_fields = [asdict(f) for f in fields if _matches(query, f.name)]
        matched_subjects = [
            asdict(s) for s in subjects if _matches(query, s.name)
        ]
        matched_themes = [asdict(t) for t in themes if _matches(query, t.name)]

        matched_contents = []
        for content in contents:
            rendered = _content_dict(content)
            if _matches(query, content.text) or any(
                _matches(query, pda["text"]) for pda in rendered["pdas"]
            ):
                # PDA hit still renders the content whole (design D1).
                matched_contents.append(rendered)

        return {
            "fields": CatalogFieldSerializer(matched_fields, many=True).data,
            "subjects": CatalogSubjectSerializer(
                matched_subjects, many=True
            ).data,
            "cross_cutting_themes": CatalogThemeSerializer(
                matched_themes, many=True
            ).data,
            "contents": CatalogContentSerializer(
                matched_contents, many=True
            ).data,
        }
