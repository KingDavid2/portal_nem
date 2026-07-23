# Design: M4 — AI planeaciones (Celery-backed, tenant-scoped)

## Technical Approach

Port M1's hexagonal core verbatim into `backend/lesson_plans/core/`, keeping the
`LLMProvider` port boundary intact; only the config source changes (M1 `Config.from_env`
→ Django settings via a provider factory). Wrap it in the exact M3 pattern: a `LessonPlan`
`ScopedModel` (own `workspace` FK + one per-app RLS migration via `workspaces.rls`),
keyword-only `edit_content`-gated services, and a `ModelViewSet` + `WorkspacePermission` +
`capability_map`. The ~10–30s LLM call runs in a **Celery task** (locked decision — matches
design-brief §3); DRF creates a `pending` row, enqueues, returns 202, and the frontend polls
`retrieve`. The task's non-negotiable job is to re-establish the active-workspace context
(`SET LOCAL app.workspace_id` + contextvar) that `TenancyMiddleware` provides for requests —
without it, `ScopedManager` + RLS fail closed to empty. RAG is OFF (fixture `pdas.py`).

## Architecture Decisions

### Decision: Shared workspace-scope helper reused by middleware and task
**Choice**: Extract the `set_config('app.workspace_id', …, true)` + `active_workspace.set()`
logic from `TenancyMiddleware` into `workspaces/scope.py::workspace_scope(workspace_id)`
(a context manager opening its own `transaction.atomic()`). Middleware and the Celery task
both call it. `context.py` already anticipates this ("generalizes to the future Celery
task-context path").
**Alternatives**: Duplicate the SQL in the task (drifts, easy to forget `NULLIF`/`true` local flag).
**Rationale**: Single source of truth for the isolation-critical primitive; the modified
`tenancy-isolation` capability demands the task set context the *same* way as requests.

### Decision: Task owns its transaction, not the request's
**Choice**: The task runs in a Celery worker process with no HTTP request, so `ATOMIC_REQUESTS`
does not apply. `workspace_scope` opens its own `transaction.atomic()`; the LLM call happens
*before* entering it (network I/O outside the DB txn), then the row update runs scoped inside it.
**Alternatives**: Reuse request transaction (impossible — different process); hold a txn across the
LLM call (the M1/proposal anti-pattern this milestone exists to kill).
**Rationale**: Keeps the ~30s network call off any DB transaction; only the millisecond row write is
transactional and workspace-scoped.

### Decision: Eager tasks for most tests, but forced non-eager for the leak test
**Choice**: `CELERY_TASK_ALWAYS_EAGER=True` in test settings for fast service tests. The
workspace-context leak test MUST bypass eager — call the task body with **no** active contextvar
(fresh thread / cleared context) and assert it sets and clears context correctly, and that a
worker with unset context reads zero rows before `workspace_scope`.
**Alternatives**: Rely only on eager. **Rejected** — eager inherits the caller's request context and
hides exactly the bug the modified capability is about.
**Rationale**: Eager is a convenience that masks the highest risk; the leak test must exercise the
real cold-context path.

### Decision: Binary docx export fetched outside the typed client
**Choice**: `GET /api/lesson-plans/{id}/export?format=docx|md` is a `@action`. Annotate with
`@extend_schema(responses={200: OpenApiTypes.BINARY})` so the schema documents it, but the frontend
downloads via a plain credentialed `fetch` + `Blob` anchor, **not** openapi-fetch (openapi-typescript
does not model binary bodies well).
**Alternatives**: Force typed client to handle binary (brittle). **Rationale**: matches the explore
risk note; markdown could be typed but is treated identically for consistency.

### Decision: Provider factory reading `LLM_PROVIDER`
**Choice**: `core/factory.py::build_provider()` reads settings, constructs an M1 `Config`, and returns
`OpenAICompatProvider.from_config(cfg)` (default) or `ClaudeProvider.from_config(cfg)` when
`LLM_PROVIDER=claude`. The service/task calls `build_provider()` — the port boundary is untouched.
**Rationale**: Env swap only; hexagonal adapters stay verbatim.

## Data Flow

    POST /lesson-plans ──► service.generate_lesson_plan()  (edit_content, ws from membership)
       │                      creates LessonPlan(status=pending, ws=membership.ws, group PROTECT)
       │                      validates plan.ws == group.ws
       └─► enqueue task(workspace_id, lesson_plan_id) ──► 202 {id}

    Celery worker ──► build_provider() ──► provider.generate(req, pdas_for(campo))  [network, no txn]
       │  parse ok  ──► with workspace_scope(ws_id): row.proyecto=…, provenance, status=ready
       │  parse/validation fail ──► with workspace_scope: status=failed, failure_reason=…
       ▼
    GET /lesson-plans/{id}  (poll) ──► {status, proyecto?, failure_reason?}  ── refetchInterval

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/lesson_plans/core/{schema,generation,pdas}.py` | Create (port verbatim) | From M1 |
| `backend/lesson_plans/core/ports/{llm,claude,openai_compat}.py` | Create (verbatim) | Port + adapters |
| `backend/lesson_plans/core/render/{docx,markdown}.py` | Create (adapt) | `render_docx` streams to `BytesIO` instead of path |
| `backend/lesson_plans/core/factory.py` | Create | `build_provider()` reads settings → `Config` |
| `backend/lesson_plans/models.py` | Create | `LessonPlan(ScopedModel)` |
| `backend/lesson_plans/services.py` | Create | `generate_lesson_plan`, `delete_lesson_plan` (kw-only, gated) |
| `backend/lesson_plans/tasks.py` | Create | `generate_lesson_plan_task` (workspace_scope) |
| `backend/lesson_plans/{serializers,viewsets,urls}.py` | Create | DRF surface + export action |
| `backend/lesson_plans/migrations/0001_initial.py` | Create | model |
| `backend/lesson_plans/migrations/0002_rls.py` | Create | `enable_rls_sql("lesson_plans_lessonplan")`, dep `workspaces.0004` |
| `backend/config/celery.py` | Create | Celery app (`config.settings`, autodiscover) |
| `backend/config/__init__.py` | Modify | import celery app |
| `backend/workspaces/scope.py` | Create | `workspace_scope` ctx manager |
| `backend/workspaces/middleware.py` | Modify | use `workspace_scope` |
| `backend/config/settings.py` | Modify | `LLM_*`, `CELERY_*`, add `lesson_plans` app |
| `backend/pyproject.toml` | Modify | `anthropic openai instructor python-docx numpy pydantic celery redis` |
| `frontend/` | Create | list / generate / poll / viewer / export screens |

Dropped (not ported): `corpus.py`, `ports/embeddings.py`, `data/`, `cli.py`, standalone `config.py`.

## Interfaces / Contracts

**LessonPlan (ScopedModel)** — `db_table="lesson_plans_lessonplan"`:
`group = FK("schools.Group", PROTECT, related_name="lesson_plans")`; `campo` CharField;
`grade` CharField; `theme` TextField; `title` CharField (blank until ready);
`proyecto = JSONField(null=True)` (Pydantic `Proyecto` shape); `status` (`pending|ready|failed`,
default pending); `failure_reason` TextField blank; `provider` CharField; `model_name` CharField;
`prompt_tokens`/`completion_tokens` IntegerField null; `invented_pdas = BooleanField(default=False)`;
`generated_at` DateTimeField null; `created_at` auto. Invariant `workspace == group.workspace`
enforced in the service (never RLS).

**Service** — `generate_lesson_plan(*, membership, group, campo, grade, theme) -> LessonPlan`:
requires `edit_content`; `workspace=membership.workspace`; validates `group.workspace_id ==
membership.workspace_id`; creates pending row; enqueues `generate_lesson_plan_task.delay(
workspace_id=…, lesson_plan_id=…)`.

**Task** — `generate_lesson_plan_task(*, workspace_id, lesson_plan_id)`: `provider=build_provider()`;
`result=provider.generate(GenerationRequest(campo,grade,theme), pdas_for(campo))` outside any txn;
on success `with workspace_scope(workspace_id):` persist `proyecto=result.proyecto.model_dump()`,
provenance, `invented_pdas=bool(result.invented_pdas)`, `status=ready`; on `pydantic/instructor`
parse/validation error or `KeyError` (unknown campo) → `status=failed`, `failure_reason` (truncated).
Retry: `max_retries=2`, exponential backoff, only for transient provider/network errors; parse
failures are terminal (no retry). Soft time limit ~90s.

**Endpoints** (`capability_map`): `create`→edit_content (202 + id), `list`→view_workspace
(`?group=<id>` filter), `retrieve`→view_workspace (poll target, includes status), `destroy`→edit_content,
`export` action→view_workspace (docx/md bytes). Reads via `LessonPlan.objects.all()` (ScopedManager).

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | fidelity guard, factory provider selection, `render_docx` → BytesIO | pure pytest, fake provider |
| Unit | **workspace-context leak** | task body with cold/empty context → asserts scope set then cleared; unset context reads 0 rows |
| Integration | generate service: pending row + enqueue, ws==group invariant, edit_content gate | pytest-django, fake task |
| Integration | task success/parse-failure → status transitions + provenance | eager off for context test, fake provider |
| Integration | cross-workspace isolation on list/retrieve/export (404) | two workspaces |
| Integration | export docx bytes + drf-spectacular schema annotation | client + schema assert |

## Threat Matrix (process-integration boundary — Celery worker)

| Threat | Applicable | Safe behavior / RED test |
|--------|-----------|--------------------------|
| Background job runs without active workspace → RLS/manager silently empty | **Applicable** | `workspace_scope` MUST wrap every scoped write; leak test forces cold context |
| `workspace_id` in broker message tampered/spoofed | **Applicable** | Task trusts only the enqueued id set server-side from `membership.workspace`; never from client body; scope enforces isolation on write |
| Pooled connection reuses stale `SET LOCAL` across tasks | **Applicable** | `workspace_scope` uses txn-local `set_config(…, true)`, auto-cleared on commit/rollback (same guarantee as middleware) |
| Cross-workspace `group` FK on generate | **Applicable** | service validates `group.workspace_id == membership.workspace_id` → `ValueError`/400 |
| Shell/subprocess/VCS/routing execution | N/A | No shell, subprocess, or PR automation introduced |

## Migration / Rollout

Additive: two new migrations in a new app; no changes to existing tables. Requires a running Redis
broker + Celery worker process (new infra — deployment note). Rollback = remove `lesson_plans` from
`INSTALLED_APPS`, drop its migrations, revert settings/pyproject/celery/frontend and the `workspace_scope`
extraction. `PROTECT` FK means no cascade damage to Group.

## Delivery Mapping (400-line budget: High → chained PRs)

- **D1** — Port core + deps + provider factory + `LLM_*` settings. (~verbatim copies + factory; watch total)
- **D2** — `LessonPlan` model + serializer + RLS migration.
- **D3** — Celery infra (`config/celery.py`, settings, `workspace_scope` extraction + middleware refactor)
  + task + **workspace-context leak test**.
- **D4** — generation service + `create`(202)/`retrieve`(poll) endpoints.
- **D5** — CRUD (`list?group=`, `destroy`) + docx/md export action + spectacular annotation.
- **D6** — frontend: list per group + generate form + async poll.
- **D7** — frontend: proyecto viewer (read-only stages→moments→sessions→rubric) + export download.

D1 risks exceeding 400 lines (multiple ported files); if so, split D1a (schema/generation/pdas/render)
from D1b (ports + factory + settings). All others fit comfortably.

## Open Questions

- [ ] Broker choice confirmed Redis (assumed) vs RabbitMQ — Redis proposed (lighter, doubles as future cache).
- [ ] Fallback-to-Claude on repeated vLLM parse failure: deferred to a later slice, or in-task second attempt in D3? Proposed: **status=failed first cut**, provider swap is env-level.
- [ ] Frontend campo selector limited to `available_campos()` (2 of 4 campos) — gate the dropdown to fixture-backed campos (proposed).
