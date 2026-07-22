# Proposal: m2b-invitations — WorkspaceInvitation model + invite/accept/revoke

## Intent

M2a shipped tenancy but group workspaces have no way to add members. This change
adds `WorkspaceInvitation` plus invite/accept/revoke services and signup-time invite
discovery, so an owner/admin can invite by email and the invitee joins via an
**explicit accept** — never auto-join (student-PII safety, brief §2). Service-layer
only, matching M2a's signup scope; no HTTP surface yet.

## Scope

### In Scope
- `WorkspaceInvitation(workspace, email, role, invited_by, token, status, created_at, expires_at)`.
- `invite / accept / revoke` service functions in `workspaces/services.py`.
- Signup-time invite **discovery** (surface pending invites keyed by new user's email; never auto-create Membership).
- Token via `secrets.token_urlsafe(32)`, `unique=True`; `expires_at = now()+7d` computed in service.
- Lazy expiry (evaluated at read/accept time; no Celery).
- New DB migration (NOT added to `SCOPED_TABLES`).

### Out of Scope
- Move-between-workspaces service + `workspace_history` audit → deferred to `m2c-move-history`.
- HTTP layer (views/serializers/urls), Celery/scheduled expiry, frontend, NEM domain models, email-verification field.

## Capabilities

### New Capabilities
- `invitations`: WorkspaceInvitation model, status state-machine, invite/accept/revoke lifecycle, token+email ownership authorization.

### Modified Capabilities
- `workspaces`: signup provisioning gains invite-discovery step (discovery-only, no Membership side effect).

## Decisions (resolved — do not re-litigate)
1. **Discovery-only, never auto-join** (brief §2). Membership created only by explicit accept.
2. **Service-layer only** — no HTTP surface this change (M2a precedent).
3. **Verified-email v1 shortcut**: no verification field exists; match key = existing `User` with matching email. PII-adjacent v1 decision, recorded explicitly.
4. **RLS-excluded**: plain `ForeignKey(Workspace)`, NOT in `SCOPED_TABLES`. Invitee is not yet a member, so RLS/ScopedManager would hide their own pending invite (same bootstrap class as `Membership`).

## Approach

Extend the proven `provision_signup` atomic pattern in place. Status state-machine:
`pending → accepted` (invitee accept) · `pending → revoked` (`manage_members` holder) ·
`pending → expired` (lazy, when `expires_at < now()`). `accepted/revoked/expired` are
**terminal**, enforced in the service layer. Authorize two ways: inviter side =
explicit `filter(workspace=…)` gated by `has_permission(membership, "manage_members")`
(owner+admin, no permissions.py change); invitee side = `get(token, status=PENDING)` +
`request.user.email == invite.email` ownership check.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/workspaces/models.py` | New | `WorkspaceInvitation` (plain FK, not ScopedModel) |
| `backend/workspaces/services.py` | Modified | invite/accept/revoke + signup discovery hook |
| `backend/workspaces/migrations/` | New | Invitation table; NOT in `SCOPED_TABLES` |
| `backend/workspaces/tests/` | New | Reuse atomicity/rollback pattern |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| "Has account" treated as "verified" (PII-adjacent) | Med | Record as explicit v1 decision; revisit when verification lands |
| RLS-exclusion looks like a bug to reviewers | Med | Document rationale in spec/design (mirrors Membership) |
| Lazy expiry: stale `pending` rows in DB | Med | Always apply `expires_at < now()` check at read/accept; never trust raw status |
| Accept when already a member | Low | Idempotent/conflict guard defined in spec |

## Rollback Plan

Single additive migration. Rollback = `manage.py migrate workspaces <prev>` to drop the
`WorkspaceInvitation` table; revert service/model changes. No data backfill, no
`SCOPED_TABLES`/RLS-policy change, no `AUTH_USER_MODEL` impact — clean reversal.

## Success Criteria

- [ ] Owner/admin can create a pending invite; `member` cannot (via `has_permission`).
- [ ] Explicit accept creates Membership with `invite.role` and flips status atomically.
- [ ] Revoke and lazy expiry move `pending` to terminal states; terminal states reject further transitions.
- [ ] Signup discovers pending invites by email without creating any Membership.
- [ ] `WorkspaceInvitation` absent from `SCOPED_TABLES`; invitee reaches own invite by token.
