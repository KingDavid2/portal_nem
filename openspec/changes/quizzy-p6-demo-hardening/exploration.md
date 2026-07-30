# Exploration: quizzy-p6-demo-hardening

Change: `quizzy-p6-demo-hardening` · Project: `portal_nem` · Phase: explore

Make the demo link safe to hand to a stranger: throttle unauthenticated (and
generation) surfaces, expire demo tenants, decide hosting posture explicitly,
then add a showcase persona that renders grounding/provenance without calling
the LLM. Authoritative intent: `docs/quizzy_roadmap.md` §Phase 6.

## Current State

### Demo surface (M5)

- Three `AllowAny` / `authentication_classes = []` views in `demo/views.py`:
  personas list, session create (`202` + Celery provision), session poll (signs
  guest in when `ready`).
- Routes mount **only** when `demo_mode.enabled()` (`config/urls.py:45-46`) —
  absence ⇒ 404.
- `demo_mode.enabled()` requires `DEBUG` and `DEMO_MODE` truthy; boot aborts if
  `DEMO_MODE` is set with `DEBUG` off (`config/demo_mode.py`,
  `settings.py:36-41`).
- Personas: frozen `_REGISTRY` in `demo/personas.py` —
  `teacher_minimal` | `teacher_full` | `quota_exhausted`. New persona =
  subclass `DemoProvisioner` + one registry entry; serializer
  `ChoiceField(choices=personas.keys())` picks it up automatically.
- `TeacherFull` seeds school/ciclo/2 grupos/20 alumnos + 2 ready `LessonPlan`
  rows **directly** (bypass services/LLM). `QuotaExhausted` extends that and
  writes `GenerationUsage` at `monthly_limit()`.
- Provisioning task: `demo/tasks.py::provision_demo_session_task` only — no
  cleanup/reap task exists. `DemoSession` has `created_at` but no TTL/expiry
  column.

### Throttling

- `REST_FRAMEWORK` (`settings.py:182-190`) has **no**
  `DEFAULT_THROTTLE_CLASSES` / rates. Zero project-wide throttle usage.
- No `CACHES` setting — DRF throttles would fall back to LocMemCache (per-process;
  broken across gunicorn/celery workers for a public demo).
- Generation path after demo login is authenticated
  `LessonPlanViewSet.create` — monthly quota only (`GenerationQuotaExceeded`),
  not rate-limited. `teacher_minimal` guests can burn GPU via that path.
- P4 archive explicitly gated **HTTP-arm throttling to P6**
  (`openspec/changes/archive/2026-07-30-quizzy-p4-mcp-server/proposal.md`).
  MCP HTTP (`mcp_server/http.py`) is Bearer-auth, flag-gated
  (`MCP_HTTP_ENABLED`, default off); still unthrottled when on.

### Cleanup / Celery beat

- Celery app exists (`config/celery.py`); Redis broker; eager under pytest.
- **No** `CELERY_BEAT_SCHEDULE`, no `django-celery-beat`, no periodic tasks
  anywhere in the repo.
- `PROTECT` FKs: `Student.group`, `LessonPlan.group`. `ScopedModel.workspace`
  is `CASCADE`. Naive `group.delete()` / school-year cascade **raises
  `ProtectedError`** while leaves exist (already tested).
- Cleanup hazard: `ScopedManager` is fail-closed (no active workspace ⇒
  `.none()`). A reap task that deletes scoped rows **must**
  `workspace_scope(ws.id)` per tenant (or use `_base_manager` carefully).
  Prefer explicit leaf-first deletes under scope, then `workspace.delete()`,
  then demo user / `DemoSession`.
- Also mind `WorkspaceInvitation.invited_by` `PROTECT` if deleting the demo
  `User` — demo provisioners do not create invitations today.

### Grounding / provenance for showcase

- P1 landed: `invented_pdas`, `invented_pda_texts`, `grounding_selections`,
  plus `provider` / `model_name` / `prompt_tokens` / `completion_tokens` /
  `generated_at`. Viewer/export already render grounding ✓/⚠.
- **P3 not landed:** no `duration_ms`, `cost_micros`, `prompt_version`,
  `failure_kind` columns. Roadmap P6 text says “cost and latency populated”
  — those columns do not exist yet. Soft dependency on P3 or a scoped
  compromise for the persona seed.

### Tests already in place

- `demo/tests/`: models, personas, urls conditional, API, tasks,
  provisioning, provisioning_personas. No throttle or reap coverage.
- Persona list assertion hardcodes the three keys
  (`test_api.py:37`) — adding a showcase persona requires updating that.

## Affected Areas

- `backend/demo/views.py` — add `throttle_classes` / `throttle_scope`
- `backend/demo/tasks.py` — add reap task; keep provision task
- `backend/demo/personas.py` + `demo/provisioning/` — showcase provisioner +
  registry entry; likely new fixtures for grounded / warning plans
- `backend/demo/models.py` — optional TTL helper; `created_at` may suffice
- `backend/config/settings.py` — throttle rates, `CACHES` (Redis), beat
  schedule, `DEMO_SESSION_TTL_*`, hosting flag if chosen
- `backend/config/demo_mode.py` — `DEMO_DEPLOY` or documented local-only
- `backend/config/urls.py` — mount conditions if deploy flag changes gate
- `backend/lesson_plans/viewsets.py` — generation-path throttle (not just demo
  POST)
- `backend/mcp_server/http.py` — adjacent P4 carry-forward throttle (scope
  decision)
- `.env.example` + docs (`quizzy_roadmap.md` open Q4) — hosting posture
- `backend/demo/tests/*` — throttle, reap/PROTECT order, new persona

## Approaches

### A. Throttling

1. **Scoped demo AnonRateThrottle only (session create + poll + personas)**
   - Pros: Matches roadmap wording literally; low blast radius.
   - Cons: Misses the real GPU path after `django_login` (authenticated
     create). Incomplete vs exit gate.
   - Effort: Low

2. **Demo AnonRateThrottle + generation UserRateThrottle / custom IP scope
   on `LessonPlanViewSet.create`**
   - Pros: Covers both surfaces roadmap calls out; IP scope still bites
     guests who share no user history.
   - Cons: Generation throttle affects all teachers unless scoped carefully
     (e.g. `throttle_scope = "lesson_plan_generate"` with a generous prod
     rate, or only when `demo_mode.enabled()` / email matches `demo+…`).
   - Effort: Medium — **recommended**

3. **Global DEFAULT_THROTTLE_CLASSES**
   - Pros: One place.
   - Cons: Surprises every API; overbroad for P6.
   - Effort: Low but wrong blast radius

### B. Cleanup

1. **`CELERY_BEAT_SCHEDULE` in settings + `reap_expired_demo_sessions` task**
   - Pros: No new dependency; Redis already present; matches existing Celery
     style.
   - Cons: Requires a running `celery beat` process in any deploy that
     enables demo; document in posture.
   - Effort: Medium — **recommended**

2. **`django-celery-beat` DB schedules**
   - Pros: Runtime-editable.
   - Cons: New app/migration; overkill for one TTL job.
   - Effort: Medium–High

3. **Management command only (cron outside app)**
   - Pros: Simplest code.
   - Cons: Easy to forget in demo deploys; weaker as an in-repo guarantee.
   - Effort: Low

**Deletion order (required either way):** under `workspace_scope`, delete
`LessonPlan` → `Student` → (optional explicit Group/SchoolYear/School) →
delete `Workspace` → delete demo `User` if unused → delete `DemoSession`
(or let FK CASCADE from workspace/user where safe). Assert no
`ProtectedError` in tests with a `teacher_full`-shaped tenant.

### C. DEBUG / hosting posture

1. **`DEMO_DEPLOY` flag (DEBUG=False allowed) + hardening checklist**
   - Harden: throttles required, TTL reap required, Redis-backed `CACHES`,
     `SECURE_*` / HTTPS cookies, tight `ALLOWED_HOSTS`, disable browsable
     API / schema UI in that mode, never pair with `DEBUG=True`.
   - Pros: Matches phase goal (“hand to a stranger”); resolves Q4
     explicitly.
   - Cons: Larger slice; must not weaken the current DEBUG∧DEMO_MODE local
     path.
   - Effort: Medium–High — **recommended if public demo is in-scope for P6**

2. **Record local-only; keep DEBUG gate**
   - Pros: Smallest change; honest about DEBUG leaks.
   - Cons: Contradicts “hand to a stranger” until a later change; still
     must write the posture down.
   - Effort: Low

### D. Showcase persona vs P3

1. **Seed P1 grounding + existing provenance only; defer cost/latency to P3**
   - Pros: Unblocks P6 without pulling P3 schema; exit gate’s
     “grounding and provenance” still holds with today’s serializer.
   - Cons: Softens roadmap’s “cost and latency populated” sentence.
   - Effort: Low–Medium — **recommended for P6**

2. **Land minimal `duration_ms` / `cost_micros` columns inside P6 for seed**
   - Pros: Literal roadmap compliance.
   - Cons: Scope creep into P3; pricing module still missing; chained-PR
     budget risk.
   - Effort: High

### E. MCP HTTP throttle (P4 carry-forward)

1. **In P6 as a thin adjacent task** — rate-limit the HTTP mount when
   `MCP_HTTP_ENABLED` (Bearer ≠ Anon; use scoped rate or cache key on token
   hash). Effort Low–Medium.
2. **Explicit defer** with written carry-forward — if review budget is
   tight. Effort none now, risk remains.

## Recommendation

Ship P6 as **four stacked slices** under force-chained / 400-line budget:

1. **Throttle + shared Redis cache** — `AnonRateThrottle` on all three demo
   views; scoped rate on lesson-plan **create** (demo-aware or generous
   generate scope); note MCP HTTP as same-slice or immediate follow-on.
2. **TTL reap** — `CELERY_BEAT_SCHEDULE` + leaf-first delete under
   `workspace_scope`; setting `DEMO_SESSION_TTL_HOURS` (suggest 24h default
   for deploy, longer locally).
3. **Hosting posture** — prefer **`DEMO_DEPLOY` + hardening** so the phase
   goal is achievable; if slice 3 blows the budget, land a written
   **local-only** decision in roadmap Q4 and keep `DEMO_DEPLOY` as a named
   follow-up — but do not leave it implicit.
4. **Showcase persona** — `DemoProvisioner` subclass seeding one clean
   grounded plan and one with `invented_pdas=True` +
   `invented_pda_texts` / `grounding_selections`, plus
   `provider`/`model_name`/token fields and `generated_at`. Document that
   `cost_micros`/`duration_ms` wait for P3. Direct `LessonPlan.objects.create`
   like `TeacherFull`.

## Risks

- **Authenticated generation bypasses Anon throttle** if slice 1 only
  touches demo views — GPU still free.
- **LocMemCache** makes throttle ineffective across workers unless Redis
  `CACHES` is configured.
- **PROTECT + fail-closed ScopedManager** — naive `workspace.delete()` /
  unscoped ORM deletes can no-op or raise; reap tests must use a full
  `teacher_full` tenant.
- **No celery beat today** — TTL is inert without an ops process; posture
  docs must require it for any public demo.
- **P3 field gap** — “cost and latency populated” cannot be literal without
  schema work; must decide at propose.
- **Persona list test hardcodes keys** — easy miss when adding showcase.
- **MCP HTTP still unthrottled** if deferred again after P4’s explicit P6
  gate.
- **`DEMO_DEPLOY` + DEBUG=True** must be forbidden (same class of boot
  guard as today’s DEMO_MODE∧!DEBUG).

## Ready for Proposal

Yes. Orchestrator should run `sdd-propose` for `quizzy-p6-demo-hardening`
and lock: (1) generation-path throttle scope, (2) local-only vs
`DEMO_DEPLOY`, (3) P3 cost/latency soft-defer vs pull-forward, (4) MCP HTTP
throttle in/out of this change.
