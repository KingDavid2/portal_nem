# Proposal: M3 School Structure

## Intent

Build the CRUD hierarchy `school → school_year → group → student` — the data spine that
lesson plans (M4), grades, and attendance (M5) attach to. This is also the backend's first
real HTTP surface, so it must promote M2 tenancy (service-layer only) into working DRF
endpoints and close two verified authorization gaps that block any real request.

## Scope

### In Scope
- Two new screaming apps: `schools` (School, SchoolYear, Group) + `students` (Student).
- All four entities as workspace-scoped `ScopedModel` subclasses with their OWN denormalized
  `workspace` FK; migrations; per-table RLS policies (NULLIF form).
- Service layer for schools + students.
- DRF HTTP surface: viewsets, serializers, urls.
- **M2 gap fixes** (see below) — required for the first HTTP consumer to function.

### Out of Scope
- Lesson plans, grades, attendance (M4/M5).
- CURP uniqueness / dedup (locked: plain indexed field, no constraint).
- Bulk import, roster upload, cross-school moves, soft delete.
- Frontend (separate future Next.js service).

## Capabilities

### New Capabilities
- `school-structure`: CRUD hierarchy (School, SchoolYear, Group, Student), their invariants
  (uniqueness rules, FK delete behavior), and DRF endpoint contracts.

### Modified Capabilities
- `authorization`: `WorkspacePermission` gains a real `has_permission` with a
  DRF-action→capability map; `TenancyMiddleware` sets `request.membership`.
- `tenancy-isolation`: RLS policies extended to the four new tables, mirroring the `0004`
  NULLIF form.

## Locked Decisions (approved — do not re-litigate)
1. Scope = service layer **plus** DRF HTTP endpoints.
2. Two apps: `schools` + `students`.
3. CURP = plain field, indexed, **no** uniqueness constraint (design-brief §2).
4. Every entity is a `ScopedModel` with its own denormalized `workspace` FK — never
   join-through for RLS.
5. Delivery = chained PRs, one commit per delivery, strict TDD (RED→GREEN), 400-line budget.

## M2 Gaps to Close (in scope)
- **GAP 1**: `TenancyMiddleware` (`backend/workspaces/middleware.py:50`) never sets
  `request.membership` that `WorkspacePermission` (`permissions.py:54`) reads — wire it.
- **GAP 2**: `WorkspacePermission` only has `has_object_permission` and feeds `view.action`
  (a DRF verb) into a capability keyspace → always denies. Add DRF-action→capability map plus a
  `has_permission(self, request, view)`.

## Approach — Delivery Outline (D1–D7)

| # | Deliverable |
|---|-------------|
| D1 | `schools` models + `0001` + `workspaces/rls.py` helper + `schools/0002_rls` + INSTALLED_APPS |
| D2 | `students.Student` model + `0001` + `students/0002_rls` |
| D3 | Services (schools + students) |
| D4 | Wiring fixes (membership + capability map) |
| D5 | Schools DRF surface + urls |
| D6 | Students DRF surface |
| D7 | (optional) retire `WorkspaceResource` placeholder |

Order: D1 → D2 → D3/D4 → D5 → D6 → D7.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/schools/` | New | Models, migrations, services, DRF, urls |
| `backend/students/` | New | Student model, migration, service, DRF |
| `backend/workspaces/middleware.py` | Modified | Set `request.membership` |
| `backend/workspaces/permissions.py` | Modified | `has_permission` + action→capability map |
| `backend/workspaces/rls.py` | New | Reusable RLS policy helper |
| `backend/config/settings` | Modified | Register two apps |

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Capability-map fix regresses existing workspace endpoints | Med | TDD around `has_permission`; run full workspaces suite |
| RLS policy drift from `0004` form | Med | Shared `rls.py` helper enforces the NULLIF form |
| First HTTP surface exposes latent tenancy leaks | Med | RLS backstop tests per new table with a foreign-workspace row |
| Scope creep into M4/M5 relations | Low | Out-of-scope list; FK targets stop at Student |

## Rollback Plan

- All new migrations are reversible (`migrate <app> zero` / previous number); RLS policies are
  created in their own `0002_rls` migrations with matching reverse SQL.
- `workspaces/rls.py` is append-only (new module) — removal is safe.
- Middleware/permission fixes are isolated; revert the two files to restore prior behavior.
- Apps are additive; unregistering from INSTALLED_APPS + dropping tables fully reverts.

## Dependencies

- M2 tenancy foundation (archived on `main`): `ScopedModel`, `ScopedManager`, RLS via
  `SET LOCAL app.workspace_id`, capability matrix.

## Success Criteria

- [ ] CRUD works over HTTP for all four entities, scoped to the caller's workspace.
- [ ] Foreign-workspace rows are invisible via both ORM manager and RLS backstop.
- [ ] `WorkspacePermission` allows/denies by capability for `list/create/retrieve/update/destroy`.
- [ ] `request.membership` is populated by middleware for every authenticated request.
- [ ] All migrations reverse cleanly; `migrate --check` passes.
