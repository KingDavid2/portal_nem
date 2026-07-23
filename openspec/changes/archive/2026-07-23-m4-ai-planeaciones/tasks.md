# Tasks: M4 — AI planeaciones (Celery-backed, tenant-scoped)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2800-3400 total across 8 deliveries (150-450/delivery) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | D1a → D1b → D2 → D3 → D4 → D5 → D6 → D7 → D8 (9 chained commits) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| D1a | Port M1 pure core (schema/generation/pdas/render) | PR 1 | `cd backend && uv run pytest lesson_plans/core -q` | N/A — pure unit, no live infra | Delete `backend/lesson_plans/core/{schema,generation,pdas}.py`, `render/` |
| D1b | Port ports/ + factory + LLM_* settings | PR 2 | `cd backend && uv run pytest lesson_plans/core/test_factory.py -q` | N/A — provider selection is unit-testable via env fixtures | Delete `ports/`, `factory.py`; revert settings.py LLM_* block |
| D2 | Extract `workspace_scope` into `workspaces/scope.py` | PR 3 | `cd backend && uv run pytest workspaces -q` | Existing M2/M3 tenancy suite (full regression, behavior-preserving) | Revert `scope.py` + inline the extracted logic back into middleware |
| D3 | `LessonPlan` model + RLS migration | PR 4 | `cd backend && uv run pytest lesson_plans/test_models.py -q` | `uv run manage.py makemigrations --check --dry-run` clean | Drop `lesson_plans` migrations 0001/0002; remove model file |
| D4 | Celery infra + task + leak test | PR 5 | `cd backend && uv run pytest lesson_plans/test_tasks.py -q` | Non-eager: real worker/broker execution against local Redis (`redis-server`, `celery -A config worker`) for the leak test | Remove `config/celery.py`, task file, CELERY_* settings; revert `config/__init__.py` |
| D5 | Generation service + create/list/retrieve/destroy endpoints | PR 6 | `cd backend && uv run pytest lesson_plans/test_services.py lesson_plans/test_viewsets.py -q` | Eager Celery for service/isolation tests (task internals already proven in D4) | Remove `services.py`, `viewsets.py`, `serializers.py`, `urls.py` entries |
| D6 | Docx/md export action + schema annotation | PR 7 | `cd backend && uv run pytest lesson_plans/test_export.py -q` | N/A — export is a synchronous view over stored `proyecto`, no live infra needed | Remove `export` action + BINARY schema annotation |
| D7 | Frontend list + generate form + poll | PR 8 | `npm test -- planeaciones` | Manual: point `NEXT_PUBLIC_API_URL` at local backend + Redis/Celery worker, generate a plan end-to-end | Remove new list/generate route files; revert client regen diff |
| D8 | Frontend proyecto viewer + docx export download | PR 9 | `npm test -- viewer` | Manual: download docx via Blob anchor from a `ready` plan | Remove viewer route + export download handler |

## Phase 1: Core Port (D1a, D1b)

- [x] 1.1 Create `backend/lesson_plans/core/schema.py` — port M1 ABPC Pydantic schema verbatim (Requirement: LessonPlan Is a Workspace-Scoped Entity — proyecto JSON shape).
- [x] 1.2 Create `backend/lesson_plans/core/generation.py` — port M1 generation orchestration verbatim.
- [x] 1.3 Create `backend/lesson_plans/core/pdas.py` — port M1 fixture PDA data (RAG OFF, per proposal Out of Scope).
- [x] 1.4 Create `backend/lesson_plans/core/render/{docx,markdown}.py` — adapt `render_docx` to stream to `BytesIO` instead of a filesystem path.
- [x] 1.5 Add `anthropic`, `openai`, `instructor`, `python-docx`, `numpy` to `backend/pyproject.toml`.
- [x] 1.6 RED: port M1 schema-validation + render-smoke tests into `backend/lesson_plans/core/test_schema.py`, `test_render.py`.
- [x] 1.7 GREEN: confirm ported tests pass against the ported core (`uv run pytest lesson_plans/core -q`).
- [x] 1.8 Create `backend/lesson_plans/core/ports/llm.py` — port `LLMProvider` port interface verbatim.
- [x] 1.9 Create `backend/lesson_plans/core/ports/openai_compat.py`, `ports/claude.py` — port adapters verbatim.
- [x] 1.10 Create `backend/lesson_plans/core/factory.py::build_provider()` — reads Django settings, builds M1 `Config`, returns `OpenAICompatProvider` (default) or `ClaudeProvider` when `LLM_PROVIDER=claude` (Requirement: Provider Selection Is Config-Driven).
- [x] 1.11 Modify `backend/config/settings.py` — add `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`.
- [x] 1.12 RED: `test_factory.py` — default (unset `LLM_PROVIDER`) selects OpenAI-compatible adapter; `LLM_PROVIDER=claude` selects Claude adapter without service-layer changes (Scenarios: Default configuration selects vLLM; Switching to Claude requires only configuration).
- [x] 1.13 GREEN: confirm `build_provider()` passes both scenarios.

## Phase 2: Tenancy Primitive Extraction (D2)

- [x] 2.1 Create `backend/workspaces/scope.py::workspace_scope(workspace_id)` — context manager opening its own `transaction.atomic()`, executing `SET LOCAL app.workspace_id` + `active_workspace.set()`, extracted verbatim from `TenancyMiddleware`.
- [x] 2.2 Modify `backend/workspaces/middleware.py::TenancyMiddleware` to call `workspace_scope` instead of inlining the SQL/contextvar logic.
- [x] 2.3 REFACTOR: run the full existing tenancy/middleware suite unchanged and confirm still green (behavior-preserving extraction, no new test needed here — full suite is the proof).

## Phase 3: LessonPlan Model + RLS (D3)

- [x] 3.1 RED: `test_models.py` — `LessonPlan.workspace_id` is populated directly on the row, not derived by joining `Group` (Scenario: LessonPlan row carries its own workspace FK).
- [x] 3.2 RED: `test_models.py` — deleting a `Group` with referencing `LessonPlan` rows returns 4xx, not delete (Scenario: Deleting a Group with lesson plans is blocked).
- [x] 3.3 GREEN: Create `backend/lesson_plans/models.py::LessonPlan(ScopedModel)` — `group=FK(schools.Group, PROTECT)`, `campo`, `grade`, `theme`, `title`, `proyecto=JSONField(null=True)`, `status` (`pending|ready|failed`, default `pending`), `failure_reason`, `provider`, `model_name`, `prompt_tokens`/`completion_tokens`, `invented_pdas=BooleanField(default=False)`, `generated_at`, `created_at`.
- [x] 3.4 Create `backend/lesson_plans/migrations/0001_initial.py`.
- [x] 3.5 Create `backend/lesson_plans/migrations/0002_rls.py` — `enable_rls_sql("lesson_plans_lessonplan")` via `workspaces.rls` helper, depends on `workspaces.0004`.
- [x] 3.6 Register `lesson_plans` in `INSTALLED_APPS`.
- [x] 3.7 RED/GREEN: RLS backstop test — direct DB access without `workspace_scope` context returns zero rows for `LessonPlan`.
- [x] 3.8 Run `uv run manage.py makemigrations --check --dry-run` — confirm clean.

## Phase 4: Celery Infra + Task + Leak Test (D4)

- [x] 4.1 Create `backend/config/celery.py` — Celery app bound to `config.settings`, autodiscover tasks.
- [x] 4.2 Modify `backend/config/__init__.py` to import the Celery app.
- [x] 4.3 Modify `backend/config/settings.py` — `CELERY_BROKER_URL` (Redis), `CELERY_TASK_ALWAYS_EAGER=True` in test settings only.
- [x] 4.4 RED (non-eager, CRITICAL): `test_tasks.py::test_task_without_established_context_fails_closed_not_cross_tenant` — dispatch task body with no inherited contextvar/request context (fresh thread or real worker path); assert zero rows read/written for any workspace before `workspace_scope` is entered (Scenario: Task without established context fails closed, not cross-tenant; Tenancy Isolation delta).
- [x] 4.5 RED (non-eager, CRITICAL): `test_tasks.py::test_task_sets_own_workspace_context_from_a_cold_thread` — task resolves `workspace_id` from enqueue args, calls `workspace_scope(workspace_id)`, context is set then cleared after commit/rollback (Scenario: Task sets its own workspace context before reading/writing).
- [x] 4.6 Document in the test module why `CELERY_TASK_ALWAYS_EAGER` is insufficient for 4.4/4.5 (Scenario: Test proves the behavior under real non-eager task execution).
- [x] 4.7 GREEN: Create `backend/lesson_plans/tasks.py::generate_lesson_plan_task(*, workspace_id, lesson_plan_id)` — `build_provider()` + `provider.generate(...)` outside any txn; on success `with workspace_scope(workspace_id):` persist `proyecto`, provenance, `invented_pdas`, `status=ready`; on parse/validation/`KeyError` → `status=failed` + truncated `failure_reason`; `max_retries=2` exponential backoff for transient provider errors only, soft time limit ~90s.
- [x] 4.8 GREEN: confirm 4.4-4.5 pass under real (non-eager) execution — cold `ThreadPoolExecutor` thread (fresh contextvars, separate DB connection via `transaction=True`), not `CELERY_TASK_ALWAYS_EAGER`.
- [x] 4.9 Integration RED/GREEN: `test_tasks.py` — success path sets `status=ready` with provenance; schema-parse failure sets `status=failed` with reason (Scenarios: Celery task completes generation successfully; Celery task fails on schema-parse failure; LLM Provider Requirement: Generation Failures Surface as a Failed Status).

## Phase 5: Generation Service + Create/List/Retrieve/Destroy (D5)

- [x] 5.1 RED: `test_services.py` — caller without `edit_content` cannot create a generation request, no row persisted (Scenario: Caller without edit_content cannot request generation).
- [x] 5.2 RED: `test_services.py` — client-supplied `workspace_id` ignored, row assigned to `membership.workspace` (Scenario: Client-supplied workspace_id is ignored on generation).
- [x] 5.3 RED: `test_services.py` — `group.workspace_id != membership.workspace_id` raises `ValueError`/400 (Requirement: `workspace == group.workspace` invariant, `tenancy-isolation`).
- [x] 5.4 GREEN: Create `backend/lesson_plans/services.py::generate_lesson_plan(*, membership, group, campo, grade, theme)` — keyword-only, `edit_content`-gated, creates `pending` row, enqueues `generate_lesson_plan_task.delay(...)`.
- [x] 5.5 RED/GREEN: PDA-fidelity guard flags an invented PDA and withholds `status=ready` without surfacing the flag (Scenario: Generated projeto invents a PDA not in the source set).
- [x] 5.6 Create `backend/lesson_plans/serializers.py` — request/response serializers including `status`, `proyecto`, `failure_reason`.
- [x] 5.7 Create `backend/lesson_plans/viewsets.py::LessonPlanViewSet` — `ModelViewSet` + `WorkspacePermission` + `capability_map` (`create`→edit_content 202+id, `list`→view_workspace `?group=`, `retrieve`→view_workspace, `destroy`→edit_content).
- [x] 5.8 Create `backend/lesson_plans/urls.py` and wire into project urls.
- [x] 5.9 RED: `test_viewsets.py` — POST generate returns 202 with pending `LessonPlan` id, does not block on LLM call (Scenario: POST generate returns a pending LessonPlan immediately).
- [x] 5.10 RED: `test_viewsets.py` — list scoped to `?group=` returns only that group's workspace-A rows; cross-workspace list/retrieve returns empty/404 (Scenarios: List endpoint returns only the requested group's plans; Retrieve of a foreign-workspace LessonPlan returns 404).
- [x] 5.11 RED: `test_viewsets.py` — repeated polling of retrieve reflects `pending`→`ready`/`failed` transitions (Scenario: Client polls until generation completes).
- [x] 5.12 GREEN: confirm all 5.1-5.11 pass; full suite green.

## Phase 6: Export Action (D6)

- [x] 6.1 RED: `test_export.py` — export of a `pending` `LessonPlan` is rejected, no partial/empty document returned (Scenario: Export of a pending plan is rejected).
- [x] 6.2 GREEN: Add `export` `@action` to `LessonPlanViewSet` (`GET /api/lesson-plans/<id>/export?format=docx|md`), `view_workspace`-gated, `@extend_schema(responses={200: OpenApiTypes.BINARY})`.
- [x] 6.3 RED/GREEN: `test_export.py` — docx export of a `ready` plan returns a valid docx binary reflecting the stored proyecto (Scenario: Export ready plan as docx).
- [x] 6.4 RED/GREEN: markdown export of a `ready` plan returns text reflecting the stored proyecto.
- [x] 6.5 Verify drf-spectacular schema generation includes the BINARY annotation without error.

## Phase 7: Frontend List + Generate + Poll (D7)

- [x] 7.1 Regenerate `schema.d.ts` from the updated OpenAPI schema (includes `lesson-plans` paths).
- [x] 7.2 Create planeaciones list screen per group, using the M3 generated typed client + TanStack Query.
- [x] 7.3 Create generate form (campo/grado/theme), gated to `available_campos()` fixture-backed campos.
- [x] 7.4 Wire async poll on the created `LessonPlan` id via `refetchInterval` until `status` is `ready` or `failed`.
- [x] 7.5 Test: list renders only the active workspace's plans for the selected group; generate form submits and shows pending state; poll stops on ready/failed.

## Phase 8: Frontend Proyecto Viewer + Export Download (D8)

- [x] 8.1 Create read-only proyecto viewer (stages → moments → sessions → rubric) rendering the stored `proyecto` JSON.
- [x] 8.2 Add docx export download via a plain credentialed `fetch` + `Blob` anchor, outside the typed client (binary bodies unsupported by openapi-fetch).
- [x] 8.3 Add regenerate action from the viewer (regenerate-only, no in-app partial editing per proposal scope).
- [x] 8.4 Test: viewer renders a `ready` plan's full structure; export download triggers a file save with correct content-type; regenerate re-enters `pending`/poll flow.
