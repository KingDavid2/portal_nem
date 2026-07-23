# Spec: tenancy-isolation

Row-level security, scoped queries, and cross-tenant isolation guarantees.

## Requirements

### Requirement: Workspace-Scoped Manager Reads Active-Workspace Context

The system MUST provide a base manager/queryset that filters all reads by the active workspace, read from a request-scoped `contextvar`. When no active-workspace context is set, the manager MUST fail closed: it MUST return an empty result set and MUST NOT return rows from any workspace.

#### Scenario: Query scoped to active workspace

- GIVEN the active-workspace contextvar is set to workspace A
- WHEN a workspace-scoped model is queried
- THEN only rows belonging to workspace A MUST be returned

#### Scenario: Query with no active-workspace context denies all

- GIVEN the active-workspace contextvar is unset
- WHEN a workspace-scoped model is queried
- THEN the system MUST return zero rows
- AND the system MUST NOT return rows from any workspace as a fallback

### Requirement: RLS SET LOCAL Inside Per-Request Transaction

The system MUST issue `SET LOCAL app.workspace_id` inside the same database transaction as the per-request `ATOMIC_REQUESTS` transaction, storing the resolved workspace id in a request-scoped contextvar for the middleware to read. The system MUST NOT use plain `SET` (session-scoped), because it leaks across pooled connections.

#### Scenario: SET LOCAL scoped to request transaction

- GIVEN a request resolves an active workspace
- WHEN the request's per-request transaction begins
- THEN the middleware MUST execute `SET LOCAL app.workspace_id` with the resolved workspace id inside that transaction

#### Scenario: Setting persists only for the transaction lifetime

- GIVEN a request has executed `SET LOCAL app.workspace_id`
- WHEN that request's transaction commits or rolls back
- THEN the `app.workspace_id` setting MUST NOT persist to a subsequent request reusing the same pooled connection

### Requirement: RLS Policies Deny Foreign-Workspace Rows

The system MUST ship Postgres row-level security policies (applied via a reversible `RunSQL` migration) on workspace-scoped tables that permit access only to rows where `workspace_id` matches `current_setting('app.workspace_id')`. The application database role MUST NOT have the `BYPASSRLS` attribute.

#### Scenario: RLS policy blocks foreign-workspace row at the database layer

- GIVEN RLS is enabled on a workspace-scoped table
- AND `app.workspace_id` is set to workspace A for the current transaction
- WHEN a query attempts to read a row belonging to workspace B
- THEN Postgres MUST exclude that row from the result, independent of any ORM-level filtering

#### Scenario: App role lacks BYPASSRLS

- GIVEN the application connects to Postgres using its configured role
- WHEN `rolbypassrls` is checked for that role via `pg_roles`
- THEN the value MUST be `false`

### Requirement: Cross-Tenant Isolation Holds Under Connection Pooling

The system MUST prove, via an automated test, that both the workspace-scoped QuerySet and the RLS backstop deny foreign-workspace reads when a single physical database connection is reused across two different workspace contexts (simulating pooled-connection reuse).

#### Scenario: Reused connection with switched workspace context denies foreign-workspace rows

- GIVEN a single database connection first sets `app.workspace_id` to workspace A and executes a query
- WHEN the same connection is reused, `app.workspace_id` is reset via `SET LOCAL` to workspace B, and a new transaction queries for workspace A's rows
- THEN both the ORM-level scoped QuerySet and the raw RLS-protected query MUST deny access to workspace A's rows

#### Scenario: Negative control using plain SET demonstrates the leak it guards against

- GIVEN a single reused connection sets `app.workspace_id` via plain `SET` (not `SET LOCAL`) for workspace A
- WHEN a second logical request reuses the same connection without resetting the setting
- THEN the test MUST demonstrate that plain `SET` would leak workspace A's context into the second request
- AND the test MUST assert the production code path uses `SET LOCAL`, not plain `SET`

### Requirement: RLS Coverage Extends to School Structure Tables

The system MUST enable Postgres row-level security, with the `ws_isolation` policy in the NULLIF form (mirroring the existing `0004` migration's pattern), on all four new workspace-scoped tables: `schools_school`, `schools_schoolyear`, `schools_group`, and `students_student`. Each table's RLS migration MUST be reversible.

#### Scenario: RLS enabled on all four new tables

- GIVEN the school-structure migrations have been applied
- WHEN RLS status is checked for `schools_school`, `schools_schoolyear`, `schools_group`, and `students_student`
- THEN each table MUST have row-level security enabled
- AND each MUST carry a `ws_isolation` policy using the NULLIF form

#### Scenario: Foreign-workspace row denied at the database layer for a new table

- GIVEN `app.workspace_id` is set to workspace A for the current transaction
- WHEN a raw query attempts to read a `Student` row belonging to workspace B
- THEN Postgres MUST exclude that row from the result, independent of any ORM-level filtering

### Requirement: TenancyMiddleware Attaches Resolved Membership to the Request

`TenancyMiddleware` MUST attach the resolved `Membership` object to `request.membership` for every request that resolves an active workspace. Downstream permission classes and views MUST be able to read `request.membership` without re-resolving it.

#### Scenario: Membership is available on the request after middleware runs

- GIVEN a request carries a valid `X-Workspace-Id` header resolving to an existing Membership
- WHEN `TenancyMiddleware` processes the request
- THEN `request.membership` MUST be set to that resolved `Membership` instance

#### Scenario: No membership resolved leaves request.membership unset or None

- GIVEN a request's `X-Workspace-Id` does not resolve to any Membership for the caller
- WHEN `TenancyMiddleware` processes the request
- THEN `request.membership` MUST NOT be set to a Membership belonging to a different caller or workspace
- AND downstream permission checks relying on `request.membership` MUST deny the request

### Requirement: Cross-Origin Credentialed Requests Restricted to Trusted Origins

The system MUST permit cross-origin, credentialed (cookie-bearing) requests
only from an explicit allowlist of trusted origins (CORS allowlist and
`CSRF_TRUSTED_ORIGINS`). Requests from origins outside the allowlist MUST NOT
receive `Access-Control-Allow-Credentials` and MUST NOT be able to complete a
credentialed CSRF-protected write.

#### Scenario: Trusted origin can complete a credentialed request

- GIVEN a request originates from an origin present in the CORS/CSRF trusted-origin allowlist
- WHEN the client sends a credentialed request with the CSRF token echoed
- THEN the response MUST include CORS headers permitting that origin with credentials
- AND the request MUST be processed normally

#### Scenario: Untrusted origin is rejected

- GIVEN a request originates from an origin NOT present in the trusted-origin allowlist
- WHEN the client sends a credentialed cross-origin request
- THEN the system MUST NOT grant that origin `Access-Control-Allow-Credentials`
- AND a state-changing request from that origin MUST be rejected

### Requirement: Workspace-List Read Exposes Only the Caller's Own Membership Rows

The workspace-list read (`GET /api/workspaces/`) necessarily queries across
membership rows spanning multiple workspaces to find the caller's own
memberships. This query MUST still be scoped to rows where the membership's
user is the requesting caller, and MUST NOT leak membership or workspace rows
belonging only to other users.

#### Scenario: Cross-workspace read stays scoped to the caller's own rows

- GIVEN memberships exist for multiple users across multiple workspaces
- WHEN the workspace-list read executes for caller U
- THEN only membership rows where the user is U MUST be returned
- AND no membership row belonging to a different user MUST be returned, regardless of workspace

### Requirement: Celery Generation Tasks Must Establish Their Own Workspace RLS Context

A Celery task performing asynchronous work (e.g., LessonPlan generation) runs OUTSIDE `TenancyMiddleware` and
therefore does NOT inherit any request-scoped `contextvar` or `SET LOCAL
app.workspace_id` from an HTTP request. Before performing any scoped read or write, the
task MUST explicitly resolve the target workspace (from the arguments passed at enqueue
time, e.g. the `LessonPlan` id and its workspace) and MUST itself execute `SET LOCAL
app.workspace_id` for that workspace within its own transaction, and MUST set the
workspace-scoped `contextvar` for the ORM manager before any `ScopedModel` read or write.
A task that fails to establish this context MUST NOT read or write rows belonging to any
workspace — it MUST fail closed (empty reads, denied writes), never fall back to an
unscoped or wrong-workspace view.

This requirement MUST be proven under REAL (non-eager) Celery task execution — i.e. the
task dispatched to and consumed by an actual worker process (or a test harness that
executes the task body in a separate execution context from the enqueuing request),
NOT `CELERY_TASK_ALWAYS_EAGER=True` synchronous inline execution. Eager mode executes
the task inline within the enqueuing request/thread and would silently inherit that
request's already-set workspace context, which would pass even if the task itself never
set the context — hiding exactly the bug this requirement guards against.

#### Scenario: Task sets its own workspace context before reading/writing

- GIVEN a Celery generation task is dispatched with a `LessonPlan` id belonging to workspace A
- AND the task executes in a worker context with no inherited request-scoped workspace contextvar
- WHEN the task begins execution
- THEN the task MUST resolve workspace A from the passed arguments
- AND MUST execute `SET LOCAL app.workspace_id` for workspace A in its own transaction
- AND MUST set the ORM's workspace-scoped contextvar to workspace A before any `LessonPlan` read or write

#### Scenario: Task without established context fails closed, not cross-tenant

- GIVEN a Celery task implementation that omits the workspace-context-setting step (simulating a regression)
- WHEN that task attempts to read or write a `LessonPlan` row
- THEN the read MUST return zero rows or the write MUST be denied
- AND the task MUST NOT read or write a row belonging to a different workspace than the one implied by its arguments

#### Scenario: Test proves the behavior under real (non-eager) task execution

- GIVEN a test harness that dispatches the Celery generation task through an actual worker/broker execution path (not `CELERY_TASK_ALWAYS_EAGER`)
- AND the enqueuing request context is torn down or otherwise not accessible to the worker
- WHEN the task runs and is asserted to correctly scope its reads/writes to the target workspace
- THEN the test MUST fail if the task relies on an inherited contextvar instead of setting the context itself
- AND the test suite MUST document why eager-mode execution is insufficient to prove this requirement

---

**Source**: M2a — Tenancy Foundation Core (proposal: `2026-07-22-m2a-tenancy-core`); M3 — School Structure (proposal: `m3-school-structure`); M3 — Frontend Foundation (proposal: `m3-frontend-foundation`); M4 — AI planeaciones (proposal: `m4-ai-planeaciones`)
