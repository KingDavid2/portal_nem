# Delta for Tenancy Isolation

## ADDED Requirements

### Requirement: Celery Generation Tasks Must Establish Their Own Workspace RLS Context

A Celery task performing LessonPlan generation runs OUTSIDE `TenancyMiddleware` and
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
