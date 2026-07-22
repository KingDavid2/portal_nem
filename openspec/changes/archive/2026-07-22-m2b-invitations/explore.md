# Exploration: m2b-invitations — WorkspaceInvitation model + invite/accept flow

## Current State

M2a shipped the tenancy skeleton but **no signup HTTP endpoint exists yet** — `backend/workspaces/services.py::provision_signup(email, password)` is a plain service function (called only from tests: `backend/workspaces/tests/test_services.py`), not wired to any view/serializer/URL (`backend/config/urls.py` has only `admin/`, `api/schema/`, `api/docs/`; `backend/users/` has no `views.py`/`serializers.py`). It runs in one `transaction.atomic()` block: create personal `Workspace` → create `User` → create owner `Membership`, in that order — proven by `test_failure_during_provisioning_rolls_back_all_records`.

Tenancy has two enforcement layers (`backend/workspaces/models.py`, `managers.py`, `middleware.py`):
- **App-level**: `ScopedModel` (abstract, `workspace` FK) + `ScopedManager`, fail-closed via a `WORKSPACE_UNSET` contextvar sentinel (`workspaces/context.py`).
- **DB-level (RLS)**: `workspaces/migrations/0003_rls.py` enables RLS only on tables listed in `SCOPED_TABLES` (currently `["workspaces_workspaceresource"]`), keyed on `current_setting('app.workspace_id', true)::uuid`, set via `SET LOCAL` inside `TenancyMiddleware`.

Critically, `Membership` is **deliberately excluded** from `ScopedModel`/RLS (M2a design.md, D8 note): *"`Membership` is intentionally left un-RLS-scoped because `TenancyMiddleware` must read the user's memberships to RESOLVE the active workspace before `app.workspace_id` is set — RLS on `Membership` would deadlock that bootstrap."* Any `Membership`-backed view must filter by `request.user` explicitly, no RLS backstop. This is the precedent `WorkspaceInvitation` follows for a related but distinct reason (see Q3).

Authorization is centralized in `backend/workspaces/permissions.py`: `has_permission(membership, action)` against a `CAPABILITIES` dict. `manage_members` is already granted to `owner` and `admin`, not `member` — the natural gate for invite/revoke.

No email-verification concept exists anywhere in the codebase (`User` has no `is_verified`/`email_confirmed` field, grepped repo-wide, zero hits). Brief §6 lists *"Whether invitation email-match requires a verified email before linking"* as an open question.

## Affected Areas

- `backend/workspaces/models.py` — add `WorkspaceInvitation` (NOT a `ScopedModel` subclass — see Q3).
- `backend/workspaces/services.py` — invite/accept/revoke service functions; extend the signup path for "match pending invites at signup" hook.
- `backend/workspaces/migrations/` — new migration; must NOT be added to `0003_rls.py`'s `SCOPED_TABLES`.
- `backend/workspaces/permissions.py` — no structural change; `manage_members` already covers invite/revoke authorization.
- `backend/workspaces/tests/` — reuse the existing atomicity/rollback test pattern.
- `backend/users/models.py` — no "verified email" field today (v1 shortcut decision, see risks).

## Key Questions — Findings

**Q1. Signup invite-matching hook location + semantics.**
Lives in/alongside `provision_signup` (the single atomic signup entry point). Brief §2 LOCKS the semantics: "Explicit accept (not auto-join) — matters for student PII." Therefore **matching = discovery/association only** (surface pending invites keyed by the new user's email); it never auto-creates a `Membership`. Accept is always a separate explicit step. This is a locked decision, not an open question.

**Q2. Token generation/uniqueness + expiry.**
`secrets.token_urlsafe(32)` (256-bit), DB `unique=True`, no retry loop needed. `expires_at` computed in the service at creation (`now() + timedelta(days=7)`), keeping the business rule in `services.py` per codebase convention.

**Q3. RLS scoping — the tricky part. `WorkspaceInvitation` is EXCLUDED from `ScopedModel`/RLS.**
Reason differs from `Membership`'s: the **invitee is not yet (and may never become) a member of the target workspace**. `TenancyMiddleware` resolves `active_workspace` only from the requester's existing `Membership` set; a non-member requesting the target workspace gets a hard 403. If `WorkspaceInvitation` were `ScopedModel`-gated, the invitee could never reach their own pending invite by token — `ScopedManager` returns `.none()` and RLS denies the row. Authorize by two distinct paths instead:
- **Inviter side** (list/create/revoke): explicit filter `WorkspaceInvitation.objects.filter(workspace=membership.workspace)` gated by `has_permission(membership, "manage_members")`.
- **Invitee side** (accept by token): `get(token=token, status=PENDING)` + ownership check (`request.user.email == invite.email`) — capability-token semantics, not tenancy-membership.

**Q4. Accept flow / who can invite.**
Invite creation gated by `has_permission(inviter_membership, "manage_members")` (owner+admin, no permissions.py change). Accept creates `Membership(user, workspace, role=invite.role)` and flips status to accepted, atomically. Guard: user already a member of that workspace (idempotent/conflict decision in spec), invite not expired/terminal.

**Q5. Status transitions + revoke.**
`pending → accepted` (invitee, via accept). `pending → revoked` (`manage_members` holder, via revoke). `pending → expired` — **no Celery in scope**, so expiry is evaluated **lazily** at read/accept time (`expires_at < now()`), optionally persisting `status=expired` as a side effect. `accepted`/`revoked`/`expired` are terminal, enforced in the service layer.

## Approaches

1. **Extend the signup path in place** — add invite-discovery as a step near `provision_signup`. Pros: reuses proven atomic/test pattern, minimal surface. Cons: signup grows a second concern. Effort: Low.
2. **Separate `match_pending_invites(user)` service called from a signup view** — cleaner separation but requires building the not-yet-existing HTTP signup endpoint (scope growth). Effort: Medium.

**Recommendation**: Approach 1, discovery-only (per locked Q1). Stay **service-layer only** (no views/urls), consistent with M2a's own signup scope — defer the HTTP layer to a later change.

## Decisions Carried to Proposal (resolved, do not re-explore)

- **Q1 semantics**: matching = discovery-only, never auto-join (locked by brief §2).
- **HTTP layer**: OUT — service-layer only this change, matching M2a precedent.
- **Verified email**: no verification field exists; v1 shortcut = an existing account with the matching email is the match key. Flag as an explicit PII-adjacent v1 decision in proposal/spec.
- **RLS exclusion**: `WorkspaceInvitation` NOT in `SCOPED_TABLES` — deliberate, documented so no reviewer "fixes" it.

## Risks

- Silently treating "has an account with this email" as "verified" is a plausible v1 shortcut but PII-adjacent — record it explicitly.
- RLS-exclusion is a deliberate deviation from "everything is a workspace / RLS-backed" — needs explicit design sign-off.
- Lazy expiry: a `pending` row past `expires_at` stays `pending` in the DB until read; any count relying on raw `status="pending"` (skipping the lazy check) would be wrong. Flag for spec/design.

## Ready for Proposal

Yes.
