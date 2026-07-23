# AI Planeaciones Specification

## Purpose

Defines the `LessonPlan` entity, the generation request/response lifecycle, the async
Celery-backed generation flow, CRUD contracts, and export for AI-generated NEM/ABPC
planeaciones. This spec applies M3's `ScopedModel`/service/viewset patterns to the
lesson-plan domain and layers on an asynchronous, provider-driven generation step.

## Requirements

### Requirement: LessonPlan Is a Workspace-Scoped Entity With Its Own Denormalized FK

`LessonPlan` MUST subclass `ScopedModel` and MUST carry its own denormalized `workspace`
foreign key, not derived via a join through `Group`. `LessonPlan.group` MUST be a foreign
key to `schools.Group` with `on_delete=PROTECT`. The generated ABPC proyecto MUST be
stored as a JSON field. `LessonPlan` MUST record provenance: `provider`, `model`,
`tokens` (or equivalent usage metric), `cost`, `generated_at`, and a `status` field
constrained to `pending`, `ready`, or `failed`.

#### Scenario: LessonPlan row carries its own workspace FK

- GIVEN a `LessonPlan` linked to a `Group`
- WHEN the `LessonPlan` row is inspected
- THEN it MUST have a `workspace_id` column populated directly on the `LessonPlan` table
- AND this value MUST NOT be computed by joining through `Group`

#### Scenario: Deleting a Group with lesson plans is blocked

- GIVEN a `Group` has one or more `LessonPlan` rows referencing it
- WHEN a caller with `edit_content` requests deletion of that `Group`
- THEN the system MUST return a 4xx response describing the conflict
- AND MUST NOT delete the `Group`

### Requirement: Generation Request Is Gated, Workspace-Bound, and Schema-Validated

Creating a generation request MUST be gated by the `edit_content` capability. The
workspace assigned to the new `LessonPlan` MUST be taken from the caller's active
`Membership`, never from client-supplied input. The request MUST accept a target
`Group`, a campo formativo, a grado, and a theme. Before the generated proyecto is
persisted as `ready`, it MUST be validated against the ABPC Pydantic schema. The system
MUST run a PDA-fidelity guard that flags any PDA in the generated content not present in
the source PDA set as an invented ("hallucinated") PDA.

#### Scenario: Caller without edit_content cannot request generation

- GIVEN a Membership lacking the `edit_content` capability
- WHEN the caller attempts to POST a generation request
- THEN the system MUST reject the request
- AND no `LessonPlan` row MUST be persisted

#### Scenario: Client-supplied workspace_id is ignored on generation

- GIVEN a caller with an active Membership in workspace A
- WHEN the caller submits a generation request with an explicit `workspace_id` for workspace B
- THEN the system MUST assign the new `LessonPlan` to workspace A

#### Scenario: Generated proyecto invents a PDA not in the source set

- GIVEN the LLM response references a PDA not present in the fixture PDA set for the requested campo formativo
- WHEN the PDA-fidelity guard evaluates the generated proyecto
- THEN the system MUST flag the invented PDA
- AND the resulting `LessonPlan` status MUST NOT be set to `ready` without surfacing the flag

### Requirement: Generation Runs Asynchronously via a Celery Task

A generation request MUST create a `LessonPlan` row with `status=pending` synchronously
within the request/response cycle, then enqueue a Celery task to perform the LLM call.
The request MUST return immediately (without blocking on the LLM call) with the pending
`LessonPlan`'s identifier. The Celery task MUST populate `proyecto` and provenance
fields and set `status=ready` on success, or set `status=failed` (with a reason) on any
error, timeout, or schema-parse failure. A client MUST be able to poll the retrieve
endpoint to observe the transition from `pending` to `ready` or `failed`.

#### Scenario: POST generate returns a pending LessonPlan immediately

- GIVEN a caller with `edit_content` submits a valid generation request
- WHEN the request is processed
- THEN the response MUST return a `LessonPlan` with `status=pending`
- AND the response MUST NOT wait for the LLM call to complete

#### Scenario: Celery task completes generation successfully

- GIVEN a pending `LessonPlan` has been enqueued for generation
- WHEN the Celery task runs and the LLM call succeeds and the output validates against the ABPC schema
- THEN the task MUST update the `LessonPlan` with the generated `proyecto` and provenance
- AND MUST set `status=ready`

#### Scenario: Celery task fails on schema-parse failure

- GIVEN a pending `LessonPlan` has been enqueued for generation
- WHEN the Celery task runs and the LLM output fails to validate against the ABPC schema
- THEN the task MUST set `status=failed`
- AND MUST record a failure reason
- AND MUST NOT leave the `LessonPlan` in `pending` indefinitely

#### Scenario: Client polls until generation completes

- GIVEN a `LessonPlan` is `pending`
- WHEN the client repeatedly calls the retrieve endpoint
- THEN each response MUST reflect the current `status`
- AND once the Celery task finishes, subsequent polls MUST return `ready` or `failed`

### Requirement: CRUD Endpoints Are Workspace-Scoped

`LessonPlan` MUST expose DRF list (scoped per `Group`), retrieve, and delete endpoints,
via `ScopedManager`, gated by a valid `X-Workspace-Id` header. Reads MUST be scoped to
the active workspace; requests targeting a row in a foreign workspace MUST return an
empty list or 404.

#### Scenario: List endpoint returns only the requested group's plans in the active workspace

- GIVEN `LessonPlan` rows exist for multiple groups across workspace A and workspace B
- WHEN a caller with an active Membership in workspace A lists plans for one of workspace A's groups
- THEN the response MUST contain only that group's workspace-A `LessonPlan` rows

#### Scenario: Retrieve of a foreign-workspace LessonPlan returns 404

- GIVEN a `LessonPlan` belongs to workspace B
- WHEN a caller with an active Membership in workspace A requests it by id
- THEN the response MUST be 404

### Requirement: Ready LessonPlan Can Be Exported as Docx or Markdown

A `LessonPlan` with `status=ready` MUST be exportable as a docx binary and as markdown
text, reflecting the stored proyecto content. Export of a `LessonPlan` that is not
`ready` MUST be rejected.

#### Scenario: Export ready plan as docx

- GIVEN a `LessonPlan` with `status=ready`
- WHEN the caller requests the docx export endpoint
- THEN the system MUST return a valid docx binary reflecting the stored proyecto

#### Scenario: Export of a pending plan is rejected

- GIVEN a `LessonPlan` with `status=pending`
- WHEN the caller requests an export endpoint for it
- THEN the system MUST reject the request
- AND MUST NOT return a partial or empty document
