# Verify Report: m2b-invitations (re-verify after D6 gap-fix)

**Mode**: Full spec-driven verification (proposal + specs + design + tasks all present, Strict TDD active)
**Verdict**: **PASS**

## Completeness (tasks.md)

All 6 delivery phases (D1-D6), 21/21 sub-tasks checked `[x]`. Matches apply-progress.md's
"6/6 deliveries complete (D6 gap-fix added post-verify)" claim.

## Test Execution Evidence

| Command | Result |
|---|---|
| `uv run pytest -q` (from `backend/`) | **62 passed, 0 failed, 0 skipped** in ~6s |
| `uv run python manage.py migrate --check` | exit `0` — no missing migrations |

### Corrected baseline

The prior verify pass (pre-D6) confirmed via an isolated worktree checkout of commit `b201dbb`
(last commit before `m2b-invitations` work, end of M2a) that the true pre-m2b baseline is
**39 passed**, not 41 (as stated in an earlier verify prompt) nor 42 (apply-progress.md's D1-start
figure, which already includes fixture/setup work from this change's own branch). This report
adopts **39** as the corrected, source-verified baseline.

Current full suite: **62 passed** = 39 (baseline) + 23 added across D1-D6 (model/migration,
`invite_member`, `accept_invitation`, `revoke_invitation`, signup discovery hook,
`list_invitations`). Confirmed additive — 0 regressions, 0 removed tests.

## Gap-Fix Confirmation: "Inviter-side access is filtered explicitly, not by RLS"

Previously CRITICAL — now resolved:

- `list_invitations(*, membership)` exists in `backend/workspaces/services.py:143-157`.
- Gated by `has_permission(membership, "manage_members")`, raising `PermissionDenied` otherwise
  (source-verified at `services.py:151-152`) — confirmed by
  `test_list_invitations_denied_for_member_without_manage_members`.
- Filters explicitly by `WorkspaceInvitation.objects.filter(workspace=membership.workspace,
  status=WorkspaceInvitation.Status.PENDING)` — a plain `.filter()` on the default `Manager`,
  NOT `ScopedManager`/RLS (source-verified at `services.py:154-157`).
- Cross-workspace isolation proven at runtime, not just by inspection:
  `test_list_invitations_does_not_leak_other_workspace_invites` creates an invite in a second,
  unrelated workspace and asserts the caller's `list_invitations()` result is `[]` — a genuine
  negative-leak proof, paired with `test_list_invitations_owner_can_list_workspace_pending_invites`
  (non-empty companion assertion), so this is not an orphan empty-check.
- Owner and admin paths both covered separately
  (`test_list_invitations_owner_can_list_workspace_pending_invites`,
  `test_list_invitations_admin_can_list_workspace_pending_invites`).

All 4 tests pass (`uv run pytest workspaces/tests/test_invitations.py -k list_invitations -q` →
4 passed, confirmed in apply-progress.md's D6 Work Unit Evidence and re-verified in the full-suite
run above).

## Load-Bearing Design Constraints (re-verified, source-checked)

| Constraint | Verified | Evidence |
|---|---|---|
| `WorkspaceInvitation` NOT in `SCOPED_TABLES` | Yes | `0003_rls.py:18` and `0004_rls_fix_empty_setting.py:16` both list only `["workspaces_workspaceresource"]`; unchanged by D6 |
| `WorkspaceInvitation` uses default `Manager`, plain FK, not `ScopedModel` | Yes | `models.py:97-100` — class does not subclass `ScopedModel`, `workspace` is a plain `ForeignKey`; unchanged by D6 |
| `accept_invitation` atomic, idempotent for already-member, guards expired/terminal | Yes | unchanged from D3, re-confirmed passing in full suite |
| Discovery hook creates NO Membership | Yes | unchanged from D5, re-confirmed passing in full suite |
| `has_permission("manage_members")` gates invite/revoke/list | Yes | `invite_member`, `revoke_invitation`, and now `list_invitations` all call `has_permission(membership, "manage_members")` and raise `PermissionDenied` on failure |

All five load-bearing constraints hold. `list_invitations` correctly reuses the established
authorization/filter patterns from `invite_member`/`revoke_invitation` — no new architectural
risk introduced.

## Spec Compliance Matrix — `specs/invitations/spec.md`

| Requirement / Scenario | Covering test | Status |
|---|---|---|
| Model Shape — Token unique/unguessable | `test_token_is_generated_via_secrets_and_unique` | PASS |
| Model Shape — Expiry computed at creation | `test_invite_member_expiry_set_to_now_plus_seven_days` | PASS |
| RLS Exclusion — Invitee reaches own invite without membership | `test_workspace_invitation_is_not_a_scoped_model`, `test_workspace_invitation_table_absent_from_scoped_tables` | PASS |
| RLS Exclusion — Inviter-side access filtered explicitly, not by RLS | `test_list_invitations_owner_can_list_workspace_pending_invites`, `test_list_invitations_admin_can_list_workspace_pending_invites`, `test_list_invitations_denied_for_member_without_manage_members`, `test_list_invitations_does_not_leak_other_workspace_invites` | **PASS (resolved)** |
| Invite Creation Auth — Owner creates | `test_invite_member_owner_can_invite` | PASS |
| Invite Creation Auth — Admin creates | `test_invite_member_admin_can_invite` | PASS |
| Invite Creation Auth — Member denied | `test_invite_member_denied_for_member` | PASS |
| Accept Flow — Valid accept | `test_accept_invitation_valid_accept_creates_membership_and_flips_status` | PASS |
| Accept Flow — Email mismatch | `test_accept_invitation_email_mismatch_rejects` | PASS |
| Accept Flow — Expired rejected | `test_accept_invitation_expired_invite_rejected_and_persists_expired` | PASS |
| Accept Flow — Terminal rejected | `test_accept_invitation_terminal_invite_rejected_no_transition` | PASS |
| Idempotent Accept — Already member | `test_accept_invitation_already_member_is_idempotent_no_duplicate` | PASS |
| Revoke — Owner revokes pending | `test_revoke_invitation_owner_revokes_pending` | PASS |
| Revoke — Terminal rejected | `test_revoke_invitation_terminal_rejected` | PASS |
| Revoke — Member denied | `test_revoke_invitation_denied_for_member_without_manage_members` | PASS |
| Lazy Expiry — Stale pending surfaces as expired on read | `test_accept_invitation_expired_invite_rejected_and_persists_expired` | PASS (only via combined accept path — WARNING carried over, non-blocking) |
| Lazy Expiry — Expired cannot be accepted before lazy read | `test_accept_invitation_expired_invite_rejected_and_persists_expired` | PASS |
| Terminal State Machine — No transition out of terminal | `test_accept_invitation_terminal_invite_rejected_no_transition`, `test_revoke_invitation_terminal_rejected` | PASS |

**Zero remaining gaps in `specs/invitations/spec.md`.**

## Spec Compliance Matrix — `specs/workspaces/spec.md`

| Requirement / Scenario | Covering test | Status |
|---|---|---|
| Signup surfaces matching pending invite | `test_signup_surfaces_matching_pending_invite` | PASS |
| Signup with no invites unaffected | `test_signup_with_no_invites_is_unaffected` | PASS |
| Expired/terminal invites not surfaced | `test_signup_does_not_surface_expired_or_terminal_invites` | PASS |

**Zero remaining gaps in `specs/workspaces/spec.md`.**

## TDD Compliance (Strict TDD)

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | Yes | apply-progress.md's "TDD Cycle Evidence" table covers D1-D6 |
| All tasks have tests | Yes | 6/6 deliveries have dedicated test cases in `test_invitations.py` |
| RED confirmed (tests exist) | Yes | D6's 4 tests exist in `test_invitations.py:428-481`, verified by direct read |
| GREEN confirmed (tests pass) | Yes | 62/62 pass on independent execution in this verify pass |
| Triangulation adequate | Yes | D6 triangulated across owner/admin/member-denied/cross-workspace-leak (4 distinct assertions, not repeats) |
| Safety Net for modified files | Yes | `services.py` modified incrementally D2→D6, full suite green after each step per apply-progress.md |

**TDD Compliance**: 6/6 checks passed

### Assertion Quality (D6 scan)

No tautologies, no assertion-without-production-call, no ghost loops. All 4 D6 test cases call
`list_invitations()` directly and assert on its concrete return value (either an exact invite list
or `PermissionDenied`). `test_list_invitations_does_not_leak_other_workspace_invites` asserts an
empty list but has a companion non-empty assertion in the immediately preceding test — not an
orphan empty check.

**Assertion quality**: All assertions verify real behavior.

## Issues

### CRITICAL

None.

### WARNING

1. Design's own Testing Strategy called for a live-DB restricted-role/pooling integration test for
   RLS-exclusion proof (mirroring M2a's `test_pooling_leak.py`); what shipped is structural/unit-level
   coverage instead. Valid proxy proof, not a blocker (carried over from prior verify pass).
2. `provision_signup`'s return-type change to `SignupResult` remains a breaking contract change
   absorbed entirely inside this change (confirmed via `rg`, no external callers). Flag for any
   downstream API/serializer layer added later (carried over from prior verify pass).
3. Baseline test-count traceability is now corrected in this report (39, not 41/42) — the earlier
   discrepancy across verify-prompt/apply-progress.md docs is resolved; no further action needed.

### SUGGESTION

1. Consider a light integration/property test that forces a `token` collision (e.g. mock
   `secrets.token_urlsafe` to return a duplicate) to prove the DB `unique=True` constraint is
   enforced end-to-end (carried over from prior verify pass).

## Final Verdict

**PASS.** 62/62 tests pass (39 corrected baseline + 23 added, purely additive, 0 regressions) and
`migrate --check` is clean. All load-bearing design constraints hold in source. The previously
CRITICAL gap — inviter-side `list_invitations` filtered explicitly by `workspace=`, gated by
`manage_members`, with a runtime-proven cross-workspace isolation test — is now implemented and
covered. Every spec requirement/scenario across both delta specs (`specs/invitations/spec.md`,
`specs/workspaces/spec.md`) traces to a passing test. Zero remaining gaps. `sdd-archive` may
proceed.
