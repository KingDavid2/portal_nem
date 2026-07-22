# Apply Progress: m2b-invitations

**Mode**: Strict TDD
**Branch**: `m2b-invitations` (feature-branch-chain, one commit per delivery)
**Status**: 5/5 deliveries complete. All tasks `[x]` in `tasks.md`.

## TDD Cycle Evidence

| Delivery | RED (test written first, observed failing) | GREEN (implementation, observed passing) | REFACTOR |
|---|---|---|---|
| D1 model+migration | `test_invitations.py` model tests (3) — 2 failed on `ImportError: cannot import name 'WorkspaceInvitation'` before model existed | `WorkspaceInvitation` model + `0005_workspaceinvitation.py` migration (dep on `0004`, no `SCOPED_TABLES` change) — 3/3 passed | None needed |
| D2 invite_member | 4 tests appended — all 4 failed on `ImportError: cannot import name 'invite_member'` | `invite_member()` in `services.py` (has_permission gate, `secrets.token_urlsafe(32)`, `now()+7d`) — 4/4 passed | None needed |
| D3 accept_invitation | 5 tests appended — all 5 failed on `ImportError: cannot import name 'accept_invitation'` | `accept_invitation()` — lazy-expiry-first check, terminal-state guard, email-ownership guard, atomic get_or_create Membership + status flip — 5/5 passed | None needed |
| D4 revoke_invitation | 3 tests appended — all 3 failed on `ImportError: cannot import name 'revoke_invitation'` | `revoke_invitation()` — has_permission gate, explicit workspace-ownership check, terminal-state guard — 3/3 passed | None needed |
| D5 discovery hook | 4 tests appended — 1 failed on `ImportError` (discover_pending_invites), 3 failed on `AttributeError: 'User' object has no attribute 'pending_invites'` (provision_signup still returned bare `User`) | `discover_pending_invites()` + `provision_signup()` now returns `SignupResult(user, pending_invites)`; discovery called after the atomic block, never creates Membership — 4/4 passed | Updated `test_services.py`'s existing assertion (`user = provision_signup(...)` → `result = provision_signup(...); user = result.user`) since D5 changed `provision_signup`'s return contract — required to keep the pre-existing M2a test green |

## Work Unit Evidence

| Unit | Focused test command + result | Runtime harness | Rollback boundary |
|---|---|---|---|
| D1 | `uv run pytest workspaces/tests/test_invitations.py -k model -q` → 3 passed | `python manage.py migrate --check` (exit 1 before apply, exit 0 after `migrate` applied `0005`); confirmed `workspaces_workspaceinvitation` absent from `SCOPED_TABLES` in both `0003_rls.py` and `0004_rls_fix_empty_setting.py` | `manage.py migrate workspaces 0004` (plain `CreateModel` reverses cleanly); commit `34d5df9` |
| D2 | `uv run pytest workspaces/tests/test_invitations.py -k invite_member -q` → 4 passed | N/A — pure service call exercised directly by tests (owner/admin/member paths), no separate shell/process boundary | Revert `invite_member` from `services.py`; commit `de81a0b` |
| D3 | `uv run pytest workspaces/tests/test_invitations.py -k accept_invitation -q` → 5 passed | N/A — same as D2 | Revert `accept_invitation`; commit `df98c03` |
| D4 | `uv run pytest workspaces/tests/test_invitations.py -k revoke_invitation -q` → 3 passed | N/A — same as D2 | Revert `revoke_invitation`; commit `b08e73e` |
| D5 | `uv run pytest workspaces/tests/test_invitations.py -k discover -q` → 1 passed (`discover`-substring match); full `-k "discover or signup"` → 4 passed | Exercised via `provision_signup(...)` end-to-end (workspace+user+membership+discovery in one call), matching the real signup call path | Remove `discover_pending_invites` call + revert `provision_signup`/`SignupResult`; also revert the `test_services.py` assertion update; commit `171f637` |

Full suite after every GREEN step: 42 → 46 → 51 → 54 → 58 passed, 0 failed (final: `uv run pytest -q` → **58 passed**).

## Commits

1. `34d5df9` feat(workspaces): WorkspaceInvitation model + migration
2. `de81a0b` feat(workspaces): invite_member service
3. `df98c03` feat(workspaces): accept_invitation service
4. `b08e73e` feat(workspaces): revoke_invitation service
5. `171f637` feat(workspaces): signup discovery hook

## Deviations from Design

- **`provision_signup` return shape**: design.md said "attach result to signup return value" without pinning the exact shape. Introduced `SignupResult(user, pending_invites)` (a `dataclasses.dataclass`) instead of a bare `User`, since the spec requires surfacing discovered invites "in the signup result." This is a breaking change to `provision_signup`'s public contract, so the pre-existing M2a test in `test_services.py` was updated (`result.user` instead of a bare `user`) to keep the suite green. No other caller of `provision_signup` exists in the codebase (verified via `rg`).
- Everything else matches design.md's Interfaces/Contracts section exactly (field names, types, guard ordering, atomicity boundaries).

## Issues Found

None.

## Remaining Tasks

None — all D1-D5 tasks are `[x]` in `tasks.md`.

## Status

5/5 deliveries complete. Ready for verify.
