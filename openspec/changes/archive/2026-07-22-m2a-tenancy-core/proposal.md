# Proposal: M2a — Tenancy Foundation Core

## Intent

First real Django backend for portal_nem: stand up the project and the defense-in-depth
multi-tenancy substrate every future NEM domain model depends on. Without a workspace-scoped
data path proven safe under connection pooling, no student/grade/attendance model can be built
without risking cross-tenant PII leaks. This slice makes "everything is a workspace" structurally
enforced, not conventional.

## Scope

### In Scope (deliveries D1–D9, one commit each, strict TDD)
- **D1** Django scaffold: `config/` settings, `ATOMIC_REQUESTS=True`, DRF, drf-spectacular, pgvector Postgres; fix README FastAPI remnant.
- **D2** Custom email user model; `AUTH_USER_MODEL` set before first migration; session-cookie auth (httpOnly, CSRF).
- **D3** `workspaces` app: `Workspace(type: personal|group)` + `Membership(role: owner|admin|member as CharField choices)`.
- **D4** Transactional signup: user + personal workspace + owner membership provisioned atomically.
- **D5** Workspace-scoped base manager/QuerySet reading an active-workspace contextvar with fail-closed sentinel.
- **D6** Capability matrix `has_permission(membership, action)` + DRF permission class (no inline role-string checks).
- **D7** RLS middleware: `SET LOCAL app.workspace_id` inside the per-request txn + contextvar storage.
- **D8** RLS policies migration (`RunSQL`, `ENABLE ROW LEVEL SECURITY`, scoped by `current_setting('app.workspace_id')`); restricted non-owner non-`BYPASSRLS` app role.
- **D9** Cross-tenant leak test under connection pooling: asserts scoped QuerySet AND RLS both deny foreign-workspace reads; asserts app role lacks `BYPASSRLS`.

### Out of Scope (non-goals)
- NEM domain models (Student/Grade/Attendance/Planeacion), boleta export, AI planeaciones, frontend.
- CURP uniqueness/merge; personal-workspace sharing.
- **All M2b items**: `WorkspaceInvitation` lifecycle, move-between-workspaces service, `workspace_history` audit, Celery workspace helper.

## Capabilities

### New Capabilities
- `identity-auth`: custom email user model + session-cookie authentication (httpOnly, CSRF).
- `workspaces`: Workspace + Membership models and transactional signup provisioning.
- `tenancy-isolation`: workspace-scoped manager/contextvar (primary) + Postgres RLS backstop, proven under pooling.
- `authorization`: capability matrix `has_permission` + DRF permission class.

### Modified Capabilities
- None (greenfield; no existing specs).

## Approach

Defense-in-depth per brief §2: workspace-scoped ORM manager is the primary review-visible mechanism;
Postgres RLS is the backstop. A request middleware resolves the active workspace, stores it in a
`contextvar`, and issues `SET LOCAL app.workspace_id` inside the `ATOMIC_REQUESTS` transaction
(pool-safe; plain `SET` leaks). RLS policies ship as a `RunSQL` migration; the app connects as a
restricted non-`BYPASSRLS` role. Authorization (can-do-X) routes solely through `has_permission`,
kept distinct from RLS isolation (can-see-workspace-Y). Fail-closed sentinel: absent workspace
context denies all rows.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `config/` | New | Django settings, DRF, spectacular, pgvector DB config |
| `users/` | New | Custom email user, session auth |
| `workspaces/` | New | Models, manager, contextvar, capability matrix, RLS middleware + migration |
| `README.md` | Modified | Remove dropped FastAPI service from stack table |
| project layout / uv package | New | Repo-root vs `backend/` subdir — TBD in design |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `SET LOCAL` vs `SET` pooling leak | High | D9 leak test with active negative control (same connection, two contexts) |
| `AUTH_USER_MODEL` sequencing irreversible | Med | D2 lands before any auth-adjacent migration; verified in tasks ordering |
| Managed Postgres role bypasses RLS | Med | Assert `rolbypassrls = false` for app role in D9 |
| Fail-closed sentinel gap on non-request paths | Med | Sentinel denies by default; Celery path deferred to M2b but sentinel anticipates it |

## Rollback Plan

- **RLS migration**: reversible `RunSQL` — reverse SQL drops policies and `DISABLE ROW LEVEL SECURITY` per table; `migrate <app> <prev>` restores prior state. App-scoped manager still enforces isolation if RLS is rolled back.
- **`AUTH_USER_MODEL`**: irreversible once first migration runs. Rollback = drop the database and re-migrate (greenfield, no production data). Mitigation is ordering, not reversal — D2 must precede any dependent migration.

## Dependencies

- PostgreSQL with pgvector; a second restricted Postgres role for the app connection.
- uv/pytest tooling conventions carried from the M0/M1 spikes.

## Open Questions (flagged for sdd-design)

- Active-workspace resolution when a user has multiple memberships (request header / session / URL).
- Two-Postgres-role setup + how to verify `BYPASSRLS` absence in a test.
- Connection-pooling leak-test approach (simulated connection reuse vs real PgBouncer).
- Project layout: repo-root vs `backend/` subdir; uv package name.

## Success Criteria (maps to design-brief §5 slice-1 gates)

- [ ] Signup transactionally creates user + personal workspace + owner membership.
- [ ] Cross-tenant leak test proves QuerySet + RLS both deny foreign-workspace reads under connection pooling.
- [ ] App verified connecting as non-owner, non-`BYPASSRLS` role.
- [ ] All authorization routes through `has_permission`.
