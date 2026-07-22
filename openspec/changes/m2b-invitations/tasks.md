# Tasks: M2b — Invitations

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~550-700 across D1-D5 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | D1 → D2 → D3 → D4 → D5 (5 commits on tracker branch) |
| Delivery strategy | force-chained |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

Chain strategy and delivery strategy are already pinned in `state.yaml` (force-chained /
feature-branch-chain); `sdd-apply` proceeds delivery by delivery on branch `m2b-invitations`
without asking. Each delivery below is one commit on that tracker branch.

### Suggested Work Units

| Unit | Goal | Commit | Focused test command | Runtime harness | Rollback boundary |
|------|------|--------|----------------------|-----------------|-------------------|
| D1 | `WorkspaceInvitation` model + migration exist, excluded from RLS | model+migration | `pytest backend/workspaces/tests/test_invitations.py -k model` | `manage.py migrate --check`; confirm table absent from `SCOPED_TABLES` | `manage.py migrate workspaces 0004`; drops table cleanly |
| D2 | `invite_member` creates pending invite with capability gate | services.py | `pytest backend/workspaces/tests/test_invitations.py -k invite_member` | Django shell: call `invite_member` as owner/admin/member | delete function, D1 unaffected |
| D3 | `accept_invitation` atomic Membership + status flip, guards | services.py | `pytest backend/workspaces/tests/test_invitations.py -k accept_invitation` | Django shell: accept by token as matching/mismatched user | delete function, D1-D2 unaffected |
| D4 | `revoke_invitation` pending→revoked with capability gate | services.py | `pytest backend/workspaces/tests/test_invitations.py -k revoke_invitation` | Django shell: revoke as owner vs member | delete function, D1-D3 unaffected |
| D5 | Signup discovery hook surfaces pending invites, no Membership | services.py hook | `pytest backend/workspaces/tests/test_invitations.py -k discover` | Django test client signup call, inspect result payload | remove hook call from `provision_signup`, D1-D4 unaffected |

## Phase D1: feat(workspaces): WorkspaceInvitation model + migration

- [x] 1.1 RED: `backend/workspaces/tests/test_invitations.py` — token-unique-and-generated-via-secrets scenario, model-not-ScopedModel/plain-FK scenario, table-absent-from-`SCOPED_TABLES` scenario.
- [x] 1.2 GREEN: `backend/workspaces/models.py` — add `WorkspaceInvitation` (plain `ForeignKey(Workspace)`, `Status` TextChoices `pending|accepted|revoked|expired`, fields per design, `Meta.indexes` on `(workspace,status)` and `(email,status)`, default `Manager` — NOT `ScopedManager`).
- [x] 1.3 GREEN: `backend/workspaces/migrations/0005_workspaceinvitation.py` — depends on `0004`; plain `CreateModel`; inline comment: MUST NOT append to `0003_rls.py::SCOPED_TABLES`.
- [x] 1.4 Commit: `feat(workspaces): WorkspaceInvitation model + migration`.

## Phase D2: feat(workspaces): invite_member service

- [x] 2.1 RED (append to `test_invitations.py`): owner-can-invite scenario, admin-can-invite scenario, member-denied-invite scenario (no record created), expiry-set-to-now-plus-7-days scenario.
- [x] 2.2 GREEN: `backend/workspaces/services.py` — `invite_member(*, inviter_membership, email, role)`: `has_permission(inviter_membership, "manage_members")` gate raising `PermissionDenied`; `token=secrets.token_urlsafe(32)`; `expires_at=timezone.now()+timedelta(days=7)`; create `status=pending`.
- [x] 2.3 Commit: `feat(workspaces): invite_member service`.

## Phase D3: feat(workspaces): accept_invitation service

- [ ] 3.1 RED (append to `test_invitations.py`): valid-accept-creates-Membership-and-flips-status scenario (atomic), email-mismatch-rejected scenario, expired-invite-rejected-and-persists-expired scenario (lazy expiry), terminal-invite-rejected-no-transition scenario, already-member-idempotent-no-duplicate scenario.
- [ ] 3.2 GREEN: `backend/workspaces/services.py` — `accept_invitation(*, user, token)`: lookup by token; lazy-expire check (`expires_at < now()` → persist `status=expired`, reject) before terminal check; reject non-`pending`; reject `user.email != invite.email`; `transaction.atomic()` wrapping `Membership.objects.get_or_create(...)` (idempotent) + `invite.status=accepted` save.
- [ ] 3.3 Commit: `feat(workspaces): accept_invitation service`.

## Phase D4: feat(workspaces): revoke_invitation service

- [ ] 4.1 RED (append to `test_invitations.py`): owner-revokes-pending scenario, revoke-terminal-rejected scenario, member-without-manage_members-denied scenario.
- [ ] 4.2 GREEN: `backend/workspaces/services.py` — `revoke_invitation(*, actor_membership, invitation)`: `has_permission(actor_membership, "manage_members")` gate; explicit `workspace=actor_membership.workspace` check; reject non-`pending`; set `status=revoked`.
- [ ] 4.3 Commit: `feat(workspaces): revoke_invitation service`.

## Phase D5: feat(workspaces): signup discovery hook

- [ ] 5.1 RED (append to `test_invitations.py`): signup-surfaces-matching-pending-invite scenario (no Membership created for invited workspace), signup-with-no-invites-unaffected scenario, expired-or-terminal-invites-not-surfaced scenario.
- [ ] 5.2 GREEN: `backend/workspaces/services.py` — `discover_pending_invites(*, user)` read-only QuerySet filtered by `email=user.email, status=pending, expires_at__gte=now()`; call from `provision_signup` after its existing atomic block, attach result to signup return value without creating Membership.
- [ ] 5.3 Commit: `feat(workspaces): signup discovery hook`.
