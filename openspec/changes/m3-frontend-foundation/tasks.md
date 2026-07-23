# Tasks: m3-frontend-foundation — Next.js frontend foundation + backend auth seam

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2100-2600 total across 8 deliveries (~150-400 each) |
| 400-line budget risk | High (as a whole change); Low-Medium per delivery |
| Chained PRs recommended | Yes |
| Suggested split | D1 → D2 → D3 → D4 → D5 → D6 → D7 → D8 (one commit per delivery, sequential) |
| Delivery strategy | force-chained @ 400-line budget (no remote, tracker branch only) |
| Chain strategy | feature-branch-chain (all commits land on `m3-frontend-foundation`, no PRs) |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Delivery | Focused test command | Runtime harness | Rollback boundary |
|------|------|----------|----------------------|-----------------|-------------------|
| 1 | corsheaders + CORS/CSRF settings + csrf-bootstrap endpoint | D1 | `cd backend && uv run pytest -q users/tests/test_cors.py users/tests/test_csrf.py` | N/A — settings-only, exercised via pytest APIClient | revert `settings.py` CORS block + drop `csrf` view/url |
| 2 | session login/logout/me endpoints | D2 | `cd backend && uv run pytest -q users/tests/test_auth.py` | N/A — DRF APIClient covers real routes | revert `users/{serializers,views,urls}.py`, drop from `config/urls.py` |
| 3 | workspace-list endpoint | D3 | `cd backend && uv run pytest -q workspaces/tests/test_workspace_list.py` | N/A — APIClient | revert `workspaces/{views,urls}.py`, drop from `config/urls.py` |
| 4 | Next.js scaffold | D4 | `cd frontend && npm run build` | `cd frontend && npm run dev` (manual load of `/`) | delete `frontend/` |
| 5 | schema dump + TS codegen + drift check | D5 | `cd backend && uv run manage.py spectacular --file schema.yaml --validate` then `cd frontend && npx openapi-typescript ../backend/schema.yaml -o src/lib/api/schema.d.ts` and diff | CI job dry-run (`act` or manual script run) | revert `schema.yaml`, `schema.d.ts`, codegen script, CI job |
| 6 | fetch layer: session/CSRF/workspace header wiring | D6 | `cd frontend && npm test -- fetch-client` | manual: login → `GET /api/auth/me/` → switch workspace → `GET /api/workspaces/` | revert `frontend/src/lib/api/*` client wrapper + login/switcher components |
| 7 | school + school_year CRUD screens | D7 | `cd frontend && npm test -- school` | manual: create/list/edit/delete a School and SchoolYear via UI | revert `frontend/src/app/(app)/schools/*`, `school-years/*` |
| 8 | group + student CRUD screens + exit-gate walkthrough | D8 | `cd frontend && npm test -- group student` | manual exit-gate: teacher creates school→ciclo→grupo→alumno via Next.js app | revert `frontend/src/app/(app)/groups/*`, `students/*` |

## Phase 1: Backend auth-seam (Slice 1, strict TDD, pytest)

### D1 — corsheaders + CORS/CSRF settings + CSRF-bootstrap endpoint
_Spec: identity-auth "CSRF-Bootstrap Path Sets the CSRF Cookie"; tenancy-isolation "Cross-Origin Credentialed Requests Restricted to Trusted Origins"_

- [x] 1.1 RED: `backend/users/tests/test_cors.py` — cross-origin credentialed request from an allowlisted origin gets `Access-Control-Allow-Credentials`; request from a non-allowlisted origin does not.
- [x] 1.2 RED: `backend/users/tests/test_csrf.py` — `GET /api/auth/csrf/` sets non-httpOnly `csrftoken` cookie for anon client; echoing that token on a subsequent write is accepted.
- [x] 1.3 GREEN: add `django-cors-headers` to `backend/pyproject.toml`; add `corsheaders` app + `CorsMiddleware` at correct position in `MIDDLEWARE` (`backend/config/settings.py`).
- [x] 1.4 GREEN: env-gated `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS=True`, `CSRF_TRUSTED_ORIGINS` in `backend/config/settings.py` (dev: `localhost:3000`→`:8000`, no `SESSION_COOKIE_DOMAIN`; prod: `app.*`/`api.*` + `SESSION_COOKIE_DOMAIN`/`CSRF_COOKIE_DOMAIN`/`*_SECURE`).
- [x] 1.5 GREEN: `csrf_bootstrap` view (`AllowAny` + `@ensure_csrf_cookie`) in `backend/users/views.py`; mount `GET /api/auth/csrf/` in `backend/users/urls.py`.
- [x] 1.6 Run `cd backend && uv run pytest -q` — full suite (131 baseline + new) green.
- [x] 1.7 Commit: `feat(auth): add CORS + CSRF-bootstrap endpoint`.

### D2 — session login/logout/me endpoints
_Spec: identity-auth "Session Login/Logout/Me Endpoints"_ — depends on D1 (CSRF cookie + real `/api/auth/` mount point)

- [x] 2.1 RED: retarget `backend/users/tests/test_auth.py` from throwaway urlconf to real `/api/auth/login/`, `/logout/`, `/me/` routes; cover valid login (200 + cookie), invalid login (4xx, no cookie), logout clears session, `/me/` authed vs anon (401/403).
- [x] 2.2 GREEN: `LoginSerializer`/`UserSerializer` in `backend/users/serializers.py`.
- [x] 2.3 GREEN: `login`/`logout`/`me` views in `backend/users/views.py` (session auth, no JWT).
- [x] 2.4 GREEN: mount `/api/auth/login/`, `/api/auth/logout/`, `/api/auth/me/` in `backend/users/urls.py`; include `users.urls` under `api/` in `backend/config/urls.py`.
- [x] 2.5 Run `cd backend && uv run pytest -q` — full suite green.
- [x] 2.6 Commit: `feat(auth): add session login/logout/me endpoints`.

### D3 — workspace-list endpoint
_Spec: workspaces "Workspace-List Endpoint Returns Only the Caller's Memberships"; tenancy-isolation "Workspace-List Read Exposes Only the Caller's Own Membership Rows"_ — depends on D1 (auth/session available for APIClient login in tests)

- [ ] 3.1 RED: `backend/workspaces/tests/test_workspace_list.py` — `GET /api/workspaces/` returns only caller's memberships (id, name, type, role); never includes another user's workspace; anonymous request denied; no `X-Workspace-Id` required.
- [ ] 3.2 GREEN: `MembershipListSerializer` + `WorkspaceListView` in `backend/workspaces/views.py`, querying `Membership.objects.filter(user=request.user)` via the default (RLS-excluded) manager — no `WorkspacePermission`/`capability_map`.
- [ ] 3.3 GREEN: mount `GET /api/workspaces/` in `backend/workspaces/urls.py`; include under `api/` in `backend/config/urls.py`.
- [ ] 3.4 Run `cd backend && uv run pytest -q` and `uv run manage.py makemigrations --check --dry-run` — both clean.
- [ ] 3.5 Commit: `feat(workspaces): add workspace-list endpoint`.

## Phase 2: Frontend scaffold + codegen (Slice 2) — depends on D1-D3

### D4 — Next.js App Router scaffold
_Spec: frontend-foundation (project shell, prerequisite for all Requirements)_

- [ ] 4.1 Scaffold `frontend/` (Next.js App Router + TypeScript + Tailwind), own `package.json`, sibling to `backend/`.
- [ ] 4.2 Install + configure shadcn/ui and TanStack Query/Table.
- [ ] 4.3 Minimal runnable app shell (`frontend/src/app/layout.tsx`, `page.tsx`) — builds and runs with `npm run dev`.
- [ ] 4.4 Commit: `feat(frontend): scaffold Next.js app shell`.

### D5 — type pipeline: schema dump + TS codegen + CI drift check
_Spec: frontend-foundation "Generated TypeScript Client Tracks the OpenAPI Schema"_ — depends on D4

- [ ] 5.1 Add `backend/schema.yaml` dump script (`manage.py spectacular --file schema.yaml --validate`), commit initial dump.
- [ ] 5.2 Add `openapi-typescript` + `openapi-fetch` deps to `frontend/package.json`; generate `frontend/src/lib/api/schema.d.ts` and a thin client wrapper.
- [ ] 5.3 Add CI job (`.github/workflows/schema-drift.yml` or equivalent) that regenerates `schema.yaml` and `schema.d.ts` and fails on `git diff --exit-code`.
- [ ] 5.4 Commit: `feat(frontend): add OpenAPI schema→TS codegen pipeline with drift check`.

### D6 — fetch-layer auth/session/workspace wiring
_Spec: frontend-foundation "Session/CSRF Auth Lifecycle", "Active-Workspace Context on Every Data Request"_ — depends on D2, D3, D5

- [ ] 6.1 `createClient({baseUrl, credentials:'include'})` wrapper in `frontend/src/lib/api/client.ts`; middleware reads `csrftoken` cookie → sets `X-CSRFToken` on unsafe methods.
- [ ] 6.2 Login/logout flow calling `POST /api/auth/csrf/` → `POST /api/auth/login/` → `POST /api/auth/logout/`; `GET /api/auth/me/` bootstrap on app load.
- [ ] 6.3 Active-workspace store + switcher UI backed by `GET /api/workspaces/`; middleware sets `X-Workspace-Id` on every data request; block data requests when no workspace selected.
- [ ] 6.4 `frontend` test: `npm test -- fetch-client` — credentials always included, CSRF rejection surfaces, workspace header follows switcher.
- [ ] 6.5 Commit: `feat(frontend): wire session/CSRF/workspace fetch layer`.

## Phase 3: CRUD screens (Slice 3) — depends on D6

### D7 — school + school_year CRUD screens
_Spec: frontend-foundation "CRUD Screens Cover School Structure Entities" (School, SchoolYear)_

- [ ] 7.1 School list/create/edit/delete screens over the generated client + TanStack Table (`frontend/src/app/(app)/schools/*`).
- [ ] 7.2 SchoolYear list/create/edit/delete screens (`frontend/src/app/(app)/school-years/*`).
- [ ] 7.3 Surface backend validation errors on invalid create/edit payloads.
- [ ] 7.4 Commit: `feat(frontend): add School and SchoolYear CRUD screens`.

### D8 — group + student CRUD screens + exit-gate
_Spec: frontend-foundation "CRUD Screens Cover School Structure Entities" (Group, Student)_

- [ ] 8.1 Group list/create/edit/delete screens (`frontend/src/app/(app)/groups/*`).
- [ ] 8.2 Student list/create/edit/delete screens (`frontend/src/app/(app)/students/*`).
- [ ] 8.3 Manual exit-gate walkthrough: logged-in teacher creates school → ciclo → grupo → alumno end-to-end via the app; note result in PR description.
- [ ] 8.4 Commit: `feat(frontend): add Group and Student CRUD screens`.
