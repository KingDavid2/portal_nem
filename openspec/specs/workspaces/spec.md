# Spec: workspaces

Workspace and membership models, provisioning, and lifecycle.

## Requirements

### Requirement: Workspace and Membership Models

The system MUST provide a `Workspace` model with a `type` field constrained to `personal` or `group`, and a `Membership` model linking a user to a workspace with a `role` field constrained to `owner`, `admin`, or `member` via a `CharField` with `choices` (not a free-text field).

#### Scenario: Workspace type restricted to allowed values

- GIVEN an attempt to create a Workspace with `type="enterprise"`
- WHEN the record is validated
- THEN the system MUST reject the value as not among the allowed choices

#### Scenario: Membership role restricted to allowed values

- GIVEN an attempt to create a Membership with `role="superadmin"`
- WHEN the record is validated
- THEN the system MUST reject the value as not among the allowed choices

### Requirement: Transactional Signup Provisioning

The system MUST provision, as a single atomic database transaction, a new User, a personal Workspace for that user, and an owner Membership linking them on signup. If any step fails, the system MUST leave no partial state (no orphaned user, workspace, or membership).

#### Scenario: Successful signup creates all three records

- GIVEN a valid signup payload (email + password)
- WHEN the signup request completes successfully
- THEN a User record MUST exist
- AND a personal Workspace MUST exist owned by that user
- AND a Membership with role `owner` MUST link the user to that workspace

#### Scenario: Failure during provisioning rolls back all records

- GIVEN a valid signup payload
- WHEN Membership creation fails after the User and Workspace have been created in the same transaction
- THEN the system MUST roll back the entire transaction
- AND no User, Workspace, or Membership record from this attempt MUST exist in the database afterward

---

**Source**: M2a — Tenancy Foundation Core (proposal: `2026-07-22-m2a-tenancy-core`)
