# School Structure Specification

## Purpose

Defines the CRUD data spine for the school hierarchy — School, SchoolYear, Group, Student — as workspace-scoped entities, their invariants, service-layer behavior, and DRF HTTP contracts. This spec is the foundation for M4 lesson plans and M5 grades/attendance.

## Requirements

### Requirement: Workspace-Scoped Entities With Own Denormalized FK

`School`, `SchoolYear`, `Group`, and `Student` MUST each subclass the workspace-scoped base model (`ScopedModel`) and MUST each carry their own denormalized `workspace` foreign key. No entity MUST derive its workspace via a join through a parent entity.

#### Scenario: Student row carries its own workspace FK

- GIVEN a `Student` linked to a `Group`, which is linked to a `SchoolYear`, which is linked to a `School`
- WHEN the `Student` row is inspected
- THEN it MUST have a `workspace_id` column populated directly on the `Student` table
- AND this value MUST NOT be computed by joining through `Group`/`SchoolYear`/`School`

### Requirement: Entity Field Shapes and Constraints

`School.name` MUST be required; `School.cct` MUST be optional; `School.level` MUST be an enum. `SchoolYear` MUST enforce uniqueness on `(school, label)`. `Group.grado` MUST be constrained to values 1–3; `Group.grupo` MUST be a single letter; `Group` MUST enforce uniqueness on `(school_year, grado, grupo)`. `Student.curp` MUST be stored and indexed but MUST NOT be unique. `Student.group` MUST be a foreign key with `on_delete=PROTECT`.

#### Scenario: Duplicate SchoolYear label rejected

- GIVEN a `SchoolYear` with label "2025-2026" already exists for School X
- WHEN a second `SchoolYear` with the same `(school=X, label="2025-2026")` is created
- THEN the system MUST reject the creation with a uniqueness violation

#### Scenario: Duplicate Group grado+grupo rejected

- GIVEN a `Group` with `grado=1, grupo="A"` exists for a given `SchoolYear`
- WHEN a second `Group` with the same `(school_year, grado=1, grupo="A")` is created
- THEN the system MUST reject the creation with a uniqueness violation

#### Scenario: Duplicate CURP is allowed

- GIVEN a `Student` with CURP "ABCD010101HDFRRL01" already exists
- WHEN a second `Student` with the identical CURP is created in the same workspace
- THEN the creation MUST succeed

### Requirement: CRUD Gated by edit_content Capability

Create, update, and delete operations on `School`, `SchoolYear`, `Group`, and `Student` MUST be gated by the `edit_content` capability, evaluated via the authorization capability matrix. Read operations MUST require only `view_workspace`.

#### Scenario: Caller without edit_content cannot create a School

- GIVEN a Membership lacking the `edit_content` capability
- WHEN the caller attempts to create a `School`
- THEN the system MUST reject the request
- AND no row MUST be persisted

### Requirement: Cross-Entity Workspace Consistency Validation

The service layer MUST validate that a child entity's referenced parent (e.g., `SchoolYear.school`, `Group.school_year`, `Student.group`) belongs to the same workspace as the child being created or updated. The workspace assigned to a new entity MUST be taken from the caller's active `Membership`, never from client-supplied input.

#### Scenario: Parent from a different workspace is rejected

- GIVEN a `School` belonging to workspace A
- AND the caller's active membership is in workspace B
- WHEN the caller attempts to create a `SchoolYear` referencing that `School`
- THEN the system MUST reject the creation
- AND MUST NOT persist a `SchoolYear` row

#### Scenario: Client-supplied workspace_id is ignored

- GIVEN a caller with an active Membership in workspace A
- WHEN the caller submits a create request with an explicit `workspace_id` for workspace B
- THEN the system MUST assign the new row to workspace A
- AND MUST NOT use the client-supplied `workspace_id`

### Requirement: DRF CRUD Endpoints Are Workspace-Scoped and Isolated

Each entity MUST expose DRF list, retrieve, create, update, and destroy endpoints. All endpoints MUST require a valid `X-Workspace-Id` header resolving to an active Membership. Reads MUST be scoped to the active workspace; requests targeting a row in a foreign workspace MUST return an empty list (for list) or 404 (for retrieve/update/destroy), never the foreign row's data.

#### Scenario: List endpoint returns only active-workspace rows

- GIVEN Students exist in both workspace A and workspace B
- WHEN a caller with an active Membership in workspace A calls the Student list endpoint
- THEN the response MUST contain only workspace A's Students

#### Scenario: Retrieve of a foreign-workspace row returns 404

- GIVEN a `Group` belongs to workspace B
- WHEN a caller with an active Membership in workspace A requests that `Group` by id
- THEN the response MUST be 404
- AND MUST NOT leak the row's existence or data

#### Scenario: Missing X-Workspace-Id is rejected

- GIVEN a request to any school-structure endpoint
- WHEN the `X-Workspace-Id` header is absent or does not resolve to an active Membership
- THEN the system MUST reject the request before reaching entity data

### Requirement: PROTECT Surfaces a Clean 4xx on Group Delete With Students

Deleting a `Group` that still has associated `Student` rows MUST be blocked by the `PROTECT` FK constraint and MUST surface as a clean 4xx API error, not an unhandled 500.

#### Scenario: Deleting a Group with students returns 4xx

- GIVEN a `Group` has one or more `Student` rows referencing it
- WHEN a caller with `edit_content` requests deletion of that `Group`
- THEN the system MUST return a 4xx response describing the conflict
- AND MUST NOT delete the `Group`
- AND MUST NOT raise an unhandled server error

---

**Source**: M3 — School Structure (proposal: `m3-school-structure`)
