"""Tests for the `DemoSession` model.

DemoSession is a platform-level provisioning receipt — it must be readable
before any workspace exists, which is why it inherits from the plain
`models.Model` and not from `ScopedModel`. These tests cover the default
state and the `provisioned` property.
"""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model

from demo.models import DemoSession
from workspaces.models import Workspace

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(
        email="demo-test@example.com",
        password="s3cret-pass",
    )


@pytest.fixture
def workspace():
    return Workspace.objects.create(type=Workspace.Type.GROUP)


def test_new_session_defaults_to_pending():
    session = DemoSession.objects.create(persona="teacher_minimal")

    assert session.status == DemoSession.Status.PENDING
    assert session.error_message == ""
    assert session.user is None
    assert session.workspace is None


def test_provisioned_is_false_when_pending_even_with_user_and_workspace(user, workspace):
    """A pending session is not provisioned, even if user and workspace are set.

    This catches the bug where `provisioned` would return True because it
    only checked user_id and workspace_id without looking at status.
    """
    session = DemoSession.objects.create(
        persona="teacher_minimal",
        status=DemoSession.Status.PENDING,
        user=user,
        workspace=workspace,
    )

    assert session.provisioned is False


def test_provisioned_is_false_when_ready_but_user_missing(workspace):
    """READY status with a workspace but no user is NOT provisioned.

    The Ruby original requires both user_id AND account_id present. Mirrored
    here as user_id AND workspace_id.
    """
    session = DemoSession.objects.create(
        persona="teacher_minimal",
        status=DemoSession.Status.READY,
        user=None,
        workspace=workspace,
    )

    assert session.provisioned is False


def test_provisioned_is_false_when_ready_but_workspace_missing(user):
    """READY status with a user but no workspace is NOT provisioned."""
    session = DemoSession.objects.create(
        persona="teacher_minimal",
        status=DemoSession.Status.READY,
        user=user,
        workspace=None,
    )

    assert session.provisioned is False


def test_provisioned_is_true_only_when_ready_with_both(user, workspace):
    """The happy path: READY status with user AND workspace set.

    This is the case that matters — if `provisioned` returned
    `self.status == READY` alone, the tests above would pass but real
    sessions without user/workspace would incorrectly appear provisioned.
    """
    session = DemoSession.objects.create(
        persona="teacher_minimal",
        status=DemoSession.Status.READY,
        user=user,
        workspace=workspace,
    )

    assert session.provisioned is True


def test_provisioned_is_false_when_failed_with_both(user, workspace):
    """A failed session is never provisioned, regardless of FKs."""
    session = DemoSession.objects.create(
        persona="teacher_minimal",
        status=DemoSession.Status.FAILED,
        user=user,
        workspace=workspace,
        error_message="Something went wrong",
    )

    assert session.provisioned is False


def test_session_id_is_an_unguessable_uuid():
    """The session id is the only thing guarding an unauthenticated poll
    endpoint, so it must not be a sequential integer."""
    first = DemoSession.objects.create(persona="teacher_minimal")
    second = DemoSession.objects.create(persona="teacher_minimal")

    assert isinstance(first.pk, uuid.UUID)
    assert first.pk != second.pk