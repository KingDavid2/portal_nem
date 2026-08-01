# Proposal: M7 Daily Attendance

## Intent

Ship the teacher daily attendance grid: mark present/absent/late/excused for a
group+date, one save, live counts. Attendance half of M7 only — grades deferred.

## Scope

### In Scope
- New app `attendance`: `AttendanceRecord` (`ScopedModel`), migration, RLS, services.
- DRF roster GET + bulk PUT upsert (atomic).
- Frontend `/asistencia` (`LXprh`): filters, grid, stats, Guardar, nav + OpenAPI hooks.
- `EstadoButton`/`StatCard` tone variants if missing.

### Out of Scope
- Grades, Periodo/`Term`, auto-save, Exportar, pagination, tutor portal, versioning.

## Capabilities

### New Capabilities
- `attendance`: record invariants, roster + bulk API, `/asistencia` UX, status enum.

### Modified Capabilities
- `authorization`: map `roster` → `view_workspace`, `bulk` → `edit_content`.
- `tenancy-isolation`: RLS for the new attendance table (NULLIF form).

## Locked Decisions (approved — do not re-litigate)
1. Attendance-only (grades OUT).
2. New screaming app `attendance`.
3. Design frame **`LXprh`** authoritative (not `y4w3Hb`).
4. Explicit **Guardar**; defer auto-save.
5. Defer Periodo backend — UI omits/disables Periodo.
6. Defer Exportar.
7. API: `GET …/roster/?group=&date=` + `PUT …/bulk/` atomic upsert.
8. Status: `present|absent|late|excused`; UI Presente/Ausente/Retardo/Justificado.
9. Force-chained stacked-to-main, 400-line, Strict TDD, one commit/delivery.
10. Date = date-only `DateField`; client local calendar `YYYY-MM-DD`; no datetime.

## Approach — Delivery Outline (D1–D3)

| # | Deliverable |
|---|-------------|
| D1 | Model + migration + RLS + services + unit tests |
| D2 | Roster + bulk DRF, API/RLS tests, OpenAPI |
| D3 | Hooks + `/asistencia` + nav + vitest |

Unique `(student, date)`; `student` PROTECT; no `group` FK; bulk validates
group+workspace. No row until save; UI draft defaults `present`. Full roster
client-side (≤~40). Periodo omit/disable.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/attendance/` | New | Model, RLS, services, DRF, tests |
| `backend/config/{settings,urls}.py` | Modified | App + routes |
| `frontend/src/app/(app)/asistencia/` | New | Page |
| `frontend/src/app/(app)/layout.tsx` | Modified | Nav |
| `frontend/src/lib/api/{attendance.ts,schema.d.ts}` | New/Mod | Hooks + OpenAPI |
| `frontend/src/components/ui/{estado-button,stat-card}.tsx` | Modified | P/A/R/J tones |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| First bulk endpoint | Med | Spec all-or-nothing txn; TDD |
| Concurrent last-write-wins | Med | Accept v1; document |
| Tone gaps vs `LXprh` | Med | Extend primitives in D3 |

## Rollback Plan

Migrations reversible; RLS reverse SQL; app/page/nav additive — revert per slice.

## Dependencies

M3 spine + `SchoolTeachingContext`; M2 ScopedModel/RLS/`edit_content`; M6 primitives.

## Success Criteria

- [ ] Roster + one Guardar saves P/A/R/J (+ notes) for group+date.
- [ ] Bulk atomic; wrong-group / foreign-workspace rejected.
- [ ] Counts match; draft default present; RLS denies cross-workspace.
- [ ] `/asistencia` matches `LXprh` body; Periodo/Exportar deferred.
