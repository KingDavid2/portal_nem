# Apply Progress: M2a — Tenancy Foundation Core

**Mode**: Strict TDD (RED → GREEN → REFACTOR)
**Branch**: `m2a-tenancy-core` (no remote; local sequential commits per delivery)
**Status**: ALL DELIVERIES DONE (D1-D9). `state.yaml` `phases.apply` → `done`, `next_recommended` → `verify`.

## Batch 2 (D4-D9) — this update

Batch scope: D4, D5, D6, D7, D8, D9 — completes M2a. Continues directly from
the Batch 1 state below (D1-D3 already committed). Full suite green after
every delivery; `python manage.py migrate --check` clean throughout.

### Commits (Batch 2)

| Delivery | Commit | Subject |
|----------|--------|---------|
| D4 | `a8ba05d` | `feat(workspaces): transactional signup provisioning` |
| D5 | `e7737eb` | `feat(workspaces): workspace-scoped manager` |
| D6 | `003b0d8` | `feat(workspaces): capability matrix and DRF permission` |
| D7 | `420e263` | `feat(workspaces): RLS middleware and SET LOCAL wiring` |
| D8 | `3772e64` | `feat(workspaces): RLS policies and restricted app role` |
| D9 | `b201dbb` | `test(workspaces): cross-tenant leak test under pooling` |

Full delivery chain: `ef7fc31` (D1) → `60e36ac` (D2) → `1fff304` (D3) →
`a8ba05d` (D4) → `e7737eb` (D5) → `003b0d8` (D6) → `420e263` (D7) →
`3772e64` (D8) → `b201dbb` (D9).

### D4 — transactional signup provisioning

`workspaces/services.py::provision_signup(email, password)` wraps
Workspace-then-User-then-Membership creation in one `transaction.atomic()`.
Forced failure = pre-existing duplicate email, which makes the internal
`User.objects.create_user(...)` raise `IntegrityError` **after** the
Workspace row was already created in the same atomic block — proving the
whole transaction rolls back (not just the failing step). Order was
deliberately chosen (Workspace before User) so the rollback test actually
exercises rollback of an already-created row, not just "nothing was created
because the first step failed."

- RED: `ModuleNotFoundError: No module named 'workspaces.services'`.
- GREEN: `pytest workspaces/tests/test_services.py -v` → 2 passed.

### D5 — workspace-scoped manager

`workspaces/context.py`: `WORKSPACE_UNSET = object()` sentinel,
`active_workspace: ContextVar` (module-level, default = sentinel).
`workspaces/managers.py`: `ScopedQuerySet._scoped()` returns `.none()` when
`active_workspace.get() is WORKSPACE_UNSET`, else `.filter(workspace_id=ws)`;
`ScopedManager.get_queryset()` calls it. `ScopedModel.objects = ScopedManager()`.
Test used a throwaway concrete `ScopedProbe(ScopedModel)` model whose table
is created/dropped via `connection.schema_editor()` inside a fixture (no
migration needed — Postgres DDL is transactional, so pytest-django's
per-test rollback also undoes the `CREATE TABLE`). `.create()` bypasses the
filtered *read* path (Django's `QuerySet.create()` doesn't depend on
`get_queryset()` filtering), so test setup succeeds even with no context set.

- RED: `.none()`-denial assertion failed (returned the row) +
  `ModuleNotFoundError: No module named 'workspaces.context'`.
- GREEN: `pytest workspaces/tests/test_managers.py -v` → 2 passed.

### D6 — capability matrix + DRF permission

`workspaces/permissions.py`: `CAPABILITIES: dict[str, frozenset[str]]`
(owner/admin/member), `has_permission(membership, action) -> bool` (unknown
role → `CAPABILITIES.get(role, frozenset())` → deny), `WorkspacePermission
(BasePermission)` whose `has_object_permission` calls `has_permission` only.
Gate #4 (no inline `membership.role == "..."` comparisons) verified by a
dedicated test that `inspect.getsource()`s the module and asserts
`".role =="` / `".role !="` are absent — first run false-failed because the
module's own *docstring* mentioned the literal pattern in prose; fixed by
rewording the docstring (not weakening the assertion). Repo-wide grep after
GREEN confirms `.role ==` appears only in test assertion files, never in
`workspaces/*.py` production code.

- RED: `ModuleNotFoundError: No module named 'workspaces.permissions'` (all 5 tests).
- GREEN: `pytest workspaces/tests/test_permissions.py -v` → 5 passed.

### D7 — RLS middleware + SET LOCAL wiring

`workspaces/middleware.py::TenancyMiddleware`: unauthenticated → pass
through untouched (sentinel stays unset downstream). `X-Workspace-Id`
header present → membership lookup by `(user, workspace_id)`; not a member
→ `403 JsonResponse` (fail-closed, no silent fallback). Header missing →
fall back to the user's personal workspace (`Membership` joined to
`Workspace(type=PERSONAL)`, `order_by("created_at").first()`); none found →
`403`. Once resolved: `token = active_workspace.set(ws_id)`, then
`with transaction.atomic(): cursor.execute("SELECT set_config('app.workspace_id', %s, %s)", [str(ws_id), True]); response = self.get_response(request)`,
then `finally: active_workspace.reset(token)`. Registered in
`config/settings.py` `MIDDLEWARE`, directly after
`AuthenticationMiddleware` (so `request.user` is resolved first) and before
`MessageMiddleware`.

**Design-vs-implementation note (documented deviation)**: the design text
says the `SET LOCAL` should run "inside the open `ATOMIC_REQUESTS` txn."
Verified via Django source (`BaseHandler.make_view_atomic`) that
`ATOMIC_REQUESTS` only wraps the *view callable itself*, not middleware
`__call__` code that runs before/after `self.get_response(request)` — so
literally relying on the pre-existing `ATOMIC_REQUESTS` transaction from
middleware code would NOT actually be "inside" it. Implementation instead
opens its own `transaction.atomic()` explicitly around
`self.get_response(request)` in the middleware; `ATOMIC_REQUESTS`'s own
per-view wrap then nests as a savepoint inside it. Functionally equivalent
to (and verified via the real transaction-boundary test below) — `SET
LOCAL` is scoped to exactly the middleware's own transaction, and is
cleared when it commits/rolls back.

- RED: 4/6 failed (`context_value` was `None` instead of the resolved
  workspace id; not-a-member request returned `200` instead of `403`) —
  confirms the sentinel-only default was in effect before the middleware existed.
- GREEN: `pytest workspaces/tests/test_middleware.py -v` → 6 passed,
  including `test_set_local_does_not_persist_past_the_request_transaction`
  which uses `pytest.mark.django_db(transaction=True)` (real commits, not a
  rolled-back savepoint) to prove `current_setting('app.workspace_id', true)`
  is empty from a fresh query issued after the request's transaction ended.

### D8 — RLS policies + restricted app role

M2a ships no NEM domain models yet. Per the apply-instructions'
explicit fallback ("add a minimal concrete scoped model \(documented\)
rather than leaving nothing to test"), added
`workspaces.models.WorkspaceResource(ScopedModel)` — a `name: CharField`
with no product meaning, documented in its own docstring as a throwaway
RLS-exercise table pending real M2b+ domain models.

**Why not put RLS on `Membership` instead (design's own example)**:
`TenancyMiddleware` must query `Membership` (by `request.user`) to *resolve*
which workspace to activate, before `app.workspace_id` is ever set for the
request. If RLS were enabled on `workspaces_membership` keyed on
`app.workspace_id`, that bootstrap lookup would itself be denied by RLS
(chicken-and-egg — no context yet), breaking every authenticated request
once traffic ran as the restricted `portal_app` role. `Membership` access is
inherently scoped by *user identity* (`request.user`), not by workspace
tenancy, so it correctly stays outside the RLS backstop in this design;
noting this as a **documented deviation** from the design text's own
Membership example, kept for `sdd-verify` to confirm is acceptable.

`workspaces/migrations/0002_workspace_resource.py`: plain `CreateModel`
(via `manage.py makemigrations`). `workspaces/migrations/0003_rls.py`:
three `RunSQL` blocks, each independently reversible —
1. `CREATE ROLE portal_app WITH LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB
   NOCREATEROLE` guarded by an `IF NOT EXISTS` check against `pg_roles`
   (idempotent); reverse does `DROP OWNED BY portal_app; DROP ROLE
   portal_app` guarded the same way.
2. `GRANT USAGE ON SCHEMA public`, `GRANT SELECT/INSERT/UPDATE/DELETE ON ALL
   TABLES`, `GRANT USAGE/SELECT ON ALL SEQUENCES`, plus matching `ALTER
   DEFAULT PRIVILEGES` so future tables/sequences inherit the same grants
   automatically; reverse is a no-op (dropping the role in \#1's reversal
   revokes everything it was granted).
3. Per scoped table (currently just `workspaces_workspaceresource`):
   `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + `CREATE POLICY
   ws_isolation ... USING/WITH CHECK (workspace_id =
   current_setting('app.workspace_id', true)::uuid)`; reverse drops the
   policy and disables RLS. No `FORCE ROW LEVEL SECURITY` needed — the
   owner/migrate role that creates these rows locally is the Postgres
   superuser, and superusers always bypass RLS regardless of `FORCE`; only
   non-owner, non-superuser roles (i.e. `portal_app`) are subject to the
   policy, which is exactly the intent.

Migrations run as the owner role (`davidnahumcrdz`, local superuser, trust
auth) per the existing two-role settings split from D1
(`DJANGO_DB_ROLE=migrate` default); runtime traffic is meant to set
`DJANGO_DB_ROLE=runtime` + `APP_DATABASE_URL` pointing at `portal_app` — no
further settings restructuring needed, this was already wired ahead of time
in D1.

Verified directly via `psql`: `SELECT rolname, rolbypassrls, rolsuper FROM
pg_roles WHERE rolname='portal_app'` → `f | f` (no bypass, not a
superuser).

- RED: `psycopg.OperationalError: role "portal_app" does not exist` +
  `ImportError: cannot import name 'WorkspaceResource'`.
- GREEN: `pytest workspaces/tests/test_rls.py -v` → 4 passed (app role
  lacks BYPASSRLS; RLS denies with no context set; RLS permits when
  context matches; RLS blocks a specific foreign-workspace row while
  permitting the matching one) — against the REAL Postgres role and REAL
  RLS policy, no mocking.

### D9 — cross-tenant leak test under pooling (the exit gate)

`workspaces/tests/test_pooling_leak.py`: reuses ONE real `psycopg`
connection (connected as `portal_app`, `autocommit=False`) across two
sequential transactions to simulate a pooled connection handed to a
different logical request.

**Bug found and fixed by this test** (documented, not glossed over):
`current_setting('app.workspace_id', true)` does **not** return `NULL`
once a `SET LOCAL`-scoped value's transaction ends — Postgres resets it to
an **empty string `''`**. The original D8 policy predicate
(`current_setting(...)::uuid`) then raised
`psycopg.errors.InvalidTextRepresentation: invalid input syntax for type
uuid: ""` on the next query issued on the same connection with no
re-activated context, instead of denying the row — an ERROR, not a
fail-closed denial. Root-caused by
`test_reused_connection_with_no_reactivated_context_denies_all_rows`.
Fixed in `workspaces/migrations/0004_rls_fix_empty_setting.py`: wraps the
cast in `NULLIF(current_setting('app.workspace_id', true), '')::uuid` so an
absent/cleared setting evaluates to `NULL` (predicate → unknown/false →
deny), never an error. Migration is reversible (drops back to the original,
buggy predicate — kept intentionally as the literal pre-fix SQL for an
accurate reverse). D8's own commit (`3772e64`) was left as-is (it was
genuinely green against its own test file, which didn't exercise the
committed-then-cleared edge case); the fix ships as part of D9's commit
per the apply instructions ("fix any gap the test surfaces").

Five tests, all real DB / real role / no mocking:
1. **Positive control** — `set_config(..., true)` for workspace A, query,
   commit (ends txn 1); same connection, `set_config(..., true)` for
   workspace B, explicit query `WHERE workspace_id = A`, commit (txn 2) →
   zero rows via raw RLS. Then, independently, sets the Python
   `active_workspace` contextvar to B and asserts
   `WorkspaceResource.objects.filter(workspace_id=A.id)` also returns
   `[]` — the ORM-level gate, verified separately from the DB gate (design's
   "two independent gates" claim, both exercised).
2. **No-reactivation denies all** — after workspace A's transaction commits,
   the very next transaction on the same connection (no new `set_config`
   call at all) sees `current_setting(...)` as `''`/`NULL` and `count(*) ==
   0` — proves fail-closed-deny-all, not "falls back to visible."
3. **Negative control** — plain `set_config(..., false)` (session-scoped,
   i.e. literal `SET`, not `SET LOCAL`) for workspace A; commit; next
   transaction on the same connection, *without resetting anything*, still
   sees `current_setting(...) == str(workspace_a.id)` and `count(*) == 1`
   — the leak actually happens with plain `SET`, proving the harness can
   truly detect a leak (not a vacuously-passing control).
4. **Production code path assertion** — `inspect.getsource(middleware)`
   asserts the literal `set_config('app.workspace_id', %s, %s)` call site
   passes `[str(workspace_id), True]` (never `False]`) — ties the middleware
   source directly to the "SET LOCAL, never plain SET" guarantee the
   negative control demonstrates the failure mode of.
5. **App role lacks BYPASSRLS** (gate #2/#3), reconfirmed against the
   `portal_app` role via a fresh connection.

- RED/discovery run: 4/5 passed, 1 failed with the `InvalidTextRepresentation`
  bug above — a genuine RED that drove the D8→D9 migration fix, not a
  scaffolding RED (this is the intended "RED test surfaces a real gap"
  path per the apply instructions for D9.3).
- GREEN: `pytest workspaces/tests/test_pooling_leak.py -v` → 5 passed,
  against real Postgres, no mocking of the DB, negative control genuinely
  demonstrates a leak.

## TDD Cycle Evidence (Batch 2, D4-D9)

| Unit | RED (test written first, observed failing) | GREEN (implementation passes) | REFACTOR |
|------|----------------------------------------------|--------------------------------|----------|
| D4 `test_services.py::test_successful_signup_creates_user_workspace_and_owner_membership` | RED: `ModuleNotFoundError: workspaces.services` | GREEN after `services.py` | — |
| D4 `test_services.py::test_failure_during_provisioning_rolls_back_all_records` | RED (same) | GREEN | — |
| D5 `test_managers.py::test_no_context_denies_all_rows` | RED: manager returned the row instead of `.none()` (no `context.py`/`managers.py` yet, error path) | GREEN after `context.py` + `managers.py` + wiring `ScopedModel.objects` | — |
| D5 `test_managers.py::test_query_scoped_to_active_workspace` | RED: `ModuleNotFoundError: workspaces.context` | GREEN | — |
| D6 `test_permissions.py::test_owner_permitted_a_privileged_action` | RED: `ModuleNotFoundError: workspaces.permissions` | GREEN after `permissions.py` | — |
| D6 `test_permissions.py::test_member_denied_a_privileged_action` | RED (same) | GREEN | — |
| D6 `test_permissions.py::test_unknown_role_denied` | RED (same) | GREEN | — |
| D6 `test_permissions.py::test_drf_permission_class_delegates_to_has_permission` | RED (same) | GREEN | — |
| D6 `test_permissions.py::test_permissions_module_has_no_inline_role_string_comparisons` | RED (same); then a SECOND red after `permissions.py` existed (docstring prose matched `.role ==`) | GREEN after rewording the docstring | Verified repo-wide via `grep -rn "\.role =="` that no production file matches |
| D7 `test_middleware.py::test_header_resolves_membership_and_sets_that_workspace` | RED: `context_value` was `None` | GREEN after `middleware.py` + `MIDDLEWARE` registration | — |
| D7 `test_middleware.py::test_missing_header_falls_back_to_personal_workspace` | RED (same) | GREEN | — |
| D7 `test_middleware.py::test_header_present_but_not_member_returns_403` | RED: `200` instead of `403` | GREEN | — |
| D7 `test_middleware.py::test_unauthenticated_request_has_no_context_set` | Passed pre-implementation too (sentinel default already correct) | GREEN | — |
| D7 `test_middleware.py::test_set_local_is_issued_inside_the_request_transaction` | RED: `db_setting` was `None` | GREEN | — |
| D7 `test_middleware.py::test_set_local_does_not_persist_past_the_request_transaction` | Passed once GREEN reached (real-transaction harness) | GREEN | — |
| D8 `test_rls.py::test_app_role_lacks_bypassrls` | RED: `psycopg.OperationalError: role "portal_app" does not exist` | GREEN after `0003_rls.py` role creation | — |
| D8 `test_rls.py::test_rls_denies_rows_with_no_workspace_context_set` | RED: `ImportError: WorkspaceResource` | GREEN after model + migrations | — |
| D8 `test_rls.py::test_rls_permits_rows_when_workspace_context_matches` | RED (same) | GREEN | — |
| D8 `test_rls.py::test_rls_blocks_foreign_workspace_row_specifically` | RED (same) | GREEN | — |
| D9 `test_pooling_leak.py::test_reused_connection_switched_context_denies_foreign_workspace_rows` | Passed on first run against D4-D8's already-correct implementation | GREEN | — |
| D9 `test_pooling_leak.py::test_reused_connection_with_no_reactivated_context_denies_all_rows` | RED: `psycopg.errors.InvalidTextRepresentation: invalid input syntax for type uuid: ""` (real bug, not scaffolding) | GREEN after `0004_rls_fix_empty_setting.py` (`NULLIF`) | — |
| D9 `test_pooling_leak.py::test_negative_control_plain_set_demonstrates_the_leak_it_guards_against` | Passed on first run (by construction — it exercises plain `SET`, unaffected by the RLS predicate fix) | GREEN | — |
| D9 `test_pooling_leak.py::test_production_code_path_uses_set_local_not_plain_set` | Passed on first run (inspects already-correct D7 source) | GREEN | — |
| D9 `test_pooling_leak.py::test_app_role_lacks_bypassrls_gate` | Passed on first run (reconfirms D8's role) | GREEN | — |

## Work Unit Evidence (Batch 2, D4-D9)

### D4 — transactional signup provisioning

| Evidence | Value |
|---|---|
| Focused test command and result | `cd backend && uv run pytest workspaces/tests/test_services.py -v` → 2 passed |
| Runtime harness | `uv run python manage.py migrate --check` clean; full suite `uv run pytest -q` → 17 passed at this point |
| Rollback boundary | `git revert a8ba05d` — deletes `services.py` + its test; D3 unaffected (D4 has no migrations) |

### D5 — workspace-scoped manager

| Evidence | Value |
|---|---|
| Focused test command and result | `pytest workspaces/tests/test_managers.py -v` → 2 passed |
| Runtime harness | Full suite `uv run pytest -q` → 19 passed |
| Rollback boundary | `git revert e7737eb` — deletes `context.py`/`managers.py`, reverts the `ScopedModel.objects` wiring; concrete `ScopedModel` subclasses fall back to Django's default manager (no migration to reverse) |

### D6 — capability matrix + DRF permission

| Evidence | Value |
|---|---|
| Focused test command and result | `pytest workspaces/tests/test_permissions.py -v` → 5 passed |
| Runtime harness | N/A — pure unit module, no external harness (per tasks.md Work Units table); full suite `uv run pytest -q` → 24 passed |
| Rollback boundary | `git revert 003b0d8` — deletes `permissions.py`, no dependents yet |

### D7 — RLS middleware + SET LOCAL wiring

| Evidence | Value |
|---|---|
| Focused test command and result | `pytest workspaces/tests/test_middleware.py -v` → 6 passed |
| Runtime harness | Django test client through the REAL middleware stack (`X-Workspace-Id` header, session auth); real Postgres queries via `connection.cursor()` inside the view for the transaction-boundary assertions; full suite `uv run pytest -q` → 30 passed |
| Rollback boundary | `git revert 420e263` — removes `TenancyMiddleware` from `MIDDLEWARE` and deletes `middleware.py`; D5's `ScopedManager` still fails closed on its own (defense-in-depth intact even without the middleware) |

### D8 — RLS policies + restricted app role

| Evidence | Value |
|---|---|
| Focused test command and result | `pytest workspaces/tests/test_rls.py -v` → 4 passed (real Postgres, real `portal_app` role, real RLS) |
| Runtime harness | `uv run python manage.py migrate --check` clean; `psql -d portal_nem -c "SELECT rolname, rolbypassrls, rolsuper FROM pg_roles WHERE rolname='portal_app'"` → `f, f`; full suite `uv run pytest -q` → 34 passed |
| Rollback boundary | `uv run python manage.py migrate workspaces 0002_workspace_resource` (reversible `RunSQL` drops the role/grants/policy); `git revert 3772e64` for the code side |

### D9 — cross-tenant leak test under pooling

| Evidence | Value |
|---|---|
| Focused test command and result | `pytest workspaces/tests/test_pooling_leak.py -v` → 5 passed (real Postgres, real `portal_app` role, ONE physical connection reused across two real transactions, no DB mocking) |
| Runtime harness | Single-connection reuse harness IS the runtime harness for this delivery (design D-5); `uv run python manage.py migrate --check` clean; full suite `uv run pytest -q` → 39 passed |
| Rollback boundary | Test-only file (`git revert b201dbb` for the test); the RLS-predicate bugfix migration (`0004_rls_fix_empty_setting.py`) is itself reversible (`manage.py migrate workspaces 0003_rls`) but reverting it would reintroduce the `InvalidTextRepresentation` bug — flagging that the test file and the fix migration are not independently revertable without regressing D9's own exit gate |

## Environment Setup (Batch 1: D1-D3)

- DB `portal_nem` created locally as owner role `davidnahumcrdz` (Postgres.app, trust auth, unix socket, port 5432).
- `CREATE EXTENSION vector;` run manually once to confirm availability (`0.8.1` available in `pg_available_extensions`), then re-enabled reproducibly via `backend/core/migrations/0001_enable_pgvector.py` (`CreateExtension("vector")`). No manual extra install step was needed — pgvector shipped with this Postgres.app build.
- `portal_app` runtime role (NOSUPERUSER NOBYPASSRLS) is **not created yet** — that's D8. `config/settings.py` already expresses the two-role split via `DJANGO_DB_ROLE` / `DATABASE_URL` / `APP_DATABASE_URL`, so D8 only needs to create the role and set `APP_DATABASE_URL` — no settings restructuring required.
- `.env` files could not be created in this sandbox (permission-denied on any `.env*` path). Settings fall back to sane defaults (`DATABASE_URL` default `postgres:///portal_nem`, i.e. local unix-socket connection as the OS user) when no env file/vars are present. `backend/.env.example` (documented in `backend/README.md`) could not be written for the same reason — noted here instead: copy the `DATABASE_URL`/`DJANGO_SECRET_KEY` pattern from `config/settings.py` comments into a local `backend/.env` if overriding defaults.

## Delivery Status (ALL DONE)

| Delivery | Status | Commit |
|----------|--------|--------|
| D1 — scaffold Django project | Done | `ef7fc31` |
| D2 — custom email user model | Done | `60e36ac` |
| D3 — Workspace + Membership models | Done | `1fff304` |
| D4 — transactional signup provisioning | Done | `a8ba05d` |
| D5 — workspace-scoped manager | Done | `e7737eb` |
| D6 — capability matrix + DRF permission | Done | `003b0d8` |
| D7 — RLS middleware + SET LOCAL wiring | Done | `420e263` |
| D8 — RLS policies + restricted app role | Done | `3772e64` |
| D9 — cross-tenant leak test under pooling | Done | `b201dbb` |

## TDD Cycle Evidence (Batch 1: D1-D3)

| Unit | RED (test written first, observed failing) | GREEN (implementation passes) | REFACTOR |
|------|----------------------------------------------|--------------------------------|----------|
| D1 `test_scaffold.py::test_django_settings_import_cleanly` | Passed immediately once settings module existed (no separate RED — settings creation and this assertion were written together as the first artifact of the delivery) | Passed | N/A |
| D1 `test_scaffold.py::test_migrate_check_reports_no_pending_migrations` | RED confirmed: `migrate --check` failed (`Engine not recognized from url: {...empty...}`) due to an `env.db_url(..., default=None)` bug in settings | GREEN after fixing `APP_DATABASE_URL` resolution to only call `env.db_url` when the env var is actually set | Verified via direct `env.db_url()` REPL probe before patching |
| D2 `test_models.py::test_user_created_with_email_as_identifier` | RED confirmed: `TypeError: UserManager.create_user() missing 1 required positional argument: 'username'` (default `auth.User` manager, custom model not wired) | GREEN after adding `users/models.py` (`User`, `UserManager`) + `AUTH_USER_MODEL` + DB drop/remigrate | — |
| D2 `test_models.py::test_duplicate_email_rejected` | RED (same failure mode as above) | GREEN | — |
| D2 `test_models.py::test_superuser_creation_requires_is_staff_and_is_superuser` | RED (same) | GREEN | — |
| D2 `test_auth.py::test_login_issues_httponly_session_cookie` | RED confirmed: `session_cookie is None` (test used Django admin login against a non-staff user, which silently fails) | GREEN after fixing the test to use a dedicated `LoginView` test urlconf/template instead of `/admin/login/` | Production `SESSION_COOKIE_HTTPONLY=True` + DRF `SessionAuthentication` were already configured in D1's scaffold settings (ahead of D2), so this cycle's GREEN came from a test-harness fix, not a production code change — see Deviations |
| D2 `test_auth.py::test_unauthenticated_request_denied` | Passed on first run — session/DRF auth config from D1 already satisfies this scenario | Passed | — |
| D2 `test_auth.py::test_state_changing_request_without_csrf_token_rejected` | Passed on first run — `CsrfViewMiddleware` already in `MIDDLEWARE` from D1 | Passed | — |
| D2 `test_auth.py::test_session_cookie_settings_are_httponly_and_samesite` | Passed on first run | Passed | — |
| D3 `test_models.py::test_workspace_type_restricted_to_allowed_values` | RED confirmed: `ModuleNotFoundError: No module named 'workspaces.models'` | GREEN after `workspaces/models.py` (`Workspace`, `Membership`, `ScopedModel`) + migration | — |
| D3 `test_models.py::test_workspace_type_accepts_personal_and_group` | RED (same) | GREEN | — |
| D3 `test_models.py::test_membership_role_restricted_to_allowed_values` | RED (same) | GREEN | — |
| D3 `test_models.py::test_membership_role_is_charfield_with_choices` | RED (same) | GREEN | — |
| D3 `test_models.py::test_membership_accepts_valid_roles` | RED (same) | GREEN | — |
| D3 `test_models.py::test_scoped_model_provides_workspace_fk` | RED (same) | GREEN | — |

## Work Unit Evidence (Batch 1: D1-D3)

### D1 — scaffold Django project

| Evidence | Value |
|---|---|
| Focused test command and result | `cd backend && uv run pytest tests/test_scaffold.py -v` → 2 passed |
| Runtime harness | `uv run python manage.py migrate` → clean apply on fresh `portal_nem` DB (all Django-stock migrations + `core.0001_enable_pgvector`) |
| Rollback boundary | `git revert ef7fc31`; no dependents yet (D2/D3 not applied at that point) |

### D2 — custom email user model

| Evidence | Value |
|---|---|
| Focused test command and result | `cd backend && uv run pytest users/ -v` → 7 passed |
| Runtime harness | `uv run python manage.py migrate --check` → clean; verified via `psql \dt` that only `users`/`users_groups`/`users_user_permissions` exist, no `auth_user` table |
| Rollback boundary | Irreversible per design (`AUTH_USER_MODEL` set before first migration). Greenfield DB: `dropdb`/`createdb`/`migrate` resets cleanly — no production data exists yet |

### D3 — Workspace + Membership models

| Evidence | Value |
|---|---|
| Focused test command and result | `cd backend && uv run pytest workspaces/tests/test_models.py -v` → 6 passed |
| Runtime harness | `uv run python manage.py migrate --check` → clean; full suite `uv run pytest` → 15 passed |
| Rollback boundary | `uv run python manage.py migrate workspaces zero` (reversible — this is a plain `CreateModel` migration, no RLS/data yet) |

## Files Changed (All Batches, D1-D9)

| File | Action | Delivery |
|------|--------|----------|
| `backend/pyproject.toml` | Created | D1 |
| `backend/manage.py` | Created | D1 |
| `backend/config/settings.py` | Created (D1), modified (D2 `AUTH_USER_MODEL`+app, D3 app, D7 `MIDDLEWARE`) | D1/D2/D3/D7 |
| `backend/config/urls.py`, `wsgi.py`, `asgi.py` | Created | D1 |
| `backend/core/` (`apps.py`, `migrations/0001_enable_pgvector.py`) | Created | D1 |
| `backend/tests/test_scaffold.py` | Created | D1 |
| `backend/README.md`, `.python-version`, `uv.lock` | Created | D1 |
| `README.md` (repo root) | Modified — removed FastAPI row from stack table | D1 |
| `backend/users/` (`models.py`, `apps.py`, `migrations/0001_initial.py`, `tests/`) | Created | D2 |
| `backend/workspaces/models.py` | Created (D3: `Workspace`, `Membership`, `ScopedModel`), modified (D5: `ScopedModel.objects = ScopedManager()`; D8: added `WorkspaceResource`) | D3/D5/D8 |
| `backend/workspaces/apps.py`, `migrations/0001_initial.py`, `tests/test_models.py` | Created | D3 |
| `backend/workspaces/services.py`, `tests/test_services.py` | Created | D4 |
| `backend/workspaces/context.py`, `managers.py`, `tests/test_managers.py` | Created | D5 |
| `backend/workspaces/permissions.py`, `tests/test_permissions.py` | Created | D6 |
| `backend/workspaces/middleware.py`, `tests/test_middleware.py` | Created | D7 |
| `backend/workspaces/migrations/0002_workspace_resource.py`, `0003_rls.py`, `tests/test_rls.py` | Created | D8 |
| `backend/workspaces/migrations/0004_rls_fix_empty_setting.py`, `tests/test_pooling_leak.py` | Created | D9 |

## Deviations from Design

- **`backend/core/` app added** (not in design's File Changes table). Needed to express "enable pgvector via migration" reproducibly per apply instructions; a bare `CREATE EXTENSION` isn't tied to any of the D1-D3 apps otherwise. Minimal footprint (one migration, no models).
- **D1's `REST_FRAMEWORK`/`SESSION_COOKIE_HTTPONLY` settings were written ahead of D2** as part of the initial scaffold (design lists DRF+spectacular config as a D1 File Change). This meant most of D2's `test_auth.py` scenarios passed on first run rather than failing first — documented per-test in the Batch 1 TDD Cycle Evidence table rather than silently treated as satisfied. Only the httpOnly-cookie test needed an actual RED→GREEN cycle (a test-harness bug, not production code).
- **`.env` / `.env.example` could not be written** — sandbox permission denies writes to any `.env*` path. Settings use safe defaults (local unix-socket, current OS user, `portal_nem` DB) so `migrate`/`pytest` work without any env file.
- **Greenfield DB drop/remigrate performed once**, between D1 and D2, because D1's `migrate` applied the stock `auth.User` migration before `AUTH_USER_MODEL` was set. Matches the design's own stated rollback plan — no data existed to lose.
- **D7 — `TenancyMiddleware` opens its own explicit `transaction.atomic()`** around `self.get_response(request)` rather than relying on the pre-existing `ATOMIC_REQUESTS` transaction, because `ATOMIC_REQUESTS` only wraps the view callable itself (verified via Django source), not middleware code around it. Functionally equivalent — verified by the real transaction-boundary test in D7 and the full D9 exit gate.
- **D8 — RLS applied only to `WorkspaceResource` (a new, minimal, documented, product-meaningless concrete `ScopedModel`), not to `Membership`** as the design text's own example suggested. `TenancyMiddleware` must query `Membership` (by `request.user`) to resolve the active workspace *before* `app.workspace_id` is set for the request; enabling RLS on `Membership` would create a bootstrap chicken-and-egg deadlock once the app connects as the restricted `portal_app` role. `Membership` access is scoped by user identity, not tenancy, so this is treated as an intentional correction to the design text, not a shortcut — **flagging explicitly for `sdd-verify`** to confirm this reading of D-4/D-5 is acceptable, and for the design doc to be updated if so.
- **D9 surfaced and fixed a real RLS-predicate bug from D8**: `current_setting('app.workspace_id', true)` returns `''` (not `NULL`) once a `SET LOCAL` value's transaction ends, and the original `current_setting(...)::uuid` cast raised `InvalidTextRepresentation` on `''` instead of denying. Fixed via `NULLIF(..., '')` in a new migration (`0004_rls_fix_empty_setting.py`) rather than editing D8's already-committed migration — see D9 section above for full detail. D8's own commit and tests remain valid/green (the bug only manifests on a second reused transaction, which D8's test file never exercised).

## Blockers

None. All nine deliveries reached green, including the D9 exit gate (real Postgres, real `portal_app` role, real connection reuse, no DB mocking, negative control genuinely detects a leak).

## Next Steps

M2a is complete. `state.yaml`: `phases.apply` → `done`, `next_recommended` → `verify`. Recommend `sdd-verify` next; flag the D8 Membership-vs-WorkspaceResource RLS-scope deviation (above) for explicit confirmation during verification, and consider promoting `WorkspaceResource` to a real M2b domain model (or removing it) once actual NEM domain models exist.
