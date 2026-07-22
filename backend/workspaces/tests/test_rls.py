"""RED tests for RLS policies + restricted app role (tenancy-isolation spec).

M2a ships no NEM domain models yet, so these tests exercise RLS against
`WorkspaceResource` — a minimal concrete `ScopedModel` added purely to give
the RLS backstop (and the D9 leak test) a real table to protect. See its
docstring in `workspaces/models.py`.
"""

import psycopg
import pytest
from django.db import connection

pytestmark = pytest.mark.django_db(transaction=True)


def _portal_app_connection():
    db_settings = connection.settings_dict
    return psycopg.connect(
        dbname=db_settings["NAME"],
        host=db_settings["HOST"] or None,
        port=db_settings["PORT"] or None,
        user="portal_app",
    )


def test_app_role_lacks_bypassrls():
    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        (bypass,) = cur.fetchone()

    assert bypass is False


def test_rls_denies_rows_with_no_workspace_context_set():
    from workspaces.models import Workspace, WorkspaceResource

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    # Written via the owner/migrate connection (table owner bypasses RLS by
    # default) — proves the *read* denial below is RLS, not "table empty".
    WorkspaceResource.objects.create(workspace=workspace, name="secret")

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM workspaces_workspaceresource")
        (count,) = cur.fetchone()

    assert count == 0


def test_rls_permits_rows_when_workspace_context_matches():
    from workspaces.models import Workspace, WorkspaceResource

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    WorkspaceResource.objects.create(workspace=workspace, name="visible")

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.workspace_id', %s, false)", [str(workspace.id)]
        )
        cur.execute("SELECT count(*) FROM workspaces_workspaceresource")
        (count,) = cur.fetchone()

    assert count == 1


def test_rls_blocks_foreign_workspace_row_specifically():
    from workspaces.models import Workspace, WorkspaceResource

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    WorkspaceResource.objects.create(workspace=workspace_a, name="mine")
    WorkspaceResource.objects.create(workspace=workspace_b, name="not-mine")

    with _portal_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.workspace_id', %s, false)", [str(workspace_a.id)]
        )
        cur.execute("SELECT name FROM workspaces_workspaceresource ORDER BY name")
        rows = [row[0] for row in cur.fetchall()]

    assert rows == ["mine"]
