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
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from django.utils import timezone
from pydantic import ValidationError

from workspaces.scope import workspace_scope

from .core.catalog import subject_by_id, theme_by_id
from .core.catalog_pdas import content_pdas_for
from .core.factory import build_provider
from .core.generation import GenerationRequest, scenario_label, stamp_request_context
from .core.ports.llm import TransientProviderError
from .models import LessonPlan

__all__ = ["TransientProviderError", "generate_lesson_plan_task"]

logger = logging.getLogger(__name__)

# A plan created before the planning form captured official contents carries
# no selection at all. There is no safe fallback — generating against a whole
# field's fixture would silently ignore what the teacher chose — so it fails.
NO_CONTENT_SELECTION_ERROR = "Lesson plan has no official content selection."

# Truncate stored failure reasons so a verbose provider/traceback message
# never blows out the TextField or leaks unbounded detail to the client.
FAILURE_REASON_MAX_LENGTH = 2000

# Errors that indicate the request or the generated output itself is unusable
# (bad schema, unresolvable catalog id, missing content selection) are terminal
# — retrying would produce the same failure.
_TERMINAL_ERRORS = (ValidationError, KeyError, ValueError)

# Shown to the teacher when the whole run outlived its budget. `SoftTimeLimitExceeded`
# carries no message of its own, and "" would render as a failed plan with no
# explanation at all.
TIME_LIMIT_ERROR = "Generation exceeded its time limit before the provider responded."

# Any exception that reaches the catch-all is, by definition, one nobody classified.
UNEXPECTED_ERROR = "Unexpected generation failure: "

# The provider stayed unreachable across every attempt.
RETRIES_EXHAUSTED_ERROR = "Generation failed after all retries: "


def _selected_pdas(plan: LessonPlan):
    """The official contents/PDAs the teacher actually chose for this plan."""
    if not plan.content_selections:
        raise ValueError(NO_CONTENT_SELECTION_ERROR)
    return content_pdas_for(plan.field_id, plan.content_selections)


def _iso(value) -> str:
    return value.isoformat() if value else ""


def _build_request(plan: LessonPlan) -> GenerationRequest:
    """Turn the persisted planning context into prompt-ready Spanish text.

    Catalog ids are resolved to their display names here so the prompt never
    shows the model an internal id; an id that no longer resolves raises
    `KeyError`, which is terminal.
    """
    subject = subject_by_id(plan.field_id, plan.subject_id).name if plan.subject_id else ""
    return GenerationRequest(
        campo=plan.campo,
        grade=plan.grade,
        theme=plan.theme,
        subject=subject,
        duration_weeks=plan.duration_weeks or 0,
        start_date=_iso(plan.start_date),
        end_date=_iso(plan.end_date),
        scenario=scenario_label(plan.scenario),
        context_diagnosis=plan.context_diagnosis,
        cross_cutting_themes=tuple(
            theme_by_id(theme_id).name for theme_id in plan.cross_cutting_theme_ids
        ),
    )


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
    # A 20k-token nested `Proyecto` under vLLM guided-JSON decoding takes minutes on
    # the self-hosted box, not the seconds a cloud provider needs. The soft limit sits
    # above `REQUEST_TIMEOUT_SECONDS` so the HTTP client always times out first and the
    # adapter gets to translate the failure; the hard limit is the backstop for a
    # worker wedged somewhere the soft limit cannot interrupt.
    soft_time_limit=600,
    time_limit=660,
)
def generate_lesson_plan_task(self, *, workspace_id, lesson_plan_id):
    """Generate the ABPC proyecto for `lesson_plan_id` in `workspace_id`.

    Design Interfaces/Contracts: `provider=build_provider()`;
    `result=provider.generate(...)` runs *outside* any transaction (the
    minutes-long network call must never hold a DB txn open); on success the row
    is updated inside `workspace_scope(workspace_id)` with `status=ready`;
    on schema-parse/validation/unresolvable-selection failure, `status=failed` with a
    truncated `failure_reason` (no retry — the output would not change).
    Transient provider/network errors retry up to twice with exponential
    backoff.

    Every exit path must leave the row in a terminal state. A `pending` plan the
    worker has already given up on is the worst outcome available: the client polls
    it forever and the teacher is never told anything went wrong. The catch-all
    below exists solely to make that unreachable — it is a safety net, not a
    substitute for classifying failures in the adapters.
    """
    # Establish workspace context for the read of the pending row itself —
    # this is the task's own context-setting step (tenancy-isolation spec),
    # not something inherited from an enqueuing request.
    with workspace_scope(workspace_id):
        plan = LessonPlan.objects.get(pk=lesson_plan_id)

    try:
        provider = build_provider()
        pdas = _selected_pdas(plan)
        request = _build_request(plan)
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
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            # Raised from inside this handler, so no sibling `except` below can see
            # it — the row would be orphaned unless it is failed right here.
            logger.warning(
                "generate_lesson_plan_task retries exhausted workspace=%s plan=%s: %s",
                workspace_id,
                lesson_plan_id,
                exc,
            )
            _fail(workspace_id, lesson_plan_id, f"{RETRIES_EXHAUSTED_ERROR}{exc}")
            raise
    except SoftTimeLimitExceeded:
        # Not retried: a run that exhausted the budget once will exhaust it again.
        logger.warning(
            "generate_lesson_plan_task timed out workspace=%s plan=%s",
            workspace_id,
            lesson_plan_id,
        )
        _fail(workspace_id, lesson_plan_id, TIME_LIMIT_ERROR)
        return
    except Exception as exc:
        # Unclassified — the adapter should have translated this. Fail the row so it
        # is never orphaned, then re-raise so the gap stays loud in the worker log.
        logger.exception(
            "generate_lesson_plan_task unexpected failure workspace=%s plan=%s",
            workspace_id,
            lesson_plan_id,
        )
        _fail(workspace_id, lesson_plan_id, f"{UNEXPECTED_ERROR}{exc}")
        raise

    # The asignatura and the date range in the header are the request's, not
    # the model's — stamp them over whatever came back.
    proyecto = stamp_request_context(result.proyecto, request)

    with workspace_scope(workspace_id):
        plan = LessonPlan.objects.get(pk=lesson_plan_id)
        plan.proyecto = proyecto.model_dump(mode="json")
        plan.title = proyecto.title
        plan.provider = getattr(provider, "name", "")
        plan.model_name = getattr(provider, "model", "")
        plan.prompt_tokens = result.usage.input_tokens
        plan.completion_tokens = result.usage.output_tokens
        plan.invented_pdas = bool(result.invented_pdas)
        plan.status = LessonPlan.Status.READY
        plan.generated_at = timezone.now()
        plan.save()
