# Workspace History Specification

## Purpose

Provide an auditable, cross-workspace trail of membership lifecycle events
(currently: `moved`). Governs the `WorkspaceHistory` model and its RLS
exclusion. Read/list APIs and retrofitting other lifecycle events
(invite/accept/revoke) are out of scope for this change.

## Requirements

### Requirement: WorkspaceHistory Model Shape

The system MUST provide a `WorkspaceHistory` model with fields: `actor`
(`ForeignKey(User)`, nullable, for system-initiated events), `action`
(`CharField` with `choices`, at minimum `moved`), `target_user`
(`ForeignKey(User)`), `from_workspace` (`ForeignKey(Workspace)`, nullable),
`to_workspace` (`ForeignKey(Workspace)`, nullable), `created_at`
(`auto_now_add`), and `metadata` (`JSONField`, default empty dict).

#### Scenario: Moved row records both workspace references

- GIVEN a member is moved from workspace A to workspace B
- WHEN the move completes
- THEN a `WorkspaceHistory` row with `action="moved"` MUST be created
- AND `from_workspace` MUST reference A and `to_workspace` MUST reference B
- AND `actor` MUST reference the user who performed the move
- AND `target_user` MUST reference the moved member

#### Scenario: Action field restricted to allowed values

- GIVEN an attempt to create a `WorkspaceHistory` row with `action="teleported"`
- WHEN the record is validated
- THEN the system MUST reject the value as not among the allowed choices

### Requirement: RLS Exclusion for Cross-Workspace Audit Rows

`WorkspaceHistory` MUST NOT be listed in `SCOPED_TABLES` and MUST NOT inherit
`ScopedModel`. A `moved` row references two distinct workspaces in a single
write, but the tenancy middleware sets exactly one `app.workspace_id` per
transaction; an RLS `WITH CHECK` scoped to a single workspace cannot be
satisfied for a row that legitimately spans two. This mirrors the existing
exclusion for `Membership` and `WorkspaceInvitation`. The migration MUST
include an explicit comment stating the table is intentionally excluded from
`SCOPED_TABLES` and why.

#### Scenario: Moved row is writable under the restricted database role

- GIVEN the move transaction runs under the `portal_app` restricted role with
  `app.workspace_id` set to the source workspace
- WHEN the `moved` `WorkspaceHistory` row is inserted with `to_workspace` set
  to a different workspace
- THEN the insert MUST succeed (no RLS `WITH CHECK` violation)

#### Scenario: History table absent from scoped tables configuration

- GIVEN the `SCOPED_TABLES` configuration used by the RLS migration
- WHEN it is inspected
- THEN `workspace_history` MUST NOT be present in that list

---

**Source**: M2c — Move member + workspace history (proposal: `m2c-move-history`)
