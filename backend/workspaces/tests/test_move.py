"""RED-first tests for move_member_to_workspace + WorkspaceHistory audit trail
(workspace-history spec, workspaces spec — Atomic Member Move Between
Workspaces, authorization spec — Dual-Workspace Authorization for Member
Moves).
"""

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db

User = get_user_model()


# --- D1: WorkspaceHistory model / migration --------------------------------


def test_workspace_history_is_not_a_scoped_model():
    from workspaces.managers import ScopedManager
    from workspaces.models import ScopedModel, WorkspaceHistory

    assert not issubclass(WorkspaceHistory, ScopedModel)
    assert not isinstance(WorkspaceHistory.objects, ScopedManager)


def test_workspace_history_action_restricted_to_allowed_values():
    from django.core.exceptions import ValidationError

    from workspaces.models import Workspace, WorkspaceHistory

    target = User.objects.create_user(email="target@example.com", password="s3cret-pass")
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    history = WorkspaceHistory(
        action="teleported",
        target_user=target,
        from_workspace=workspace,
        to_workspace=workspace,
    )
    with pytest.raises(ValidationError):
        history.full_clean()


def test_workspace_history_table_absent_from_scoped_tables():
    import importlib

    rls_module = importlib.import_module("workspaces.migrations.0003_rls")
    assert "workspaces_workspacehistory" not in rls_module.SCOPED_TABLES


# --- D2: move_member_to_workspace atomic core -------------------------------


@pytest.fixture
def source_workspace():
    from workspaces.models import Workspace

    return Workspace.objects.create(type=Workspace.Type.GROUP)


@pytest.fixture
def target_workspace():
    from workspaces.models import Workspace

    return Workspace.objects.create(type=Workspace.Type.GROUP)


@pytest.fixture
def mover_user():
    return User.objects.create_user(email="mover@example.com", password="s3cret-pass")


@pytest.fixture
def actor_user():
    return User.objects.create_user(email="actor@example.com", password="s3cret-pass")


@pytest.fixture
def actor_source_membership(actor_user, source_workspace):
    from workspaces.models import Membership

    return Membership.objects.create(
        user=actor_user, workspace=source_workspace, role=Membership.Role.OWNER
    )


@pytest.fixture
def actor_target_membership(actor_user, target_workspace):
    from workspaces.models import Membership

    return Membership.objects.create(
        user=actor_user, workspace=target_workspace, role=Membership.Role.OWNER
    )


@pytest.fixture
def member(mover_user, source_workspace):
    from workspaces.models import Membership

    return Membership.objects.create(
        user=mover_user, workspace=source_workspace, role=Membership.Role.MEMBER
    )


def test_move_member_success_revokes_source_creates_target_and_writes_history(
    actor_source_membership, actor_target_membership, member, source_workspace,
    target_workspace, mover_user, actor_user,
):
    from workspaces.models import Membership, WorkspaceHistory
    from workspaces.services import move_member_to_workspace

    new_membership = move_member_to_workspace(
        actor_source_membership=actor_source_membership,
        actor_target_membership=actor_target_membership,
        member=member,
    )

    assert not Membership.objects.filter(pk=member.pk).exists()
    assert new_membership.workspace_id == target_workspace.pk
    assert new_membership.user_id == mover_user.pk
    assert new_membership.role == "member"

    history = WorkspaceHistory.objects.get(action="moved", target_user=mover_user)
    assert history.actor_id == actor_user.pk
    assert history.from_workspace_id == source_workspace.pk
    assert history.to_workspace_id == target_workspace.pk


def test_move_member_role_always_forced_to_member(
    actor_source_membership, actor_target_membership, source_workspace,
    target_workspace,
):
    from workspaces.models import Membership
    from workspaces.services import move_member_to_workspace

    admin_user = User.objects.create_user(
        email="admin-mover@example.com", password="s3cret-pass"
    )
    admin_member = Membership.objects.create(
        user=admin_user, workspace=source_workspace, role=Membership.Role.ADMIN
    )

    new_membership = move_member_to_workspace(
        actor_source_membership=actor_source_membership,
        actor_target_membership=actor_target_membership,
        member=admin_member,
    )

    assert new_membership.role == "member"


def test_move_member_rollback_on_failure_leaves_source_intact(
    actor_source_membership, actor_target_membership, member, source_workspace,
    target_workspace,
):
    from unittest.mock import patch

    from workspaces.models import Membership, WorkspaceHistory
    from workspaces.services import move_member_to_workspace

    member_pk = member.pk
    member_user_id = member.user_id

    with patch(
        "workspaces.services.WorkspaceHistory.objects.create",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError):
            move_member_to_workspace(
                actor_source_membership=actor_source_membership,
                actor_target_membership=actor_target_membership,
                member=member,
            )

    assert Membership.objects.filter(pk=member_pk, workspace=source_workspace).exists()
    assert not Membership.objects.filter(
        user=member_user_id, workspace=target_workspace
    ).exists()
    assert not WorkspaceHistory.objects.filter(action="moved").exists()


# --- D3: authorization + edge-case guards -----------------------------------


def _assert_no_writes(member_pk, source_workspace, target_workspace, member_user_id):
    from workspaces.models import Membership, WorkspaceHistory

    assert Membership.objects.filter(pk=member_pk, workspace=source_workspace).exists()
    assert not Membership.objects.filter(
        user=member_user_id, workspace=target_workspace
    ).exists()
    assert not WorkspaceHistory.objects.filter(action="moved").exists()


def test_move_member_edge_denied_when_source_actor_lacks_manage_members(
    actor_user, actor_target_membership, member, source_workspace, target_workspace,
):
    from django.core.exceptions import PermissionDenied

    from workspaces.models import Membership
    from workspaces.services import move_member_to_workspace

    weak_source_membership = Membership.objects.create(
        user=actor_user, workspace=source_workspace, role=Membership.Role.MEMBER
    )

    with pytest.raises(PermissionDenied):
        move_member_to_workspace(
            actor_source_membership=weak_source_membership,
            actor_target_membership=actor_target_membership,
            member=member,
        )

    _assert_no_writes(member.pk, source_workspace, target_workspace, member.user_id)


def test_move_member_edge_denied_when_target_actor_lacks_manage_members(
    actor_user, actor_source_membership, member, source_workspace, target_workspace,
):
    from django.core.exceptions import PermissionDenied

    from workspaces.models import Membership
    from workspaces.services import move_member_to_workspace

    weak_target_membership = Membership.objects.create(
        user=actor_user, workspace=target_workspace, role=Membership.Role.MEMBER
    )

    with pytest.raises(PermissionDenied):
        move_member_to_workspace(
            actor_source_membership=actor_source_membership,
            actor_target_membership=weak_target_membership,
            member=member,
        )

    _assert_no_writes(member.pk, source_workspace, target_workspace, member.user_id)


def test_move_member_edge_denied_when_actor_users_differ(
    member, source_workspace, target_workspace,
):
    from django.core.exceptions import PermissionDenied

    from workspaces.models import Membership
    from workspaces.services import move_member_to_workspace

    owner_a = User.objects.create_user(email="owner-a@example.com", password="s3cret-pass")
    owner_b = User.objects.create_user(email="owner-b@example.com", password="s3cret-pass")
    source_membership = Membership.objects.create(
        user=owner_a, workspace=source_workspace, role=Membership.Role.OWNER
    )
    target_membership = Membership.objects.create(
        user=owner_b, workspace=target_workspace, role=Membership.Role.OWNER
    )

    with pytest.raises(PermissionDenied):
        move_member_to_workspace(
            actor_source_membership=source_membership,
            actor_target_membership=target_membership,
            member=member,
        )

    _assert_no_writes(member.pk, source_workspace, target_workspace, member.user_id)


def test_move_member_edge_owner_move_rejected(
    actor_source_membership, actor_target_membership, mover_user, source_workspace,
    target_workspace,
):
    from workspaces.models import Membership
    from workspaces.services import move_member_to_workspace

    owner_member = Membership.objects.create(
        user=mover_user, workspace=source_workspace, role=Membership.Role.OWNER
    )

    with pytest.raises(ValueError):
        move_member_to_workspace(
            actor_source_membership=actor_source_membership,
            actor_target_membership=actor_target_membership,
            member=owner_member,
        )

    _assert_no_writes(
        owner_member.pk, source_workspace, target_workspace, owner_member.user_id
    )


def test_move_member_edge_personal_target_rejected(
    actor_source_membership, actor_user, member, source_workspace,
):
    from workspaces.models import Membership, Workspace
    from workspaces.services import move_member_to_workspace

    personal_target = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    actor_personal_membership = Membership.objects.create(
        user=actor_user, workspace=personal_target, role=Membership.Role.OWNER
    )

    with pytest.raises(ValueError):
        move_member_to_workspace(
            actor_source_membership=actor_source_membership,
            actor_target_membership=actor_personal_membership,
            member=member,
        )

    _assert_no_writes(member.pk, source_workspace, personal_target, member.user_id)


def test_move_member_edge_duplicate_target_membership_rejected(
    actor_source_membership, actor_target_membership, member, source_workspace,
    target_workspace, mover_user,
):
    from workspaces.models import Membership
    from workspaces.services import move_member_to_workspace

    Membership.objects.create(
        user=mover_user, workspace=target_workspace, role=Membership.Role.MEMBER
    )

    with pytest.raises(ValueError):
        move_member_to_workspace(
            actor_source_membership=actor_source_membership,
            actor_target_membership=actor_target_membership,
            member=member,
        )

    assert Membership.objects.filter(pk=member.pk, workspace=source_workspace).exists()
    from workspaces.models import WorkspaceHistory

    assert not WorkspaceHistory.objects.filter(action="moved").exists()


def test_move_member_edge_source_workspace_mismatch_rejected(
    actor_user, actor_target_membership, member, source_workspace, target_workspace,
):
    from django.core.exceptions import PermissionDenied

    from workspaces.models import Membership, Workspace
    from workspaces.services import move_member_to_workspace

    unrelated_workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    mismatched_source_membership = Membership.objects.create(
        user=actor_user, workspace=unrelated_workspace, role=Membership.Role.OWNER
    )

    with pytest.raises(PermissionDenied):
        move_member_to_workspace(
            actor_source_membership=mismatched_source_membership,
            actor_target_membership=actor_target_membership,
            member=member,
        )

    _assert_no_writes(member.pk, source_workspace, target_workspace, member.user_id)
