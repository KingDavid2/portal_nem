"""Workspace-scoped manager (design D-3, tenancy-isolation spec).

Fail-closed by construction: with no active-workspace context, reads return
zero rows rather than falling back to "everything" or raising. This is the
primary, review-visible isolation mechanism; Postgres RLS (D8) is the
backstop for the same guarantee.
"""

from django.db import models

from workspaces.context import WORKSPACE_UNSET, active_workspace


class ScopedQuerySet(models.QuerySet):
    def _scoped(self):
        workspace_id = active_workspace.get()
        if workspace_id is WORKSPACE_UNSET:
            return self.none()
        return self.filter(workspace_id=workspace_id)


class ScopedManager(models.Manager.from_queryset(ScopedQuerySet)):
    def get_queryset(self):
        return super().get_queryset()._scoped()
