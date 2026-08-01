# Spec: authorization

Authorization, permission checks, and capability matrix.

## Requirements

### Requirement: Capability Matrix as Sole Authorization Path

The system MUST provide a `has_permission(membership, action)` function that is the single source of truth for authorization decisions (can-do-X). All authorization checks (views, serializers, DRF permission classes) MUST route through `has_permission`. The system MUST NOT contain inline role-string comparisons (e.g., `if membership.role == "admin"`) as a substitute for this check.

#### Scenario: Owner permitted a privileged action

- GIVEN a Membership with role `owner`
- WHEN `has_permission(membership, action="delete_workspace")` is evaluated
- THEN the result MUST be `True`

#### Scenario: Member denied a privileged action

- GIVEN a Membership with role `member`
- WHEN `has_permission(membership, action="delete_workspace")` is evaluated
- THEN the result MUST be `False`

#### Scenario: DRF permission class delegates to has_permission

- GIVEN an API view protected by the workspace DRF permission class
- WHEN a request is evaluated for a given membership and action
- THEN the permission class MUST call `has_permission` to decide the outcome
- AND MUST NOT independently compare `membership.role` against a literal string

### Requirement: Authorization Is Distinct From Tenancy Isolation

The system MUST keep authorization (can-do-X, decided by `has_permission`) architecturally separate from tenancy isolation (can-see-workspace-Y, decided by the scoped manager and RLS). A caller with permission to perform an action MUST still be denied if the target row is outside their active workspace.

#### Scenario: Permitted action still blocked by workspace scoping

- GIVEN a Membership with role `owner` in workspace A
- AND `has_permission` grants the requested action
- WHEN the action targets a resource belonging to workspace B
- THEN the workspace-scoped manager MUST deny access to that resource regardless of the `has_permission` result

### Requirement: Dual-Workspace Authorization for Member Moves

For a `move_member_to_workspace` operation, the system MUST require that the
caller's `Membership` satisfies `has_permission(membership, "manage_members")`
in BOTH the source workspace AND the target workspace. Satisfying the
capability in only one of the two workspaces MUST NOT be sufficient to
authorize the move.

#### Scenario: Caller authorized in both workspaces succeeds

- GIVEN a caller holds an `owner`-role Membership in source workspace A and an
  `admin`-role Membership in target workspace B
- WHEN the caller requests a move from A to B
- THEN the authorization check MUST pass for both workspaces
- AND the move MUST proceed

#### Scenario: Caller lacking manage_members in target workspace is denied

- GIVEN a caller holds an `owner`-role Membership in source workspace A
- AND the caller has no Membership (or only a `member`-role Membership) in
  target workspace B
- WHEN the caller requests a move from A to B
- THEN the system MUST reject the move
- AND no Membership or `WorkspaceHistory` changes MUST occur

#### Scenario: Caller lacking manage_members in source workspace is denied

- GIVEN a caller holds an `admin`-role Membership in target workspace B
- AND the caller has only a `member`-role Membership in source workspace A
- WHEN the caller requests a move from A to B
- THEN the system MUST reject the move
- AND no Membership or `WorkspaceHistory` changes MUST occur

### Requirement: WorkspacePermission Implements has_permission via a Capability Map

`WorkspacePermission` MUST implement `has_permission(request, view)` and MUST map the DRF view action to a capability using an explicit `capability_map`: `list` and `retrieve` MUST map to `view_workspace`; `create`, `update`, `partial_update`, and `destroy` MUST map to `edit_content`. `WorkspacePermission` MUST NOT feed raw DRF action verbs (e.g., `"create"`, `"destroy"`) directly into the capability matrix — the action MUST first be translated through `capability_map` into a capability name recognized by `has_permission(membership, action)`.

#### Scenario: List action maps to view_workspace

- GIVEN a DRF view with `action = "list"`
- WHEN `WorkspacePermission.has_permission` evaluates the request
- THEN it MUST resolve the required capability to `view_workspace`
- AND MUST call `has_permission(membership, "view_workspace")`

#### Scenario: Destroy action maps to edit_content

- GIVEN a DRF view with `action = "destroy"`
- WHEN `WorkspacePermission.has_permission` evaluates the request
- THEN it MUST resolve the required capability to `edit_content`
- AND MUST call `has_permission(membership, "edit_content")`

#### Scenario: Raw action verb never reaches the capability matrix

- GIVEN a DRF view with `action = "partial_update"`
- WHEN `WorkspacePermission.has_permission` evaluates the request
- THEN the literal string `"partial_update"` MUST NOT be passed to `has_permission`
- AND only the mapped capability (`edit_content`) MUST be passed

### Requirement: MCP Tool Dispatch Authorizes via a Capability Map

MCP tool dispatch MUST route every authorization decision through
`workspaces.permissions.has_permission(membership, action)`, using an explicit
capability map from tool name to capability — the same discipline
`WorkspacePermission` already applies to DRF view actions. The tool name MUST
first be translated through that map; the raw tool name (e.g. `"get_quota"`)
MUST NOT be passed to `has_permission`. Read tools MUST map to
`view_workspace`; create/update/delete school-structure tools MUST map to
`edit_content`.

No tool body, dispatcher, or transport MAY compare `membership.role` against a
literal string as a substitute for this check.

Authorization remains architecturally distinct from tenancy isolation: passing
`has_permission` MUST NOT by itself grant access to any row — the tool still
reads inside `workspace_scope`, and rows outside the caller's workspace stay
denied by the scoped manager and RLS.

#### Scenario: Tool name is mapped to a capability before the matrix is consulted

- GIVEN an authenticated caller invoking `get_quota`
- WHEN dispatch evaluates authorization
- THEN the literal string `"get_quota"` MUST NOT be passed to `has_permission`
- AND only the mapped capability `view_workspace` MUST be passed

#### Scenario: A role outside the capability matrix is denied every tool

- GIVEN a `Membership` whose role is not present in the capability matrix
- WHEN that caller invokes each of `list_groups`, `list_lesson_plans`, `get_lesson_plan`, `get_quota`, and `search_catalog`
- THEN every call MUST be denied
- AND no tool body MUST execute a scoped read

#### Scenario: Create tool requires edit_content

- GIVEN a `Membership` that lacks `edit_content`
- WHEN that caller invokes `create_student`
- THEN the call MUST be denied
- AND no student row MUST be created

#### Scenario: No tool compares a role string inline

- GIVEN the `mcp_server` app source
- WHEN it is inspected for authorization logic
- THEN no comparison of `membership.role` against a literal role string MUST be present
- AND every decision MUST reach `has_permission`

#### Scenario: Permitted capability still blocked by workspace scoping

- GIVEN a caller whose membership in workspace A grants `view_workspace`
- WHEN a tool targets a resource belonging to workspace B
- THEN the workspace-scoped manager MUST deny access to that resource regardless of the `has_permission` result

### Requirement: Attendance Endpoints Map Custom Actions to Capabilities

Attendance DRF views MUST authorize through `WorkspacePermission` with an explicit `capability_map` for custom actions: `roster` MUST map to `view_workspace`; `bulk` MUST map to `edit_content`. The literal action names `roster` and `bulk` MUST NOT be passed to `has_permission` — only the mapped capability names.

#### Scenario: Roster action maps to view_workspace

- GIVEN an attendance view with `action = "roster"`
- WHEN `WorkspacePermission.has_permission` evaluates the request
- THEN it MUST resolve the required capability to `view_workspace`
- AND MUST call `has_permission(membership, "view_workspace")`

#### Scenario: Bulk action maps to edit_content

- GIVEN an attendance view with `action = "bulk"`
- WHEN `WorkspacePermission.has_permission` evaluates the request
- THEN it MUST resolve the required capability to `edit_content`
- AND MUST call `has_permission(membership, "edit_content")`

#### Scenario: Member without edit_content cannot bulk-save

- GIVEN a Membership lacking `edit_content`
- WHEN the caller sends `PUT /api/attendance/bulk/`
- THEN the request MUST be denied before any attendance row is written

---

**Source**: M2a — Tenancy Foundation Core (proposal: `2026-07-22-m2a-tenancy-core`); M2c — Move member + workspace history (proposal: `m2c-move-history`); M3 — School Structure (proposal: `m3-school-structure`); Quizzy P4 — MCP server (proposal: `quizzy-p4-mcp-server`); M7 — Daily Attendance (proposal: `m7-attendance`)
