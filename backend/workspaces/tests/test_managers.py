"""RED tests for the workspace-scoped manager (tenancy-isolation spec)."""

import pytest
from django.db import connection

from workspaces.models import ScopedModel

pytestmark = pytest.mark.django_db


class ScopedProbe(ScopedModel):
    """Minimal concrete ScopedModel subclass, test-only.

    Its table is created/dropped per test via `schema_editor` (Postgres DDL
    is transactional, so pytest-django's per-test rollback also undoes the
    `CREATE TABLE`) rather than shipping a real migration for a throwaway
    probe model.
    """

    class Meta:
        app_label = "workspaces"


@pytest.fixture
def scoped_table():
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(ScopedProbe)
    yield ScopedProbe


def test_no_context_denies_all_rows(scoped_table):
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    # .create() inserts directly (doesn't depend on the filtered read path),
    # so it succeeds even while the manager's *read* path is fail-closed.
    ScopedProbe.objects.create(workspace=workspace)

    assert list(ScopedProbe.objects.all()) == []


def test_query_scoped_to_active_workspace(scoped_table):
    from workspaces.context import active_workspace
    from workspaces.models import Workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)

    row_a = ScopedProbe.objects.create(workspace=workspace_a)
    ScopedProbe.objects.create(workspace=workspace_b)

    token = active_workspace.set(workspace_a.id)
    try:
        rows = list(ScopedProbe.objects.all())
    finally:
        active_workspace.reset(token)

    assert rows == [row_a]
