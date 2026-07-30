# Tasks: Quizzy P6 — Demo hardening, then the showcase persona

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~750–900 total (5 slices) |
| 400-line budget risk | High (total); per-slice Low–Medium after 1a/1b split |
| Chained PRs recommended | Yes |
| Suggested split | PR 1a → PR 1b → PR 2 → PR 3 → PR 4 |
| Delivery strategy | force-chained (auto-chain) |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1a | Redis CACHES + conftest + demo throttle scopes | PR 1 | `uv run pytest backend/demo/tests/test_throttling.py` | N/A — pytest LocMem override replaces Redis; no live broker needed | `backend/conftest.py` + `settings.py` CACHES block + demo rates deletable; `demo/views.py` throttle attrs removable |
| 1b | `GenerationRateThrottle` + MCP HTTP throttle | PR 2 | `uv run pytest backend/lesson_plans/test_throttling.py backend/mcp_server/tests/test_http_throttle.py` | N/A — LocMem + mock bearer; no live GPU or Redis needed | `core/throttling.py`, `demo/identity.py`, `mcp_server/throttling.py` deletable; `viewsets.py` / `http.py` revert |
| 2 | TTL reap (beat + leaf-first delete) | PR 3 | `uv run pytest backend/demo/tests/test_reaping.py` | N/A — service called directly, no broker needed | `demo/reaping.py` deletable; beat entry + `DEMO_SESSION_TTL_HOURS` removed from settings |
| 3 | `DEMO_DEPLOY` hosting-posture gate + docs | PR 4 | `uv run pytest backend/config/tests/test_demo_deploy.py` | N/A — validator called with explicit args, no live Django runtime needed | `demo_mode.py` reverts; `DEMO_DEPLOY` left unset restores today's behavior |
| 4 | Showcase persona provisioner + registry | PR 5 | `uv run pytest backend/demo/tests/test_provisioning_showcase.py` | N/A — SQLite + existing fixtures; no LLM call | Remove `_REGISTRY` entry to roll back; no migration to reverse |

---

## Phase 1 — Redis CACHES + conftest + demo throttle scopes (Slice 1a)

- [x] 1.1 **[RED]** Create `backend/demo/tests/test_throttling.py` — failing tests: `demo_personas` 429 at request 61, `demo_session_create` 429 at request 6, `demo_session_poll` 429 at request 121; scope independence; full provision cycle reaches poll-120 without hitting create counter
- [x] 1.2 **[GREEN]** Modify `backend/config/settings.py`: add `CACHES["default"]` with `redis.RedisCache` at `REDIS_CACHE_URL`; add pytest `LocMemCache` override block; add `DEFAULT_THROTTLE_RATES` for `demo_personas`, `demo_session_create`, `demo_session_poll`
- [x] 1.3 **[GREEN]** Create `backend/conftest.py`: autouse `cache.clear()` fixture so throttle counters never leak across tests
- [x] 1.4 **[GREEN]** Modify `backend/demo/views.py`: add `throttle_classes = [ScopedRateThrottle]` and `throttle_scope` to `DemoPersonaListView`, `DemoSessionCreateView`, `DemoSessionDetailView`
- [x] 1.5 **[VERIFY]** Run `uv run pytest backend/demo/tests/test_throttling.py` — all green; run `uv run pytest` full suite — no new failures

## Phase 2 — `GenerationRateThrottle` + MCP HTTP throttle (Slice 1b)

- [x] 2.1 **[RED]** Create `backend/lesson_plans/test_throttling.py` — failing: demo guest 429 at request 4, no new `LessonPlan` created, quota `used` unchanged; teacher up to 30 unaffected; counters independent
- [x] 2.2 **[RED]** Create `backend/mcp_server/tests/test_http_throttle.py` — failing: per-token 429 after rate ceiling; two distinct bearer tokens have independent counters; no tool executed on 429
- [x] 2.3 **[GREEN]** Modify `backend/config/settings.py`: add `lesson_plan_generate_demo` (3/hour), `lesson_plan_generate` (30/hour), `mcp_http` (60/min) to `DEFAULT_THROTTLE_RATES`
- [x] 2.4 **[GREEN]** Create `backend/demo/identity.py`: `is_demo_guest(user) -> bool` via `DemoSession.objects.filter(user_id=…, status=READY).exists()`
- [x] 2.5 **[GREEN]** Create `backend/core/throttling.py`: `GenerationRateThrottle(SimpleRateThrottle)` — `get_cache_key()` sets `self.scope` to demo or teacher scope based on `is_demo_guest(request.user)`; deferred import of `is_demo_guest`
- [x] 2.6 **[GREEN]** Modify `backend/lesson_plans/viewsets.py`: add `get_throttles()` returning `[GenerationRateThrottle()]` when `self.action == "create"` else `[]`
- [x] 2.7 **[GREEN]** Create `backend/mcp_server/throttling.py`: `McpHttpTokenThrottle(SimpleRateThrottle)` keyed on `sha256(bearer)`, rate from `settings.MCP_HTTP_THROTTLE_RATE`
- [x] 2.8 **[GREEN]** Modify `backend/mcp_server/http.py`: insert `McpHttpTokenThrottle` check after 401 gate; return 429 + `Retry-After` header on limit
- [x] 2.9 **[VERIFY]** `uv run pytest backend/lesson_plans/test_throttling.py backend/mcp_server/tests/test_http_throttle.py` green; full suite clean

## Phase 3 — TTL reap (Slice 2)

- [ ] 3.1 **[RED]** Create `backend/demo/tests/test_reaping.py` — failing: expired `teacher_full`-shaped tenant deleted leaf-first without `ProtectedError`; `DemoSession` row absent after reap; unexpired session untouched; two workspaces — only expired workspace rows deleted
- [ ] 3.2 **[GREEN]** Modify `backend/config/settings.py`: add `DEMO_SESSION_TTL_HOURS = env.int("DEMO_SESSION_TTL_HOURS", default=24)`; add `CELERY_BEAT_SCHEDULE` entry `"reap-expired-demo-sessions"` with `crontab(minute=0)`
- [ ] 3.3 **[GREEN]** Create `backend/demo/reaping.py`: `reap_expired_demo_sessions(now=None) -> int` — query `DemoSession` with `created_at < now - TTL`; per session delete in order `LessonPlan → Student → GenerationUsage → Group → SchoolYear → School` inside `workspace_scope`; then `workspace.delete()`; then `user.delete()` if no remaining memberships; direct delete for sessions with no workspace
- [ ] 3.4 **[GREEN]** Modify `backend/demo/tasks.py`: add `reap_expired_demo_sessions_task` as thin Celery task wrapping `reaping.reap_expired_demo_sessions()`
- [ ] 3.5 **[VERIFY]** `uv run pytest backend/demo/tests/test_reaping.py` green; `uv run pytest` full suite clean

## Phase 4 — DEMO_DEPLOY hosting-posture gate + docs (Slice 3)

- [ ] 4.1 **[RED]** Create `backend/config/tests/test_demo_deploy.py` — failing: `DEMO_DEPLOY=True` + `DEBUG=True` → `DebugNotAllowedInDemoDeploy`; each hardening violation → `DemoDeployNotHardened`; `DEMO_DEPLOY=True` + `DEMO_MODE=False` → `DemoDeployNotHardened`; `enabled()` truth table for all four `DEMO_MODE`/`DEBUG`/`DEMO_DEPLOY` combinations
- [ ] 4.2 **[GREEN]** Modify `backend/config/demo_mode.py`: update `enabled()` to `DEMO_MODE and (DEBUG or DEMO_DEPLOY)`; add `validate_deploy_hardening(*, debug, allowed_hosts, secret_key, caches, session_cookie_secure, csrf_cookie_secure)` — raises `DebugNotAllowedInDemoDeploy` or `DemoDeployNotHardened` per contract; add both exception classes; existing `validate()` and `ProductionNotAllowed` untouched
- [ ] 4.3 **[GREEN]** Modify `backend/config/settings.py`: add `DEMO_DEPLOY = env.bool("DEMO_DEPLOY", default=False)`; call `validate_deploy_hardening(...)` at tail; force `SPECTACULAR_SETTINGS["SERVE_INCLUDE_SCHEMA"] = False` and drop browsable renderer when `DEMO_DEPLOY`
- [ ] 4.4 **[GREEN]** Modify `.env.example`: add `REDIS_CACHE_URL`, `DEMO_SESSION_TTL_HOURS`, `DEMO_DEPLOY` entries + posture comment block
- [ ] 4.5 **[GREEN]** Modify `docs/quizzy_roadmap.md`: resolve open Q4 with `DEMO_DEPLOY` contract summary
- [ ] 4.6 **[VERIFY]** `uv run pytest backend/config/tests/test_demo_deploy.py` green; existing `test_demo_mode.py` still green; `uv run pytest` full suite clean

## Phase 5 — Showcase persona provisioner (Slice 4)

- [ ] 5.1 **[RED]** Create `backend/demo/tests/test_provisioning_showcase.py` — failing: showcase renders grounding ✓ for clean plan (⚠ for warning plan); provenance fields present (`provider`, `model_name`, `generated_at`, tokens); zero `GenerationUsage` rows; both plans `status=ready`; `cost_micros`/`duration_ms` absent or null
- [ ] 5.2 **[RED]** Modify `backend/demo/tests/test_api.py` line 37: add `"showcase"` to persona-key assertion set (expected to fail until registry entry added)
- [ ] 5.3 **[GREEN]** Create `backend/demo/provisioning/showcase.py`: `Showcase(DemoProvisioner)` with `persona_key = "showcase"`; seeds school + ciclo + `1°A` group + 10 students via services layer; writes two `LessonPlan` rows directly from `proyecto_demo.json` (clean) and `proyecto_lenguajes.json` (warning) with P1 provenance fields populated
- [ ] 5.4 **[GREEN]** Modify `backend/demo/personas.py`: add `"showcase": Showcase` to `_REGISTRY`
- [ ] 5.5 **[VERIFY]** `uv run pytest backend/demo/tests/test_provisioning_showcase.py backend/demo/tests/test_api.py` green; `uv run makemigrations --check` clean; `uv run pytest` full suite green
