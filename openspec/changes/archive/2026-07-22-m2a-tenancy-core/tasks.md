# Tasks: M2a — Tenancy Foundation Core

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1500-1900 across D1-D9 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | D1 → D2 → D3 → D4 → D5 → D6 → D7 → D8 → D9 (9 local commits) |
| Delivery strategy | auto-chain |
| Chain strategy | local-commits (no remote; sequential commits on `m2a-tenancy-core`) |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

No GitHub PRs exist for this repo; each delivery below is one local commit on branch `m2a-tenancy-core`, applied in order. `auto-chain` resolves the decision automatically — `sdd-apply` proceeds delivery by delivery without asking.

### Suggested Work Units

| Unit | Goal | Commit | Focused test command | Runtime harness | Rollback boundary |
|------|------|--------|----------------------|-----------------|-------------------|
| D1 | Django scaffold boots, migrates clean | `backend/` scaffold | `cd backend && pytest` | `python manage.py migrate --check` | `git revert` D1; no dependents yet |
| D2 | Custom user model, session auth | users app | `pytest backend/users` | `python manage.py migrate --check` | drop DB + remigrate (irreversible per design) |
| D3 | Workspace/Membership models | workspaces models | `pytest backend/workspaces/tests/test_models.py` | `manage.py migrate --check` | `manage.py migrate workspaces zero` |
| D4 | Atomic signup provisioning | services.py | `pytest backend/workspaces/tests/test_services.py` | Django test client signup call | delete `services.py`, D3 unaffected |
| D5 | Scoped manager + contextvar | context.py/managers.py | `pytest backend/workspaces/tests/test_managers.py` | shell: set contextvar, query | delete files, models fall back to default manager |
| D6 | Capability matrix + DRF permission | permissions.py | `pytest backend/workspaces/tests/test_permissions.py` | N/A — pure unit, no external harness needed | delete `permissions.py` |
| D7 | RLS middleware + SET LOCAL | middleware.py | `pytest backend/workspaces/tests/test_middleware.py` | Django test client with `X-Workspace-Id` header | remove middleware from `MIDDLEWARE` list |
| D8 | RLS policies + app role | migration + role | `pytest backend/workspaces/tests/test_rls.py` | `manage.py migrate workspaces --check`; connect as `portal_app` | `manage.py migrate workspaces <prev>` (reversible RunSQL) |
| D9 | Cross-tenant leak test under pooling | leak test | `pytest backend/workspaces/tests/test_pooling_leak.py` | single-connection reuse harness (test-only) | test-only; no production rollback |

## Phase D1: chore: scaffold Django project

- [x] 1.1 Create `backend/pyproject.toml` — uv project `portal-nem-backend`, deps: django, djangorestframework, drf-spectacular, psycopg, pgvector.
- [x] 1.2 Create `backend/manage.py`, `backend/config/{settings.py,urls.py,wsgi.py,asgi.py}` — `ATOMIC_REQUESTS=True`, DRF + spectacular installed apps, two-role DB config (owner vs `portal_app`, env-switched).
- [x] 1.3 Fix `README.md` — remove dropped FastAPI row from stack table.
- [x] 1.4 RED: `backend/tests/test_scaffold.py` — asserts `manage.py migrate --check` succeeds and Django settings import cleanly.
- [x] 1.5 GREEN: run `python manage.py migrate` clean, `pytest` passes.
- [x] 1.6 Commit: `chore: scaffold Django project`.

## Phase D2: feat(users): custom email user model

- [x] 2.1 RED: `backend/users/tests/test_models.py` — email-as-identifier scenario, duplicate-email-rejected scenario (spec identity-auth).
- [x] 2.2 GREEN: `backend/users/models.py` — custom `User` (email, no username), `UserManager`; set `AUTH_USER_MODEL = "users.User"` in `config/settings.py` BEFORE first migration.
- [x] 2.3 RED: `backend/users/tests/test_auth.py` — httpOnly session cookie scenario, CSRF-rejection scenario, unauthenticated-denied scenario.
- [x] 2.4 GREEN: configure session-cookie auth (`SESSION_COOKIE_HTTPONLY=True`, CSRF middleware, DRF `SessionAuthentication`).
- [x] 2.5 Generate `users/migrations/0001_initial.py`; verify no default `auth.User` table created.
- [x] 2.6 Commit: `feat(users): custom email user model`.

## Phase D3: feat(workspaces): Workspace + Membership models

- [x] 3.1 RED: `backend/workspaces/tests/test_models.py` — Workspace `type` choices-rejection scenario, Membership `role` choices-rejection scenario.
- [x] 3.2 GREEN: `backend/workspaces/models.py` — `Workspace(type: personal|group)`, `Membership(role: TextChoices owner/admin/member, CharField)`, `ScopedModel` abstract base (workspace_id FK).
- [x] 3.3 Generate `workspaces/migrations/0001_initial.py`.
- [x] 3.4 Commit: `feat(workspaces): Workspace + Membership models`.

## Phase D4: feat(workspaces): transactional signup provisioning

- [x] 4.1 RED: `backend/workspaces/tests/test_services.py` — successful-signup scenario (User+Workspace+Membership exist), failure-during-provisioning rollback scenario (no partial state).
- [x] 4.2 GREEN: `backend/workspaces/services.py` — `provision_signup(email, password)` wrapped in `transaction.atomic()`.
- [x] 4.3 Commit: `feat(workspaces): transactional signup provisioning`.

## Phase D5: feat(workspaces): workspace-scoped manager

- [x] 5.1 RED: `backend/workspaces/tests/test_managers.py` — query-scoped-to-active-workspace scenario, no-context-denies-all scenario (fail-closed `.none()`).
- [x] 5.2 GREEN: `backend/workspaces/context.py` — `WORKSPACE_UNSET` sentinel, `active_workspace: ContextVar`.
- [x] 5.3 GREEN: `backend/workspaces/managers.py` — `ScopedQuerySet`/`ScopedManager.get_queryset()` reading contextvar, `.none()` on sentinel; wire into `ScopedModel`.
- [x] 5.4 Commit: `feat(workspaces): workspace-scoped manager`.

## Phase D6: feat(workspaces): capability matrix + DRF permission

- [x] 6.1 RED: `backend/workspaces/tests/test_permissions.py` — owner-permitted scenario, member-denied scenario, DRF-permission-class-delegates scenario (asserts no inline `membership.role == "..."` comparison in the class).
- [x] 6.2 GREEN: `backend/workspaces/permissions.py` — `CAPABILITIES: dict[str, frozenset[str]]`, `has_permission(membership, action)`, `WorkspacePermission(BasePermission)` calling `has_permission` only.
- [x] 6.3 Commit: `feat(workspaces): capability matrix + DRF permission`.

## Phase D7: feat(workspaces): RLS middleware + SET LOCAL wiring

- [x] 7.1 RED: `backend/workspaces/tests/test_middleware.py` — header-resolves-membership scenario, missing-header-falls-back-to-personal scenario, header-present-not-member-403 scenario, unauthenticated-sentinel scenario, `SET LOCAL` issued inside per-request txn scenario, setting does not persist past txn scenario.
- [x] 7.2 GREEN: `backend/workspaces/middleware.py` — `TenancyMiddleware`: resolve `X-Workspace-Id` → membership lookup → `active_workspace.set(id)` → `set_config('app.workspace_id', str(id), True)` inside the open `ATOMIC_REQUESTS` txn → `finally: active_workspace.reset(token)`; register in `config/settings.py` `MIDDLEWARE`.
- [x] 7.3 Commit: `feat(workspaces): RLS middleware + SET LOCAL wiring`.

## Phase D8: feat(workspaces): RLS policies + restricted app role

- [x] 8.1 RED: `backend/workspaces/tests/test_rls.py` — RLS-policy-blocks-foreign-row scenario (raw cursor, current_setting predicate), app-role-lacks-bypassrls scenario (`rolbypassrls=false` via `pg_roles`).
- [x] 8.2 GREEN: `backend/workspaces/migrations/000X_rls.py` — reversible `RunSQL`: `ENABLE ROW LEVEL SECURITY`, `CREATE POLICY ws_isolation ... USING/WITH CHECK (workspace_id = current_setting('app.workspace_id', true)::uuid)` per scoped table; reverse drops policies + disables RLS.
- [x] 8.3 GREEN: create `portal_app` Postgres role (`NOSUPERUSER NOBYPASSRLS`), `GRANT` table/sequence privileges; wire runtime `DATABASES['default']` to connect as `portal_app`, migrations run as owner role.
- [x] 8.4 Commit: `feat(workspaces): RLS policies + restricted app role`.

## Phase D9: test(workspaces): cross-tenant leak test under pooling

- [x] 9.1 RED: `backend/workspaces/tests/test_pooling_leak.py` — reused-connection-switched-context-denies-foreign-rows scenario (positive control: `SET LOCAL`, single connection, two sequential txns/workspaces; asserts both scoped QuerySet and raw RLS query deny foreign rows).
- [x] 9.2 RED (same file): negative-control-plain-SET-demonstrates-leak scenario (plain `SET`, same connection, no reset → asserts leak occurs, proving the test can detect it) plus an assertion that production code path uses `SET LOCAL` not plain `SET` (grep/inspect `middleware.py`).
- [x] 9.3 GREEN: no production code change expected (D5-D8 already implement the safe path); fix any gap the test surfaces.
- [x] 9.4 Commit: `test(workspaces): cross-tenant leak test under pooling`.
