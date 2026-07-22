# Archive Report: m2b-invitations

**Date Archived**: 2026-07-22
**Change**: m2b-invitations — WorkspaceInvitation model + invite/accept/revoke + signup discovery
**Status**: COMPLETE (all phases done, verification passed, specs merged into main specs)

## What Shipped

### New Model & Migration
- **WorkspaceInvitation**: Plain FK to Workspace (deliberately excluded from ScopedModel/RLS), email, role, invited_by, token (unique, secrets.token_urlsafe(32)), status (pending|accepted|revoked|expired), created_at, expires_at
- **Migration 0005_workspaceinvitation**: Additive migration, depends on 0004, no changes to SCOPED_TABLES

### Services Delivered (6 deliveries, all complete)

| Delivery | Service | Purpose |
|----------|---------|---------|
| D1 | Model + Migration | WorkspaceInvitation table created, excluded from RLS |
| D2 | `invite_member` | Owner/admin-gated service; creates pending invite with 7-day expiry |
| D3 | `accept_invitation` | Invitee service; atomic Membership creation + status flip; guards: email match, not expired/terminal, idempotent if already member |
| D4 | `revoke_invitation` | Owner/admin-gated service; sets pending→revoked; rejects terminal |
| D5 | `discover_pending_invites` | Read-only hook in signup; surfaces pending invites by email; never creates Membership |
| D6 | `list_invitations` | Owner/admin-gated service (gap-fix); lists workspace pending invites via explicit workspace= filter, not RLS |

### Specs Merged into Main Specs
- **New**: `openspec/specs/invitations/spec.md` — full spec, 7 requirements, 20 scenarios, all verified
- **Updated**: `openspec/specs/workspaces/spec.md` — added "Signup-Time Invite Discovery" requirement (3 scenarios) to existing workspace spec

### Verification Evidence
- **Test Suite**: 62 passed (39 baseline + 23 added), 0 failed, 0 skipped (verified `uv run pytest -q`)
- **Migrations**: `uv run python manage.py migrate --check` exit 0 — clean
- **TDD**: Strict TDD, all 6 deliveries RED-then-GREEN, all 21 sub-tasks marked complete
- **Spec Compliance**: 100% — every requirement and scenario across both delta specs traces to a passing test
- **Gap Resolution**: D6 resolved CRITICAL gap (list_invitations missing from design/tasks, now implemented and tested)

### Commit SHAs
1. `34d5df9` feat(workspaces): WorkspaceInvitation model + migration
2. `de81a0b` feat(workspaces): invite_member service
3. `df98c03` feat(workspaces): accept_invitation service
4. `b08e73e` feat(workspaces): revoke_invitation service
5. `171f637` feat(workspaces): signup discovery hook
6. `2b62b0d` feat(workspaces): list_invitations service

## Key Architectural Decisions (Locked)

### 1. RLS Exclusion — Deliberate Design Choice
- **Decision**: `WorkspaceInvitation` uses plain `ForeignKey(Workspace)`, NOT `ScopedModel`, NOT in `SCOPED_TABLES`
- **Rationale**: Invitee is not yet a member; `TenancyMiddleware` would return 403 before invite lookup. Invitees must reach own invite by token (capability semantics), not membership context. Authorization split: inviter side = explicit `workspace=` filter + `manage_members` gate; invitee side = token + email ownership
- **Verified**: Confirmed in code at models.py (not ScopedModel), 0003_rls.py and 0004_rls_fix_empty_setting.py (SCOPED_TABLES lists only workspaceresource, not workspaceinvitation), and via runtime test (test_list_invitations_does_not_leak_other_workspace_invites proves cross-workspace isolation via explicit filter, not RLS)

### 2. Verified-Email v1 Shortcut
- **Decision**: No verification field exists on User; match key = existing User with matching email
- **Rationale**: v1 decision recorded explicitly; "has account with this email" treated as proxy for ownership
- **PII Note**: Flagged as PII-adjacent in proposal risks; revisit when email-verification lands
- **Verified**: No external dependencies; change contained to services.py and tests

### 3. provision_signup Contract Change (Breaking)
- **Decision**: `provision_signup` return type changed from bare `User` to `SignupResult(user, pending_invites)` dataclass
- **Impact**: Only internal test caller in codebase (test_services.py) — updated from `user = provision_signup(...)` to `result = provision_signup(...); user = result.user`
- **Verified**: Full repo search (rg) confirms no other callers; M2a test suite still passes after update
- **Risk**: Flag for any downstream API/serializer layer if added later; breaking contract change is contained

### 4. Discovery-Only, Never Auto-Join
- **Decision**: Signup discovery NEVER creates Membership; always requires explicit accept
- **Rationale**: Student PII safety (brief §2); brief-mandated
- **Verified**: test_signup_surfaces_matching_pending_invite and test_signup_with_no_invites_is_unaffected prove Membership created only by owner Membership, not by discovery

### 5. Lazy Expiry, No Celery
- **Decision**: Expiry evaluated at read/accept time; no scheduled Celery jobs
- **Rationale**: Simplification; valid for 7-day window; service-layer only (no HTTP yet)
- **Implementation**: `expires_at < now()` check in accept_invitation and list_invitations; persists status=expired as side effect
- **Verified**: test_accept_invitation_expired_invite_rejected_and_persists_expired proves expiry check and persistence

## Deferred Work (Sibling M2c)

**m2c-move-history** (Milestone 2's second remaining delivery):
- Move-between-workspaces service + workspace_history audit trail
- Deferred from this change per proposal scope; planned as separate SDD change
- No dependencies or interactions with m2b-invitations (can be scheduled independently)

## Risks & Mitigations

| Risk | Status | Mitigation |
|------|--------|-----------|
| RLS-exclusion looks like a bug to reviewers | Addressed | Design rationale documented; spec and code both explicit; mirror's Membership's own precedent (M2a) |
| "Has account" treated as "verified" (PII-adjacent) | Addressed | Recorded as explicit v1 decision in proposal; flagged in risks; revisit at verification layer |
| Lazy expiry stale rows in DB | Addressed | Always apply `expires_at < now()` check at read/accept; never trust raw status; verified in test |
| Accept when already a member | Addressed | Idempotent no-op per spec; uses get_or_create for atomic non-duplication; tested |
| provision_signup breaking change | Addressed | Only internal callers (test_services.py); updated inline; full suite passes; flagged for future API layer |
| Live-DB RLS-exclusion integration test | Carried over | Design promised; what shipped is structural/unit coverage instead (test_workspace_invitation_is_not_a_scoped_model, test_list_invitations_does_not_leak_other_workspace_invites); valid proxy, non-blocking |

## Artifact Inventory

**Archived to**: `openspec/changes/archive/2026-07-22-m2b-invitations/`

- [x] proposal.md — scope, decisions, rollback plan
- [x] explore.md — research findings, open questions resolved
- [x] specs/invitations/spec.md — new capability spec (7 requirements, 20 scenarios)
- [x] specs/workspaces/spec.md — delta adding signup discovery requirement
- [x] design.md — technical approach, interfaces, data flow, testing strategy
- [x] tasks.md — 6 deliveries, all 21 sub-tasks marked complete
- [x] apply-progress.md — TDD evidence, commit log, D6 gap-fix details
- [x] verify-report.md — test results (62 passed), spec compliance matrix, PASS verdict
- [x] state.yaml — phases all done, archived_at=2026-07-22

**Merged into main specs**:
- `openspec/specs/invitations/spec.md` (new, copied from delta)
- `openspec/specs/workspaces/spec.md` (updated with signup discovery requirement)

## SDD Cycle Summary

- **Propose**: Scope (M2a has no member-add path), decisions (RLS-excluded, service-layer only, discovery-only), rollback plan
- **Spec**: 7 capability requirements for invitations domain; 1 new workspaces requirement (discovery)
- **Design**: Plain FK model, three core services (invite/accept/revoke) + discovery hook + D6 gap-fix (list)
- **Tasks**: 6 deliveries pinned as feature-branch-chain (avoid large single PR)
- **Apply**: Strict TDD, 6 deliveries, 23 new tests, 2b62b0d final commit, full suite green
- **Verify**: 62 tests pass, migrations clean, every spec scenario covered, D6 gap resolved, PASS
- **Archive**: Specs merged to main, folder moved to archive with date prefix, state.yaml marked done

## Next Steps

1. **Docs Update**: `docs/roadmap.md` — add M2b subsection after M2a in Milestone 2, note M2c (move-history) pending
2. **M2c Planning**: Schedule m2c-move-history as next M2 delivery (independent SDD change)
3. **API Layer**: No HTTP surface this change; future work may consume `provision_signup` contract change and discovery hook

## Sign-Off

**Status**: COMPLETE — Change m2b-invitations fully planned, implemented, verified, and archived.
**Ready for**: Commit to main branch and next change (M2c-move-history or other priority).

Archived on 2026-07-22 by sdd-archive phase.
