"""Monthly lesson-plan generation quota (design "Generaciones de este mes").

Window semantics: a calendar month in `settings.TIME_ZONE`. The counter
therefore resets at midnight, project-local time, on the first day of the
next month — never on a rolling 30-day window and never on the server's own
local clock, which is why every date here comes from `django.utils.timezone`
rather than `datetime.now()`.

The limit is one project-wide setting
(`LESSON_PLAN_MONTHLY_GENERATION_LIMIT`). Per-workspace overrides (paid
plans, trials, manual grants) are deliberately deferred: there is no billing
model to hang them on yet, and a nullable per-workspace column added now
would have to be migrated again once one exists.

Quota is consumed on ACCEPTED requests, including generations the LLM later
fails. There is intentionally no refund-on-failure path — a refund would
turn every provider hiccup into free retries and would need an
exactly-once guarantee the Celery task does not offer.
"""

from __future__ import annotations

from datetime import date

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from lesson_plans.models import GenerationUsage
from workspaces.scope import workspace_scope


class QuotaExceeded(Exception):
    """Raised when a workspace has already used its whole monthly allowance."""

    def __init__(self, *, used: int, limit: int, period: date) -> None:
        super().__init__(
            f"Monthly generation limit reached: {used}/{limit} "
            f"for {format_period(period)}."
        )
        self.used = used
        self.limit = limit
        self.period = period


def format_period(period: date) -> str:
    """Wire representation of a period (`YYYY-MM`).

    The 429 body and `GET /api/lesson-plans/quota/` both label the same
    window, so they format it through this one function — a second inline
    `%Y-%m` would be free to drift.
    """
    return f"{period:%Y-%m}"


def monthly_limit() -> int:
    """Read the limit at call time so tests/deploys can override the setting."""
    return int(settings.LESSON_PLAN_MONTHLY_GENERATION_LIMIT)


def current_period() -> date:
    """First day of the current month in `settings.TIME_ZONE`."""
    return timezone.localdate().replace(day=1)


def consume_generation(workspace) -> GenerationUsage:
    """Charge one generation to `workspace` for the current period.

    Concurrency-safe by construction: the period row is created with
    `get_or_create` (whose unique constraint makes a lost create a retried
    get), then locked with `SELECT ... FOR UPDATE` before the limit is
    checked. A second transaction reaching this point blocks on that lock
    until the first one commits, so it can never read a stale `count` — two
    simultaneous requests at `limit - 1` serialize and the second one raises.
    The increment itself is an in-database `F("count") + 1`, never a
    read-modify-write in Python.

    The lock is held until the caller's outermost transaction ends, so
    rolling that transaction back also refunds the count.
    """
    limit = monthly_limit()
    period = current_period()
    with workspace_scope(workspace.pk):
        usage, _ = GenerationUsage.objects.get_or_create(
            workspace=workspace, period=period
        )
        locked = GenerationUsage.objects.select_for_update().get(pk=usage.pk)
        if locked.count >= limit:
            raise QuotaExceeded(used=locked.count, limit=limit, period=period)
        GenerationUsage.objects.filter(pk=locked.pk).update(count=F("count") + 1)
        locked.refresh_from_db(fields=["count"])
        return locked


def current_usage(workspace) -> tuple[int, int]:
    """`(used, limit)` for `workspace` in the current period, without charging.

    A workspace that has not generated this month has no ledger row yet; that
    is reported as `0`, not as a missing period.
    """
    limit = monthly_limit()
    with workspace_scope(workspace.pk):
        usage = GenerationUsage.objects.filter(
            workspace=workspace, period=current_period()
        ).first()
    return (usage.count if usage is not None else 0, limit)
