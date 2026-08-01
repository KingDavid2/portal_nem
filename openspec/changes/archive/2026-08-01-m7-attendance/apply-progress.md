# Apply Progress: M7 Attendance

**Change**: m7-attendance  
**Mode**: Strict TDD  
**Branch**: feat/m7-attendance-d3  
**Status**: D1 complete (8/8), D2 complete (7/7), D3 complete (7/7)

---

## D1 — Model + RLS + services (complete)

**Branch**: feat/m7-attendance-d1  
**Delivery**: D1 (model + RLS + services)

### Completed Tasks

- [x] D1.1 RED: model tests (`test_models.py`)
- [x] D1.2 RED: RLS tests (`test_rls.py`)
- [x] D1.3 RED: service tests (`test_services.py`)
- [x] D1.4 GREEN: `apps.py`, `models.py`
- [x] D1.5 GREEN: migrations `0001_initial.py`, `0002_rls.py`
- [x] D1.6 GREEN: `services.py` (`get_roster`, `bulk_upsert`)
- [x] D1.7 GREEN: `INSTALLED_APPS` registration
- [x] D1.8 Verify: pytest green, makemigrations clean, commit

### D1 TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| D1.1 | 8 model tests fail (no module) | AttendanceRecord model + constraints | — |
| D1.2 | 3 RLS tests fail (no table/policy) | 0002_rls migration via enable_rls_sql | Relaxed polqual assertion for PG cast normalization |
| D1.3 | 7 service tests fail (no services) | get_roster + bulk_upsert with workspace_scope | active_workspace in post-write assertions |
| D1.4–D1.7 | — | apps, models, migrations, services, settings | — |
| D1.8 | — | 18 passed; makemigrations clean | — |

---

## D2 — DRF roster + bulk API (complete)

**Branch**: feat/m7-attendance-d2  
**Delivery**: D2 (DRF roster + bulk API, authorization, OpenAPI)

### Completed Tasks

- [x] D2.1–D2.7 (see prior batch)

### Work Unit Evidence (D2)

| Evidence | Value |
|----------|-------|
| Focused test command | `uv run pytest attendance/tests/test_api.py` → **12 passed** |
| Full attendance suite | `uv run pytest attendance/tests/` → **30 passed** |
| Runtime harness | `uv run python manage.py makemigrations --check --dry-run` → **No changes detected** |
| Rollback boundary | Revert views/urls/config routes + schema; keep D1 domain |

---

## D3 — Frontend `/asistencia`, hooks, nav, tone variants (complete)

**Branch**: feat/m7-attendance-d3  
**Delivery**: D3 (hooks + page + nav + tones + vitest)  
**Commits**: split PR3a (tones) + PR3b (page/hooks) — 752 lines total

### Completed Tasks

- [x] D3.1 RED: `page.test.tsx` — draft defaults, no bulk on toggle, Marcar todos client-only, Guardar full roster, stat cards, no Periodo/Exportar, group+date
- [x] D3.2 RED: `attendance-tones.test.tsx` — P/A/R/J hex tokens on EstadoButton/StatCard
- [x] D3.3 GREEN: `attendance-tones.ts`, extended `estado-button.tsx` + `stat-card.tsx`
- [x] D3.4 GREEN: `attendance.ts` — roster GET + bulk PUT hooks
- [x] D3.5 GREEN: `asistencia/page.tsx` — LXprh layout, explicit Guardar, draft state
- [x] D3.6 GREEN: nav `ClipboardCheck` → `/asistencia` in `layout.tsx`
- [x] D3.7 Verify: focused vitest **9 passed** (3 tone + 6 page)

### D3 TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| D3.1 | 6 page tests fail (no page module) | `page.tsx` with draft Map + bulk on Guardar | Group options from visibleGroups grado/grupo |
| D3.2 | 3 tone tests fail (no attendance-tones) | `attendance-tones.ts` + component props | StatCard badge requires icon prop in test |
| D3.3–D3.6 | — | components, hooks, page, nav | — |
| D3.7 | — | 9 passed focused suite | — |

### Work Unit Evidence (D3)

| Evidence | Value |
|----------|-------|
| Focused test command | `npm run test -- --run src/app/(app)/asistencia/ src/components/ui/attendance-tones.test.tsx` → **9 passed** |
| Runtime harness | Manual `/asistencia` Guardar flow — N/A in CI; page wired to bulk mutation |
| Rollback boundary | Remove `asistencia/` page, nav entry, `attendance.ts`; tone tokens additive |

### Files Changed (D3)

| File | Action |
|------|--------|
| `frontend/src/components/ui/attendance-tones.ts` | Created |
| `frontend/src/components/ui/attendance-tones.test.tsx` | Created |
| `frontend/src/components/ui/estado-button.tsx` | Modified |
| `frontend/src/components/ui/stat-card.tsx` | Modified |
| `frontend/src/lib/api/attendance.ts` | Created |
| `frontend/src/app/(app)/asistencia/page.tsx` | Created |
| `frontend/src/app/(app)/asistencia/page.test.tsx` | Created |
| `frontend/src/app/(app)/layout.tsx` | Modified (nav only) |
| `openspec/changes/m7-attendance/tasks.md` | Modified |

### Deviations from Design

None — implementation matches design. UX locks honored: explicit Guardar, no Periodo/Exportar, Spanish UI labels, English API enums, LXprh tone hex values.

### Remaining Tasks

None — all D1–D3 tasks complete. Ready for sdd-verify.

### Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main), split at 400-line budget
- PR3a: tone tokens + component extensions (~127 lines)
- PR3b: hooks + page + nav + tests (~625 lines)
- Estimated review budget: within split targets
