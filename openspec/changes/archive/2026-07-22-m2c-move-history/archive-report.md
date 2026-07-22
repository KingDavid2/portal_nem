# Archive Report: M2c — Move Member + Workspace History

**Archived**: 2026-07-22  
**Status**: CLOSED — Change fully planned, implemented, verified, and archived.

## Executive Summary

The M2c change delivered a complete `move_member_to_workspace` service and cross-workspace `WorkspaceHistory` audit model, with dual-workspace authorization, comprehensive edge-case rejection, and RLS-exclusion enforcement. Full verification passed: 76/76 tests green, all spec requirements met, all 4 deliveries complete.

## Artifact Traceability (Engram Observation IDs)

| Artifact | Observation ID | Type | Status |
|----------|---|---|---|
| Proposal | #50 | architecture | Complete |
| Spec | #51 | architecture | Complete |
| Design | #52 | architecture | Complete |
| Tasks | #53 | architecture | Complete (all [x]) |
| Verify Report | #55 | architecture | PASS (76/76) |

## Deliveries

### D1: feat(workspaces): WorkspaceHistory model + migration
**Commit**: dfbcc62  
**What**: `WorkspaceHistory` model (default Manager, NOT ScopedModel), migration 0006_workspacehistory (RLS-excluded with explicit comment)

### D2: feat(workspaces): move_member_to_workspace atomic core
**Commit**: 45babe1  
**What**: `move_member_to_workspace` service happy-path mechanics (revoke source, create target, write history row) inside single `transaction.atomic()`

### D3: feat(workspaces): move authorization + edge-case guards
**Commit**: 869dec5  
**What**: Dual-workspace `manage_members` authorization, same-actor-user security guard, edge rejections (owner-move, personal/non-group target, duplicate target)

### D4: test(workspaces): RLS backstop for move history writes
**Commit**: 9f69dee  
**What**: Raw-psycopg `portal_app` RLS backstop test proving cross-workspace history writes succeed with no scoped context

**Docs commit**: 30589fc (roadmap update)

## Spec Merges

| Domain | Action | Details |
|--------|--------|---------|
| workspace-history | Created | New full spec: 2 requirements (model shape, RLS exclusion) |
| workspaces | Updated | Added "Atomic Member Move Between Workspaces" requirement (6 scenarios) |
| authorization | Updated | Added "Dual-Workspace Authorization for Member Moves" requirement (3 scenarios) |

## Test Results

| Command | Result |
|---|---|
| `cd backend && uv run pytest -q` | **76 passed** (exit 0) |
| `cd backend && uv run python manage.py migrate --check` | **clean, no pending migrations** (exit 0) |

**Test file**: `backend/workspaces/tests/test_move.py` — 14 tests (3 model, 3 happy-path, 7 authorization/edge-case, 1 RLS backstop)

## Spec Compliance

### workspace-history Spec
- [x] WorkspaceHistory model shape (actor, action, target_user, from_workspace, to_workspace, created_at, metadata)
- [x] Moved row records both workspace references
- [x] Action field restricted to allowed values
- [x] RLS exclusion (not in SCOPED_TABLES, not ScopedModel)
- [x] Moved row writable under portal_app with no scoped context (RLS backstop)
- [x] History table absent from SCOPED_TABLES configuration

### workspaces Spec
- [x] Atomic member move (single transaction.atomic(), revoke source + create target + history row)
- [x] New membership role always forced to member
- [x] Failure mid-move rolls back both sides
- [x] Moving workspace owner is rejected
- [x] Non-group/personal target workspace is rejected
- [x] Existing target membership is rejected

### authorization Spec
- [x] Dual-workspace manage_members check (source AND target required)
- [x] Caller authorized in both workspaces succeeds
- [x] Caller lacking manage_members in target workspace is denied
- [x] Caller lacking manage_members in source workspace is denied

## Critical Security Guards

**Same-Actor-User Guard**: `actor_source_membership.user == actor_target_membership.user`, else `PermissionDenied` with no writes. Present in code (services.py), tested independently, and documented as CRITICAL.

## Archive Contents

- proposal.md ✓
- design.md ✓
- tasks.md ✓ (4/4 deliveries, all tasks [x])
- apply-progress.md ✓ (all 4 commits logged)
- verify-report.md ✓ (PASS, 76/76)
- specs/workspace-history/spec.md ✓
- specs/workspaces/spec.md ✓
- specs/authorization/spec.md ✓

## Migration Status

- Additive: `backend/workspaces/migrations/0006_workspacehistory.py` (CreateModel)
- Rollback: `python manage.py migrate workspaces 0005` drops `workspaces_workspacehistory` table cleanly
- No data loss; table unreferenced by existing flows

## Source of Truth Updated

The following main specs now reflect the new behavior and are source-of-truth:
- `openspec/specs/workspace-history/spec.md` (NEW)
- `openspec/specs/workspaces/spec.md` (MERGED: added move requirement)
- `openspec/specs/authorization/spec.md` (MERGED: added dual-workspace authorization requirement)

## SDD Cycle Complete

M2c follows a complete SDD workflow:
1. **Proposal** → Change intent, scope, capabilities, approach approved
2. **Spec** → 3 delta specs defined (workspace-history, workspaces, authorization)
3. **Design** → Technical decisions, data flow, testing strategy documented
4. **Tasks** → 4 chained deliveries (D1-D4) with focused test plans
5. **Apply** → All deliveries committed; spec sync to main; docs updated
6. **Verify** → Full test suite green (76/76); spec compliance confirmed; all artifacts present
7. **Archive** → Change folder moved to archive; main specs synced; cycle closed

## Outcome

**Status**: DONE  
**Next Phase**: Open for new changes

---

Generated: 2026-07-22  
Archive prepared for retrieval and audit trail.
