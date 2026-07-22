# Proposal: M2c — move_member_to_workspace service + workspace_history audit trail

## Intent

Members currently have no supported path to be relocated between workspaces, and membership lifecycle events (invite/accept/revoke/move) leave no auditable trail. M2c adds a service-layer atomic move plus a cross-workspace `workspace_history` audit model, so admins can reorganize members safely and every membership change is recorded. Service layer only — no HTTP endpoints in this change.

## Scope

### In Scope
- `move_member_to_workspace` service: single `transaction.atomic()` that revokes the member's source `Membership` and creates a new `Membership` in the target workspace (mirrors `provision_signup` atomicity).
- `WorkspaceHistory` model + migration; writes a `moved` audit row within the move transaction.
- Authorization via existing `manage_members` capability, required in BOTH source and target workspaces.
- TDD RED-first tests for atomicity, rollback, edge cases, and audit-row correctness.

### Out of Scope
- Retrofitting `invite_member`/`accept_invitation`/`revoke_invitation` to write history rows (fast-follow; schema is designed to support it now).
- Any HTTP/DRF views, serializers, or Celery notifications.
- History read/list API or per-workspace history RLS filtering.

## Capabilities

### New Capabilities
- `workspace-history`: audit trail model recording membership lifecycle events (actor, action, target user, source/target workspace refs, timestamp, metadata); RLS-excluded.

### Modified Capabilities
- `workspaces`: add the `move_member_to_workspace` service requirement and its move semantics/authorization rules.

## Approach

- **RLS**: `WorkspaceHistory` is EXCLUDED from `SCOPED_TABLES`. A `moved` row references two workspaces in one write; the middleware sets exactly one `app.workspace_id` per transaction, so an RLS `WITH CHECK` cannot be satisfied under `portal_app`. Same rationale that keeps `Membership` and `WorkspaceInvitation` unscoped. Add an explicit "do not add to SCOPED_TABLES" comment in the migration.
- **Columns**: `actor` (User FK, nullable for system events), `action` (CharField+choices: `invited`/`accepted`/`revoked`/`moved`), `target_user` (User FK), `from_workspace` (FK, nullable), `to_workspace` (FK, nullable), `created_at` (auto_now_add), `metadata` (JSONField, default dict). Move sets both workspace refs; invite/accept/revoke (future retrofit) set `to_workspace` only.
- **Move semantics**: reject moving a member whose role is `owner` (would orphan the source workspace); reject when target is not `group` type; reject when target is a personal workspace; if the user already holds a Membership in the target, raise (no duplicate, respects `unique_user_workspace_membership`); new Membership role defaults to `member` (never carries owner/admin across tenants).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/workspaces/models.py` | Modified | Add `WorkspaceHistory` model |
| `backend/workspaces/services.py` | Modified | Add `move_member_to_workspace`; optional `record_history` helper |
| `backend/workspaces/migrations/0006_workspacehistory.py` | New | CreateModel; RLS-excluded (comment) |
| `backend/workspaces/tests/test_move.py` (+ history) | New | TDD RED tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| History row accidentally RLS-scoped | Med | Explicit exclusion + migration comment + test writing a `moved` row under `portal_app` |
| Cross-tenant privilege escalation via move | Med | Require `manage_members` in both source and target; force new role to `member` |
| Owner move orphans workspace | Low | Reject moving `owner`-role memberships |

## Rollback Plan

Revert the feature commit and run `migrate workspaces 0005` to drop the `workspace_history` table. No data backfill; the table is additive and unreferenced by existing flows.

## Dependencies

- M2a tenancy core + M2b invitations (present in tree). No external dependencies.

## Success Criteria

- [ ] `move_member_to_workspace` moves a member atomically; a mid-transaction failure leaves no partial Membership change.
- [ ] Each successful move writes one `moved` `WorkspaceHistory` row with correct `from_workspace`/`to_workspace`/`actor`/`target_user`.
- [ ] Owner move, duplicate-target, personal-target, and non-group-target cases are rejected with clear errors.
- [ ] A `moved` row is writable under the restricted `portal_app` role (proves RLS exclusion).
- [ ] `manage_members` enforced in both source and target workspaces.
