"""Tests for the demo provisioning Celery task.

Mirrors paysys/crm `Demo::ProvisionJob`: the task is idempotent (a session
that is no longer `pending` is left untouched), it backfills user + workspace
on success, and it records `failed` with the reason on any exception instead
of leaving the row stranded at `pending` — a guest polls this row, so a
non-terminal state means an eternal spinner.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from demo.models import DemoSession
from demo.tasks import provision_demo_session_task

pytestmark = pytest.mark.django_db


def test_ready_session_carries_user_and_workspace():
    session = DemoSession.objects.create(persona="teacher_minimal")

    provision_demo_session_task(str(session.pk))

    session.refresh_from_db()
    assert session.status == DemoSession.Status.READY
    assert session.provisioned is True
    assert session.user.email.startswith("demo+teacher_minimal+")
    assert session.workspace_id is not None


def test_failure_records_the_reason_and_leaves_no_pending_row():
    session = DemoSession.objects.create(persona="teacher_minimal")

    with patch(
        "demo.provisioning.teacher_minimal.TeacherMinimal.provision",
        side_effect=RuntimeError("seeding blew up"),
    ):
        provision_demo_session_task(str(session.pk))

    session.refresh_from_db()
    assert session.status == DemoSession.Status.FAILED
    assert "seeding blew up" in session.error_message
    assert session.user_id is None
    assert session.workspace_id is None


def test_unknown_persona_fails_the_session():
    session = DemoSession.objects.create(persona="not_a_persona")

    provision_demo_session_task(str(session.pk))

    session.refresh_from_db()
    assert session.status == DemoSession.Status.FAILED
    assert "not_a_persona" in session.error_message


def test_task_is_idempotent_for_a_session_already_ready():
    session = DemoSession.objects.create(persona="teacher_minimal")
    provision_demo_session_task(str(session.pk))
    session.refresh_from_db()
    first_workspace_id = session.workspace_id

    provision_demo_session_task(str(session.pk))

    session.refresh_from_db()
    assert session.workspace_id == first_workspace_id


def test_a_failed_session_is_not_retried_by_a_second_call():
    session = DemoSession.objects.create(
        persona="teacher_minimal",
        status=DemoSession.Status.FAILED,
        error_message="earlier failure",
    )

    with patch("demo.provisioning.teacher_minimal.TeacherMinimal.provision") as provision:
        provision_demo_session_task(str(session.pk))

    provision.assert_not_called()
    session.refresh_from_db()
    assert session.error_message == "earlier failure"


def test_error_message_is_truncated():
    session = DemoSession.objects.create(persona="teacher_minimal")

    with patch(
        "demo.provisioning.teacher_minimal.TeacherMinimal.provision",
        side_effect=RuntimeError("x" * 5000),
    ):
        provision_demo_session_task(str(session.pk))

    session.refresh_from_db()
    assert len(session.error_message) <= 2000
