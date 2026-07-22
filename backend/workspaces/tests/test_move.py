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
