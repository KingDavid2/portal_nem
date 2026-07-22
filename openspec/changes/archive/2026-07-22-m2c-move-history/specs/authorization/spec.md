# Delta for Authorization

## ADDED Requirements

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

---

**Source**: M2c — Move member + workspace history (proposal: `m2c-move-history`)
