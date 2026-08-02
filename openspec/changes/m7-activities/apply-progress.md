# Apply Progress: m7-activities

**Mode**: Strict TDD  
**Delivery**: force-chained / stacked-to-main  
**Status**: D1 + D2 + D3 complete

## Completed Tasks

### D1 — models + RLS + services
**Branch**: `feat/m7-activities-d1` (from `origin/main`)  
**Commit**: `feat(grades): add models, RLS, and services`

- [x] D1.1–D1.8

### D2 — DRF activities + matrix/bulk API
**Branch**: `feat/m7-activities-d2` (from `feat/m7-activities-d1`)  
**Commit**: `feat(grades): add activities and scores API`

- [x] D2.1–D2.7

### D3 — Frontend hooks + Por actividad list/modal + nav
**Branch**: `feat/m7-activities-d3` (from `feat/m7-activities-d2`)  
**Commit**: `feat(actividades): add list, modal, and grades hooks`

- [x] D3.1 RED vitest list/modal stubs
- [x] D3.2 GREEN `frontend/src/lib/api/grades.ts`
- [x] D3.3 GREEN `/actividades` page (toggle + Por actividad table + create modal)
- [x] D3.4 GREEN nav `NotebookPen` → `/actividades`
- [x] D3.5 Verify focused vitest green + commit

## Remaining

- [ ] D4–D5 (not in this batch)

## TDD Cycle Evidence

### D1–D2

(see prior apply-progress revisions — preserved)

| Task | Result |
|------|--------|
| D1.8 | ✅ 31 passed |
| D2.7 | ✅ 46 passed |

### D3

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| D3.1 | `frontend/src/app/(app)/actividades/page.test.tsx` | Integration (jsdom) | N/A (new) | ✅ Written (`Failed to resolve import "./page"`) | ✅ 5/5 | ✅ Periodo empty vs selected; dialog open; POST payload; no Guardar/Exportar | ✅ Compacted helpers |
| D3.2 | (driven by page tests + hooks used) | Unit hooks | N/A (new) | Driven by D3.1 | ✅ grades.ts hooks | ✅ list/create/matrix/bulk surfaces | ✅ Compressed query helpers |
| D3.3 | same page.test | Integration | N/A | Driven by D3.1 | ✅ page.tsx | Covered above | ✅ Lean modal/list |
| D3.4 | layout nav | Structural | N/A | ➖ Triangulation skipped: single nav entry | ✅ NotebookPen → `/actividades` | ➖ Single | ➖ None needed |
| D3.5 | `npm run test -- --run src/app/(app)/actividades/` | — | — | — | ✅ **5 passed** | — | — |

## Work Unit Evidence

### D3

| Evidence | Value |
|---|---|
| Focused test command and exact result | `npm run test -- --run 'src/app/(app)/actividades/'` → **5 passed** (1 file) in ~0.5s |
| Runtime harness command/scenario and exact result | Manual smoke deferred to verify/PR: `/actividades` → pick Periodo → Nueva → Crear → list refresh. No dedicated E2E harness in repo for this route. |
| Rollback boundary | Remove `frontend/src/app/(app)/actividades/`, `frontend/src/lib/api/grades.ts`; revert Actividades nav row in `layout.tsx`; keep D2 API |

## Test Summary

- **Total tests written (cumulative FE D3)**: 5
- **Total tests passing (focused)**: 5
- **Backend grades suite**: untouched this batch (D2: 46 passed previously)
- **Layers used**: Integration/jsdom (page), typed API hooks
- **Approval tests**: None — new FE surface
- **Pure helpers**: `activitiesQueryEnabled`

## Deviations from Design

- Asistencia nav item is not on this branch/`main`; Actividades placed after Alumnos (slot after where Asistencia will land).
- Modal omits “Seleccionar todas las asignaturas del campo” control to keep page lean (D5 polish candidate); multi-checkbox still works.
- `FALLBACK_TERMS` uses ids 1–3 until first successful list returns real `terms[]` (chicken-and-egg: list requires term id). Real workspaces with non-1..3 term PKs need a bootstrap path (D5 / follow-up).
- Filters/stats/banner deferred to D5; Por alumno matrix/Guardar deferred to D4 (stub toggle only).
- Authored volume ~616 lines (over 400 budget) after aggressive lean — single D3 commit per orchestrator request; PR may need D3a/D3b split if reviewer enforces hard cap.

## Issues / Risks

- **400-line budget overrun**: ~616 authored (grades.ts ~121 + page ~285 + test ~199 + layout ~11). Split option (list shell vs modal) available if PR review requires it.
- Term-id bootstrap via `FALLBACK_TERMS` may 404 against non-empty DBs until terms are known.

## Workload / PR Boundary

- Mode: stacked PR slice (D3 → previous D2 branch / `main` after D2 merges)
- Current work unit: D3
- Boundary: FE hooks + Por actividad list/modal + nav; no matrix Guardar (D4); no stats/filters polish (D5)
- Next: `sdd-apply` D4 or `sdd-verify` for D3 slice
