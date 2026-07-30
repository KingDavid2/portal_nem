"""RED tests for the workspace-scoped manager (tenancy-isolation spec)."""

import pytest
from django.apps import apps
from django.db import connection

from workspaces.models import ScopedModel, Workspace

pytestmark = pytest.mark.django_db


@pytest.fixture
def scoped_table():
    """Ephemeral ScopedModel + table, unregistered after the test.

    Defined inside the fixture (not at module import) so ``Workspace.delete()``
    collectors in later tests never cascade into a rolled-back probe table.
    Postgres DDL is transactional, so pytest-django's per-test rollback also
    undoes the ``CREATE TABLE``.
    """

    class ScopedProbe(ScopedModel):
        class Meta:
            app_label = "workspaces"

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(ScopedProbe)
    try:
        yield ScopedProbe
    finally:
        apps.all_models["workspaces"].pop(ScopedProbe._meta.model_name, None)
        apps.clear_cache()
        Workspace._meta._expire_cache()


def test_no_context_denies_all_rows(scoped_table):
    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    # .create() inserts directly (doesn't depend on the filtered read path),
    # so it succeeds even while the manager's *read* path is fail-closed.
    scoped_table.objects.create(workspace=workspace)

    assert list(scoped_table.objects.all()) == []


def test_query_scoped_to_active_workspace(scoped_table):
    from workspaces.context import active_workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)

    row_a = scoped_table.objects.create(workspace=workspace_a)
    scoped_table.objects.create(workspace=workspace_b)

    token = active_workspace.set(workspace_a.id)
    try:
        rows = list(scoped_table.objects.all())
    finally:
        active_workspace.reset(token)

    assert rows == [row_a]
