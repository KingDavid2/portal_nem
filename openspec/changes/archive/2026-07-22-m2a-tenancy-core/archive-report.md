# Archive Report: M2a — Tenancy Foundation Core

**Change**: `m2a-tenancy-core`
**Archived**: 2026-07-22 (ISO date)
**Status**: COMPLETE — All phases done, SDD cycle closed

---

## Executive Summary

M2a — Tenancy Foundation Core has been fully implemented, verified, and archived. The change delivered 9 commits (D1–D9) establishing the foundational Django backend, defense-in-depth multi-tenancy, and workspace-scoped data isolation for the Portal NEM system. All 4 domain specs synced to main specs; 39 tests passing; 0 CRITICAL issues in verification.

---

## What Was Archived

| Artifact | Status | Location |
|----------|--------|----------|
| `proposal.md` | Synced | `openspec/changes/archive/2026-07-22-m2a-tenancy-core/` |
| `design.md` | Synced | `openspec/changes/archive/2026-07-22-m2a-tenancy-core/` |
| 4 delta specs (identity-auth, workspaces, tenancy-isolation, authorization) | Synced | `openspec/changes/archive/2026-07-22-m2a-tenancy-core/specs/` |
| `tasks.md` | Synced | `openspec/changes/archive/2026-07-22-m2a-tenancy-core/` |
| `apply-progress.md` | Synced | `openspec/changes/archive/2026-07-22-m2a-tenancy-core/` |
| `verify-report.md` | Synced | `openspec/changes/archive/2026-07-22-m2a-tenancy-core/` |
| `exploration.md` | Synced | `openspec/changes/archive/2026-07-22-m2a-tenancy-core/` |
| `state.yaml` | Synced | `openspec/changes/archive/2026-07-22-m2a-tenancy-core/` |

---

## Specs Synced to Main

Four new domain specs were created as **greenfield** (all ADDED requirements, no existing specs to merge):

| Domain | Main Spec Created | Requirements Count | Key Features |
|--------|-------------------|-------------------|--------------|
| `identity-auth` | `openspec/specs/identity-auth/spec.md` | 2 | Custom email user, session-cookie auth (httpOnly, CSRF) |
| `workspaces` | `openspec/specs/workspaces/spec.md` | 2 | Workspace/Membership models, transactional signup provisioning |
| `tenancy-isolation` | `openspec/specs/tenancy-isolation/spec.md` | 4 | Scoped manager, RLS middleware, RLS policies, pooling leak test |
| `authorization` | `openspec/specs/authorization/spec.md` | 2 | Capability matrix as sole auth path, authorization ≠ isolation |

All specs are now the source of truth for M2a+ work.

---

## Implementation Summary

### Deliveries (D1–D9)

| Delivery | Commit | Feature | Status |
|----------|--------|---------|--------|
| D1 | `ef7fc31` | Django scaffold | Done — 2 tests |
| D2 | `60e36ac` | Custom email user + session auth | Done — 7 tests |
| D3 | `1fff304` | Workspace + Membership models | Done — 6 tests |
| D4 | `a8ba05d` | Transactional signup provisioning | Done — 2 tests |
| D5 | `e7737eb` | Workspace-scoped manager (fail-closed contextvar) | Done — 2 tests |
| D6 | `003b0d8` | Capability matrix + DRF permission | Done — 5 tests |
| D7 | `420e263` | RLS middleware + SET LOCAL wiring | Done — 6 tests |
| D8 | `3772e64` | RLS policies + restricted app role | Done — 4 tests |
| D9 | `b201dbb` | Cross-tenant leak test under pooling | Done — 5 tests |

**Total**: 9 commits, 39 passing tests, 0 failed, 0 skipped.

### Design-Brief §5 Acceptance Gates

All 4 gates CONFIRMED:

1. **Transactional signup** — User + personal workspace + owner membership created atomically; rollback verified.
2. **Cross-tenant leak test** — Both scoped QuerySet and RLS backstop independently deny foreign-workspace rows under connection pooling; negative control proves leak detection works.
3. **App role is non-BYPASSRLS** — Verified via `pg_roles` query as the runtime `portal_app` role; `rolbypassrls=f, rolsuper=f`.
4. **All authorization through `has_permission`** — No inline role-string comparisons found in production code; DRF permission class delegates solely to `has_permission`.

---

## Verification Summary

**Verdict**: PASS WITH WARNINGS (2 WARNING, 1 SUGGESTION, 0 CRITICAL)

### Critical Issues
None.

### Warnings
1. **D7 deviation** — `TenancyMiddleware` opens its own explicit `transaction.atomic()` instead of relying on Django's `ATOMIC_REQUESTS` (which only wraps the view, not middleware). Implementation is correct and tested; `design.md` text should be updated for clarity.

2. **D8 deviation** — RLS applied to `WorkspaceResource` (minimal throwaway model), not `Membership`, due to bootstrap chicken-and-egg: middleware must query memberships to resolve the active workspace *before* `app.workspace_id` is set. `Membership` stays outside RLS by design. **M2b follow-up required**: any future `Membership`-backed view/serializer MUST filter by `request.user` explicitly (no RLS backstop by design).

### Suggestions
1. `WorkspaceResource` is documented as a throwaway RLS-exercise table. Recommend replacing or removing it once real M2b domain models exist.

---

## Carry-Forward Notes for M2b

### Blocked by M2a Completion
- **`WorkspaceResource` cleanup** — Remove or replace the throwaway model once Student/Grade/Attendance or other real domain models land.
- **`Membership`-backed API views** — Must filter by `request.user` explicitly (no RLS backstop). Do not assume scoped manager alone prevents `Membership` exposure.

### Deferred (Out of M2a Scope)
- `WorkspaceInvitation` lifecycle
- Move-between-workspaces service
- `workspace_history` audit trail
- Celery workspace task context (but fail-closed sentinel anticipates it)
- Real PgBouncer CI hardening

---

## File Summary

**Delta specs merged**: 4 (all greenfield, no conflicts)
**Main specs created**: 4 (`openspec/specs/{domain}/spec.md`)
**Archive folder**: `openspec/changes/archive/2026-07-22-m2a-tenancy-core/`
**Change folder removed from active**: `openspec/changes/m2a-tenancy-core/` (moved to archive)
**State updated**: `phases.archive: done`, `next_recommended: none`

---

## Traceability

All SDD artifacts preserved in archive:
- Proposal, design, tasks, apply-progress, verify-report, exploration
- 4 delta specs (identity-auth, workspaces, tenancy-isolation, authorization)
- State tracking (state.yaml with all phases complete)

Archive path: `/Users/davidnahumcrdz/projects/portal_nem/openspec/changes/archive/2026-07-22-m2a-tenancy-core/`

---

## SDD Cycle Closure

**M2a is complete.** The change has progressed through all 8 phases (explore → propose → spec → design → tasks → apply → verify → archive) with clean, documented exits at each gate. The foundation is set for M2b domain models and workspace lifecycle features.

Recommendation: Begin M2b planning with explicit carry-forward of the Membership-filtering requirement and WorkspaceResource cleanup task.
