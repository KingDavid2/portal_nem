# Apply Progress: M7 Attendance

**Change**: m7-attendance  
**Mode**: Strict TDD  
**Branch**: feat/m7-attendance-d2  
**Status**: D1 complete (8/8), D2 complete (7/7)

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

- [x] D2.1 RED: HTTP tests in `test_api.py` (roster merge, empty group, cross-workspace 404, missing params 400, bulk atomic/wrong-group/invalid status/notes, X-Workspace-Id required)
- [x] D2.2 RED: capability map tests (roster→view_workspace, bulk→edit_content, 403 without edit_content)
- [x] D2.3 GREEN: `serializers.py` with roster/bulk serializers + `@extend_schema`
- [x] D2.4 GREEN: `views.py` — `AttendanceRosterView`, `AttendanceBulkView` (quizzy APIView pattern)
- [x] D2.5 GREEN: `urls.py` + `config/urls.py` wiring
- [x] D2.6 GREEN: `schema.yaml` + `schema.d.ts` regenerated
- [x] D2.7 Verify: 30 passed; makemigrations clean; commit

### D2 TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| D2.1 | 10 HTTP tests fail (404/no routes) | serializers, views, urls, config wiring | IntegerField for group/student IDs (BigAutoField) |
| D2.2 | 2 capability tests fail (no views module) | capability_map keys match action names | — |
| D2.3–D2.5 | — | serializers + views + urls | Cross-workspace missing students → 400 not 404 |
| D2.6 | — | gen:schema + gen:api | — |
| D2.7 | — | 30 passed (12 new API + 18 D1) | — |

### Work Unit Evidence (D2)

| Evidence | Value |
|----------|-------|
| Focused test command | `uv run pytest attendance/tests/test_api.py` → **12 passed** |
| Full attendance suite | `uv run pytest attendance/tests/` → **30 passed** |
| Runtime harness | `uv run python manage.py makemigrations --check --dry-run` → **No changes detected** |
| Rollback boundary | Revert views/urls/config routes + schema; keep D1 domain |

### Files Changed (D2)

| File | Action |
|------|--------|
| `backend/attendance/serializers.py` | Created |
| `backend/attendance/views.py` | Created |
| `backend/attendance/urls.py` | Created |
| `backend/attendance/tests/test_api.py` | Created |
| `backend/config/urls.py` | Modified |
| `backend/schema.yaml` | Modified |
| `frontend/src/lib/api/schema.d.ts` | Modified |
| `openspec/changes/m7-attendance/tasks.md` | Modified |

### Deviations from Design

- `capability_map` keys use custom action names (`roster`, `bulk`) not HTTP verbs — required by `WorkspacePermission._resolve_capability` which indexes by `view.action` (authorization spec alignment).

### Remaining Tasks

D3 (frontend `/asistencia`, hooks, nav, tones) pending.

### Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main)
- Current work unit: D2 complete
- Estimated review budget: ~280–360 lines (within 400 budget)
