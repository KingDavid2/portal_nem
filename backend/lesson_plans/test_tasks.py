"""Tests for `generate_lesson_plan_task` (design D4 — "Generation Runs
Asynchronously via a Celery Task"; tenancy-isolation spec — "Celery
Generation Tasks Must Establish Their Own Workspace RLS Context").

Why `CELERY_TASK_ALWAYS_EAGER` is insufficient for the workspace-context
tests (tenancy-isolation spec, Scenario "Test proves the behavior under real
(non-eager) task execution"):

`config/settings.py` sets `CELERY_TASK_ALWAYS_EAGER = True` under pytest so
the ordinary test suite never needs a live worker/broker. But eager mode
runs the task body inline, on the *same thread*, as whatever called
`.delay()`. Python `contextvars.ContextVar` values (here, `active_workspace`)
are inherited by code running later on the same thread — so if the
enqueuing test had already set `active_workspace` (e.g. via a prior
`workspace_scope` block, or because it runs inside `TenancyMiddleware`),
eager execution would silently see that already-set context even if the
task itself never called `workspace_scope`. That would make a task with the
context-setting step *removed* pass the test anyway — exactly the
regression this requirement guards against.

Each new Python thread gets its own default `contextvars.Context` — values
set on one thread are NOT visible on another. `test_task_sets_own_workspace_context_from_a_cold_thread`
below therefore dispatches the task body on a fresh `ThreadPoolExecutor`
thread with no `active_workspace` set, which is a real cold-context
execution path distinct from the enqueuing test thread — not
`CELERY_TASK_ALWAYS_EAGER`. (`@pytest.mark.django_db(transaction=True)` is
required alongside this: a second thread opens its own DB connection, which
only sees rows committed to the database, not rows sitting inside another
connection's uncommitted transaction.)
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from unittest.mock import patch

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db import connections

from celery.exceptions import SoftTimeLimitExceeded

from lesson_plans.core.catalog import pda_by_id
from lesson_plans.core.ports.llm import (
    BaseProvider,
    GenerationResult,
    TransientProviderError,
    Usage,
)
from lesson_plans.core.schema import (
    ArticulatingAxis,
    ContentPda,
    Datos,
    Proyecto,
    Rubric,
    RubricCriterion,
)
from lesson_plans.models import LessonPlan
from lesson_plans.tasks import NO_CONTENT_SELECTION_ERROR, generate_lesson_plan_task
from workspaces.context import active_workspace

LANGUAGES_CONTENT = "languages-text-resources"
SELECTED_PDA = "languages-accentuation"
# Official in the same field, but deliberately left out of every selection
# below — the fidelity guard must treat it as invented.
UNSELECTED_PDA = "languages-coherent-texts"


def _canned_proyecto(pdas: list[str] | None = None) -> Proyecto:
    return Proyecto(
        datos=Datos(
            school_name="Escuela Uno",
            grade="SEGUNDO",
            campo_formativo="Lenguajes",
            date="2026-01-01",
        ),
        title="Héroes y Gestas",
        purpose="Comprender la independencia.",
        articulating_axes=[ArticulatingAxis(name="Vida saludable", justification="x")],
        problem_or_theme="La independencia",
        contents_and_pdas=[
            ContentPda(
                content="Recursos lingüísticos y textuales para la comprensión y "
                "producción de textos.",
                pdas=pdas
                if pdas is not None
                else [pda_by_id("languages", SELECTED_PDA).text],
            )
        ],
        stages=[],
        rubric=Rubric(criteria=[RubricCriterion(criterion="Participación", levels=["a", "b", "c", "d"])]),
    )


class _FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.request = None
        self.pdas = None

    def generate(self, request, pdas):
        self.request, self.pdas = request, pdas
        if self._error is not None:
            raise self._error
        return self._result


class _GuardedFakeProvider(BaseProvider):
    """Runs the real `find_invented_pdas` guard over a canned proyecto, so the
    fidelity signal is exercised end to end instead of being asserted on a
    hand-written `GenerationResult`."""

    name = "guarded-fake"

    def __init__(self, proyecto: Proyecto) -> None:
        super().__init__(
            complete=lambda system, user: (proyecto, Usage(input_tokens=1, output_tokens=2)),
            model="guarded-fake-model",
        )


def _make_group(workspace):
    from schools.models import Group, School, SchoolYear

    school = School.objects.create(
        workspace=workspace, name="Escuela Uno", level=School.Level.SECUNDARIA
    )
    school_year = SchoolYear.objects.create(
        workspace=workspace, school=school, label="2024-2025"
    )
    return Group.objects.create(workspace=workspace, school_year=school_year, grado=1, grupo="A")


def _create_pending_plan(
    workspace,
    group,
    *,
    campo="Lenguajes",
    grade="SEGUNDO",
    theme="La independencia",
    **overrides,
):
    """A plan carrying the same validated catalog ids the create endpoint
    persists, so the task under test sees a production-shaped row."""
    fields = dict(
        field_id="languages",
        subject_id="spanish",
        methodology_id="community-based-project-learning",
        duration_weeks=4,
        start_date=date(2026, 1, 12),
        end_date=date(2026, 2, 9),
        scenario=LessonPlan.Scenario.COMMUNITY,
        context_diagnosis="El grupo redacta con poca cohesión.",
        cross_cutting_theme_ids=["critical-thinking", "inclusion"],
        content_selections=[
            {"content_id": LANGUAGES_CONTENT, "pda_ids": [SELECTED_PDA]}
        ],
    )
    fields.update(overrides)
    token = active_workspace.set(workspace.id)
    try:
        return LessonPlan.objects.create(
            workspace=workspace, group=group, campo=campo, grade=grade, theme=theme, **fields
        )
    finally:
        active_workspace.reset(token)


def _run_task_in_cold_thread(**kwargs):
    """Run the task on a fresh thread (no inherited `active_workspace`
    contextvar) and close the thread's own DB connection afterwards so
    pytest-django's test-database teardown doesn't race a still-open
    connection from a non-main thread."""

    def _call():
        try:
            generate_lesson_plan_task(**kwargs)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_call).result(timeout=10)


def _read_plan_in(workspace, plan_id):
    token = active_workspace.set(workspace.id)
    try:
        return LessonPlan.objects.get(pk=plan_id)
    finally:
        active_workspace.reset(token)


@pytest.mark.django_db(transaction=True)
def test_task_sets_own_workspace_context_from_a_cold_thread():
    """Scenario: Task sets its own workspace context before reading/writing.

    Dispatches the task body on a fresh thread with no inherited
    `active_workspace` contextvar — see module docstring for why this,
    rather than eager execution, is required to prove the task establishes
    context itself.
    """
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    other_workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group)

    assert active_workspace.get() is not workspace.id  # sanity: caller thread not scoped to it either

    fake = _FakeProvider(
        result=GenerationResult(
            proyecto=_canned_proyecto(),
            usage=Usage(input_tokens=10, output_tokens=20),
            invented_pdas=[],
        )
    )

    with patch("lesson_plans.tasks.build_provider", return_value=fake):
        # New thread => fresh contextvars.Context => no inherited
        # active_workspace, proving the task must set it itself.
        _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    updated = _read_plan_in(workspace, plan.id)
    assert updated.status == LessonPlan.Status.READY
    assert updated.proyecto["title"] == "Héroes y Gestas"
    assert updated.provider == "fake"
    assert updated.model_name == "fake-model"
    assert updated.prompt_tokens == 10
    assert updated.completion_tokens == 20
    assert updated.invented_pdas is False
    assert updated.generated_at is not None

    # The task must not have touched any row in the other workspace.
    assert not _list_plans_in(other_workspace)


def _list_plans_in(workspace):
    token = active_workspace.set(workspace.id)
    try:
        return list(LessonPlan.objects.all())
    finally:
        active_workspace.reset(token)


@pytest.mark.django_db(transaction=True)
def test_task_provider_schema_failure_sets_status_failed_with_reason():
    """Scenarios: Celery task fails on schema-parse failure; Generation
    Failures Surface as a Failed Status."""
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group)

    fake = _FakeProvider(error=ValueError("Proyecto schema validation failed: missing 'title'"))

    with patch("lesson_plans.tasks.build_provider", return_value=fake):
        _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    updated = _read_plan_in(workspace, plan.id)
    assert updated.status == LessonPlan.Status.FAILED
    assert updated.failure_reason != ""
    assert updated.proyecto is None


@pytest.mark.django_db(transaction=True)
def test_task_unresolvable_content_id_sets_status_failed():
    """`content_pdas_for` raises `KeyError` for a stored id that no longer
    resolves — terminal, not retried, surfaces as `status=failed` instead of
    silently generating against something the teacher never picked."""
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(
        workspace,
        group,
        content_selections=[{"content_id": "retired-content", "pda_ids": [SELECTED_PDA]}],
    )

    _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    updated = _read_plan_in(workspace, plan.id)
    assert updated.status == LessonPlan.Status.FAILED
    assert "retired-content" in updated.failure_reason


@pytest.mark.django_db(transaction=True)
def test_task_passes_the_selected_contents_and_planning_context_to_the_provider():
    """The prompt is grounded on exactly what the teacher chose, with catalog
    ids resolved to the Spanish wording the model should read."""
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group)

    fake = _FakeProvider(
        result=GenerationResult(
            proyecto=_canned_proyecto(),
            usage=Usage(input_tokens=1, output_tokens=1),
            invented_pdas=[],
        )
    )

    with patch("lesson_plans.tasks.build_provider", return_value=fake):
        _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    assert [selected.content for selected in fake.pdas] == [
        "Recursos lingüísticos y textuales para la comprensión y producción de textos."
    ]
    assert fake.pdas[0].pdas == [pda_by_id("languages", SELECTED_PDA).text]
    assert fake.request.subject == "Español"
    assert fake.request.scenario == "Comunidad"
    assert fake.request.duration_weeks == 4
    assert fake.request.start_date == "2026-01-12"
    assert fake.request.end_date == "2026-02-09"
    assert fake.request.context_diagnosis == "El grupo redacta con poca cohesión."
    assert fake.request.cross_cutting_themes == ("Pensamiento crítico", "Inclusión")


@pytest.mark.django_db(transaction=True)
def test_stored_proyecto_header_carries_the_subject_and_the_period():
    """The rendered header must state the asignatura and the date range the
    teacher asked for — they are the server's, so they are stamped after the
    parse rather than trusted to the model."""
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group)

    fake = _FakeProvider(
        result=GenerationResult(
            proyecto=_canned_proyecto(),
            usage=Usage(input_tokens=1, output_tokens=1),
            invented_pdas=[],
        )
    )

    with patch("lesson_plans.tasks.build_provider", return_value=fake):
        _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    datos = _read_plan_in(workspace, plan.id).proyecto["datos"]
    assert datos["subject"] == "Español"
    assert datos["start_date"] == "2026-01-12"
    assert datos["end_date"] == "2026-02-09"


@pytest.mark.django_db(transaction=True)
def test_task_flags_an_official_pda_of_a_non_selected_content_as_invented():
    """Grounding on the selection makes the fidelity guard strictly stricter:
    `languages-coherent-texts` is official Phase 6 text in the plan's own
    field, so the old whole-field fixture accepted it. It was not selected
    here, so it now counts as invented."""
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group)

    offending_pda = pda_by_id("languages", UNSELECTED_PDA).text
    proyecto = _canned_proyecto(pdas=[offending_pda])

    with patch(
        "lesson_plans.tasks.build_provider", return_value=_GuardedFakeProvider(proyecto)
    ):
        _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    updated = _read_plan_in(workspace, plan.id)
    assert updated.status == LessonPlan.Status.READY
    assert updated.invented_pdas is True
    # Persist the verbatim offending PDA so the audit trail shows exactly what was invented.
    assert updated.invented_pda_texts == [offending_pda]
    # Persist the resolved selection the plan was checked against.
    assert updated.grounding_selections == [
        {
            "content": "Recursos lingüísticos y textuales para la comprensión y producción de textos.",
            "pdas": [pda_by_id("languages", SELECTED_PDA).text],
        }
    ]


@pytest.mark.django_db(transaction=True)
def test_task_persists_empty_invented_texts_and_non_empty_selection_on_clean_plan():
    """A plan whose output PDAs are all inside the selection must still persist
    the grounding selections — an empty list would mean the viewer has nothing
    to show a teacher even when everything is fine."""
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group)

    proyecto = _canned_proyecto()  # uses SELECTED_PDA, which is in the plan's selection

    with patch(
        "lesson_plans.tasks.build_provider", return_value=_GuardedFakeProvider(proyecto)
    ):
        _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    updated = _read_plan_in(workspace, plan.id)
    assert updated.status == LessonPlan.Status.READY
    assert updated.invented_pdas is False
    assert updated.invented_pda_texts == []
    # The critical assertion: even on a clean plan, grounding_selections must be
    # non-empty so the viewer can show what the plan was checked against.
    assert updated.grounding_selections == [
        {
            "content": "Recursos lingüísticos y textuales para la comprensión y producción de textos.",
            "pdas": [pda_by_id("languages", SELECTED_PDA).text],
        }
    ]


@pytest.mark.django_db(transaction=True)
def test_task_without_content_selection_fails_terminally_without_retrying():
    """A legacy row predating the official-content picker has nothing to
    ground on. There is no fixture to fall back to, so it fails once with a
    clear reason and is never retried."""
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group, content_selections=[])

    fake = _FakeProvider(
        result=GenerationResult(
            proyecto=_canned_proyecto(),
            usage=Usage(input_tokens=1, output_tokens=1),
            invented_pdas=[],
        )
    )

    with patch("lesson_plans.tasks.build_provider", return_value=fake):
        with patch.object(generate_lesson_plan_task, "retry") as retry:
            _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    retry.assert_not_called()
    assert fake.request is None  # never reached the provider
    updated = _read_plan_in(workspace, plan.id)
    assert updated.status == LessonPlan.Status.FAILED
    assert updated.failure_reason == NO_CONTENT_SELECTION_ERROR


@pytest.mark.django_db(transaction=True)
def test_task_retries_a_transient_provider_error_without_failing_the_row():
    """A timeout against the self-hosted endpoint is worth retrying — the same
    request may well succeed on a less loaded box. The row must NOT be marked
    failed on the attempt that retries, or the teacher sees a permanent error
    for a plan still in flight."""
    from celery.exceptions import Retry
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group)

    fake = _FakeProvider(error=TransientProviderError("Request timed out."))

    with patch("lesson_plans.tasks.build_provider", return_value=fake):
        with patch.object(generate_lesson_plan_task, "retry", side_effect=Retry()) as retry:
            with pytest.raises(Retry):
                _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    retry.assert_called_once()
    updated = _read_plan_in(workspace, plan.id)
    assert updated.status == LessonPlan.Status.PENDING
    assert updated.failure_reason == ""


@pytest.mark.django_db(transaction=True)
def test_task_exhausting_the_time_limit_fails_the_row_without_retrying():
    """Celery raises `SoftTimeLimitExceeded` inside the task when the whole run
    outlives its budget. Retrying would burn the identical budget again, so this
    is terminal — but it must still land as `failed` with a reason rather than
    escaping and orphaning the row at `pending`."""
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group)

    fake = _FakeProvider(error=SoftTimeLimitExceeded())

    with patch("lesson_plans.tasks.build_provider", return_value=fake):
        with patch.object(generate_lesson_plan_task, "retry") as retry:
            _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    retry.assert_not_called()
    updated = _read_plan_in(workspace, plan.id)
    assert updated.status == LessonPlan.Status.FAILED
    assert updated.failure_reason != ""


@pytest.mark.django_db(transaction=True)
def test_task_never_leaves_the_row_pending_on_an_unmapped_error():
    """The regression that motivated this guard: `InstructorError` matched neither
    the terminal tuple nor `TransientProviderError`, so it escaped both handlers,
    `_fail()` never ran, and the plan sat at `pending` forever while the UI polled
    a row that would never change. Any unmapped exception must fail the row — and
    still propagate, so the failure stays visible in Celery."""
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group)

    fake = _FakeProvider(error=RuntimeError("Request timed out."))

    with patch("lesson_plans.tasks.build_provider", return_value=fake):
        with pytest.raises(RuntimeError):
            _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    updated = _read_plan_in(workspace, plan.id)
    assert updated.status == LessonPlan.Status.FAILED
    assert "timed out" in updated.failure_reason


@pytest.mark.django_db(transaction=True)
def test_task_fails_the_row_once_the_retry_budget_is_exhausted():
    """`self.retry()` raises `MaxRetriesExceededError` on the last attempt. Without
    the catch-all that too would orphan the row, so the retry path must terminate
    in `failed` rather than in silence."""
    from celery.exceptions import MaxRetriesExceededError
    from workspaces.models import Workspace

    workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
    group = _make_group(workspace)
    plan = _create_pending_plan(workspace, group)

    fake = _FakeProvider(error=TransientProviderError("Request timed out."))
    exhausted = MaxRetriesExceededError("retries exhausted")

    with patch("lesson_plans.tasks.build_provider", return_value=fake):
        with patch.object(generate_lesson_plan_task, "retry", side_effect=exhausted):
            with pytest.raises(MaxRetriesExceededError):
                _run_task_in_cold_thread(workspace_id=workspace.id, lesson_plan_id=plan.id)

    updated = _read_plan_in(workspace, plan.id)
    assert updated.status == LessonPlan.Status.FAILED
    assert updated.failure_reason != ""


@pytest.mark.django_db
def test_task_without_established_context_fails_closed_not_cross_tenant():
    """Scenario: Task without established context fails closed, not
    cross-tenant.

    Simulates a regression where the workspace-context-setting step is
    omitted entirely: reading a `LessonPlan` row with no `workspace_scope`
    active MUST return zero rows (via `ScopedManager`'s fail-closed
    `_scoped()`), never fall through to an unscoped or wrong-workspace view,
    even when a row for a *different* workspace exists and is queried by id.
    """
    from workspaces.models import Workspace

    workspace_a = Workspace.objects.create(type=Workspace.Type.GROUP)
    workspace_b = Workspace.objects.create(type=Workspace.Type.GROUP)
    group_b = _make_group(workspace_b)
    plan_b = _create_pending_plan(workspace_b, group_b)

    assert active_workspace.get() is not workspace_b.id

    with pytest.raises(ObjectDoesNotExist):
        LessonPlan.objects.get(pk=plan_b.id)

    assert list(LessonPlan.objects.all()) == []
