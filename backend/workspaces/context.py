"""Active-workspace request-scoped context (design D-3, tenancy-isolation spec).

`active_workspace` is set by `TenancyMiddleware` (D7) for the lifetime of a
request and read by `ScopedManager` (D5) on every query. The sentinel is an
object identity — never `None`/`0` — so it can never collide with a real
workspace id, and it generalizes to the future M2b Celery task-context path.
"""

from contextvars import ContextVar

WORKSPACE_UNSET = object()

active_workspace: ContextVar = ContextVar("active_workspace", default=WORKSPACE_UNSET)
