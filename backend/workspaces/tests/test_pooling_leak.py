"""D9 — cross-tenant leak test under simulated connection-pooling reuse.

Design D-5 / tenancy-isolation spec ("Cross-Tenant Isolation Holds Under
Connection Pooling"). Real Postgres, real `portal_app` role, ONE physical
connection reused across two sequential transactions ("requests") — no DB
mocking. Positive control proves `SET LOCAL` is scoped to a single
transaction; negative control proves the harness can actually detect a leak
(plain `SET` does leak); a final check asserts the production code path
(`TenancyMiddleware`) uses the safe `SET LOCAL` semantics, not plain `SET`.
"""

import inspect

import psycopg
import pytest
from django.db import connection

from workspaces.context import active_workspace

pytestmark = pytest.mark.django_db(transaction=True)


def _portal_app_connection():
    db_settings = connection.settings_dict
    return psycopg.connect(
        dbname=db_settings["NAME"],
        host=db_settings["HOST"] or None,
        port=db_settings["PORT"] or None,
        user="portal_app",
        autocommit=False,
    )


@pytest.fixture
def two_workspaces_with_resources():
    from workspaces.models import Workspace, WorkspaceResource

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    WorkspaceResource.objects.create(workspace=workspace_a, name="a-secret")
    WorkspaceResource.objects.create(workspace=workspace_b, name="b-secret")
    return workspace_a, workspace_b


def test_reused_connection_switched_context_denies_foreign_workspace_rows(
    two_workspaces_with_resources,
):
    """Positive control: SET LOCAL scopes to exactly one transaction.

    Reuses ONE physical connection across two sequential transactions
    (simulating a pooled connection handed to a different request). The
    second transaction re-activates a DIFFERENT workspace (B) via
    `SET LOCAL`; workspace A's rows must be denied by both the raw
    RLS-protected query AND the ORM-level scoped QuerySet.
    """
    workspace_a, workspace_b = two_workspaces_with_resources
    conn = _portal_app_connection()
    try:
        # --- "request 1": workspace A ---
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.workspace_id', %s, true)",
                [str(workspace_a.id)],
            )
            cur.execute("SELECT name FROM workspaces_workspaceresource")
            rows = [row[0] for row in cur.fetchall()]
        assert rows == ["a-secret"]
        conn.commit()  # ends the transaction -> SET LOCAL is cleared

        # --- "request 2", same physical connection: workspace B ---
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.workspace_id', %s, true)",
                [str(workspace_b.id)],
            )
            cur.execute(
                "SELECT name FROM workspaces_workspaceresource WHERE workspace_id = %s",
                [str(workspace_a.id)],
            )
            foreign_rows = cur.fetchall()
        assert foreign_rows == []
        conn.commit()
    finally:
        conn.close()

    # ORM-level scoped QuerySet: same denial, driven by the Python contextvar
    # rather than the DB session — an independent gate (design Data Flow).
    from workspaces.models import WorkspaceResource

    token = active_workspace.set(workspace_b.id)
    try:
        orm_rows = list(WorkspaceResource.objects.filter(workspace_id=workspace_a.id))
    finally:
        active_workspace.reset(token)
    assert orm_rows == []


def test_reused_connection_with_no_reactivated_context_denies_all_rows(
    two_workspaces_with_resources,
):
    """A committed `SET LOCAL` must not leak into the next transaction at
    all — not even as "everything visible". The fail-closed default (deny
    all, not fallback to all) applies once the setting is cleared.
    """
    workspace_a, _workspace_b = two_workspaces_with_resources
    conn = _portal_app_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.workspace_id', %s, true)",
                [str(workspace_a.id)],
            )
            cur.execute("SELECT count(*) FROM workspaces_workspaceresource")
            (count,) = cur.fetchone()
        assert count == 1
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT current_setting('app.workspace_id', true)")
            (leftover,) = cur.fetchone()
            cur.execute("SELECT count(*) FROM workspaces_workspaceresource")
            (count_after,) = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    assert leftover in (None, "")
    assert count_after == 0


def test_negative_control_plain_set_demonstrates_the_leak_it_guards_against(
    two_workspaces_with_resources,
):
    """Negative control: plain `SET` (session-scoped, `is_local=False`)
    DOES leak across the next transaction on the same connection. This
    proves the harness can actually detect a leak — the positive-control
    assertions above are not vacuously passing.
    """
    workspace_a, _workspace_b = two_workspaces_with_resources
    conn = _portal_app_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.workspace_id', %s, false)",
                [str(workspace_a.id)],
            )
        conn.commit()  # ends the transaction; plain SET is unaffected

        with conn.cursor() as cur:
            cur.execute("SELECT current_setting('app.workspace_id', true)")
            (leaked_value,) = cur.fetchone()
            cur.execute("SELECT count(*) FROM workspaces_workspaceresource")
            (count,) = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    assert leaked_value == str(workspace_a.id)  # leaked into the next "request"
    assert count == 1  # workspace A's row is visible again — the exact leak


def test_production_code_path_uses_set_local_not_plain_set():
    """`TenancyMiddleware` delegates to `workspace_scope` (design Decision:
    "Shared workspace-scope helper reused by middleware and task"), which
    must issue `set_config(..., True)` (SET LOCAL semantics), never
    `is_local=False` — the negative control above shows exactly what would
    happen otherwise.
    """
    from workspaces import scope

    source = inspect.getsource(scope)
    assert "set_config('app.workspace_id', %s, %s)" in source
    assert "[str(workspace_id), True]" in source
    assert "False]" not in source


def test_app_role_lacks_bypassrls_gate():
    conn = _portal_app_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )
            (bypass,) = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    assert bypass is False
