# Apply Progress: m7-activities

**Mode**: Strict TDD  
**Delivery**: force-chained / stacked-to-main  
**Status**: D1 + D2 + D3 + D4 complete

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
**Commit**: `e66fe30` `feat(actividades): add list, modal, and grades hooks`

- [x] D3.1 RED vitest list/modal stubs
- [x] D3.2 GREEN `frontend/src/lib/api/grades.ts`
- [x] D3.3 GREEN `/actividades` page (toggle + Por actividad table + create modal)
- [x] D3.4 GREEN nav `NotebookPen` → `/actividades`
- [x] D3.5 Verify focused vitest green + commit

### D4 — Por alumno matrix + draft Map + Guardar
**Branch**: `feat/m7-activities-d4` (from `feat/m7-activities-d3`)  
**Commit**: `feat(actividades): add score matrix and Guardar`

- [x] D4.1 RED extend page.test.tsx — matrix toggle, draft Map key, no bulk until Guardar, null≠0.0
- [x] D4.2 GREEN Por alumno matrix + draft Map + Guardar → bulk PUT
- [x] D4.3 Verify focused vitest green + commit

## Remaining

- [ ] D5 (stats/filters/banner/Periodo polish)

## TDD Cycle Evidence

### D1–D3

(see prior apply-progress revisions — preserved)

| Task | Result |
|------|--------|
| D1.8 | ✅ 31 passed |
| D2.7 | ✅ 46 passed |
| D3.5 | ✅ 5 passed |

### D4

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| D4.1 | `actividades/page.test.tsx` | Integration | ✅ 5/5 | ✅ Written (5 fail) | — | — | — |
| D4.2 | same | Integration | driven | driven | ✅ matrix+draft+Guardar | ✅ null vs 0.0; helpers; dirty-only bulk | ✅ pure `scoreDraftKey`/`displayScore`/`parseDraftEntries` |
| D4.3 | vitest actividades | — | — | — | ✅ **13 passed** | — | — |

## Work Unit Evidence

### D4

| Evidence | Value |
|---|---|
| Focused test command and exact result | `npm run test -- --run 'src/app/(app)/actividades/'` → **13 passed** (1 file) |
| Runtime harness command/scenario and exact result | Manual smoke deferred: Por alumno → edit cell → Guardar → reload. No dedicated E2E harness for this route. |
| Rollback boundary | Revert matrix/draft/Guardar hunks in `page.tsx` + D4 tests in `page.test.tsx`; keep D3 list/modal/hooks |

## Test Summary

- **Total tests written (cumulative FE)**: 13 (5 D3 + 8 D4)
- **Total tests passing (focused)**: 13
- **Layers used**: Integration/jsdom (page), pure helpers
- **Approval tests**: None — additive matrix surface
- **Pure helpers**: `scoreDraftKey`, `displayScore`, `parseDraftEntries`

## Deviations from Design

- Frame `CteCl` PROM./footer pagination deferred to D5 polish (matrix core only).
- Filters (Campo/Asignatura/Tipo) on Por alumno deferred to D5.
- Guardar sends dirty draft entries only (not full matrix) — matches draft Map semantics; LWW on server.
- Authored ~381 changed lines (337+/44−) under 400 budget for page+test only.

## Issues / Risks

- None blocking. Manual smoke still pending for verify.

## Workload / PR Boundary

- Mode: stacked PR slice (D4 → `feat/m7-activities-d3` / `main` after D3 merges)
- Current work unit: D4
- Boundary: Por alumno matrix + draft Map + Guardar; no stats/filters/banner polish (D5)
- Next: `sdd-verify` (D4 slice) or `sdd-apply` D5
