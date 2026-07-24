"""Services layer for LessonPlan (ai-planeaciones spec — Generation Request
Is Gated, Workspace-Bound, and Schema-Validated; CRUD Endpoints Are
Workspace-Scoped). Same shape as `schools/services.py`/`students/services.py`.

`generate_lesson_plan` creates a `pending` row synchronously, taking the
workspace from `membership.workspace` (never client input), enforces the
`workspace == group.workspace` invariant explicitly (never relies on RLS for
this authorization decision — design Interfaces/Contracts), charges the
workspace's monthly generation quota, then enqueues
`generate_lesson_plan_task` to perform the LLM call asynchronously.
"""

from __future__ import annotations

from datetime import date

from django.core.exceptions import PermissionDenied
from django.db import transaction

from lesson_plans.core.catalog import field_by_id
from lesson_plans.models import LessonPlan
from lesson_plans.quota import consume_generation
from lesson_plans.tasks import generate_lesson_plan_task
from workspaces.permissions import has_permission


def _require_edit_content(membership) -> None:
    if not has_permission(membership, "edit_content"):
        raise PermissionDenied("Membership lacks edit_content capability.")


def generate_lesson_plan(
    *,
    membership,
    group,
    field_id: str,
    methodology_id: str,
    theme: str,
    context_diagnosis: str,
    scenario: str,
    duration_weeks: int,
    start_date: date,
    end_date: date,
    cross_cutting_theme_ids: list[str],
    content_selections: list[dict],
    subject_id: str = "",
) -> LessonPlan:
    """Persist a validated planning request and enqueue its generation.

    The caller passes the catalog ids the teacher picked; `campo` and `grade`
    are never client input — they are derived here from the resolved field and
    the group so the stored row cannot disagree with its own context.
    """
    _require_edit_content(membership)
    if group.workspace_id != membership.workspace_id:
        raise ValueError("Group does not belong to the caller's workspace.")
    with transaction.atomic():
        # Charged before the row exists, and inside the same transaction, so a
        # rejected request persists nothing and any later rollback refunds the
        # count automatically (`lesson_plans.quota`).
        consume_generation(membership.workspace)
        plan = LessonPlan.objects.create(
            workspace=membership.workspace,
            group=group,
            campo=field_by_id(field_id).name,
            grade=str(group.grado),
            theme=theme,
            field_id=field_id,
            subject_id=subject_id,
            methodology_id=methodology_id,
            duration_weeks=duration_weeks,
            start_date=start_date,
            end_date=end_date,
            scenario=scenario,
            context_diagnosis=context_diagnosis,
            cross_cutting_theme_ids=cross_cutting_theme_ids,
            content_selections=content_selections,
        )
    generate_lesson_plan_task.delay(workspace_id=membership.workspace_id, lesson_plan_id=plan.pk)
    return plan


def delete_lesson_plan(*, membership, lesson_plan: LessonPlan) -> None:
    _require_edit_content(membership)
    if lesson_plan.workspace_id != membership.workspace_id:
        raise ValueError("LessonPlan does not belong to the caller's workspace.")
    with transaction.atomic():
        lesson_plan.delete()
