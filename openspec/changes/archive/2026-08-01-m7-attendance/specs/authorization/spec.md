# Delta for authorization

## ADDED Requirements

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

**Source**: M7 — Daily Attendance (proposal: `m7-attendance`)
