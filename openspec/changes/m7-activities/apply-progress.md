# Apply Progress: m7-activities

**Mode**: Strict TDD  
**Work unit**: D1 — models + RLS + services  
**Branch**: `feat/m7-activities-d1` (from `origin/main`)  
**Delivery**: force-chained / stacked-to-main  
**Commit**: `feat(grades): add models, RLS, and services`

## Completed Tasks

- [x] D1.1 RED model tests
- [x] D1.2 RED RLS tests
- [x] D1.3 RED service tests
- [x] D1.4 GREEN apps/models
- [x] D1.5 GREEN migrations + RLS
- [x] D1.6 GREEN services
- [x] D1.7 GREEN INSTALLED_APPS
- [x] D1.8 Verify + commit

## Remaining

- [ ] D2–D5 (not in this batch)

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| D1.1 | `backend/grades/tests/test_models.py` | Unit | N/A (new) | ✅ Written (`ModuleNotFoundError`) | ✅ 16 model tests pass | ✅ ScopedModel / uniqueness / ProtectedError / null≠0 / empty subjects | ✅ Clean |
| D1.2 | `backend/grades/tests/test_rls.py` | Integration (Postgres RLS) | N/A (new) | ✅ Written | ✅ 5 RLS tests pass | ✅ 3 tables + no-context + foreign-ws | ➖ Single policy form |
| D1.3 | `backend/grades/tests/test_services.py` | Unit/Integration | N/A (new) | ✅ Written | ✅ 10 service tests pass | ✅ ensure_terms idempotent; bad tipo/empty/cross-field; filters+stats; matrix null; bulk 10.5 + wrong student + workspace | ✅ Extracted `_filter_activities` / `_compute_stats` |
| D1.4–D1.7 | (same) | — | N/A | Driven by D1.1–D1.3 | ✅ Implemented | Covered above | Minimal |
| D1.8 | `uv run pytest backend/grades/` | — | — | — | ✅ 31 passed; makemigrations clean | — | — |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `uv run pytest backend/grades/` → **31 passed** in ~2.0s |
| Runtime harness command/scenario and exact result | `uv run python manage.py makemigrations --check --dry-run` → **No changes detected**. Rollback harness: `uv run python manage.py migrate grades zero` (not executed; reversible migrations present) |
| Rollback boundary | Drop `backend/grades/`; remove `grades` from `INSTALLED_APPS` in `backend/config/settings.py`; revert `openspec/changes/m7-activities/` if desired |

## Test Summary

- **Total tests written**: 31
- **Total tests passing**: 31
- **Layers used**: Unit (models/services), Integration/RLS (portal_app + NULLIF)
- **Approval tests**: None — new code
- **Pure helpers**: `_filter_activities`, `_compute_stats`, `_validate_catalog`, `_validate_group_workspace`

## Deviations from Design

- `Term.school_year` uses `PROTECT` (spec) rather than design’s CASCADE wording — spec is authoritative.
- Design ownership table listed `settings.py` under D2; tasks + apply scope assign `INSTALLED_APPS` to D1 (followed tasks).
- `grades` registered after `students` on `main` (no `attendance` app on `main` yet).

## Issues / Risks

- Authored line count for D1 (tests + migrations + services) likely exceeds the ~280–360 / 400-line review budget forecast; PR may need reviewer note or trim in verify. Product code alone (~models+services+apps+settings) is ~394 lines; tests inflate the PR.
- Attendance mirror lived on `feat/m7-attendance-d*` and is **not** on `main`; patterns were taken from that branch history, not the current tree.

## Workload / PR Boundary

- Mode: stacked PR slice (D1 → `main`)
- Current work unit: D1
- Boundary: new `grades` domain (models/RLS/services/tests) + planning artifacts + INSTALLED_APPS
- Next: D2 APIs on `feat/m7-activities-d2` after D1 merges (or stacked onto this branch per orchestrator)
