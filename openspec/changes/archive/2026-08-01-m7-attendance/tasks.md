# Tasks: M7 Daily Attendance

Delivery strategy: `force-chained` (chain_strategy=`stacked-to-main`). One commit per delivery (D1→D2→D3), strict TDD (RED → GREEN), each delivery ≤~400 changed lines. Tests travel with the code in the same work unit.

Backend test command: `uv run pytest backend/attendance/`
Migration check: `uv run python manage.py makemigrations --check --dry-run`
Frontend test command: `npm run test -- --run src/app/\(app\)/asistencia/`

Every delivery MUST end with its focused test command green before opening the next stacked PR.

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~850–1080 total (~250–320 + ~280–360 + ~320–400) |
| 400-line budget risk | Medium–High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 (D1) → PR2 (D2) → PR3 (D3), each stacked to `main` |
| Delivery strategy | force-chained |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium–High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| D1 | Model + RLS + services + unit/RLS tests | PR1 → `main` | `uv run pytest backend/attendance/` | `uv run python manage.py migrate attendance zero` | Drop `backend/attendance/`; remove from `INSTALLED_APPS` |
| D2 | DRF roster/bulk + API tests + OpenAPI | PR2 → `main` | `uv run pytest backend/attendance/tests/test_api.py` | `curl GET/PUT /api/attendance/*` with `X-Workspace-Id` | Revert views/urls/config routes; keep D1 domain |
| D3 | Hooks + `/asistencia` + nav + tones + vitest | PR3 → `main` | `npm run test -- --run src/app/\(app\)/asistencia/` | Manual: `/asistencia` Guardar flow | Remove page/nav/hooks; tone tokens additive |

If D3 exceeds 400 lines, split tones (`estado-button`/`stat-card`) into PR3a and page/hooks into PR3b before apply.

---

## D1 — `attendance` app: model + RLS + services

Satisfies: attendance §AttendanceRecord Invariants; tenancy-isolation §RLS Coverage Extends to Attendance Records; bulk service preconditions for §Bulk Upsert Endpoint.

Sequential (must land before D2–D3). Est. ~250–320 lines. PR1 base = `main`.

- [x] D1.1 RED: failing model tests in `backend/attendance/tests/test_models.py` — `AttendanceRecord(ScopedModel)`, `student` PROTECT, `date` DateField, status enum (`present|absent|late|excused`), `notes` ≤500 blank default, unique `(student, date)`, no `group` FK, `db_table=attendance_attendancerecord`; duplicate `(S,D)` raises; deleting student with records raises `ProtectedError`.
- [x] D1.2 RED: failing RLS tests in `backend/attendance/tests/test_rls.py` — `_portal_app_connection()` pattern; RLS enabled + `ws_isolation` NULLIF policy on `attendance_attendancerecord`; foreign-workspace row invisible; no-context denies.
- [x] D1.3 RED: failing service tests in `backend/attendance/tests/test_services.py` — `get_roster(membership, group, date)` returns full group roster merged with saved rows (unsaved default `present`); `bulk_upsert` atomic all-or-nothing; student not in group → reject with no partial write; notes >500 → validation error; workspace from membership only.
- [x] D1.4 GREEN: create `backend/attendance/{apps,models}.py` per design field shapes and constraints.
- [x] D1.5 GREEN: `backend/attendance/migrations/0001_initial.py` + `0002_rls.py` via `workspaces.rls.enable_rls_sql` (reversible; no GRANT/role).
- [x] D1.6 GREEN: implement `backend/attendance/services.py` — `get_roster`, `bulk_upsert` (keyword-only, `transaction.atomic`, group+workspace validation).
- [x] D1.7 GREEN: register `attendance` in `backend/config/settings.py` (`INSTALLED_APPS`, after `students`).
- [x] D1.8 Verify: `uv run pytest backend/attendance/` green; `uv run python manage.py makemigrations --check --dry-run` clean. Commit `[M7] add attendance model RLS and services`.

---

## D2 — DRF roster + bulk API, authorization, OpenAPI

Satisfies: attendance §Roster Read Endpoint, §Bulk Upsert Endpoint, §Status Enum and UI Labels; authorization §Attendance Endpoints Map Custom Actions to Capabilities.

Sequential, depends on D1. Est. ~280–360 lines. PR2 base = `main` (after PR1 merged).

- [x] D2.1 RED: failing HTTP tests in `backend/attendance/tests/test_api.py` — `GET /api/attendance/roster/?group=&date=` (mixed saved/unsaved, empty group, cross-workspace isolation, missing params 400); `PUT /api/attendance/bulk/` (atomic N rows, wrong-group 400 no partial write, invalid status `tardy`, notes >500); `X-Workspace-Id` required.
- [x] D2.2 RED: failing capability tests in `backend/attendance/tests/test_api.py` (or extend `backend/workspaces/tests/test_permissions.py`) — view `action=roster` maps to `view_workspace`; `action=bulk` maps to `edit_content`; membership without `edit_content` gets 403 on bulk before any write.
- [x] D2.3 GREEN: `backend/attendance/serializers.py` — roster query/response, bulk request/response; `@extend_schema` on views.
- [x] D2.4 GREEN: `backend/attendance/views.py` — `AttendanceRosterView` (GET, `capability_map={"roster":"view_workspace"}`, `action="roster"`), `AttendanceBulkView` (PUT, `capability_map={"bulk":"edit_content"}`, `action="bulk"`) mirroring `quizzy/views.py` APIView pattern; delegate to services.
- [x] D2.5 GREEN: `backend/attendance/urls.py` + wire `path("api/attendance/", include(...))` in `backend/config/urls.py`.
- [x] D2.6 GREEN: regenerate `backend/schema.yaml` (`npm run gen:schema` from frontend) + `npm run gen:api` → update `frontend/src/lib/api/schema.d.ts`.
- [x] D2.7 Verify: `uv run pytest backend/attendance/` green; schema drift workflow inputs clean. Commit `[M7] add attendance roster and bulk API`.

---

## D3 — Frontend `/asistencia`, hooks, nav, tone variants

Satisfies: attendance §Daily Attendance Screen, §No Persisted Row Until Explicit Save, §Status Enum and UI Labels (Presente/Ausente/Retardo/Justificado).

Sequential, depends on D2. Est. ~320–400 lines. PR3 base = `main` (after PR2 merged).

- [x] D3.1 RED: failing vitest in `frontend/src/app/(app)/asistencia/page.test.tsx` — draft defaults `present`; toggle without Guardar does not call bulk API; Marcar todos presentes client-only; Guardar sends full roster entries; stat cards match draft; Periodo absent/disabled; Exportar absent; group from `SchoolTeachingContext` + local date `YYYY-MM-DD`.
- [x] D3.2 RED: failing component tests for P/A/R/J tone tokens on `EstadoButton`/`StatCard` — Presente `#72E128`, Ausente `#FF4D49`, Retardo `#FDB528`, Justificado `#26C6F9`.
- [x] D3.3 GREEN: extend `frontend/src/components/ui/estado-button.tsx` and `stat-card.tsx` with attendance tone variants per `LXprh`.
- [x] D3.4 GREEN: create `frontend/src/lib/api/attendance.ts` — typed hooks for roster GET and bulk PUT from generated schema.
- [x] D3.5 GREEN: create `frontend/src/app/(app)/asistencia/page.tsx` — header + Guardar asistencia, Grupo/Fecha filters, four StatCards, DataTable (#, alumno, CURP, P/A/R/J `EstadoButton`, observación), range footer; full roster client-side (no pagination).
- [x] D3.6 GREEN: add nav entry in `frontend/src/app/(app)/layout.tsx` — `ClipboardCheck` → `/asistencia`.
- [x] D3.7 Verify: `npm run test -- --run src/app/\(app\)/asistencia/` green; manual smoke on `/asistencia` Guardar + reload. Commit `[M7] add asistencia page and attendance hooks`.

---

## Threat Matrix

N/A — no applicable threat-matrix rows (design). Authz covered by D2 capability tests + D1 RLS backstop.
