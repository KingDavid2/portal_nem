# Design: M2c — move_member_to_workspace + workspace_history audit trail

## Technical Approach

Service-layer only. Add one atomic service `move_member_to_workspace` that revokes the
member's source `Membership` and creates a target-workspace `Membership`, writing one
`moved` `WorkspaceHistory` row inside the same `transaction.atomic()` — mirroring
`provision_signup`/`accept_invitation` atomicity. `WorkspaceHistory` is a plain-FK
model on the default `Manager` (NOT `ScopedModel`) and is EXCLUDED from RLS
`SCOPED_TABLES`, exactly like `WorkspaceInvitation`. Authorization reuses the
`has_permission(..., "manage_members")` capability matrix — never inline role strings.

## Architecture Decisions

### Decision: move signature — dual explicit actor memberships

**Choice**: `move_member_to_workspace(*, actor_source_membership: Membership,
actor_target_membership: Membership, member: Membership) -> Membership`.
- `member` is the moved user's `Membership` in the source workspace.
- Returns the newly created target-workspace `Membership` (role `member`).
- Raises `PermissionDenied` (auth/workspace-mismatch) and `ValueError` (edge cases).

**Alternatives considered**: (A) `actor: User` + service-internal `Membership` lookups
in both workspaces; (B) source `actor_membership` + opaque `target_authorization` arg.

**Rationale**: Existing services (`invite_member`, `revoke_invitation`,
`list_invitations`) all take resolved `Membership` objects and never do implicit
membership lookups — authorization inputs are explicit and caller-supplied. Two actor
memberships let the service check `manage_members` on BOTH sides via one matrix call
each, and satisfy the cross-workspace requirement without the service guessing which
membership the actor holds. Rejected (A): hides lookups, diverges from convention;
rejected (B): under-specifies the target check.

### Decision: WorkspaceHistory is RLS-excluded (plain FK model)

**Choice**: default `Manager`, plain `ForeignKey(Workspace)`, absent from
`SCOPED_TABLES`; migration carries a "do not add to SCOPED_TABLES" comment.

**Rationale**: A `moved` row references two workspaces in one INSERT. Middleware sets
exactly one `app.workspace_id` per transaction, so an RLS `WITH CHECK` keyed on a
single `workspace_id` can never be satisfied for a two-workspace write under
`portal_app`. Same rationale that keeps `Membership` and `WorkspaceInvitation`
unscoped. History read/list filtering is out of scope (fast-follow).

### Decision: single transaction, ordered writes

**Choice**: inside one `transaction.atomic()`: (1) validate edges, (2) delete source
`Membership`, (3) create target `Membership` (role `member`), (4) create
`WorkspaceHistory` `moved` row. Any exception rolls back all four.

**Rationale**: Matches `accept_invitation`'s get_or_create + save pattern. Rollback
proof: force the history write to raise (e.g. patch to raise mid-block) and assert the
source `Membership` still exists and no target `Membership`/history row was created.

## Data Flow

    caller ─(actor_source_membership, actor_target_membership, member)─▶ move service
       │  has_permission(manage_members) on BOTH sides
       ▼
    transaction.atomic():
       validate ─▶ delete source Membership ─▶ create target Membership ─▶ WorkspaceHistory(moved)
       (any failure → full rollback; both source+target Membership + history unscoped)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/workspaces/models.py` | Modify | Add `WorkspaceHistory` (default Manager) |
| `backend/workspaces/services.py` | Modify | Add `move_member_to_workspace` (+ optional `record_history` helper) |
| `backend/workspaces/migrations/0006_workspacehistory.py` | Create | CreateModel; RLS-excluded with comment |
| `backend/workspaces/tests/test_move.py` | Create | RED-first move + history + RLS-backstop tests |

## Interfaces / Contracts

```python
class WorkspaceHistory(models.Model):
    class Action(models.TextChoices):
        INVITED = "invited", "Invited"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"
        MOVED = "moved", "Moved"

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, related_name="workspace_actions")
    action = models.CharField(max_length=20, choices=Action.choices)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name="workspace_history")
    from_workspace = models.ForeignKey(Workspace, on_delete=models.SET_NULL, null=True,
                                       related_name="history_from")
    to_workspace = models.ForeignKey(Workspace, on_delete=models.SET_NULL, null=True,
                                     related_name="history_to")
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "workspaces_workspacehistory"
    # objects = default Manager (NOT ScopedManager)
```

Edge-case enforcement (order, all before writes): `PermissionDenied` if either actor
lacks `manage_members` or `actor_source_membership.workspace != member.workspace`;
`ValueError` if `member.role == owner`, `to_workspace.type != group`,
`to_workspace.type == personal`, or `member.user` already has a target Membership
(honors `unique_user_workspace_membership`). New role forced to `member`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Happy path: source Membership gone, target Membership role=`member`, one `moved` row with correct actor/target_user/from/to | `pytest.mark.django_db` |
| Unit | Rollback: history write raises → source Membership intact, no target/history rows | patch to raise inside atomic |
| Unit | Edges: owner-move, personal-target, non-group-target, duplicate-target, missing `manage_members` (each side) | assert raises + no writes |
| Model | `WorkspaceHistory` not `ScopedModel`; absent from `0003_rls.SCOPED_TABLES` | import assertions |
| Integration | RLS backstop: write a `moved` row via raw psycopg as `portal_app` with NO `app.workspace_id` set → succeeds | mirror `test_rls.py` `_portal_app_connection()` |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification,
or process-integration boundary. Pure Django service + migration.

## Migration / Rollout

Additive table only. Rollback: revert commit and `migrate workspaces 0005` to drop
`workspaces_workspacehistory`. No backfill; table is unreferenced by existing flows.

## Open Questions

- [ ] None blocking. Retrofitting invite/accept/revoke to write history rows is
  deferred (out of scope); schema already supports it via nullable `from_workspace`.
