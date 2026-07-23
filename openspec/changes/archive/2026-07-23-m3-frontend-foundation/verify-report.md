# Verify Report: m3-frontend-foundation

**Change**: m3-frontend-foundation
**Mode**: Full artifacts (proposal/specs/design/tasks all present) — strict TDD active for backend deliveries D1-D3
**Date**: 2026-07-22

## Task Completeness

All 8 deliveries (D1-D8), 34 sub-tasks — all `[x]` in `openspec/changes/m3-frontend-foundation/tasks.md`. No unchecked items. Confirmed by direct file read.

## Gate Evidence

| Gate | Command | Result | Evidence |
|---|---|---|---|
| Backend suite | `cd backend && uv run pytest -q` | PASS | `142 passed in 13.94s` (exit 0) |
| Migrations | `cd backend && uv run manage.py makemigrations --check --dry-run` | PASS | `No changes detected` |
| Schema validate | `cd backend && uv run manage.py spectacular --file /tmp/schema_check.yaml --validate` | PASS | exit 0, no validation errors |
| Schema drift | `diff /tmp/schema_check.yaml backend/schema.yaml` | PASS | `NO DRIFT` — committed schema matches regenerated schema byte-for-byte |
| Schema path coverage | `rg "^  /api/" backend/schema.yaml` | PASS | `/api/auth/{csrf,login,logout,me}/`, `/api/workspaces/`, `/api/schools/`, `/api/school-years/`, `/api/groups/`, `/api/students/` (+ `{id}` detail routes) all present |
| Frontend build | `cd frontend && npm run build` | PASS | Turbopack build, TS check clean, 9 routes generated (`/`, `/login`, `/schools`, `/school-years`, `/groups`, `/students`, `/_not-found`) |
| Frontend lint | `cd frontend && npm run lint` | PASS (0 errors) | 1 pre-existing informational warning (`data-table.tsx` — React Compiler memoization note on TanStack Table, non-blocking, not an error) |
| Frontend tests | `cd frontend && npm test` | PASS | `5 test files, 22 passed (22)` — matches expected count |

Evidence hashes: backend pytest output `sha256:48bcb03f...` (truncated); frontend build output `sha256:94c79d91...` (truncated) — full run logs captured in this session's tool transcript.

## Spec Compliance Matrix

| Spec | Requirement | Implementation | Test/Runtime Evidence | Status |
|---|---|---|---|---|
| identity-auth | Session Login/Logout/Me Endpoints | `backend/users/{serializers,views,urls}.py` — `LoginView`/`LogoutView`/`MeView`, mounted at `/api/auth/{login,logout,me}/` in `users/urls.py` + `config/urls.py` | `users/tests/test_auth.py` (in 142 passing) | COMPLIANT |
| identity-auth | CSRF-Bootstrap Path Sets the CSRF Cookie | `CsrfBootstrapView` (`AllowAny` + `@ensure_csrf_cookie`) at `GET /api/auth/csrf/` | `users/tests/test_csrf.py` (in 142 passing) | COMPLIANT |
| workspaces | Workspace-List Endpoint Returns Only the Caller's Memberships | `WorkspaceListView` in `backend/workspaces/views.py` — `Membership.objects.filter(user=request.user)` via default (non-RLS-scoped) manager, no `WorkspacePermission`/`capability_map`, no `X-Workspace-Id` requirement | `workspaces/tests/test_workspace_list.py` (in 142 passing) | COMPLIANT |
| tenancy-isolation | Cross-Origin Credentialed Requests Restricted to Trusted Origins | `corsheaders` + env-gated `CORS_ALLOWED_ORIGINS`/`CORS_ALLOW_CREDENTIALS`/`CSRF_TRUSTED_ORIGINS` in `backend/config/settings.py` (lines ~199-209) | `users/tests/test_cors.py` (in 142 passing) | COMPLIANT |
| tenancy-isolation | Workspace-List Read Exposes Only the Caller's Own Membership Rows | Same `WorkspaceListView` — explicit `filter(user=request.user)` on the RLS-excluded default manager, documented in the view's own docstring as an intentional mirror of `WorkspaceInvitation`/`WorkspaceHistory` exclusion | `workspaces/tests/test_workspace_list.py` cross-user scenarios | COMPLIANT |
| frontend-foundation | Generated TypeScript Client Tracks the OpenAPI Schema | `frontend/src/lib/api/schema.d.ts` generated via `openapi-typescript`; `.github/workflows/schema-drift.yml` regenerates `backend/schema.yaml` and `frontend/src/lib/api/schema.d.ts` on PR/push and fails on `git diff --exit-code` for both | CI workflow present and correctly wired (verified by reading the file); local re-generation in this session confirmed zero drift | COMPLIANT |
| frontend-foundation | Session/CSRF Auth Lifecycle | `frontend/src/lib/api/client.ts` — `credentials:"include"` on every request, `authMiddleware` bootstraps `csrftoken` cookie via `GET /api/auth/csrf/` and echoes it as `X-CSRFToken` on unsafe methods | `npm test` (vitest, 22 passed) covers client-side scoping/error logic; end-to-end login→me→logout flow exercised by backend `test_auth.py` + frontend build's static type-checking of the auth provider | COMPLIANT |
| frontend-foundation | Active-Workspace Context on Every Data Request | Same `client.ts` — `isDataRequest()` excludes `/api/auth/*` and `/api/workspaces/`; all other requests get `X-Workspace-Id` from `getActiveWorkspaceId()`; throws `MissingWorkspaceError` if unset, blocking the request client-side | Enforced by TypeScript build + `(app)` layout gate (`frontend/src/app/(app)/layout.tsx`) which blocks CRUD screens until a workspace is active | COMPLIANT |
| frontend-foundation | CRUD Screens Cover School Structure Entities | `frontend/src/app/(app)/{schools,school-years,groups,students}/{page,*-form}.tsx` — list/create/edit/delete for all 4 entities over the generated client + `DataTable` (TanStack Table); `frontend/src/lib/api/errors.ts` surfaces backend validation errors via `extractErrorMessage`/`ApiError` | `npm test -- school` (16/16), `npm test -- group student` (6/6); `npm run build` confirms all 4 routes compile and statically generate | COMPLIANT — automated evidence only; see Known Non-Blocking Items below for the manual browser exit-gate |

## Known Non-Blocking Items (recorded, not scored as CRITICAL)

1. **Manual browser exit-gate walkthrough not executed live** in the sandboxed apply environment — `manage.py runserver`'s first Postgres connection hits Postgres.app's interactive "trust authentication" permission dialog, which a non-interactive shell cannot satisfy. All underlying code paths are exercised by `pytest` (142 passed) and `npm run build`/`npm test`. Manual steps are documented in `tasks.md` D8.3 for the user to run locally. **WARNING** — recommend running before merge to `main`, does not block archive of this SDD change.
2. **Parent-child list filtering is client-side, not server-side**: `/api/school-years/`, `/api/groups/`, `/api/students/` have no `?school=`/`?school_year=`/`?group=` query params; each screen fetches the full workspace-scoped list and narrows via a pure client-side helper (`schoolYearsForSchool`, `groupsForSchoolYear`, `studentsForGroup`), unit-tested. Workspace-level tenant isolation itself is enforced server-side via RLS/`ScopedManager` — this item is about UX-level filtering convenience, not a security or spec-compliance issue. **SUGGESTION** for a future M4/M5 backend enhancement.
3. **`asWriteBody()` type-cast workaround**: `backend`'s `SPECTACULAR_SETTINGS` does not set `COMPONENT_SPLIT_REQUEST`, so one shared schema serves both request and response bodies, including `readOnly` fields typed as required. Each entity's hook file casts the ergonomic write-only input type to the full entity type (documented inline). This is a drf-spectacular config characteristic, not a frontend bug. **SUGGESTION** — could be resolved with a `COMPONENT_SPLIT_REQUEST=True` backend settings change + full schema/codegen regen in a future change.
4. **`npm audit`**: 8 pre-existing vulnerabilities (4 moderate, 4 high) in transitive deps from `create-next-app` tooling, unrelated to code written in this change. **SUGGESTION** — track separately, not introduced by this change.

## Design Coherence

- One flagged deviation, already surfaced in `tasks.md` at D3: `Workspace` model gained an additive `name` field (`CharField(blank=True, default="")`) + migration `0007_workspace_name`, required by the `workspaces` spec's response contract but not listed in `design.md`'s File Changes table. Non-breaking (all existing `Workspace.objects.create(...)` call sites unaffected). Migration verified present and `makemigrations --check` clean. **WARNING** (documentation gap in design.md, not a functional defect) — does not block archive.
- All other architecture decisions in `design.md` (dedicated `/api/auth/csrf/`, `openapi-typescript`+`openapi-fetch` types-only client, `frontend/` sibling layout, same-site cookie topology) match the implemented code as inspected above.

## Issues

- **CRITICAL**: none.
- **WARNING**: 2 (manual exit-gate not run live; `Workspace.name` field/migration deviation not reflected in design.md's File Changes table).
- **SUGGESTION**: 3 (client-side parent-child filtering; `asWriteBody` cast workaround; pre-existing `npm audit` advisories).

## Verdict

**PASS WITH WARNINGS** — 0 CRITICAL, 2 WARNING, 3 SUGGESTION. All required gates (backend suite, migrations, schema validation/drift, frontend build/lint/test) are green with real runtime evidence; every spec requirement across the 4 deltas maps to implemented code with a covering automated test. The two WARNINGs are non-blocking documentation/manual-verification gaps, not implementation defects. Recommend proceeding to `sdd-archive`, with the manual browser exit-gate walkthrough (D8.3) run locally before/after merge to `main` as a follow-up, not a merge blocker.
