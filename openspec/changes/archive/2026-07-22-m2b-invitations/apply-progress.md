# Apply Progress: m2b-invitations

**Mode**: Strict TDD
**Branch**: `m2b-invitations` (feature-branch-chain, one commit per delivery)
**Status**: 6/6 deliveries complete (D6 gap-fix added post-verify). All tasks `[x]` in `tasks.md`.

## TDD Cycle Evidence

| Delivery | RED (test written first, observed failing) | GREEN (implementation, observed passing) | REFACTOR |
|---|---|---|---|
| D1 model+migration | `test_invitations.py` model tests (3) — 2 failed on `ImportError: cannot import name 'WorkspaceInvitation'` before model existed | `WorkspaceInvitation` model + `0005_workspaceinvitation.py` migration (dep on `0004`, no `SCOPED_TABLES` change) — 3/3 passed | None needed |
| D2 invite_member | 4 tests appended — all 4 failed on `ImportError: cannot import name 'invite_member'` | `invite_member()` in `services.py` (has_permission gate, `secrets.token_urlsafe(32)`, `now()+7d`) — 4/4 passed | None needed |
| D3 accept_invitation | 5 tests appended — all 5 failed on `ImportError: cannot import name 'accept_invitation'` | `accept_invitation()` — lazy-expiry-first check, terminal-state guard, email-ownership guard, atomic get_or_create Membership + status flip — 5/5 passed | None needed |
| D4 revoke_invitation | 3 tests appended — all 3 failed on `ImportError: cannot import name 'revoke_invitation'` | `revoke_invitation()` — has_permission gate, explicit workspace-ownership check, terminal-state guard — 3/3 passed | None needed |
| D5 discovery hook | 4 tests appended — 1 failed on `ImportError` (discover_pending_invites), 3 failed on `AttributeError: 'User' object has no attribute 'pending_invites'` (provision_signup still returned bare `User`) | `discover_pending_invites()` + `provision_signup()` now returns `SignupResult(user, pending_invites)`; discovery called after the atomic block, never creates Membership — 4/4 passed | Updated `test_services.py`'s existing assertion (`user = provision_signup(...)` → `result = provision_signup(...); user = result.user`) since D5 changed `provision_signup`'s return contract — required to keep the pre-existing M2a test green |
| D6 list_invitations (gap-fix) | 4 tests appended (owner-can-list, admin-can-list, member-denied, other-workspace-not-leaked) — all 4 failed on `ImportError: cannot import name 'list_invitations'` before the function existed | `list_invitations(*, membership)` in `services.py` — `has_permission(membership, "manage_members")` gate, explicit `WorkspaceInvitation.objects.filter(workspace=membership.workspace, status=pending)` (no RLS/`ScopedManager`) — 4/4 passed | None needed |

## Work Unit Evidence

| Unit | Focused test command + result | Runtime harness | Rollback boundary |
|---|---|---|---|
| D1 | `uv run pytest workspaces/tests/test_invitations.py -k model -q` → 3 passed | `python manage.py migrate --check` (exit 1 before apply, exit 0 after `migrate` applied `0005`); confirmed `workspaces_workspaceinvitation` absent from `SCOPED_TABLES` in both `0003_rls.py` and `0004_rls_fix_empty_setting.py` | `manage.py migrate workspaces 0004` (plain `CreateModel` reverses cleanly); commit `34d5df9` |
| D2 | `uv run pytest workspaces/tests/test_invitations.py -k invite_member -q` → 4 passed | N/A — pure service call exercised directly by tests (owner/admin/member paths), no separate shell/process boundary | Revert `invite_member` from `services.py`; commit `de81a0b` |
| D3 | `uv run pytest workspaces/tests/test_invitations.py -k accept_invitation -q` → 5 passed | N/A — same as D2 | Revert `accept_invitation`; commit `df98c03` |
| D4 | `uv run pytest workspaces/tests/test_invitations.py -k revoke_invitation -q` → 3 passed | N/A — same as D2 | Revert `revoke_invitation`; commit `b08e73e` |
| D5 | `uv run pytest workspaces/tests/test_invitations.py -k discover -q` → 1 passed (`discover`-substring match); full `-k "discover or signup"` → 4 passed | Exercised via `provision_signup(...)` end-to-end (workspace+user+membership+discovery in one call), matching the real signup call path | Remove `discover_pending_invites` call + revert `provision_signup`/`SignupResult`; also revert the `test_services.py` assertion update; commit `171f637` |

Full suite after every GREEN step: 42 → 46 → 51 → 54 → 58 → 62 passed, 0 failed (final: `uv run pytest -q` → **62 passed**).

## Commits

1. `34d5df9` feat(workspaces): WorkspaceInvitation model + migration
2. `de81a0b` feat(workspaces): invite_member service
3. `df98c03` feat(workspaces): accept_invitation service
4. `b08e73e` feat(workspaces): revoke_invitation service
5. `171f637` feat(workspaces): signup discovery hook
6. (pending) feat(workspaces): list_invitations service

## Deviations from Design

- **`provision_signup` return shape**: design.md said "attach result to signup return value" without pinning the exact shape. Introduced `SignupResult(user, pending_invites)` (a `dataclasses.dataclass`) instead of a bare `User`, since the spec requires surfacing discovered invites "in the signup result." This is a breaking change to `provision_signup`'s public contract, so the pre-existing M2a test in `test_services.py` was updated (`result.user` instead of a bare `user`) to keep the suite green. No other caller of `provision_signup` exists in the codebase (verified via `rg`).
- Everything else matches design.md's Interfaces/Contracts section exactly (field names, types, guard ordering, atomicity boundaries).

## Issues Found

None.

## D6: list_invitations (gap-fix)

Verify (`verify-report.md`) found one CRITICAL gap: `specs/invitations/spec.md`'s RLS Exclusion
requirement includes the scenario "Inviter-side access is filtered explicitly, not by RLS" —
owner/admin listing pending invites for their workspace via an explicit `workspace=` filter,
gated by `has_permission(membership, "manage_members")`. This was never scheduled in
design.md/tasks.md for D1-D5 and had no implementation or test.

Implemented `list_invitations(*, membership)` in `backend/workspaces/services.py`, matching
`invite_member`'s/`revoke_invitation`'s existing denial pattern (`has_permission` gate →
`PermissionDenied`) and `revoke_invitation`'s explicit-workspace-filter pattern. The spec
scenario text says only "filter by an explicit `workspace=` clause... not rely on RLS" with no
expiry-semantics wording, so this returns a plain filtered read (`status=pending`, scoped to the
caller's own `membership.workspace`) — no lazy-expiry mutation was added, since that behavior is
only specified for the accept flow (`accept_invitation`), not for listing.

### Work Unit Evidence (D6)

| Evidence | Value |
|---|---|
| Focused test command + result | `uv run pytest workspaces/tests/test_invitations.py -k list_invitations -q` → 4 passed |
| Runtime harness | N/A — pure service call exercised directly by tests (owner/admin/member/other-workspace paths), same as D2/D4 (no separate shell/process boundary) |
| Rollback boundary | Revert `list_invitations` from `services.py` and the 4 `test_list_invitations_*` tests from `test_invitations.py`; D1-D5 unaffected |

### Deviations from Design (D6)

None — `list_invitations` was absent from design.md entirely (this was the gap itself); the
implementation follows the spec scenario text directly and reuses the exact authorization/filter
patterns already established by `invite_member` and `revoke_invitation` in D2/D4.

## Remaining Tasks

None — all D1-D6 tasks are `[x]` in `tasks.md`.

## Status

6/6 deliveries complete. Ready for verify.
