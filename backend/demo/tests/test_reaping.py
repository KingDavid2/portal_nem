"""TTL reap for expired demo sessions (Quizzy P6 Slice 2).

Covers the demo-mode spec scenarios: leaf-first delete of a teacher_full-shaped
tenant without ProtectedError, unexpired sessions left alone, and isolation
across two workspaces. The service is called directly — no Celery broker.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from demo.models import DemoSession
from demo.provisioning.quota_exhausted import QuotaExhausted
from demo.provisioning.teacher_full import TeacherFull
from demo.reaping import reap_expired_demo_sessions
from demo.tasks import reap_expired_demo_sessions_task
from lesson_plans.models import GenerationUsage, LessonPlan
from schools.models import Group, School, SchoolYear
from students.models import Student
from workspaces.models import Workspace
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db

User = get_user_model()


def _attach_ready_session(
    *,
    user,
    workspace,
    persona: str,
    created_at,
) -> DemoSession:
    """Create a READY DemoSession and backdate ``created_at`` (auto_now_add)."""
    session = DemoSession.objects.create(
        persona=persona,
        status=DemoSession.Status.READY,
        user=user,
        workspace=workspace,
    )
    DemoSession.objects.filter(pk=session.pk).update(created_at=created_at)
    session.refresh_from_db()
    return session


class TestReapExpiredTeacherFull:
    """Expired teacher_full-shaped tenant is removed without ProtectedError."""

    def test_expired_tenant_deleted_leaf_first_without_protected_error(self) -> None:
        user, workspace = TeacherFull().provision()
        now = timezone.now()
        session = _attach_ready_session(
            user=user,
            workspace=workspace,
            persona="teacher_full",
            created_at=now - timedelta(hours=25),
        )
        workspace_id = workspace.id
        user_id = user.id

        with workspace_scope(workspace_id):
            assert LessonPlan.objects.count() == 2
            assert Student.objects.count() == 20
            assert Group.objects.count() == 2

        reaped = reap_expired_demo_sessions(now=now)

        assert reaped == 1
        assert not DemoSession.objects.filter(pk=session.pk).exists()
        assert not Workspace.objects.filter(pk=workspace_id).exists()
        assert not User.objects.filter(pk=user_id).exists()

    def test_expired_quota_exhausted_also_clears_generation_usage(self) -> None:
        """Triangulation: GenerationUsage rows must go before Group/School."""
        user, workspace = QuotaExhausted().provision()
        now = timezone.now()
        session = _attach_ready_session(
            user=user,
            workspace=workspace,
            persona="quota_exhausted",
            created_at=now - timedelta(hours=48),
        )
        workspace_id = workspace.id

        with workspace_scope(workspace_id):
            assert GenerationUsage.objects.count() == 1

        reaped = reap_expired_demo_sessions(now=now)

        assert reaped == 1
        assert not DemoSession.objects.filter(pk=session.pk).exists()
        assert not Workspace.objects.filter(pk=workspace_id).exists()


class TestReapLeavesUnexpiredAlone:
    def test_unexpired_session_and_workspace_rows_remain(self) -> None:
        user, workspace = TeacherFull().provision()
        now = timezone.now()
        session = _attach_ready_session(
            user=user,
            workspace=workspace,
            persona="teacher_full",
            created_at=now - timedelta(hours=1),
        )

        reaped = reap_expired_demo_sessions(now=now)

        assert reaped == 0
        assert DemoSession.objects.filter(pk=session.pk).exists()
        assert Workspace.objects.filter(pk=workspace.id).exists()
        with workspace_scope(workspace.id):
            assert LessonPlan.objects.count() == 2
            assert Student.objects.count() == 20
            assert School.objects.count() == 1
            assert SchoolYear.objects.count() == 1
            assert Group.objects.count() == 2


class TestReapIsolatesWorkspaces:
    def test_only_expired_workspace_rows_are_deleted(self) -> None:
        now = timezone.now()
        expired_user, expired_ws = TeacherFull().provision()
        fresh_user, fresh_ws = TeacherFull().provision()
        expired_session = _attach_ready_session(
            user=expired_user,
            workspace=expired_ws,
            persona="teacher_full",
            created_at=now - timedelta(hours=25),
        )
        fresh_session = _attach_ready_session(
            user=fresh_user,
            workspace=fresh_ws,
            persona="teacher_full",
            created_at=now - timedelta(hours=1),
        )

        reaped = reap_expired_demo_sessions(now=now)

        assert reaped == 1
        assert not DemoSession.objects.filter(pk=expired_session.pk).exists()
        assert not Workspace.objects.filter(pk=expired_ws.id).exists()
        assert DemoSession.objects.filter(pk=fresh_session.pk).exists()
        assert Workspace.objects.filter(pk=fresh_ws.id).exists()
        with workspace_scope(fresh_ws.id):
            assert LessonPlan.objects.count() == 2
            assert Student.objects.count() == 20


class TestReapSessionsWithoutWorkspace:
    def test_expired_pending_session_is_deleted_directly(self) -> None:
        now = timezone.now()
        session = DemoSession.objects.create(
            persona="teacher_minimal",
            status=DemoSession.Status.PENDING,
        )
        DemoSession.objects.filter(pk=session.pk).update(
            created_at=now - timedelta(hours=25)
        )

        reaped = reap_expired_demo_sessions(now=now)

        assert reaped == 1
        assert not DemoSession.objects.filter(pk=session.pk).exists()


class TestReapSettingsAndTask:
    """Beat schedule + thin Celery wrapper (tasks 3.2 / 3.4)."""

    def test_ttl_default_and_hourly_beat_entry(self) -> None:
        from django.conf import settings

        assert settings.DEMO_SESSION_TTL_HOURS == 24
        entry = settings.CELERY_BEAT_SCHEDULE["reap-expired-demo-sessions"]
        assert entry["task"] == "demo.tasks.reap_expired_demo_sessions_task"
        # crontab(minute=0) → fires at minute 0 of every hour
        assert entry["schedule"].minute == {0}

    def test_celery_task_delegates_to_the_service(self) -> None:
        with patch(
            "demo.tasks.reap_expired_demo_sessions", return_value=3
        ) as mock_reap:
            result = reap_expired_demo_sessions_task()

        mock_reap.assert_called_once_with()
        assert result == 3

    def test_celery_task_reaps_an_expired_pending_session(self) -> None:
        session = DemoSession.objects.create(
            persona="teacher_minimal",
            status=DemoSession.Status.PENDING,
        )
        DemoSession.objects.filter(pk=session.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )

        assert reap_expired_demo_sessions_task() == 1
        assert not DemoSession.objects.filter(pk=session.pk).exists()
