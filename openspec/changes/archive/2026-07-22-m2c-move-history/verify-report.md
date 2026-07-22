# Verification Report: m2c-move-history

**Mode**: full artifacts (proposal/specs/design/tasks all present)
**Verdict**: PASS

## Test / Build Evidence

| Command | Result |
|---|---|
| `cd backend && uv run pytest -q` | `76 passed in 8.33s` (exit 0) |
| `cd backend && uv run python manage.py migrate --check` | clean, no pending migrations (exit 0) |

## Task Completeness

All items in `tasks.md` (D1–D4, 4.1–4.3 across all phases) are `[x]`. 0 unchecked tasks found (`rg -c "^- \[ \]" tasks.md` → 0).

## Spec Compliance Matrix

### `workspace-history` spec

| Requirement/Scenario | Evidence | Status |
|---|---|---|
| WorkspaceHistory model shape (actor/action/target_user/from_workspace/to_workspace/created_at/metadata) | `backend/workspaces/models.py:146-186` — all fields present, `Action` TextChoices with `moved` | COMPLIANT |
| Moved row records both workspace references | `test_move_member_success_revokes_source_creates_target_and_writes_history` | COMPLIANT (test passes) |
| Action field restricted to allowed values | `test_workspace_history_action_restricted_to_allowed_values` | COMPLIANT |
| RLS exclusion — not in SCOPED_TABLES, not ScopedModel | `models.py` docstring confirms plain Manager; `0003_rls.py:18` and `0004_rls_fix_empty_setting.py:16` `SCOPED_TABLES = ["workspaces_workspaceresource"]` only — `workspace_history` absent from every RLS migration's list; `0006_workspacehistory.py:4-8` carries the "do not add to SCOPED_TABLES" comment | COMPLIANT |
| Moved row writable under `portal_app` with no scoped context (RLS backstop) | `test_rls_permits_moved_history_row_spanning_two_workspaces_with_no_scoped_context` — raw psycopg insert as `portal_app`, no `app.workspace_id` set, insert succeeds | COMPLIANT (test passes) |
| History table absent from SCOPED_TABLES config | `test_workspace_history_table_absent_from_scoped_tables` | COMPLIANT |

### `workspaces` spec

| Requirement/Scenario | Evidence | Status |
|---|---|---|
| Atomic member move (single `transaction.atomic()`, revoke source + create target + history row) | `services.py:165-256` — one `with transaction.atomic():` block wraps delete/create/create in order | COMPLIANT |
| New membership role always forced to `member` | `services.py:243` `role=Membership.Role.MEMBER` hardcoded, never derived from source role; `test_move_member_role_always_forced_to_member` | COMPLIANT |
| Rollback on mid-move failure | `test_move_member_rollback_on_failure_leaves_source_intact` — patches `WorkspaceHistory.objects.create` to raise, asserts source Membership intact, no target Membership, no history row | COMPLIANT |
| Owner-move rejected | `services.py:222-223` `ValueError` on `Membership.Role.OWNER`; `test_move_member_edge_owner_move_rejected` | COMPLIANT |
| Non-group/personal target rejected | `services.py:227-228`; `test_move_member_edge_personal_target_rejected` | COMPLIANT |
| Duplicate target membership rejected | `services.py:231-234`; `test_move_member_edge_duplicate_target_membership_rejected` | COMPLIANT |

### `authorization` spec

| Requirement/Scenario | Evidence | Status |
|---|---|---|
| Dual `manage_members` check (source AND target) | `services.py:206-212` — both `has_permission(actor_source_membership, ...)` and `has_permission(actor_target_membership, ...)` required | COMPLIANT |
| Caller authorized both sides succeeds | `test_move_member_success_...` (uses owner/admin memberships passing both checks) | COMPLIANT |
| Missing manage_members on target denied | `test_move_member_edge_denied_when_target_actor_lacks_manage_members` | COMPLIANT |
| Missing manage_members on source denied | `test_move_member_edge_denied_when_source_actor_lacks_manage_members` | COMPLIANT |

## Critical Security Constraint: Same-Actor-User Guard

Design/task-required guard: `actor_source_membership.user == actor_target_membership.user`, else `PermissionDenied`, no writes.

- **Code**: `services.py:197-204` — first check executed, before the dual `manage_members` check, comment marked "CRITICAL security guard, do not remove."
- **Test**: `test_move_member_edge_denied_when_actor_users_differ` (`tests/test_move.py:250-273`) — constructs two distinct users each independently satisfying `manage_members` on their own side (both `OWNER` role), asserts `PermissionDenied` is still raised and `_assert_no_writes` confirms no Membership/History mutation.
- **Verdict**: present and covered — CONFIRMED, not just declared.

## Migration / RLS Exclusion Cross-Check

Grepped `SCOPED_TABLES` across every workspaces migration:
- `0003_rls.py:18` → `["workspaces_workspaceresource"]`
- `0004_rls_fix_empty_setting.py:16` → `["workspaces_workspaceresource"]`
- `0006_workspacehistory.py` → no `SCOPED_TABLES` list at all (correctly just `CreateModel` + exclusion comment)

`workspace_history` never appears in any `SCOPED_TABLES` list. Confirms exclusion.

`on_delete=SET_NULL` confirmed on `actor`, `from_workspace`, `to_workspace` (models.py:169-186), matching design's audit-retention rationale.

## Signature / Design Match

`move_member_to_workspace(*, actor_source_membership: Membership, actor_target_membership: Membership, member: Membership) -> Membership` — matches design contract exactly (services.py:165-170). Returns `new_membership` (services.py:256).

## Scope Check

- `git diff --stat 29badc7..HEAD -- backend/workspaces` (excluding tests): only `migrations/0006_workspacehistory.py`, `models.py`, `services.py` touched.
- No HTTP/DRF files (`views.py`, `urls.py`, serializers) modified.
- No changes to `invite_member`/`accept_invitation`/`revoke_invitation` history-writing behavior (grep confirms no history calls added there) — invite/accept/revoke retrofit correctly out of scope.

## Issues

None found.

- CRITICAL: 0
- WARNING: 0
- SUGGESTION: 0

## Final Verdict

**PASS** — full suite green (76/76), `migrate --check` clean, every load-bearing spec/design constraint verified in code with passing covering tests, same-actor-user guard confirmed present and tested, RLS exclusion confirmed by direct grep across all migrations, no out-of-scope work detected, all tasks genuinely complete.
