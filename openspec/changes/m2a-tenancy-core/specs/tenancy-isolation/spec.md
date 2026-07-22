# Delta for tenancy-isolation

## ADDED Requirements

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
