# Delta for tenancy-isolation

## ADDED Requirements

### Requirement: MCP Tools Must Establish Their Own Workspace RLS Context

An MCP tool body serving a tool call runs OUTSIDE `TenancyMiddleware` — over stdio
there is no HTTP request at all, and over the flag-gated Streamable-HTTP arm the
request carries a bearer token rather than a session and an `X-Workspace-Id`
header. A tool therefore does NOT inherit any request-scoped `contextvar` or
`SET LOCAL app.workspace_id`. Before performing any scoped read, the tool MUST
explicitly resolve the target workspace from the authenticated caller's
`Membership` (the row the API token resolves to, never ambient state) and MUST
itself enter `workspace_scope(membership.workspace_id)` — executing `SET LOCAL
app.workspace_id` within its own transaction and setting the workspace-scoped
`contextvar` for the ORM manager — before any `ScopedModel` read. A tool that
fails to establish this context MUST NOT read rows belonging to any workspace —
it MUST fail closed (empty reads), never fall back to an unscoped or
wrong-workspace view.

Because the MCP handler is asynchronous while `workspace_scope` is synchronous,
this requirement MUST be proven with the tool body executed through the same
`sync_to_async(..., thread_sensitive=True)` bridge production uses. A test that
calls the tool body inline from a context that already holds a workspace scope
would silently inherit that scope and would pass even if the tool never set the
context itself — hiding exactly the bug this requirement guards against.

#### Scenario: Tool sets its own workspace context before reading

- GIVEN an MCP tool call authenticated by a token resolving to a membership in workspace A
- AND the tool executes in a context with no pre-established workspace contextvar and no active `app.workspace_id`
- WHEN the tool begins execution
- THEN the tool MUST resolve workspace A from the caller's `Membership`
- AND MUST enter `workspace_scope(workspace A)` — executing `SET LOCAL app.workspace_id` in its own transaction and setting the ORM's workspace-scoped contextvar — before any `ScopedModel` read
- AND MUST return workspace A's rows

#### Scenario: Tool without established context fails closed, not cross-tenant

- GIVEN an MCP tool implementation stripped of its `workspace_scope` entry (simulating a regression)
- AND rows exist in more than one workspace
- WHEN that tool attempts to read a workspace-scoped row
- THEN the read MUST return zero rows
- AND the tool MUST NOT return rows from any workspace as a fallback

#### Scenario: Token for one workspace cannot fetch another workspace's row by id

- GIVEN a token resolving to a membership in workspace A
- AND a `LessonPlan` belonging to workspace B
- WHEN `get_lesson_plan` is invoked with workspace B's lesson-plan id
- THEN the tool MUST report the plan as not found
- AND the response MUST NOT contain any field of workspace B's row
- AND the not-found response MUST be indistinguishable from one for an id that exists nowhere

#### Scenario: Test proves the behavior across the async-to-sync boundary

- GIVEN a test harness that invokes the tool through the async MCP handler's `sync_to_async(..., thread_sensitive=True)` bridge
- AND no workspace scope is active in the calling context
- WHEN the tool is asserted to scope its reads to the caller's workspace
- THEN the test MUST fail if the tool relies on an inherited contextvar instead of entering `workspace_scope` itself
- AND the test suite MUST document why an inline call from an already-scoped context is insufficient to prove this requirement
