"""RED tests for `workspace_scope` (design Decision: "Shared workspace-scope
helper reused by middleware and task"). Focused, direct-call coverage
independent of `TenancyMiddleware` / the request cycle — the future Celery
task (D4) calls this exact primitive with no HTTP request involved.
"""

import pytest
from django.db import connection

from workspaces.context import WORKSPACE_UNSET, active_workspace
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db


def test_workspace_scope_sets_active_workspace_and_db_setting_inside_the_block():
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)

    with workspace_scope(workspace.id):
        assert active_workspace.get() == workspace.id
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.workspace_id', true)")
            (db_setting,) = cursor.fetchone()
        assert db_setting == str(workspace.id)


def test_workspace_scope_resets_active_workspace_after_the_block():
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)

    with workspace_scope(workspace.id):
        pass

    assert active_workspace.get() is WORKSPACE_UNSET


def test_workspace_scope_resets_active_workspace_even_on_exception():
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)

    with pytest.raises(ValueError):
        with workspace_scope(workspace.id):
            raise ValueError("boom")

    assert active_workspace.get() is WORKSPACE_UNSET


@pytest.mark.django_db(transaction=True)
def test_workspace_scope_clears_the_db_setting_once_its_transaction_commits():
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)

    with workspace_scope(workspace.id):
        pass

    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.workspace_id', true)")
        (leftover,) = cursor.fetchone()
    assert leftover in (None, "")


def test_workspace_scope_lets_scoped_rows_be_written_and_read_back():
    from workspaces.models import Workspace, WorkspaceResource

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)

    with workspace_scope(workspace.id):
        WorkspaceResource.objects.create(workspace=workspace, name="mine")
        rows = list(WorkspaceResource.objects.filter(workspace=workspace))

    assert [r.name for r in rows] == ["mine"]
