# Tasks: M7 Actividades (grades)

Delivery strategy: `force-chained` (chain_strategy=`stacked-to-main`). One commit per delivery (D1→D5), strict TDD (RED → GREEN), each delivery ≤~400 authored lines. Tests travel with the code in the same work unit. OpenAPI regen (`schema.yaml` / `schema.d.ts`) excluded from authored budget — if regen alone overflows the PR, land as D2b or omit from budget count.

Backend test command: `uv run pytest backend/grades/`
Migration check: `uv run python manage.py makemigrations --check --dry-run`
Frontend test command: `npm run test -- --run src/app/\(app\)/actividades/`

Session preflight: `execution_mode=auto`, `review_budget_lines=400`, Strict TDD ACTIVE.

Every delivery MUST end with its focused test command green before opening the next stacked PR.

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1290–1840 authored total (~280–360 + ~280–380 + ~300–400 + ~280–400 + ~150–300); OpenAPI regen extra / excluded |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 (D1) → PR2 (D2) → PR3 (D3) → PR4 (D4) → PR5 (D5), each stacked to `main` |
| Delivery strategy | force-chained |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| D1 | Models + RLS + services + unit/RLS tests | PR1 → `main` | `uv run pytest backend/grades/` | `uv run python manage.py migrate grades zero` | Drop `backend/grades/`; remove from `INSTALLED_APPS` |
| D2 | DRF activities/matrix/bulk + API tests + OpenAPI | PR2 → `main` | `uv run pytest backend/grades/tests/test_api.py` | `curl GET/POST /api/grades/activities/` + matrix/bulk with `X-Workspace-Id` | Revert views/urls/config routes; keep D1 domain |
| D3 | Hooks + Por actividad list/modal + nav | PR3 → `main` | `npm run test -- --run src/app/\(app\)/actividades/` (list/modal cases) | Manual: `/actividades` Nueva → create persists | Remove page/nav/hooks; keep D2 API |
| D4 | Por alumno matrix + draft Map + Guardar + vitest | PR4 → `main` | `npm run test -- --run src/app/\(app\)/actividades/` | Manual: edit cell → Guardar → reload | Revert matrix/draft hunks in page |
| D5 | Stats/filters/banner/Periodo polish | PR5 → `main` | `npm run test -- --run src/app/\(app\)/actividades/` | Manual: Periodo required; Exportar absent; banner | Revert polish-only hunks |

If D3 or D4 exceeds 400 authored lines, split modal (D3a) from list shell (D3b), or matrix UI (D4a) from Guardar/vitest (D4b) before apply. If OpenAPI regen inflates D2, land schema as D2b (or exclude from authored budget).

### File ownership (explicit)

| File | Owner |
|------|-------|
| `backend/grades/{apps,models,services}.py` | D1 |
| `backend/grades/migrations/0001_initial.py` + `0002_rls.py` | D1 |
| `backend/grades/tests/test_{models,services,rls}.py` | D1 |
| `backend/config/settings.py` (`INSTALLED_APPS`) | D1 |
| `backend/grades/{serializers,views,urls}.py` + `tests/test_api.py` | D2 |
| `backend/config/urls.py` (`api/grades/`) | D2 |
| `backend/schema.yaml`, `frontend/src/lib/api/schema.d.ts` | D2 (regen; not authored budget) |
| `frontend/src/lib/api/grades.ts` | D3 |
| `frontend/src/app/(app)/actividades/page.tsx` (+ modal) | D3 list/modal; D4 matrix; D5 polish |
| `frontend/src/app/(app)/actividades/page.test.tsx` | D4 (extend in D5 if polish cases) |
| `frontend/src/app/(app)/layout.tsx` (nav `NotebookPen` → `/actividades`) | D3 |

---

## D1 — `grades` app: models + RLS + services

Satisfies: grades §Term/Activity/ActivityScore Invariants, §Catalog Validation (service-level); tenancy-isolation §RLS Coverage Extends to Grades Tables.

Sequential (must land before D2–D5). Est. ~280–360 authored lines. PR1 base = `main`.

- [x] D1.1 RED: failing model tests in `backend/grades/tests/test_models.py` — `Term`/`Activity`/`ActivityScore` as `ScopedModel`; Term `number`∈1..3 unique`(school_year,number)` `db_table=grades_term`; Activity PROTECT→Group+Term, `activity_type`∈`task|activity|project|exam`, non-empty `subject_ids`, `db_table=grades_activity`; ActivityScore PROTECT→Activity+Student, nullable `Decimal(3,1)`, unique`(activity,student)`, `db_table=grades_activityscore`; duplicate Term/score uniqueness raises; student delete with scores → `ProtectedError`.
- [x] D1.2 RED: failing RLS tests in `backend/grades/tests/test_rls.py` — `_portal_app_connection()`; RLS + NULLIF `ws_isolation` on `grades_term`, `grades_activity`, `grades_activityscore`; foreign-workspace Activity/ActivityScore invisible; no-context denies.
- [x] D1.3 RED: failing service tests in `backend/grades/tests/test_services.py` — `ensure_terms(Y)` idempotent seeds 1–3; `create_activity` rejects bad tipo / empty subjects / subject∉field via `lesson_plans.core.catalog`; `list_activities` filters+stats; `get_score_matrix` null≠0.0; `bulk_upsert_scores` atomic all-or-nothing, score 10.5 rejected, wrong-group student no partial write; workspace from membership only.
- [x] D1.4 GREEN: create `backend/grades/{apps,models}.py` per design field shapes and constraints.
- [x] D1.5 GREEN: `backend/grades/migrations/0001_initial.py` + `0002_rls.py` via `workspaces.rls.enable_rls_sql` (reversible; no GRANT/role).
- [x] D1.6 GREEN: implement `backend/grades/services.py` — `ensure_terms`, `create_activity`, `list_activities`, `get_score_matrix`, `bulk_upsert_scores` (keyword-only where mirrored, `transaction.atomic` on bulk).
- [x] D1.7 GREEN: register `grades` in `backend/config/settings.py` (`INSTALLED_APPS`, after `students`/`attendance`).
- [x] D1.8 Verify: `uv run pytest backend/grades/` green; `makemigrations --check --dry-run` clean. Commit `[M7] add grades models RLS and services`.

---

## D2 — DRF activities + matrix/bulk API, authorization, OpenAPI

Satisfies: grades §Activities List and Create, §Scores Matrix Endpoint, §Bulk Score Upsert; authorization §Grades Endpoints Map Custom Actions to Capabilities.

Sequential, depends on D1. Est. ~280–380 authored lines (+ OpenAPI regen excluded). PR2 base = `main` (after PR1 merged).

- [x] D2.1 RED: failing HTTP tests in `backend/grades/tests/test_api.py` — `GET/POST /api/grades/activities/` (group+term required, filters, create then list, foreign group denied, `X-Workspace-Id` required); `GET /api/grades/scores/matrix/` mixed cells null≠0; `PUT /api/grades/scores/bulk/` atomic N / wrong student rollback / OOB score.
- [x] D2.2 RED: failing capability tests in `test_api.py` — `list`/`matrix`→`view_workspace`; `create`/`bulk`→`edit_content`; membership without `edit_content` 403 on POST/PUT before write; without `view_workspace` 403 on GET.
- [x] D2.3 GREEN: `backend/grades/serializers.py` — activities list/create, matrix, bulk request/response; `@extend_schema` on views.
- [x] D2.4 GREEN: `backend/grades/views.py` — `APIView`s mirroring attendance/quizzy: activities list/create (`capability_map` list/create), matrix (`action="matrix"`), bulk (`action="bulk"`); call `ensure_terms` on list/create/matrix; delegate to services.
- [x] D2.5 GREEN: `backend/grades/urls.py` + wire `path("api/grades/", include(...))` in `backend/config/urls.py`.
- [x] D2.6 GREEN: regenerate `backend/schema.yaml` (`npm run gen:schema`) + `npm run gen:api` → `frontend/src/lib/api/schema.d.ts` (not authored budget; split D2b if PR overflows).
- [x] D2.7 Verify: `uv run pytest backend/grades/` green; schema drift inputs clean. Commit `[M7] add grades activities and scores API`.

---

## D3 — Frontend hooks + Por actividad list/modal + nav

Satisfies: grades §Draft Until Guardar + Screen (Por actividad + modal create immediate; nav). Frames `qkWxk`/`nd704`.

Sequential, depends on D2. Est. ~300–400 authored lines. PR3 base = `main` (after PR2 merged).

- [x] D3.1 RED: failing vitest stubs in `frontend/src/app/(app)/actividades/page.test.tsx` — Por actividad list loads with Periodo required; Nueva opens local `role="dialog"`; submit calls POST activities (immediate persist); no score Guardar on Por actividad; Exportar absent.
- [x] D3.2 GREEN: create `frontend/src/lib/api/grades.ts` — typed hooks for activities GET/POST, matrix GET, bulk PUT from generated schema.
- [x] D3.3 GREEN: create `frontend/src/app/(app)/actividades/page.tsx` — toggle shell + Por actividad table/filters skeleton + local create modal (title/tipo/entrega/campo→asignaturas/desc); group from `SchoolTeachingContext`; field/subject picks via lesson-plans API.
- [x] D3.4 GREEN: add nav entry in `frontend/src/app/(app)/layout.tsx` — `NotebookPen` → `/actividades`.
- [x] D3.5 Verify: list/modal vitest cases green; manual smoke create → list refresh. Commit `feat(actividades): add list, modal, and grades hooks`.

---

## D4 — Por alumno matrix + draft Map + Guardar

Satisfies: grades §Draft Until Guardar + Screen (Por alumno drafts until Guardar). Frame `CteCl`.

Sequential, depends on D3. Est. ~280–400 authored lines. PR4 base = `main` (after PR3 merged).

- [x] D4.1 RED: extend `page.test.tsx` — toggle to Por alumno; draft `Map` key `${student}:${activity}`; edit without Guardar does not call bulk; Guardar sends entries; null cell stays null on refetch mock; unscored ≠ 0.0 display.
- [x] D4.2 GREEN: implement Por alumno matrix in `page.tsx` — students×activities from matrix API; client draft Map; **Guardar** → `PUT …/scores/bulk/`; LWW accept response.
- [x] D4.3 Verify: `npm run test -- --run src/app/\(app\)/actividades/` green for matrix/draft/Guardar; manual edit → Guardar → reload. Commit `[M7] add actividades score matrix and Guardar`.

---

## D5 — Stats, filters, banner, Periodo polish

Satisfies: remaining §Draft Until Guardar + Screen UX (stats, filters, Calificaciones banner MAY, Periodo required). Split if >400.

Sequential, depends on D4. Est. ~150–300 authored lines. PR5 base = `main` (after PR4 merged).

- [ ] D5.1 RED: extend vitest — Periodo empty blocks fetch; campo/asignatura/tipo/q filters update list; stats cards match API `stats`; Exportar/auto-save absent; optional Calificaciones banner static/non-navigating.
- [ ] D5.2 GREEN: polish `page.tsx` — wire filters+stats from list response; Periodo from `terms[]`; banner copy only; match frames `qkWxk`/`CteCl` density.
- [ ] D5.3 Verify: full `npm run test -- --run src/app/\(app\)/actividades/` green; manual Periodo/filter/banner smoke. Commit `[M7] polish actividades filters stats and Periodo`.

---

## Threat Matrix

N/A — no applicable threat-matrix rows (design). Authz covered by D2 capability tests + D1 RLS backstop.
