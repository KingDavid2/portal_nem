# Verification Report: M2a — Tenancy Foundation Core

**Change**: `m2a-tenancy-core`
**Mode**: Strict TDD, full spec-driven verification (proposal + design + specs + tasks all present)
**Verdict**: PASS WITH WARNINGS (0 CRITICAL; 2 WARNING, 1 SUGGESTION)

---

## Completeness

| Item | Result |
|------|--------|
| Tasks checked | 37/37 `[x]` across D1-D9 |
| Delivery commits present | 9/9 (`ef7fc31`..`b201dbb`) on branch `m2a-tenancy-core` |
| TDD Cycle Evidence table | Present, per-task, in `apply-progress.md` (Batch 1 + Batch 2) |

## Command Evidence

| Command | Result |
|---|---|
| `cd backend && uv run pytest -v` | **39 passed**, 0 failed, 0 skipped, 0 xfail, 3.11s |
| `cd backend && uv run python manage.py migrate --check` | exit 0 (clean, no pending migrations) |

No `skip`/`xfail` markers found anywhere under `backend/**/tests/`.

---

## Design-Brief §5 Acceptance Gates

### Gate #1 — Transactional signup (user + personal workspace + owner membership, all-or-nothing)
`backend/workspaces/services.py::provision_signup` wraps Workspace → User → Membership creation in one `transaction.atomic()`.
- Evidence: `workspaces/tests/test_services.py::test_successful_signup_creates_user_workspace_and_owner_membership` — PASS
- Evidence: `workspaces/tests/test_services.py::test_failure_during_provisioning_rolls_back_all_records` — PASS. Deliberately creates the Workspace *before* the User inside the atomic block, then forces `IntegrityError` on `User.objects.create_user` via a pre-existing duplicate email — genuinely proves rollback of an already-created row, not just "nothing ran."
**Status**: CONFIRMED.

### Gate #2 — Cross-tenant leak test under connection pooling, with working negative control
`backend/workspaces/tests/test_pooling_leak.py` reuses ONE real `psycopg` connection (connected as `portal_app`, `autocommit=False`) across two sequential transactions.
- Positive control (`test_reused_connection_switched_context_denies_foreign_workspace_rows`): `SET LOCAL` via `set_config(..., true)`; workspace A committed, workspace B activated on the same connection; asserts BOTH the raw RLS query and the ORM `ScopedManager`-filtered query deny workspace A's row. PASS.
- No-reactivation case (`test_reused_connection_with_no_reactivated_context_denies_all_rows`): after commit, next transaction with no new `set_config` call sees `current_setting(...)` as `''`/`NULL` and `count == 0` — fail-closed-deny-all, not "falls back to visible." PASS.
- **Negative control verified NOT vacuous**: `test_negative_control_plain_set_demonstrates_the_leak_it_guards_against` uses plain `set_config(..., false)` (session-scoped `SET`) and asserts `leaked_value == str(workspace_a.id)` and `count == 1` on the next transaction — i.e., the test *positively asserts the leak occurs* with plain `SET`. This proves the harness can detect a leak; it is not a passing-by-construction check. Read the file directly — confirmed non-vacuous.
- `test_production_code_path_uses_set_local_not_plain_set` — `inspect.getsource(middleware)` asserts the literal call site passes `[str(workspace_id), True]` and that `"False]"` is absent from the source, tying the middleware's actual code to the safe path the negative control demonstrates the failure mode of.
**Status**: CONFIRMED — both QuerySet and RLS gates independently verified, negative control genuinely fails-open (i.e., asserts the leak) when expected.

### Gate #3 — App role is non-BYPASSRLS, asserted as the runtime role
`workspaces/tests/test_rls.py::test_app_role_lacks_bypassrls` and `workspaces/tests/test_pooling_leak.py::test_app_role_lacks_bypassrls_gate` both open a fresh `psycopg` connection with `user="portal_app"` (not the Django default/owner connection) and query `SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user`. Since the connection itself authenticates as `portal_app`, `current_user` resolves to `portal_app`, not the migration/owner role. Independently confirmed via `psql`: `rolbypassrls=f, rolsuper=f` for `portal_app` (documented in apply-progress D8).
**Status**: CONFIRMED — assertion queries `pg_roles` as the actual runtime role, not the owner.

### Gate #4 — All authorization routes through `has_permission`; no inline role-string comparisons
`rg -n '\.role\s*==|\.role\s*!=|"owner"|"admin"|"member"' --glob '!*/tests/*' --glob '!*/migrations/*' backend/` returns only:
- `workspaces/models.py`: `Role.TextChoices` value definitions (`OWNER = "owner", ...`) — legitimate, not a conditional comparison.
- `workspaces/permissions.py`: `CAPABILITIES` dict keys (`"owner": frozenset(...)`, etc.) — the matrix itself, not an inline comparison.

No `membership.role == "..."` (or similar) conditional found in production code outside `permissions.py`'s own definitions. `WorkspacePermission.has_object_permission` calls `has_permission(membership, action)` only — verified by direct read of `permissions.py`, and by `test_drf_permission_class_delegates_to_has_permission` + `test_permissions_module_has_no_inline_role_string_comparisons` (the latter `inspect.getsource()`s the module itself).
**Status**: CONFIRMED.

---

## Deviation Scrutiny

### D7 — `TenancyMiddleware` opens its own `transaction.atomic()` (documented deviation from "relies on ATOMIC_REQUESTS")
Read `backend/workspaces/middleware.py` directly: `active_workspace.set(workspace_id)` is followed by `with transaction.atomic(): with connection.cursor() as cursor: cursor.execute("SELECT set_config('app.workspace_id', %s, %s)", [str(workspace_id), True]); response = self.get_response(request)`, then `finally: active_workspace.reset(token)`.
- The `SET LOCAL` and the downstream view/query execution (`self.get_response(request)`) happen inside the **same** explicit `transaction.atomic()` block and, by extension, the same DB connection/transaction — confirmed by `test_set_local_is_issued_inside_the_request_transaction` (PASS) and `test_set_local_does_not_persist_past_the_request_transaction` (PASS, uses `django_db(transaction=True)` for a real-commit harness, not a rolled-back savepoint).
- `active_workspace.reset(token)` is in a `finally` block covering both normal return and any exception path inside `get_response` — confirmed no leak across requests on a reused worker (the contextvar reset always runs regardless of outcome).
- The reasoning in apply-progress (that Django's `ATOMIC_REQUESTS` only wraps the view callable, not middleware `__call__` code around `get_response`) is architecturally correct per Django's `BaseHandler.make_view_atomic` — an explicit middleware-owned `transaction.atomic()` is the only way to guarantee the `SET LOCAL` and the view's queries share one transaction.
**Status**: WARNING (documentation only) — functionally sound and tested, but `design.md`'s Data Flow diagram text ("TenancyMiddleware (inside ATOMIC_REQUESTS txn)") should be corrected to describe the middleware's own explicit `atomic()` block for future readers. Not a spec violation.

### D8 — RLS applied to `WorkspaceResource`, not `Membership`
Verified the bootstrap reasoning: `TenancyMiddleware.__call__` queries `Membership.objects.filter(user=user, workspace_id=...)` (or the personal-workspace fallback query) *before* `active_workspace.set()` / `set_config()` is ever called for the request. If RLS were enabled on `workspaces_membership` keyed on `app.workspace_id`, that same bootstrap lookup would be denied by the app role's own policy (no context yet) — a genuine chicken-and-egg deadlock once traffic runs as the restricted `portal_app` role. This holds up on inspection of `middleware.py` (lines 50-70): `Membership` lookups happen strictly before the `SET LOCAL`/`atomic()` block begins.
`design.md` does **not** literally name `Membership` as a table requiring RLS (checked directly — the design's RLS policy shape is generic "per scoped table", and `Membership` is a plain `models.Model`, not a `ScopedModel` subclass, so it was never automatically in scope for the RLS `SCOPED_TABLES` list). The apply-progress description overstates this as "the design's own example," but the underlying engineering conclusion (Membership must stay outside RLS for bootstrap correctness) is sound and does not contradict any spec requirement — no spec text requires RLS on `Membership`.
**Membership exposure assessment**: Confirmed no API endpoint, DRF viewset, or Django admin registration currently exposes `Membership` querysets in this change (`config/urls.py` only routes `admin/`, `api/schema/`, `api/docs/`; no app-level `admin.py` registers `Membership`/`Workspace`). Today's blast radius is zero — `Membership` is only read internally by `TenancyMiddleware` and `provision_signup`, both scoped by `request.user`/creation context, not by blanket queries. This is acceptable for M2a.
**Status**: WARNING (follow-up required) — flag explicitly for M2b: when `Membership`-backed views/serializers are eventually built, they MUST filter by `request.user` explicitly (since `Membership` has no RLS backstop and is not a `ScopedModel`), and `design.md` should be updated to state this exception explicitly rather than leaving readers to infer it from apply-progress.

### D9 — NULLIF fix for `current_setting(...)` returning `''`
Verified `workspaces/migrations/0004_rls_fix_empty_setting.py`: replaces the policy predicate with `NULLIF(current_setting('app.workspace_id', true), '')::uuid` on both `USING` and `WITH CHECK` clauses, reversible (drops back to the pre-fix predicate).
- Empty-string case is covered directly by `test_reused_connection_with_no_reactivated_context_denies_all_rows`, which asserts `leftover in (None, "")` and `count_after == 0` on the very next transaction after a committed `SET LOCAL` — this exercises exactly the `''` case the fix addresses, and asserts denial (not an error), confirming the fix works as intended.
**Status**: CONFIRMED — a real bug, correctly root-caused, correctly fixed, and covered by a test that would have failed pre-fix (per apply-progress's documented RED run: `psycopg.errors.InvalidTextRepresentation`).

---

## Fail-Closed Sentinel

`workspaces/context.py`: `WORKSPACE_UNSET = object()` (identity sentinel, never `None`/`0`), `active_workspace: ContextVar` defaults to `WORKSPACE_UNSET`. `workspaces/managers.py::ScopedQuerySet._scoped()` returns `self.none()` when `active_workspace.get() is WORKSPACE_UNSET`.
- Evidence: `workspaces/tests/test_managers.py::test_no_context_denies_all_rows` — creates a row via `.create()` (bypasses the filtered read path), then asserts `list(ScopedProbe.objects.all()) == []` — proves the no-context read path returns **zero** rows, not all rows, even though a row genuinely exists in the table.
**Status**: CONFIRMED.

---

## Commit Hygiene

```
ef7fc31 chore: scaffold Django project
60e36ac feat(users): custom email user model
1fff304 feat(workspaces): Workspace and Membership models
a8ba05d feat(workspaces): transactional signup provisioning
e7737eb feat(workspaces): workspace-scoped manager
003b0d8 feat(workspaces): capability matrix and DRF permission
420e263 feat(workspaces): RLS middleware and SET LOCAL wiring
3772e64 feat(workspaces): RLS policies and restricted app role
b201dbb test(workspaces): cross-tenant leak test under pooling
```
9/9 delivery commits on branch `m2a-tenancy-core`, all conventional subjects (`chore:`/`feat(...):`/`test(...):`). `git log` bodies checked for `Co-Authored-By`/`Generated with`/`claude` — none found.
**Status**: CONFIRMED clean.

---

## Spec Compliance Matrix

| Capability | Requirement | Scenario | Covering test | Result |
|---|---|---|---|---|
| identity-auth | Custom Email User Model | User created with email as identifier | `users/tests/test_models.py::test_user_created_with_email_as_identifier` | PASS |
| identity-auth | Custom Email User Model | Duplicate email rejected | `users/tests/test_models.py::test_duplicate_email_rejected` | PASS |
| identity-auth | Session-Cookie Authentication | Login issues httpOnly session cookie | `users/tests/test_auth.py::test_login_issues_httponly_session_cookie` | PASS |
| identity-auth | Session-Cookie Authentication | CSRF rejection | `users/tests/test_auth.py::test_state_changing_request_without_csrf_token_rejected` | PASS |
| identity-auth | Session-Cookie Authentication | Unauthenticated denied | `users/tests/test_auth.py::test_unauthenticated_request_denied` | PASS |
| workspaces | Workspace and Membership Models | type/role choices rejection | `workspaces/tests/test_models.py::test_workspace_type_restricted_to_allowed_values`, `test_membership_role_restricted_to_allowed_values` | PASS |
| workspaces | Transactional Signup Provisioning | success + rollback | `workspaces/tests/test_services.py` (2 tests) | PASS |
| tenancy-isolation | Scoped manager reads contextvar | query-scoped / no-context-denies-all | `workspaces/tests/test_managers.py` (2 tests) | PASS |
| tenancy-isolation | SET LOCAL inside per-request txn | issued inside txn / does not persist | `workspaces/tests/test_middleware.py` (2 tests) | PASS |
| tenancy-isolation | RLS policies deny foreign rows | blocks foreign row / app role lacks BYPASSRLS | `workspaces/tests/test_rls.py` (4 tests) | PASS |
| tenancy-isolation | Cross-tenant isolation under pooling | reused-connection denies / negative control | `workspaces/tests/test_pooling_leak.py` (5 tests) | PASS |
| authorization | Capability matrix sole auth path | owner permitted / member denied / DRF delegates | `workspaces/tests/test_permissions.py` (5 tests) | PASS |
| authorization | Authorization distinct from isolation | N/A — architectural separation | Confirmed by code inspection: `permissions.py` never imports/touches `ScopedManager`/RLS; `has_permission` is pure role→action lookup | PASS (by inspection; no dedicated cross-cutting test, but not contradicted) |

---

## TDD Compliance

| Check | Result | Details |
|---|---|---|
| TDD Evidence reported | ✅ | Present in `apply-progress.md`, both batches |
| All tasks have tests | ✅ | 37/37 |
| RED confirmed (tests exist) | ✅ | 39/39 test files/functions verified present |
| GREEN confirmed (tests pass) | ✅ | 39/39 pass on execution |
| Triangulation adequate | ✅ | Every scenario has ≥2 test cases where the spec has multiple scenarios (services: 2, managers: 2, permissions: 5, middleware: 6, rls: 4, pooling_leak: 5) |
| Safety net for modified files | ✅ | `models.py` modified across D3/D5/D8 — full suite re-run green at each step per apply-progress Work Unit Evidence tables |

**TDD Compliance**: 6/6 checks passed

### Assertion Quality
No tautologies, no ghost loops, no assertion-without-production-call patterns found. `test_no_context_denies_all_rows` and `test_reused_connection_with_no_reactivated_context_denies_all_rows` are empty-result assertions but each has a companion non-empty-result test in the same file (`test_query_scoped_to_active_workspace`, `test_reused_connection_switched_context_denies_foreign_workspace_rows`'s workspace-A positive read). `test_production_code_path_uses_set_local_not_plain_set` and `test_permissions_module_has_no_inline_role_string_comparisons` use `inspect.getsource()` — acceptable here because each is paired with the negative-control test that demonstrates the failure mode the source-inspection assertion prevents, not a standalone smoke check.
**Assertion quality**: ✅ All assertions verify real behavior

---

## Issues

**CRITICAL**: None.

**WARNING**:
1. `design.md`'s Data Flow diagram text ("TenancyMiddleware (inside ATOMIC_REQUESTS txn)") should be corrected to reflect that the middleware opens its own explicit `transaction.atomic()` (D7 deviation) — documentation drift only, implementation and tests are correct.
2. `design.md` does not explicitly document the Membership-vs-RLS bootstrap exception (D8 deviation). Recommend updating design.md before/alongside archive so future readers don't have to reconstruct the reasoning from apply-progress. Also flag as an explicit follow-up for M2b: any future `Membership`-backed view/serializer MUST filter by `request.user`, since `Membership` has no RLS backstop.

**SUGGESTION**:
1. `WorkspaceResource` is an explicitly-documented throwaway model for exercising RLS; apply-progress already recommends removing/replacing it once real M2b domain models exist — carry this into M2b's task list.

---

## Final Verdict

**PASS WITH WARNINGS** (2 WARNING, 1 SUGGESTION, 0 CRITICAL). All 4 design-brief §5 gates hold with concrete, non-vacuous test evidence. Both documented deviations (D7, D8) are architecturally sound and correctly tested; only documentation (design.md text) lags the implementation. Recommend proceeding to `sdd-archive`, updating `design.md`'s two noted passages either before or as part of archive.
