"""Services layer for LessonPlan (ai-planeaciones spec — Generation Request
Is Gated, Workspace-Bound, and Schema-Validated; CRUD Endpoints Are
Workspace-Scoped). Same shape as `schools/services.py`/`students/services.py`.

`generate_lesson_plan` creates a `pending` row synchronously, taking the
workspace from `membership.workspace` (never client input), enforces the
`workspace == group.workspace` invariant explicitly (never relies on RLS for
this authorization decision — design Interfaces/Contracts), then enqueues
`generate_lesson_plan_task` to perform the LLM call asynchronously.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction

from lesson_plans.models import LessonPlan
from lesson_plans.tasks import generate_lesson_plan_task
from workspaces.permissions import has_permission


def _require_edit_content(membership) -> None:
    if not has_permission(membership, "edit_content"):
        raise PermissionDenied("Membership lacks edit_content capability.")


def generate_lesson_plan(
    *, membership, group, campo: str, grade: str, theme: str
) -> LessonPlan:
    _require_edit_content(membership)
    if group.workspace_id != membership.workspace_id:
        raise ValueError("Group does not belong to the caller's workspace.")
    with transaction.atomic():
        plan = LessonPlan.objects.create(
            workspace=membership.workspace,
            group=group,
            campo=campo,
            grade=grade,
            theme=theme,
        )
    generate_lesson_plan_task.delay(workspace_id=membership.workspace_id, lesson_plan_id=plan.pk)
    return plan


def delete_lesson_plan(*, membership, lesson_plan: LessonPlan) -> None:
    _require_edit_content(membership)
    if lesson_plan.workspace_id != membership.workspace_id:
        raise ValueError("LessonPlan does not belong to the caller's workspace.")
    with transaction.atomic():
        lesson_plan.delete()
