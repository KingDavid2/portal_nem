"""Celery task performing the LLM generation call for a `LessonPlan`
(design D4 — "Generation Runs Asynchronously via a Celery Task").

The worker process never runs `TenancyMiddleware`, so this task carries no
inherited request-scoped workspace context. Per the tenancy-isolation spec
("Celery Generation Tasks Must Establish Their Own Workspace RLS Context"),
the task MUST resolve its target workspace from the arguments it was
enqueued with and MUST itself enter `workspace_scope(workspace_id)` before
any `LessonPlan` read or write — never relying on anything set by the caller.

Only the create/list/retrieve/destroy endpoints that enqueue this task belong
to D5; this module is deliberately callable/testable in isolation (the task
is not yet wired to any view).
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone
from pydantic import ValidationError

from workspaces.scope import workspace_scope

from .core.factory import build_provider
from .core.generation import GenerationRequest
from .core.pdas import pdas_for
from .models import LessonPlan

logger = logging.getLogger(__name__)

# Truncate stored failure reasons so a verbose provider/traceback message
# never blows out the TextField or leaks unbounded detail to the client.
FAILURE_REASON_MAX_LENGTH = 2000

# Errors that indicate the generated output itself is unusable (bad schema,
# unknown campo) are terminal — retrying would produce the same failure.
_TERMINAL_ERRORS = (ValidationError, KeyError, ValueError)


class TransientProviderError(Exception):
    """Raised by a provider adapter for a retryable network/provider failure
    (timeout, 5xx, rate limit) — never for a schema/parse failure."""


def _fail(workspace_id, lesson_plan_id, reason: str) -> None:
    with workspace_scope(workspace_id):
        plan = LessonPlan.objects.get(pk=lesson_plan_id)
        plan.status = LessonPlan.Status.FAILED
        plan.failure_reason = reason[:FAILURE_REASON_MAX_LENGTH]
        plan.save()


@shared_task(
    bind=True,
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=60,
    soft_time_limit=90,
)
def generate_lesson_plan_task(self, *, workspace_id, lesson_plan_id):
    """Generate the ABPC proyecto for `lesson_plan_id` in `workspace_id`.

    Design Interfaces/Contracts: `provider=build_provider()`;
    `result=provider.generate(...)` runs *outside* any transaction (the
    ~10-30s network call must never hold a DB txn open); on success the row
    is updated inside `workspace_scope(workspace_id)` with `status=ready`;
    on schema-parse/validation/unknown-campo failure, `status=failed` with a
    truncated `failure_reason` (no retry — the output would not change).
    Transient provider/network errors retry up to twice with exponential
    backoff.
    """
    # Establish workspace context for the read of the pending row itself —
    # this is the task's own context-setting step (tenancy-isolation spec),
    # not something inherited from an enqueuing request.
    with workspace_scope(workspace_id):
        plan = LessonPlan.objects.get(pk=lesson_plan_id)
        campo, grade, theme = plan.campo, plan.grade, plan.theme

    try:
        provider = build_provider()
        pdas = pdas_for(campo)
        request = GenerationRequest(campo=campo, grade=grade, theme=theme)
        result = provider.generate(request, pdas)
    except _TERMINAL_ERRORS as exc:
        logger.warning(
            "generate_lesson_plan_task terminal failure workspace=%s plan=%s: %s",
            workspace_id,
            lesson_plan_id,
            exc,
        )
        _fail(workspace_id, lesson_plan_id, str(exc))
        return
    except TransientProviderError as exc:
        raise self.retry(exc=exc)

    with workspace_scope(workspace_id):
        plan = LessonPlan.objects.get(pk=lesson_plan_id)
        plan.proyecto = result.proyecto.model_dump(mode="json")
        plan.title = result.proyecto.title
        plan.provider = getattr(provider, "name", "")
        plan.model_name = getattr(provider, "model", "")
        plan.prompt_tokens = result.usage.input_tokens
        plan.completion_tokens = result.usage.output_tokens
        plan.invented_pdas = bool(result.invented_pdas)
        plan.status = LessonPlan.Status.READY
        plan.generated_at = timezone.now()
        plan.save()
