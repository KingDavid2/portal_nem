# Tasks: M2c — Move Member + Workspace History

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~380-450 across D1-D4 |
| 400-line budget risk | Medium (borderline — split protects the margin) |
| Chained PRs recommended | Yes |
| Suggested split | D1 → D2 → D3 → D4 (4 commits on tracker branch) |
| Delivery strategy | force-chained |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Medium

Chain strategy and delivery strategy are already pinned in `state.yaml` (force-chained /
feature-branch-chain); `sdd-apply` proceeds delivery by delivery on branch
`m2c-move-history` without asking. Each delivery below is one commit on that tracker
branch.

### Suggested Work Units

| Unit | Goal | Commit | Focused test command | Runtime harness | Rollback boundary |
|------|------|--------|----------------------|-----------------|-------------------|
| D1 | `WorkspaceHistory` model + migration exist, excluded from RLS | model+migration | `pytest backend/workspaces/tests/test_move.py -k model` | `manage.py migrate --check`; confirm `workspace_history` absent from `SCOPED_TABLES` | `manage.py migrate workspaces 0005`; drops table cleanly |
| D2 | `move_member_to_workspace` atomic core: revoke source, create target (forced `member` role), write `moved` history row, rollback-safe | services.py | `pytest backend/workspaces/tests/test_move.py -k "move_member and not edge"` | Django shell: call service happy-path + patched-raise rollback | delete function, D1 unaffected |
| D3 | Dual-workspace authorization + same-actor-user guard + edge-case rejections (owner-move, personal/non-group target, duplicate target) | services.py | `pytest backend/workspaces/tests/test_move.py -k edge` | Django shell: call service missing `manage_members` on each side, mismatched actor users | remove edge-case guards, D1-D2 unaffected (service becomes permissive, not deployed) |
| D4 | RLS backstop: raw-psycopg `portal_app` two-workspace write succeeds with no scoped context; `migrate --check` clean | test_move.py + config confirmation | `pytest backend/workspaces/tests/test_move.py -k rls` | `manage.py migrate --check` | none (test-only addition) |

## Phase D1: feat(workspaces): WorkspaceHistory model + migration

- [x] 1.1 RED: `backend/workspaces/tests/test_move.py` — `WorkspaceHistory` not a `ScopedModel`/plain default `Manager` scenario, `action` choices reject an unlisted value (e.g. `"teleported"`) scenario, `workspace_history` table absent from `0003_rls.py::SCOPED_TABLES` scenario (import assertion against the migration module).
- [x] 1.2 GREEN: `backend/workspaces/models.py` — add `WorkspaceHistory` per design contract: `Action` `TextChoices` (`invited`, `accepted`, `revoked`, `moved`), `actor` (`ForeignKey(User, on_delete=SET_NULL, null=True, related_name="workspace_actions")`), `action` (`CharField(choices=...)`), `target_user` (`ForeignKey(User, on_delete=CASCADE, related_name="workspace_history")`), `from_workspace`/`to_workspace` (`ForeignKey(Workspace, on_delete=SET_NULL, null=True, related_name="history_from"/"history_to")`), `created_at` (`auto_now_add=True`), `metadata` (`JSONField(default=dict, blank=True)`), `Meta.db_table="workspaces_workspacehistory"`, default `Manager` — explicitly NOT `ScopedManager`/`ScopedModel`.
- [x] 1.3 GREEN: `backend/workspaces/migrations/0006_workspacehistory.py` — depends on `0005_workspaceinvitation`; plain `CreateModel`; inline comment stating the table is intentionally excluded from `0003_rls.py::SCOPED_TABLES` and why (two-workspace write cannot satisfy a single-`app.workspace_id` `WITH CHECK`).
- [x] 1.4 Note (design risk, explicit decision): `on_delete=SET_NULL` on `actor`/`from_workspace`/`to_workspace` is a deliberate choice (audit rows outlive the referenced actor/workspace); confirm this in the model docstring/comment rather than silently defaulting — revisit only if a future spec requires hard referential integrity on history rows.
- [x] 1.5 Commit: `feat(workspaces): WorkspaceHistory model + migration`.

## Phase D2: feat(workspaces): move_member_to_workspace atomic core

- [x] 2.1 RED (append to `test_move.py`): successful-move scenario (source Membership gone, target Membership `role="member"`, one `moved` `WorkspaceHistory` row with correct `actor`/`target_user`/`from_workspace`/`to_workspace`); role-forced-to-member scenario (admin-role source Membership still yields `role="member"` target, never `admin`/`owner`); rollback scenario (patch history-write step to raise mid-`transaction.atomic()` → source Membership intact, no target Membership, no history row).
- [x] 2.2 GREEN: `backend/workspaces/services.py` — `move_member_to_workspace(*, actor_source_membership: Membership, actor_target_membership: Membership, member: Membership) -> Membership`: inside one `transaction.atomic()`, in order — (a) skip authorization/edge checks here (deferred to D3, keep this delivery focused on the happy-path mechanics with checks stubbed permissive or minimally present), (b) delete source `Membership`, (c) create target `Membership` (`workspace=actor_target_membership.workspace`, `user=member.user`, `role="member"`), (d) create `WorkspaceHistory(action="moved", actor=<caller user>, target_user=member.user, from_workspace=member.workspace, to_workspace=actor_target_membership.workspace)`; return the new target `Membership`.
- [x] 2.3 Commit: `feat(workspaces): move_member_to_workspace atomic core`.

## Phase D3: feat(workspaces): move authorization + edge-case guards

- [x] 3.1 RED (append to `test_move.py`): dual-authorization-both-sides-required scenario (denied when `manage_members` missing on source OR on target, no writes either way — 2 cases); same-actor-user guard scenario (`actor_source_membership.user != actor_target_membership.user` → `PermissionDenied`, no writes) — security guard from design, explicit reject even if both memberships individually pass `manage_members`; owner-move-rejected scenario (`member.role == "owner"` → `ValueError`, source Membership unchanged, no history row); personal-target-rejected scenario (`to_workspace.type == "personal"` → `ValueError`); non-group-target-rejected scenario (`to_workspace.type != "group"` → `ValueError`); duplicate-target-membership-rejected scenario (`member.user` already has a Membership in target workspace → `ValueError`, honors `unique_user_workspace_membership`); source-workspace-mismatch scenario (`actor_source_membership.workspace != member.workspace` → `PermissionDenied`).
- [x] 3.2 GREEN: `backend/workspaces/services.py` — extend `move_member_to_workspace` with pre-write validation block, all checks executed before any write (order per design): (1) `PermissionDenied` if `actor_source_membership.user != actor_target_membership.user` (same-actor-user guard); (2) `PermissionDenied` if `not has_permission(actor_source_membership, "manage_members")` or `not has_permission(actor_target_membership, "manage_members")`; (3) `PermissionDenied` if `actor_source_membership.workspace != member.workspace`; (4) `ValueError` if `member.role == "owner"`; (5) `ValueError` if `actor_target_membership.workspace.type != "group"` (covers both personal and non-group cases); (6) `ValueError` if `Membership.objects.filter(user=member.user, workspace=actor_target_membership.workspace).exists()`. Never inline role strings outside the `has_permission` capability matrix call.
- [x] 3.3 Commit: `feat(workspaces): move authorization + edge-case guards`.

## Phase D4: test(workspaces): RLS backstop for cross-workspace history writes

- [ ] 4.1 RED/GREEN (append to `test_move.py`, mirrors `test_rls.py::_portal_app_connection()`): raw-psycopg-as-`portal_app`-writes-moved-row-with-no-scoped-context scenario — open a `portal_app`-role connection with `app.workspace_id` unset (or set only to the source workspace), `INSERT INTO workspaces_workspacehistory (...)` referencing two distinct `workspace_id` values (`from_workspace`, `to_workspace`) directly, assert the insert succeeds with no RLS `WITH CHECK` violation.
- [ ] 4.2 GREEN: confirm `python manage.py migrate --check` is clean (no missing migrations) after D1-D3; no production code changes expected in this delivery — test-only addition plus final config sanity check.
- [ ] 4.3 Commit: `test(workspaces): RLS backstop for move history writes`.
