# Delta for Workspaces

## ADDED Requirements

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

---

**Source**: M2c — Move member + workspace history (proposal: `m2c-move-history`)
