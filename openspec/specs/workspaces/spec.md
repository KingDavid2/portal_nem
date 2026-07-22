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

### Requirement: Signup-Time Invite Discovery

During signup provisioning, the system MUST look up pending
`WorkspaceInvitation` records matching the new user's email and surface them
as an association/discovery result. This lookup MUST NOT create any
`Membership` record; joining a workspace always requires a separate, explicit
accept step.

#### Scenario: Signup surfaces a matching pending invite

- GIVEN a `pending` invite exists for `newuser@example.com`
- WHEN a user signs up with email `newuser@example.com`
- THEN signup provisioning MUST discover the pending invite and include it in the signup result
- AND no Membership MUST be created for the invited workspace as a result of signup

#### Scenario: Signup with no matching invites is unaffected

- GIVEN no invite exists for `newuser2@example.com`
- WHEN a user signs up with email `newuser2@example.com`
- THEN signup provisioning MUST complete as before (personal Workspace, User, owner Membership)
- AND no invite-related side effects MUST occur

#### Scenario: Expired or terminal invites are not surfaced as actionable

- GIVEN an invite for `newuser@example.com` has `status` in `accepted|revoked|expired`, or `status=pending` with `expires_at` in the past
- WHEN a user signs up with email `newuser@example.com`
- THEN the system MUST NOT surface that invite as an actionable pending invite

---

**Source**: M2a — Tenancy Foundation Core (proposal: `2026-07-22-m2a-tenancy-core`); M2b — Invitations (proposal: `m2b-invitations`)
