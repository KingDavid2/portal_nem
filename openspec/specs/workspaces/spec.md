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

### Requirement: Atomic Member Move Between Workspaces

The system MUST provide a `move_member_to_workspace` service that, as a single
`transaction.atomic()` block, revokes the member's `Membership` in the source
workspace and creates a new `Membership` in the target workspace, and writes
the corresponding `moved` `WorkspaceHistory` row (see `workspace-history`
spec) within the same transaction. The new `Membership`'s `role` MUST be
forced to `member` regardless of the member's role in the source workspace.
If any step fails, the system MUST roll back the entire transaction, leaving
both the source and target workspace memberships unchanged.

#### Scenario: Successful move revokes source and creates target membership

- GIVEN a `member`-role Membership for user U in workspace A (group type)
- AND workspace B is a group workspace with no existing Membership for U
- WHEN an authorized caller moves U from A to B
- THEN the Membership in A MUST be revoked/removed
- AND a new Membership for U in B MUST exist with `role="member"`
- AND a `moved` `WorkspaceHistory` row MUST be written in the same transaction

#### Scenario: New membership role is always forced to member

- GIVEN user U holds an `admin`-role Membership in workspace A
- WHEN U is moved to workspace B
- THEN the new Membership in B MUST have `role="member"`, never `admin` or `owner`

#### Scenario: Failure mid-move rolls back both sides

- GIVEN a valid move request from workspace A to workspace B
- WHEN Membership creation in B fails after the source Membership in A has
  been revoked within the same transaction
- THEN the system MUST roll back the entire transaction
- AND the original Membership in A MUST remain intact and unchanged
- AND no Membership MUST exist in B
- AND no `WorkspaceHistory` row MUST exist for this attempt

#### Scenario: Moving a workspace owner is rejected

- GIVEN user U holds an `owner`-role Membership in workspace A
- WHEN a caller attempts to move U from A to another workspace
- THEN the system MUST reject the move
- AND the Membership in A MUST remain unchanged
- AND no `WorkspaceHistory` row MUST be created

#### Scenario: Non-group or personal target workspace is rejected

- GIVEN a target workspace with `type="personal"`
- WHEN a caller attempts to move a member into that workspace
- THEN the system MUST reject the move
- AND no Membership or `WorkspaceHistory` changes MUST occur

#### Scenario: Existing target membership is rejected

- GIVEN user U already holds a Membership in workspace B
- WHEN a caller attempts to move U into workspace B from workspace A
- THEN the system MUST reject the move (no duplicate Membership)
- AND the Membership in A MUST remain unchanged

### Requirement: Workspace-List Endpoint Returns Only the Caller's Memberships

The system MUST expose `GET /api/workspaces/` returning the authenticated
caller's own memberships (workspace id, workspace name, workspace type, and
the caller's role), and MUST NOT include any other user's memberships or
workspaces the caller does not belong to.

#### Scenario: Returns the caller's own memberships

- GIVEN user U holds memberships in workspace A (role `owner`) and workspace B (role `member`)
- WHEN U sends `GET /api/workspaces/`
- THEN the response MUST include exactly A and B
- AND each entry MUST carry workspace id, name, type, and U's role in that workspace

#### Scenario: Never includes another user's workspaces

- GIVEN user U holds a membership only in workspace A
- AND another user holds a membership in workspace C, in which U has no membership
- WHEN U sends `GET /api/workspaces/`
- THEN the response MUST NOT include workspace C

#### Scenario: Anonymous request is denied

- GIVEN no valid session cookie is present
- WHEN a request is sent to `GET /api/workspaces/`
- THEN the system MUST deny the request with an authentication-required error

---

**Source**: M2a — Tenancy Foundation Core (proposal: `2026-07-22-m2a-tenancy-core`); M2b — Invitations (proposal: `m2b-invitations`); M2c — Move member + workspace history (proposal: `m2c-move-history`); M3 — Frontend Foundation (proposal: `m3-frontend-foundation`)
