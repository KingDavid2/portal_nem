# Delta for authorization

## ADDED Requirements

### Requirement: MCP Tool Dispatch Authorizes via a Capability Map

MCP tool dispatch MUST route every authorization decision through
`workspaces.permissions.has_permission(membership, action)`, using an explicit
capability map from tool name to capability — the same discipline
`WorkspacePermission` already applies to DRF view actions. The tool name MUST
first be translated through that map; the raw tool name (e.g. `"get_quota"`)
MUST NOT be passed to `has_permission`. Because the v1 surface is read-only,
every one of the five tools MUST map to `view_workspace`.

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

#### Scenario: No tool compares a role string inline

- GIVEN the `mcp_server` app source
- WHEN it is inspected for authorization logic
- THEN no comparison of `membership.role` against a literal role string MUST be present
- AND every decision MUST reach `has_permission`

#### Scenario: Permitted capability still blocked by workspace scoping

- GIVEN a caller whose membership in workspace A grants `view_workspace`
- WHEN a tool targets a resource belonging to workspace B
- THEN the workspace-scoped manager MUST deny access to that resource regardless of the `has_permission` result
