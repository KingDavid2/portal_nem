# Proposal: Quizzy P6 — Demo hardening, then the showcase persona

## Intent

The demo link cannot be handed to a stranger. Three `AllowAny` views provision a
full tenant with **no throttle** (and no `CACHES` backend to hold counters),
nothing reaps those tenants, and the `DEBUG`-only gate that makes `AllowAny`
acceptable is what makes public hosting unsafe. Only then is the showcase
persona worth seeding.

## Scope

### In Scope
- Redis `CACHES` + per-view scoped `AnonRateThrottle` on the three demo views
  (`personas`, session `create`, session `poll`).
- Scoped throttle on the **authenticated** generation path
  (`LessonPlanViewSet.create`) — the real GPU door after `django_login`.
- Per-token throttle on the MCP Streamable-HTTP mount when `MCP_HTTP_ENABLED`.
  **P4 gated this here explicitly; it is in.**
- `DEMO_SESSION_TTL_HOURS` + Celery-beat `reap_expired_demo_sessions`.
- `DEMO_DEPLOY` flag with a hardening contract; resolves roadmap open Q4.
- `showcase` persona rendering grounding + provenance with zero generations.

### Out of Scope
- P3 columns (`duration_ms`, `cost_micros`, `prompt_version`, `failure_kind`) and
  pricing. `django-celery-beat` DB schedules. Global
  `DEFAULT_THROTTLE_CLASSES`. Mutation tools (P5).

## Capabilities

### New Capabilities
- `demo-mode`: session lifecycle, persona registry, anonymous-surface rate
  limits, TTL reap, hosting-posture gate. No spec covers the M5 demo surface.

### Modified Capabilities
- `ai-planeaciones`: `create` gains a rate limit distinct from monthly quota.
- `mcp-tool-surface`: HTTP transport gains a per-token rate limit.

## Approach

| Decision | Rationale |
|---|---|
| Redis `CACHES` before any throttle | LocMemCache is per-process; counters would not survive gunicorn/celery fan-out, so the throttle would be decorative. |
| Scoped rates per view | Poll runs every few seconds during provisioning; one shared rate either breaks polling or leaves `create` open. |
| Throttle authenticated `create` too | Demo login is "an unauthenticated path to GPU time". Demo-guest scope stays tight; teacher scope generous. |
| `DEMO_DEPLOY` over local-only | The phase goal *is* public hosting. Boot MUST reject `DEMO_DEPLOY` + `DEBUG=True`, mirroring today's `DEMO_MODE ∧ !DEBUG` guard. |
| Beat schedule in `settings.py` | Celery + Redis already exist; one TTL job does not justify a new app + migration. |
| Reap deletes leaf-first inside `workspace_scope(ws.id)` | `ScopedManager` is fail-closed (no scope ⇒ `.none()`) and `Student.group` / `LessonPlan.group` are `PROTECT`, so a naive cascade raises or no-ops. Order: `LessonPlan` → `Student` → group/ciclo/school → `Workspace` → demo `User` → `DemoSession`. |
| Persona seeds P1 fields only | `cost_micros` / `duration_ms` do not exist yet. Grounding + `provider` / `model_name` / tokens / `generated_at` satisfies the exit gate; cost and latency carry to P3. |
| Seed `LessonPlan` rows directly | `TeacherFull`'s documented exception — the real path calls the LLM, which is what the visitor should do. |

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/config/settings.py` | Modified | `CACHES`, rates, `CELERY_BEAT_SCHEDULE`, TTL, `DEMO_DEPLOY` |
| `backend/config/demo_mode.py` | Modified | `DEMO_DEPLOY` path + boot guard |
| `backend/demo/views.py`, `demo/tasks.py` | Modified | Throttle scopes; reap task |
| `backend/demo/personas.py`, `demo/provisioning/showcase.py` | New/Modified | Registry entry + provisioner |
| `backend/lesson_plans/viewsets.py`, `mcp_server/http.py` | Modified | Generation and per-token rate limits |
| `.env.example`, `docs/quizzy_roadmap.md` | Modified | Posture + Q4 resolution |
| `backend/demo/tests/*` | New | Throttle, reap/PROTECT order, persona |

## Delivery — chained PRs, stacked to main (~400 lines/slice)

1. **Throttle + shared cache** — Redis `CACHES`, demo scopes, generation scope,
   MCP HTTP scope.
2. **TTL reap** — TTL setting, beat schedule, leaf-first reap under scope.
3. **Hosting posture** — `DEMO_DEPLOY`, hardening contract, boot guard, docs.
4. **Showcase persona** — provisioner, registry entry, grounded/warning fixtures.

Strict TDD. Slice 4 must update the hardcoded persona-list assertion
(`demo/tests/test_api.py:37`).

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Poll throttle breaks provisioning UX | Med | Generous poll scope; test a full provision cycle through it |
| Generation throttle hits real teachers | Med | Demo-guest scope separate from teacher scope |
| Reap raises `ProtectedError` or no-ops | High | Leaf-first order under scope; test a `teacher_full`-shaped tenant |
| TTL inert without `celery beat` | High | Beat mandatory whenever `DEMO_DEPLOY` is on |
| `DEMO_DEPLOY` weakens the local gate | Med | Additive flag; existing gate tests stay green |
| Slice 3 exceeds budget | Med | Split settings from boot guard; never fall back to implicit local-only |

## Rollback Plan

Slices 1–2 are additive and schema-free: drop the throttle scopes and the beat
entry. Slice 3 rolls back by leaving `DEMO_DEPLOY` unset — behavior returns to
today's gate. Slice 4 rolls back by removing the `_REGISTRY` entry. Prefer
deriving expiry from `created_at` + setting so no `DemoSession` migration (and
reverse migration) is needed.

## Dependencies

- Redis as a cache (broker already is) and a `celery beat` process in any demo
  deploy. P3 is **not** a dependency.

## Success Criteria

- [ ] Repeated `POST /api/demo/sessions/` returns `429` before a second tenant exists.
- [ ] A demo guest hitting `LessonPlan` create is throttled before quota fires.
- [ ] MCP HTTP returns `429` past its per-token rate when `MCP_HTTP_ENABLED`.
- [ ] Reap removes an expired `teacher_full`-shaped tenant with no `ProtectedError`.
- [ ] `DEMO_DEPLOY` + `DEBUG=True` fails boot; posture written in `.env.example` and roadmap Q4.
- [ ] `showcase` renders grounding ✓/⚠ and provenance with zero generations.
- [ ] `uv run pytest` green; `makemigrations --check` clean.

## Proposal question round

Auto mode — interactive asking was unavailable. Assumptions needing review:

1. **Hosting posture** — assumed `DEMO_DEPLOY` + hardening is in P6. Alternative:
   a written local-only decision in Q4 with `DEMO_DEPLOY` as a named follow-up,
   dropping slice 3.
2. **Rates** — assumed `create` 5/h/IP, `poll` 120/h/IP, `personas` 60/h/IP,
   demo generate 3/h, teacher generate 30/h. Confirm or set business numbers.
3. **TTL** — assumed 24h default (longer locally), hourly reap. Confirm no demo
   tenant must survive for a sales call.
4. **Cost/latency deferral** — assumed grounding + provenance meets the exit
   gate without P3 columns.
5. **MCP HTTP throttle** — assumed in, per P4's gate. Confirm not deferred again.
