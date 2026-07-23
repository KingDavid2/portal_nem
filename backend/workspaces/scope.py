"""Shared workspace-scope context manager (design Decision: "Shared
workspace-scope helper reused by middleware and task").

Extracted verbatim from `TenancyMiddleware`: opens its own
`transaction.atomic()` block so `SET LOCAL app.workspace_id` (issued via
`set_config(..., true)`) is scoped to exactly that transaction and is cleared
automatically on commit/rollback — the same guarantee `TenancyMiddleware`
relies on for the request/response cycle, and the one the Celery task path
(D4) must reuse so a worker can never read/write cross-tenant rows.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Iterator

from django.db import connection, transaction

from .context import active_workspace


@contextmanager
def workspace_scope(workspace_id: uuid.UUID) -> Iterator[None]:
    """Activate `workspace_id` for the ScopedManager/RLS for the duration of
    the block, inside its own transaction. Always clears the contextvar on
    exit, even if the block raises."""
    token = active_workspace.set(workspace_id)
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.workspace_id', %s, %s)",
                    [str(workspace_id), True],
                )
            yield
    finally:
        active_workspace.reset(token)
