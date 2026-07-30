# Design: Quizzy P6 — Demo hardening, then the showcase persona

## Technical Approach

Four additive, schema-free slices. A Redis `CACHES["default"]` lands first so DRF
throttle counters are shared across gunicorn/celery processes; scoped rates then
attach per view. TTL reap derives expiry from `DemoSession.created_at` + a setting
(no migration) and deletes leaf-first inside `workspace_scope`. `DEMO_DEPLOY` is an
additive second key to `demo_mode.enabled()` plus a pure hardening validator called
from `settings.py`. The showcase persona is one `DemoProvisioner` subclass and one
`_REGISTRY` entry, reusing the existing proyecto fixtures.

## Architecture Decisions

| # | Decision | Choice | Rejected | Rationale |
|---|---|---|---|---|
| 1 | Cache backend | `django.core.cache.backends.redis.RedisCache`, `REDIS_CACHE_URL` default `redis://localhost:6379/1` | LocMem; broker db 0 | Built-in since Django 4, no new dep. Separate db keeps throttle keys out of the broker namespace. |
| 2 | Cache under pytest | `LocMemCache` when `PYTEST_VERSION in os.environ` + autouse `cache.clear()` in new `backend/conftest.py` | Real Redis in CI | Mirrors the existing `CELERY_TASK_ALWAYS_EAGER` block. Without the clear, LocMem counters leak between tests and existing demo API tests start 429-ing. |
| 3 | Throttle wiring | Per-view `ScopedRateThrottle` + rates in `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`. `DEFAULT_THROTTLE_CLASSES` stays absent | Global default classes | Rates in one place; zero blast radius on untouched endpoints. |
| 4 | Generation throttle class home | `core/throttling.py::GenerationRateThrottle(SimpleRateThrottle)`, function-level import of `demo.identity.is_demo_guest` | Class in `lesson_plans/` importing `demo` | `demo` already imports `lesson_plans`; a module-level reverse import inverts the layering. Deferred import matches `config/urls.py:52`. |
| 5 | Demo-guest detection | `DemoSession.objects.filter(user_id=…, status=READY).exists()` (indexed FK) | `email.startswith("demo+")`; new `is_demo` column | Authoritative, no migration, no string matching. One indexed SELECT on a path that is about to call an LLM. |
| 6 | MCP HTTP limiter | `mcp_server/throttling.py::McpHttpTokenThrottle(SimpleRateThrottle)` keyed on `sha256(bearer)`, called from `mcp_http_view` **after** the 401 gate | Hand-rolled window; throttle before auth | Reuses DRF rate parsing/`wait()` from a plain Django view. Auth-first keeps P4's "unknown and revoked are byte-identical" property and only ever counts real identities. |
| 7 | Reap split | pure `demo/reaping.py::reap_expired_demo_sessions(now=None) -> int` + thin `demo/tasks.py::reap_expired_demo_sessions_task` | Logic in the task | Same services/tasks split as `lesson_plans`; reap is testable with no broker. |
| 8 | Beat schedule | `CELERY_BEAT_SCHEDULE = {"reap-expired-demo-sessions": {"task": "demo.tasks.reap_expired_demo_sessions_task", "schedule": crontab(minute=0)}}` in `settings.py` | `django-celery-beat` | One job, no new app or migration. `crontab` import is Django-free. |
| 9 | Hardening validator | `demo_mode.validate_deploy_hardening(*, debug, allowed_hosts, secret_key, caches, session_cookie_secure, csrf_cookie_secure)` — pure, args passed explicitly from the tail of `settings.py` | Reading `django.conf.settings` inside the validator | The values it checks are defined after the existing line-41 guard; explicit args avoid settings-during-construction entirely and make it a unit test. Existing `validate()` is untouched, so current gate tests stay green. |
| 10 | Showcase fixtures | Reuse `proyecto_demo.json` / `proyecto_lenguajes.json` | New fixture files | Zero new fixture bytes; the ⚠ recipe below already has a real off-selection PDA in the lenguajes field. |

## Throttle scopes

| Scope | Attached to | Rate | Key |
|---|---|---|---|
| `demo_personas` | `DemoPersonaListView` | `60/hour` | IP |
| `demo_session_create` | `DemoSessionCreateView` | `5/hour` | IP |
| `demo_session_poll` | `DemoSessionDetailView` | `120/hour` | IP |
| `lesson_plan_generate_demo` | `LessonPlanViewSet.create` (demo guest) | `3/hour` | user pk |
| `lesson_plan_generate` | `LessonPlanViewSet.create` (teacher) | `30/hour` | user pk |
| `mcp_http` | `mcp_http_view` | `60/min` | `sha256(bearer)` |

`LessonPlanViewSet` scopes only `create`: `get_throttles()` returns
`[GenerationRateThrottle()]` when `self.action == "create"`, else `[]`.

## Data Flow — reap

    beat (hourly) ──→ reap_expired_demo_sessions_task ──→ reaping.reap_expired_demo_sessions
                                                                    │
      DemoSession.created_at < now - TTL ─────────────────────────────┘
                                                                    │
      per session: capture (workspace_id, user_id) ──→ workspace_scope(ws.id):
          LessonPlan → Student → GenerationUsage → Group → SchoolYear → School
          → workspace.delete()   # cascades Membership + DemoSession
      then, outside scope: user.delete() if no memberships and no sent_invitations

Everything runs **inside** the scope, including `workspace.delete()`: `_base_manager`
is unfiltered so Django's collector sees the rows, but RLS still filters the DELETE
for the `runtime` role — an unscoped cascade would no-op in a deploy while passing
locally under the owner role. Leaf-first is required because `Student.group` and
`LessonPlan.group` are `PROTECT`. Sessions with no workspace (`pending`/`failed`)
are deleted directly.

## DEMO_DEPLOY contract

`enabled()` becomes `DEMO_MODE ∧ (DEBUG ∨ DEMO_DEPLOY)`. Boot rejections, in order:

1. `DEMO_MODE ∧ ¬DEBUG ∧ ¬DEMO_DEPLOY` → `ProductionNotAllowed` (unchanged).
2. `DEMO_DEPLOY ∧ DEBUG` → `DebugNotAllowedInDemoDeploy`.
3. `DEMO_DEPLOY` and any of: default `SECRET_KEY`, `ALLOWED_HOSTS` containing `*`
   or left at the localhost default, non-Redis `CACHES["default"]`,
   `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` false → `DemoDeployNotHardened`.
4. `DEMO_DEPLOY ∧ ¬DEMO_MODE` → `DemoDeployNotHardened` (flag without a surface).

`DEMO_DEPLOY` also forces `SPECTACULAR_SETTINGS["SERVE_INCLUDE_SCHEMA"] = False`
and drops the browsable renderer. Celery beat is contractual, not enforced at boot
(documented in `.env.example` and roadmap Q4).

## Showcase seed shape

`demo/provisioning/showcase.py::Showcase`, `persona_key = "showcase"`. Seeds school +
ciclo + one grupo `1°A` + 10 students via the services layer, then two `LessonPlan`
rows written directly (`TeacherFull`'s documented exception):

| Plan | Fixture | Grounding | Provenance |
|---|---|---|---|
| clean | `proyecto_demo.json` | `invented_pdas=False`, `invented_pda_texts=[]`, `grounding_selections=[{"content": …, "pdas": [...]}]` | `provider="anthropic"`, `model_name`, `prompt_tokens`, `completion_tokens`, `generated_at` |
| warning | `proyecto_lenguajes.json` | `invented_pdas=True`, `invented_pda_texts=[<verbatim off-selection PDA>]`, `grounding_selections` = the `languages-accentuation` group only | same |

The ⚠ recipe is the deterministic one the P1 exit gate already used: select
`languages-accentuation`, leave `languages-coherent-texts` outside the selection.
`cost_micros` / `duration_ms` do not exist yet — deferred to P3, per proposal.

## File Changes

| File | Action | Description | Slice |
|---|---|---|---|
| `backend/config/settings.py` | Modify | `CACHES` (+ pytest LocMem), `DEFAULT_THROTTLE_RATES`, `DEMO_SESSION_TTL_HOURS`, `CELERY_BEAT_SCHEDULE`, `DEMO_DEPLOY`, hardening call | 1–3 |
| `backend/conftest.py` | Create | Autouse `cache.clear()` so throttle counters never leak between tests | 1 |
| `backend/core/throttling.py` | Create | `GenerationRateThrottle` — demo/teacher scope selection | 1 |
| `backend/demo/identity.py` | Create | `is_demo_guest(user)` via `DemoSession` | 1 |
| `backend/demo/views.py` | Modify | `throttle_classes = [ScopedRateThrottle]` + `throttle_scope` on all three views | 1 |
| `backend/lesson_plans/viewsets.py` | Modify | `get_throttles()` for `create` only; `429` already documented | 1 |
| `backend/mcp_server/throttling.py` | Create | `McpHttpTokenThrottle` keyed on bearer hash | 1 |
| `backend/mcp_server/http.py` | Modify | Throttle check after the 401 gate; `429` + `Retry-After` | 1 |
| `backend/demo/reaping.py` | Create | Leaf-first delete under `workspace_scope` | 2 |
| `backend/demo/tasks.py` | Modify | `reap_expired_demo_sessions_task` wrapper | 2 |
| `backend/config/demo_mode.py` | Modify | `DEMO_DEPLOY` in `enabled()`; `validate_deploy_hardening` + two new exceptions | 3 |
| `.env.example` | Modify | `REDIS_CACHE_URL`, `DEMO_SESSION_TTL_HOURS`, `DEMO_DEPLOY` + posture block | 3 |
| `docs/quizzy_roadmap.md` | Modify | Resolve open Q4 | 3 |
| `backend/demo/provisioning/showcase.py` | Create | `Showcase` provisioner | 4 |
| `backend/demo/personas.py` | Modify | Fourth `_REGISTRY` entry | 4 |
| `backend/demo/tests/test_api.py` | Modify | Persona-key assertion at `:37` gains `"showcase"` | 4 |
| `backend/demo/tests/test_throttling.py` | Create | Per-scope 429s; a full provision cycle survives the poll rate | 1 |
| `backend/lesson_plans/test_throttling.py` | Create | Demo guest 429s before quota; teacher unaffected | 1 |
| `backend/mcp_server/tests/test_http_throttle.py` | Create | Per-token 429; distinct tokens are independent | 1 |
| `backend/demo/tests/test_reaping.py` | Create | `teacher_full`-shaped tenant reaped, no `ProtectedError`; fresh tenant untouched | 2 |
| `backend/config/tests/test_demo_deploy.py` | Create | Each boot rejection; `enabled()` truth table | 3 |
| `backend/demo/tests/test_provisioning_showcase.py` | Create | Grounding ✓/⚠ + provenance, zero `GenerationUsage` | 4 |

## Interfaces

```python
# core/throttling.py
class GenerationRateThrottle(SimpleRateThrottle):
    scope = "lesson_plan_generate"
    demo_scope = "lesson_plan_generate_demo"
    def get_cache_key(self, request, view) -> str | None: ...  # sets self.scope, then super()

# demo/reaping.py
def reap_expired_demo_sessions(now: datetime | None = None) -> int: ...

# config/demo_mode.py
def validate_deploy_hardening(*, debug, allowed_hosts, secret_key, caches,
                              session_cookie_secure, csrf_cookie_secure) -> None: ...
```

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | Rate parsing, scope selection, `is_demo_guest`, hardening validator, deletion order | pytest, no HTTP; validator called with explicit args |
| Integration | 429 on each scope, provision cycle through the poll rate, reap of a `teacher_full` tenant, showcase render | `APIClient` + `django_capture_on_commit_callbacks`, `cache.clear()` per test |
| E2E | Live smoke (P0 re-run) with Redis + `celery worker` + `celery beat` | Manual, per roadmap Verification |

Strict TDD (`openspec/config.yaml` `apply.tdd: true`): RED before each production change.

## Threat Matrix

N/A — no shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. HTTP route mounting changes, but it changes only
*whether* an existing URLconf block registers; no user-controlled routing input.

## Migration / Rollout

No migration. Expiry is derived from `created_at`, so `makemigrations --check` stays
clean. Slices 1–2 roll back by deleting the throttle scopes / beat entry; slice 3 by
leaving `DEMO_DEPLOY` unset; slice 4 by removing the `_REGISTRY` entry. Any
`DEMO_DEPLOY` host MUST run `celery beat` or the TTL is inert.

## Open Questions

- [ ] Slice 1 carries three surfaces (demo, generation, MCP) and may exceed 400
      lines. Fallback: split into **1a** (Redis `CACHES`, conftest, demo scopes) and
      **1b** (generation + MCP scopes). Decide at `sdd-tasks` forecast.
- [ ] Rates in the table are the proposal's assumed numbers, not confirmed business
      numbers (proposal question 2).
- [ ] Auth-before-throttle on the MCP mount leaves a bad-token flood paying one
      sha256 + one indexed SELECT per request. Accepted for P6; an IP-keyed
      pre-auth limiter is the follow-up if it ever matters.
