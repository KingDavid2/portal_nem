"""Leaf-first reap of expired demo tenants under workspace_scope.

Expiry is ``DemoSession.created_at`` + ``DEMO_SESSION_TTL_HOURS`` (no migration).
The entire delete — including ``workspace.delete()`` — MUST run inside
``workspace_scope`` so RLS filters the cascade for the runtime role. Leaf-first
order satisfies ``PROTECT`` on ``Student.group`` and ``LessonPlan.group``.
Sessions with no workspace (pending/failed) are deleted directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from demo.models import DemoSession
from lesson_plans.models import GenerationUsage, LessonPlan
from schools.models import Group, School, SchoolYear
from students.models import Student
from workspaces.models import Workspace
from workspaces.scope import workspace_scope

User = get_user_model()


def reap_expired_demo_sessions(now: datetime | None = None) -> int:
    """Delete demo tenants whose ``created_at`` is older than the TTL.

    Returns the number of ``DemoSession`` rows reaped.
    """
    now = timezone.now() if now is None else now
    cutoff = now - timedelta(hours=settings.DEMO_SESSION_TTL_HOURS)
    expired = list(DemoSession.objects.filter(created_at__lt=cutoff))
    reaped = 0

    for session in expired:
        workspace_id = session.workspace_id
        user_id = session.user_id

        if workspace_id is None:
            session.delete()
            reaped += 1
            continue

        with workspace_scope(workspace_id):
            # Leaf-first: PROTECT FKs on LessonPlan.group / Student.group.
            LessonPlan.objects.all().delete()
            Student.objects.all().delete()
            GenerationUsage.objects.all().delete()
            Group.objects.all().delete()
            SchoolYear.objects.all().delete()
            School.objects.all().delete()
            # workspace.delete cascades Membership + DemoSession; must stay
            # inside the scope so RLS sees the cascade under runtime.
            Workspace.objects.filter(pk=workspace_id).delete()

        if user_id is not None:
            _delete_user_if_orphaned(user_id)
        reaped += 1

    return reaped


def _delete_user_if_orphaned(user_id) -> None:
    """Drop the demo user once no memberships or sent invitations remain."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    if user.memberships.exists() or user.sent_invitations.exists():
        return
    user.delete()
