# Verification Report: m4-ai-planeaciones

**Mode**: full artifacts (proposal, specs, design, tasks all present)
**Date**: 2026-07-23
**Branch**: m4-ai-planeaciones (all 9 chained commits, D1a-D8)

## Gate Results

| # | Gate | Command | Result |
|---|------|---------|--------|
| 1 | Backend test suite | `cd backend && uv run pytest -q` | PASS — 189 passed in 18.26s |
| 2 | Migrations drift | `cd backend && uv run manage.py makemigrations --check --dry-run` | PASS — "No changes detected" |
| 3 | Schema generation/validation | `cd backend && uv run manage.py spectacular --file /tmp/m4_schema.yaml --validate` | PASS — exit 0 |
| 3b | Committed schema.yaml lesson-plans coverage | `rg lesson-plans backend/schema.yaml` | PASS — `/api/lesson-plans/` (GET list, POST create), `/api/lesson-plans/{id}/` (GET retrieve, DELETE destroy), `/api/lesson-plans/{id}/export/` (GET, format enum docx/md, BINARY + text/markdown responses) all present |
| 4a | Frontend build | `cd frontend && npm run build` | PASS — compiled successfully, `/planeaciones` static, `/planeaciones/[id]` dynamic |
| 4b | Frontend lint | `cd frontend && npm run lint` | PASS — 0 errors, 1 pre-existing unrelated warning (`data-table.tsx` React Compiler incompatible-library note, not introduced by this change) |
| 4c | Frontend tests | `cd frontend && npm test` | PASS — 35 passed (7 test files) |

## CRITICAL Spec Conformance — Workspace-Context Leak Test (tenancy-isolation delta)

Located: `backend/lesson_plans/test_tasks.py`

- `test_task_sets_own_workspace_context_from_a_cold_thread` (lines 143-184): dispatches `generate_lesson_plan_task` via a fresh `ThreadPoolExecutor` thread (`_run_task_in_cold_thread`), which gets its own default `contextvars.Context` — proving no `active_workspace` contextvar is inherited from the enqueuing test thread. Uses `@pytest.mark.django_db(transaction=True)` so the worker thread's own DB connection only sees committed rows. Asserts the task resolves `workspace_id` itself, sets `status=ready` correctly, and does not touch the other workspace's rows (`assert not _list_plans_in(other_workspace)`).
- `test_task_without_established_context_fails_closed_not_cross_tenant` (lines 234-256): proves the fail-closed guarantee the task depends on — reading a `LessonPlan` with no `workspace_scope` active returns zero rows / `ObjectDoesNotExist`, even when a row for a different workspace exists.
- Module docstring (lines 1-30) explicitly documents why `CELERY_TASK_ALWAYS_EAGER` is insufficient: eager mode runs the task body inline on the same thread as the enqueuing caller, and Python `contextvars.ContextVar` values are inherited by later code on the same thread — so an eager test would silently pass even if the task never called `workspace_scope` itself. The cold-thread test is a real, distinct-execution-context proof, satisfying the tenancy-isolation spec's explicit requirement ("Test proves the behavior under real (non-eager) task execution").

**Verdict: PASS.** This is the highest-value requirement in the change and is proven correctly — not merely asserted via eager/inherited context.

## Spec Conformance — Remaining Requirements

### ai-planeaciones spec

| Requirement | Evidence |
|---|---|
| LessonPlan is workspace-scoped, own FK, Group PROTECT, proyecto JSON, provenance, status enum | `backend/lesson_plans/models.py` — `LessonPlan(ScopedModel)`, `group = FK("schools.Group", PROTECT)`, `proyecto = JSONField`, `status` `TextChoices` (pending/ready/failed), `provider`/`model_name`/`prompt_tokens`/`completion_tokens`/`generated_at` provenance fields |
| Generation gated by edit_content, workspace from Membership, group-workspace invariant | `backend/lesson_plans/services.py::generate_lesson_plan` — `_require_edit_content`, `workspace=membership.workspace` (never client input), explicit `group.workspace_id != membership.workspace_id` → `ValueError` |
| PDA-fidelity guard | `backend/lesson_plans/tasks.py` — `result.invented_pdas` persisted as `invented_pdas` boolean; covered by D5.5 fidelity-guard test |
| Async Celery generation: pending→enqueue→202, task sets ready/failed | `services.py` creates row then `.delay()`; `viewsets.py::create` returns `202 ACCEPTED`; `tasks.py::generate_lesson_plan_task` sets `status=ready` on success / `status=failed` with `failure_reason` on terminal error via `_fail()` |
| CRUD endpoints workspace-scoped | `backend/lesson_plans/viewsets.py::LessonPlanViewSet` — `ScopedManager`-backed `get_queryset`, `?group=` filter, `capability_map` (list/retrieve→view_workspace, create/destroy→edit_content) |
| Export docx/md, reject non-ready | `viewsets.py::export` action — `plan.status != READY` → `ValidationError`; docx via `render_docx`, md via `render_md`; `@extend_schema` documents BINARY + markdown responses |

### llm-provider spec

| Requirement | Evidence |
|---|---|
| Config-driven provider selection, default vLLM | `backend/lesson_plans/core/factory.py::build_provider()` — reads `settings.LLM_PROVIDER`, defaults to `OpenAICompatProvider`, switches to `ClaudeProvider` only when `LLM_PROVIDER == "claude"`; connection settings (`LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`, `ANTHROPIC_*`) read from Django settings |
| Generation failures surface as failed status | `tasks.py::_TERMINAL_ERRORS = (ValidationError, KeyError, ValueError)` caught and routed to `_fail()`; transient errors retried via `self.retry()`, never propagate uncaught |

## Frontend Conformance (D7/D8)

- List + generate + poll: `frontend/src/app/(app)/planeaciones/page.tsx`, `generate-form.tsx`, `frontend/src/lib/api/lesson-plans.ts` (`useLessonPlansQuery`, `useCreateLessonPlanMutation`, poll via `refetchInterval`/`lessonPlanPollInterval`).
- Viewer + export download: `frontend/src/app/(app)/planeaciones/[id]/page.tsx`, `proyecto-viewer.tsx`, `frontend/src/lib/api/lesson-plan-export.ts` (`downloadLessonPlanExport`, credentialed fetch + Blob anchor, outside typed client per design decision).
- All covered by 35/35 passing frontend tests (7 test files).

## Task Completeness

All D1a-D8 tasks in `tasks.md` are checked `[x]`. `rg '^\s*-\s*\[ \]' tasks.md` returns no matches — zero unchecked tasks.

## Non-Blocking Notes (documented, not scored as CRITICAL/WARNING)

- Live end-to-end exit-gate (generate→poll→view→export against running Redis+Celery worker+real/mock model) was not manually executed this session — documented in apply-progress as a pre-merge manual step.
- `AVAILABLE_CAMPOS` is a hardcoded literal list in the frontend mirroring the backend fixture (`lesson_plans/core/pdas.py::available_campos()`) — resolves design.md's own Open Question; RAG is off in this first cut, no dedicated endpoint exists yet.
- RAG/pgvector explicitly deferred (out of scope).
- instructor/vLLM JSON-mode reliability for the full nested ABPC schema is unproven against a real model in this session; the `status=failed` terminal-error path is the designed guard against this.

## Issues

- CRITICAL: 0
- WARNING: 0
- SUGGESTION: 0

## Final Verdict: PASS

All 7 verification gates pass with real runtime evidence (189 backend tests, 35 frontend tests, clean migrations, valid schema, clean build/lint). The CRITICAL tenancy-isolation requirement (Celery task must establish its own workspace RLS context under real non-eager execution) is proven by a dedicated cold-thread test, not an eager/inherited-context shortcut. All tasks are complete and match the code state. Ready for archive.
