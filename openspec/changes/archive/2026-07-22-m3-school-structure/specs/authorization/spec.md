# Delta for authorization

## ADDED Requirements

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

---

**Source**: M3 — School Structure (proposal: `m3-school-structure`)
