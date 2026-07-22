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

---

**Source**: M2a — Tenancy Foundation Core (proposal: `2026-07-22-m2a-tenancy-core`)
