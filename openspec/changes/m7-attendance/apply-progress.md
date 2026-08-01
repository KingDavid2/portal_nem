# Apply Progress: M7 Attendance — D1

**Change**: m7-attendance  
**Mode**: Strict TDD  
**Branch**: feat/m7-attendance-d1  
**Delivery**: D1 (model + RLS + services)  
**Status**: Complete (8/8 D1 tasks)

## Completed Tasks

- [x] D1.1 RED: model tests (`test_models.py`)
- [x] D1.2 RED: RLS tests (`test_rls.py`)
- [x] D1.3 RED: service tests (`test_services.py`)
- [x] D1.4 GREEN: `apps.py`, `models.py`
- [x] D1.5 GREEN: migrations `0001_initial.py`, `0002_rls.py`
- [x] D1.6 GREEN: `services.py` (`get_roster`, `bulk_upsert`)
- [x] D1.7 GREEN: `INSTALLED_APPS` registration
- [x] D1.8 Verify: pytest green, makemigrations clean, commit

## Files Changed

| File | Action |
|------|--------|
| `backend/attendance/apps.py` | Created |
| `backend/attendance/models.py` | Created |
| `backend/attendance/services.py` | Created |
| `backend/attendance/migrations/0001_initial.py` | Created |
| `backend/attendance/migrations/0002_rls.py` | Created |
| `backend/attendance/tests/test_models.py` | Created |
| `backend/attendance/tests/test_rls.py` | Created |
| `backend/attendance/tests/test_services.py` | Created |
| `backend/config/settings.py` | Modified (INSTALLED_APPS) |
| `openspec/changes/m7-attendance/tasks.md` | Modified (D1 checkboxes) |

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| D1.1 | 8 model tests fail (no module) | AttendanceRecord model + constraints | — |
| D1.2 | 3 RLS tests fail (no table/policy) | 0002_rls migration via enable_rls_sql | Relaxed polqual assertion for PG cast normalization |
| D1.3 | 7 service tests fail (no services) | get_roster + bulk_upsert with workspace_scope | active_workspace in post-write assertions; explicit ValueError for invalid status |
| D1.4–D1.7 | — | apps, models, migrations, services, settings | — |
| D1.8 | — | 18 passed; makemigrations clean | — |

## Work Unit Evidence

| Evidence | Value |
|----------|-------|
| Focused test command | `uv run pytest attendance/tests/` → **18 passed** |
| Runtime harness | `uv run python manage.py makemigrations --check --dry-run` → **No changes detected** |
| Rollback boundary | Drop `backend/attendance/`; remove from `INSTALLED_APPS`; `migrate attendance zero` |

## Deviations from Design

None — implementation matches design. Service layer uses `workspace_scope` for ScopedManager/RLS alignment (consistent with `workspaces.scope` pattern).

## Remaining Tasks

D2 (DRF roster + bulk API) and D3 (frontend `/asistencia`) pending.

## Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main)
- Current work unit: D1 complete
- Estimated review budget: ~250–320 lines (within 400 budget)
