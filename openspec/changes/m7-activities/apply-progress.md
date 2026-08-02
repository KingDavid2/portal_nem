# Apply Progress: m7-activities

**Mode**: Strict TDD  
**Delivery**: force-chained / stacked-to-main  
**Status**: D1 + D2 + D3 + D4 + D5 complete (all implementation units done)

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

### D5 — Stats, filters, banner, Periodo polish
**Branch**: `feat/m7-activities-d5` (from `feat/m7-activities-d4`)  
**Commit**: `feat(actividades): polish filters, stats, and Periodo`

- [x] D5.1 RED extend vitest — Periodo blocks fetch; campo/asignatura/tipo/q filters; stats from API; Exportar/auto-save absent; Calificaciones banner static
- [x] D5.2 GREEN polish page — filters+stats+banner; Periodo from `terms[]`; StatCard density; Buscar only on Por actividad
- [x] D5.3 Verify focused vitest green + commit

## Remaining

- None — D1–D5 complete. Ready for `sdd-verify` (full change). Do not archive until verify.

## TDD Cycle Evidence

### D1–D4

(see prior apply-progress revisions — preserved)

| Task | Result |
|------|--------|
| D1.8 | ✅ 31 passed |
| D2.7 | ✅ 46 passed |
| D3.5 | ✅ 5 passed |
| D4.3 | ✅ 13 passed |

### D5

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| D5.1 | `actividades/page.test.tsx` | Integration | ✅ 13/13 | ✅ Written (4 fail: filters/stats×2/banner) | — | — | — |
| D5.2 | same | Integration + unit | driven | driven | ✅ filters+stats+banner+Periodo | ✅ null average `—` vs `8.3`; `displayAverage` helper | ✅ StatCard + theme tokens (no invented info/warning) |
| D5.3 | vitest actividades | — | — | — | ✅ **20 passed** | — | — |

## Work Unit Evidence

### D5

| Evidence | Value |
|---|---|
| Focused test command and exact result | `npm run test -- --run 'src/app/(app)/actividades/'` → **20 passed** (1 file) |
| Runtime harness command/scenario and exact result | Manual smoke deferred: Periodo required; filters refresh list; banner non-navigating; Exportar absent. No dedicated E2E harness for this route. |
| Rollback boundary | Revert polish hunks in `page.tsx` + D5 tests in `page.test.tsx`; keep D3 list/modal + D4 matrix/Guardar |

## Test Summary

- **Total tests written (cumulative FE)**: 20 (5 D3 + 8 D4 + 7 D5)
- **Total tests passing (focused)**: 20
- **Layers used**: Integration/jsdom (page), pure helpers (`scoreDraftKey`, `displayScore`, `displayAverage`)
- **Approval tests**: None — additive polish surface
- **Pure helpers**: `displayAverage`, `buildListFilters` (internal)

## Deviations from Design

- Banner/stats use design-system primary/success/neutral tones (no `#26C6F9` / warning tokens — not in theme).
- Buscar (`q`) shown only on Por actividad; Por alumno matrix filters omit `q` per API contract.
- Frame `CteCl` PROM. column / footer pagination still deferred (out of D5 polish scope; matrix core from D4).
- Authored ~358 changed lines (345+/13−) under 400 budget for page+test only.

## Issues / Risks

- None blocking. Manual smoke still pending for verify phase.

## Workload / PR Boundary

- Mode: stacked PR slice (D5 → `feat/m7-activities-d4` / `main` after D4 merges)
- Current work unit: D5 (final delivery)
- Boundary: filters + stats + Periodo polish + static Calificaciones banner; no backend/layout/`grades.ts` changes
- Next: `sdd-verify`
