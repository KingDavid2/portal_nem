# Apply Progress: m7-activities

**Mode**: Strict TDD  
**Delivery**: force-chained / stacked-to-main  
**Status**: D1 + D2 complete

## Completed Tasks

### D1 — models + RLS + services
**Branch**: `feat/m7-activities-d1` (from `origin/main`)  
**Commit**: `feat(grades): add models, RLS, and services`

- [x] D1.1 RED model tests
- [x] D1.2 RED RLS tests
- [x] D1.3 RED service tests
- [x] D1.4 GREEN apps/models
- [x] D1.5 GREEN migrations + RLS
- [x] D1.6 GREEN services
- [x] D1.7 GREEN INSTALLED_APPS
- [x] D1.8 Verify + commit

### D2 — DRF activities + matrix/bulk API
**Branch**: `feat/m7-activities-d2` (from `feat/m7-activities-d1`)  
**Commit**: `feat(grades): add activities and scores API`

- [x] D2.1 RED HTTP tests (activities/matrix/bulk)
- [x] D2.2 RED capability tests (list/create/matrix/bulk)
- [x] D2.3 GREEN serializers
- [x] D2.4 GREEN views (`ensure_terms` + services)
- [x] D2.5 GREEN urls + `api/grades/` include
- [x] D2.6 GREEN OpenAPI regen (`schema.yaml` + `schema.d.ts`)
- [x] D2.7 Verify + commit

## Remaining

- [ ] D3–D5 (not in this batch)

## TDD Cycle Evidence

### D1

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| D1.1 | `backend/grades/tests/test_models.py` | Unit | N/A (new) | ✅ Written (`ModuleNotFoundError`) | ✅ 16 model tests pass | ✅ ScopedModel / uniqueness / ProtectedError / null≠0 / empty subjects | ✅ Clean |
| D1.2 | `backend/grades/tests/test_rls.py` | Integration (Postgres RLS) | N/A (new) | ✅ Written | ✅ 5 RLS tests pass | ✅ 3 tables + no-context + foreign-ws | ➖ Single policy form |
| D1.3 | `backend/grades/tests/test_services.py` | Unit/Integration | N/A (new) | ✅ Written | ✅ 10 service tests pass | ✅ ensure_terms idempotent; bad tipo/empty/cross-field; filters+stats; matrix null; bulk 10.5 + wrong student + workspace | ✅ Extracted `_filter_activities` / `_compute_stats` |
| D1.4–D1.7 | (same) | — | N/A | Driven by D1.1–D1.3 | ✅ Implemented | Covered above | Minimal |
| D1.8 | `uv run pytest backend/grades/` | — | — | — | ✅ 31 passed; makemigrations clean | — | — |

### D2

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| D2.1 | `backend/grades/tests/test_api.py` | Integration (APIClient) | ✅ 31/31 | ✅ Written (404 / ModuleNotFoundError) | ✅ HTTP paths pass | ✅ create+list; filters; foreign 404; matrix null≠0; bulk N / wrong student / OOB | ✅ Decimal assertions |
| D2.2 | `backend/grades/tests/test_api.py` | Unit + Integration | ✅ 31/31 | ✅ Written | ✅ Cap map + 403 write/read | ✅ list/create/matrix/bulk maps; viewer-only write deny; no-cap read deny | ➖ Map tests single-path |
| D2.3–D2.5 | (same) | — | — | Driven by D2.1–D2.2 | ✅ serializers/views/urls | Covered above | ✅ `_resolve_group_and_term` |
| D2.6 | OpenAPI regen | — | — | — | ✅ `npm run gen:all` | ➖ Structural | N/A |
| D2.7 | `uv run pytest backend/grades/` | — | — | — | ✅ **46 passed** | — | — |

## Work Unit Evidence

### D1

| Evidence | Value |
|---|---|
| Focused test command and exact result | `uv run pytest backend/grades/` → **31 passed** in ~2.0s |
| Runtime harness command/scenario and exact result | `uv run python manage.py makemigrations --check --dry-run` → **No changes detected**. Rollback harness: `uv run python manage.py migrate grades zero` (not executed; reversible migrations present) |
| Rollback boundary | Drop `backend/grades/`; remove `grades` from `INSTALLED_APPS` in `backend/config/settings.py`; revert `openspec/changes/m7-activities/` if desired |

### D2

| Evidence | Value |
|---|---|
| Focused test command and exact result | `uv run pytest grades/` (cwd `backend/`) → **46 passed** in ~3.9s |
| Runtime harness command/scenario and exact result | `npm run gen:all` → schema + `schema.d.ts` regenerated with `/api/grades/activities/`, `/api/grades/scores/matrix/`, `/api/grades/scores/bulk/`. Manual curl deferred (local servers may use other apps); APIClient suite covers authz + contracts. |
| Rollback boundary | Revert `backend/grades/{serializers,views,urls}.py`, `backend/grades/tests/test_api.py`, `backend/config/urls.py` grades include, and OpenAPI regen files; keep D1 domain (models/services/migrations) |

## Test Summary

- **Total tests written (cumulative)**: 46 (31 D1 + 15 D2 API)
- **Total tests passing**: 46
- **Layers used**: Unit (models/services/cap maps), Integration/RLS, Integration/APIClient
- **Approval tests**: None — new code
- **Pure helpers**: D1 `_filter_activities` / `_compute_stats` / `_validate_*`; D2 `_terms_payload` / `_resolve_group_and_term`

## Deviations from Design

- `Term.school_year` uses `PROTECT` (spec) rather than design’s CASCADE wording — spec is authoritative (D1).
- Design ownership table listed `settings.py` under D2; tasks assign `INSTALLED_APPS` to D1 (followed tasks).
- D2 mirrors attendance/quizzy `APIView` + `capability_map`; activities view sets `action` to `list`/`create` in `initial()` (spec keys, not raw HTTP verbs).

## Issues / Risks

- D1 authored volume exceeded ~400-line review budget (tests + openspec inflate).
- D2 authored ~999 lines (serializers+views+urls+tests+config); product-only ~398; API tests ~601. OpenAPI regen (~1100 lines) excluded from authored budget per tasks. PR may need reviewer note.
- Attendance mirror lived on `feat/m7-attendance-d*` (used for patterns); not on `main`.

## Workload / PR Boundary

- Mode: stacked PR slice (D2 → previous D1 branch / `main` after D1 merges)
- Current work unit: D2
- Boundary: grades DRF surface + OpenAPI regen; domain models/services unchanged
- Next: D3 frontend hooks + Por actividad list/modal + nav on `feat/m7-activities-d3`
