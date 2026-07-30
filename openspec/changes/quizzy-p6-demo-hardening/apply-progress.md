# Apply Progress: quizzy-p6-demo-hardening

**Mode**: Strict TDD  
**Batch**: Slice 4 (Phase 5, tasks 5.1–5.5) — cumulative with Slice 1a + 1b + 2 + 3  
**Branch**: `feat/quizzy-p6-s4-showcase` (stacked on `feat/quizzy-p6-s3-demo-deploy` @ `ac66449`)  
**Updated**: 2026-07-30

## Completed Tasks

### Slice 1a (Phase 1)

- [x] 1.1 RED `backend/demo/tests/test_throttling.py`
- [x] 1.2 GREEN `CACHES` + `DEFAULT_THROTTLE_RATES` (demo scopes only)
- [x] 1.3 GREEN `backend/conftest.py` autouse `cache.clear()`
- [x] 1.4 GREEN demo views `ScopedRateThrottle` + scopes
- [x] 1.5 VERIFY focused + full suite

### Slice 1b (Phase 2)

- [x] 2.1 RED `backend/lesson_plans/test_throttling.py`
- [x] 2.2 RED `backend/mcp_server/tests/test_http_throttle.py`
- [x] 2.3 GREEN rates + `MCP_HTTP_THROTTLE_RATE` in settings
- [x] 2.4 GREEN `backend/demo/identity.py` (`is_demo_guest`)
- [x] 2.5 GREEN `backend/core/throttling.py` (`GenerationRateThrottle`)
- [x] 2.6 GREEN `LessonPlanViewSet.get_throttles()` for `create`
- [x] 2.7 GREEN `backend/mcp_server/throttling.py` (`McpHttpTokenThrottle`)
- [x] 2.8 GREEN `mcp_http_view` throttle after 401 + `Retry-After`
- [x] 2.9 VERIFY focused + full suite

### Slice 2 (Phase 3)

- [x] 3.1 RED `backend/demo/tests/test_reaping.py`
- [x] 3.2 GREEN `DEMO_SESSION_TTL_HOURS` + `CELERY_BEAT_SCHEDULE` (`crontab(minute=0)`)
- [x] 3.3 GREEN `backend/demo/reaping.py` leaf-first delete inside `workspace_scope`
- [x] 3.4 GREEN `reap_expired_demo_sessions_task` thin Celery wrapper
- [x] 3.5 VERIFY focused + full suite

### Slice 3 (Phase 4)

- [x] 4.1 RED `backend/config/tests/test_demo_deploy.py`
- [x] 4.2 GREEN `demo_mode.py`: `enabled()` formula + `validate_deploy_hardening` + two exceptions (`validate`/`ProductionNotAllowed` body untouched)
- [x] 4.3 GREEN `settings.py`: `DEMO_DEPLOY`, skip early `validate()` when deploy, tail hardening call, schema/browsable drop
- [x] 4.4 GREEN `.env.example` posture block
- [x] 4.5 GREEN `docs/quizzy_roadmap.md` Q4 resolved
- [x] 4.6 VERIFY focused + full suite

### Slice 4 (Phase 5) — this batch — ALL DONE

- [x] 5.1 RED `backend/demo/tests/test_provisioning_showcase.py`
- [x] 5.2 RED `test_api.py` persona keys include `"showcase"`
- [x] 5.3 GREEN `backend/demo/provisioning/showcase.py` (`Showcase`)
- [x] 5.4 GREEN `personas.py` `_REGISTRY` entry
- [x] 5.5 VERIFY focused + makemigrations --check + full suite

## Remaining

None — all implementation tasks complete. Next: `sdd-verify`.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `demo/tests/test_throttling.py` | Integration | ✅ 10/10 `demo/tests/test_api.py` | ✅ Written (6 fail: no throttle) | ✅ Deferred to 1.2–1.4 | ✅ 6 cases | ➖ N/A (test-only) |
| 1.2 | same | Integration | ✅ settings load | ✅ Covered by 1.1 | ✅ Passed after CACHES + rates | ➖ Structural (config) | ➖ None needed |
| 1.3 | same | Integration | N/A (new) | ✅ Covered by 1.1 (leak risk) | ✅ Passed with autouse clear | ➖ Structural (fixture) | ➖ None needed |
| 1.4 | same | Integration | ✅ 10/10 demo API | ✅ Covered by 1.1 | ✅ Passed after view attrs | ✅ All three views scoped | ➖ None needed |
| 1.5 | same | Integration | — | — | ✅ 6/6 focused; ✅ 505 passed full suite | — | — |
| 2.1 | `lesson_plans/test_throttling.py` | Integration | ✅ 14/14 viewsets+http | ✅ Written (2 fail on missing 429) | ✅ Deferred to 2.3–2.6 | ✅ 3 cases (demo 429+quota, teacher 30, independence) | ➖ N/A (test-only) |
| 2.2 | `mcp_server/tests/test_http_throttle.py` | Integration | ✅ same safety net | ✅ Written (2 fail on missing 429) | ✅ Deferred to 2.7–2.8 | ✅ 2 cases (ceiling+no tool, token independence) | ➖ N/A (test-only) |
| 2.3 | same | Integration | ✅ settings | ✅ Covered by 2.1/2.2 | ✅ Rates + `MCP_HTTP_THROTTLE_RATE` | ➖ Structural (config) | ➖ None needed |
| 2.4 | same | Integration | N/A (new) | ✅ Covered by demo-guest cases | ✅ `is_demo_guest` via READY DemoSession | ✅ demo vs teacher paths | ➖ None needed |
| 2.5 | same | Integration | N/A (new) | ✅ Covered by 2.1 | ✅ `GenerationRateThrottle` scope flip + deferred import | ✅ demo+teacher scopes | ✅ Re-parse rate after scope flip |
| 2.6 | same | Integration | ✅ viewsets green | ✅ Covered by 2.1 | ✅ `get_throttles()` create-only | ✅ create vs other actions | ➖ None needed |
| 2.7 | same | Integration | N/A (new) | ✅ Covered by 2.2 | ✅ `McpHttpTokenThrottle` sha256 key | ✅ two tokens | ➖ None needed |
| 2.8 | same | Integration | ✅ http green | ✅ Covered by 2.2 | ✅ post-401 throttle + Retry-After | ✅ 429 without ASGI | ➖ None needed |
| 2.9 | same | Integration | — | — | ✅ 5/5 focused; ✅ 25 related; ✅ **510 passed** full suite | — | — |
| 3.1 | `demo/tests/test_reaping.py` | Integration | ✅ 6/6 `demo/tests/test_tasks.py` | ✅ Written (collection ImportError → then fail until impl) | ✅ Deferred to 3.2–3.4 | ✅ 5 behavior cases (teacher_full, quota_exhausted, unexpired, isolation, pending) | ➖ N/A (test-only) |
| 3.2 | same | Integration | ✅ settings | ✅ Covered by TTL/beat assertions | ✅ `DEMO_SESSION_TTL_HOURS` + `CELERY_BEAT_SCHEDULE` | ✅ default 24 + crontab minute={0} | ➖ None needed |
| 3.3 | same | Integration | N/A (new) | ✅ Covered by 3.1 | ✅ leaf-first inside `workspace_scope` incl. `workspace.delete()` | ✅ GenerationUsage path + pending direct delete | ➖ None needed |
| 3.4 | same | Integration | ✅ tasks module | ✅ Covered by wrapper tests | ✅ thin `reap_expired_demo_sessions_task` | ✅ mock delegate + real pending reap | ➖ None needed |
| 3.5 | same | Integration | — | — | ✅ 8/8 focused; ✅ **518 passed** full suite | — | — |
| 4.1 | `config/tests/test_demo_deploy.py` | Unit | ✅ 20/20 `config/test_demo_mode.py` | ✅ Written (ImportError on new symbols) | ✅ Deferred to 4.2 | ✅ debug + 7 hardening + 8-row enabled truth table | ➖ N/A (test-only) |
| 4.2 | same | Unit | ✅ existing gate tests | ✅ Covered by 4.1 | ✅ `enabled()` formula + pure validator + 2 exceptions | ✅ all violation paths + truth table | ➖ validate() body left intact |
| 4.3 | same | Unit | ✅ settings load | ✅ Covered by contract | ✅ `DEMO_DEPLOY` + skip early validate + tail call + renderer/schema | ➖ Structural (settings wiring) | ➖ None needed |
| 4.4 | — | — | N/A | ➖ Docs | ✅ `.env.example` posture block | ➖ Structural | ➖ |
| 4.5 | — | — | N/A | ➖ Docs | ✅ Q4 resolved in roadmap | ➖ Structural | ➖ |
| 4.6 | same | Unit | — | — | ✅ 17/17 focused; ✅ 20/20 existing; ✅ **535 passed** full suite | — | — |
| 5.1 | `demo/tests/test_provisioning_showcase.py` | Integration | ✅ 21/21 `test_provisioning_personas.py`; ✅ 22/22 api+personas | ✅ Written (ModuleNotFoundError on Showcase) | ✅ Deferred to 5.3 | ✅ shape + clean ✓ + warning ⚠ + zero usage + soft-defer | ➖ N/A (test-only) |
| 5.2 | `demo/tests/test_api.py` | Integration | ✅ 22/22 api+personas | ✅ Assertion fails (showcase missing) | ✅ Deferred to 5.4 | ➖ Structural (key list) | ➖ None needed |
| 5.3 | `demo/provisioning/showcase.py` | Integration | N/A (new) | ✅ Covered by 5.1 | ✅ Showcase seeds school/grupo/students + 2 plans | ✅ clean vs warning paths | ➖ None needed |
| 5.4 | `demo/personas.py` | Integration | ✅ personas registry | ✅ Covered by 5.2 | ✅ `_REGISTRY` showcase entry | ➖ Structural (registry) | ➖ None needed |
| 5.5 | same | Integration | — | — | ✅ 17 focused; ✅ 29 with personas; ✅ **542 passed** full suite; makemigrations --check clean | — | — |

### Work Unit Evidence (Slice 4)

| Evidence | Value |
|----------|-------|
| Focused test command | `cd backend && uv run pytest demo/tests/test_provisioning_showcase.py demo/tests/test_api.py` → **17 passed** |
| Related safety net | `… test_personas.py` (+ focused) → **29 passed** |
| Full suite | `cd backend && uv run pytest` → **542 passed in 39.50s** |
| Migrations | `uv run python manage.py makemigrations --check` → **No changes detected** |
| Runtime harness | N/A — SQLite/Postgres test DB + fixtures; no LLM call |
| Rollback boundary | Remove `_REGISTRY` showcase entry, `provisioning/showcase.py`, `test_provisioning_showcase.py`; revert `test_api.py` key list |

### Work Unit Evidence (Slice 3 — preserved)

| Evidence | Value |
|----------|-------|
| Focused test command | `cd backend && uv run pytest config/tests/test_demo_deploy.py config/test_demo_mode.py` → **37 passed** |
| Full suite | `cd backend && uv run pytest` → **535 passed in 39.23s** |
| Runtime harness | N/A — validator called with explicit args; no live Django boot under DEMO_DEPLOY in CI |
| Rollback boundary | Leave `DEMO_DEPLOY` unset; revert `demo_mode.py` enabled/validator + settings tail + `.env.example` + Q4 docs + `config/tests/test_demo_deploy.py` |

### Work Unit Evidence (Slice 2 — preserved)

| Evidence | Value |
|----------|-------|
| Focused test command | `cd backend && uv run pytest demo/tests/test_reaping.py` → **8 passed** |
| Related safety net | `… test_managers.py test_reaping.py` → **10 passed**; `test_reaping + test_tasks + test_throttling` → **20 passed** |
| Full suite | `cd backend && uv run pytest` → **518 passed in 38.77s** |
| Runtime harness | N/A — service called directly; eager Celery under pytest; no broker needed |
| Rollback boundary | Remove `demo/reaping.py`, beat entry + `DEMO_SESSION_TTL_HOURS`, task wrapper, `test_reaping.py`; revert `test_managers.py` ScopedProbe fixture unregister |

### Work Unit Evidence (Slice 1b — preserved)

| Evidence | Value |
|----------|-------|
| Focused test command | `cd backend && uv run pytest lesson_plans/test_throttling.py mcp_server/tests/test_http_throttle.py` → **5 passed** |
| Related safety net | `… test_viewsets.py test_http.py demo/tests/test_throttling.py` (+ focused) → **25 passed** |
| Full suite | `cd backend && uv run pytest` → **510 passed in 38.29s** |
| Runtime harness | N/A — LocMem + mocked provider / patched ASGI; no live GPU or Redis needed |
| Rollback boundary | Remove `core/throttling.py`, `demo/identity.py`, `mcp_server/throttling.py`, rates/`MCP_HTTP_THROTTLE_RATE`, `get_throttles` / http throttle insert, and the two new test files |

### Work Unit Evidence (Slice 1a — preserved)

| Evidence | Value |
|----------|-------|
| Focused test command | `cd backend && uv run pytest demo/tests/test_throttling.py` → **6 passed** |
| Full suite | `cd backend && uv run pytest` → **505 passed in 37.35s** |
| Runtime harness | N/A — pytest LocMem override replaces Redis |
| Rollback boundary | Remove `conftest.py`, `CACHES`/demo rates, demo view throttle attrs, `demo/tests/test_throttling.py` |

### Workload / PR Boundary

- Mode: stacked PR slice (`stacked-to-main`)
- Current work unit: Slice 4 — Showcase persona (LAST apply slice)
- Boundary: showcase provisioner + registry only; no throttle/reap/deploy changes
- Estimated review budget: Low (under 400 authored lines)

### Deviations from Design

- Slice 3: `validate_deploy_hardening` takes explicit `demo_mode` kwarg; early `_demo_mode_validate()` skipped when `DEMO_DEPLOY`.
- Slice 4: None — implementation matches design showcase seed shape.

### Issues Found

None.
