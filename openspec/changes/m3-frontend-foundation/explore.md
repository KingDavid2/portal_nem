# Exploration: M3 Frontend Foundation (Next.js bootstrap + backend auth seam)

Change: `m3-frontend-foundation` · Project: portal_nem · Phase: explore

The one-time frontend bootstrap M4–M7 build on. Authoritative intent: `docs/roadmap.md`
(Milestone 3 — Frontend) and `docs/design-brief.md` §3 (auth seam). No implementation here.

## Current State

**HTTP surface today** (`backend/config/urls.py`): `admin/`, `api/schema/` + `api/docs/`
(drf-spectacular, `SERVE_INCLUDE_SCHEMA: False`), and `api/` includes `schools.urls` +
`students.urls` — two `DefaultRouter`s registering `SchoolViewSet`, `SchoolYearViewSet`,
`GroupViewSet` (`backend/schools/viewsets.py`) and `StudentViewSet`
(`backend/students/viewsets.py`). All are `ModelViewSet`s with `[IsAuthenticated,
WorkspacePermission]` + a `capability_map` (`list/retrieve → view_workspace`,
`create/update/partial_update/destroy → edit_content`). A TS client consumes:
`GET/POST /api/schools/`, `/api/school-years/`, `/api/groups/`, `/api/students/` — all
requiring session auth + `X-Workspace-Id`.

**Auth config** (`backend/config/settings.py:165-187`): `SessionAuthentication` is the sole
`DEFAULT_AUTHENTICATION_CLASSES`; cookies already match design-brief §3:
`SESSION_COOKIE_HTTPONLY=True`, `CSRF_COOKIE_HTTPONLY=False`, both `SAMESITE=Lax`.
`INSTALLED_APPS`/`MIDDLEWARE` have **no `corsheaders`** — confirmed absent from both lists and
from `pyproject.toml` dependencies.

**Workspace/tenancy path** (`backend/workspaces/middleware.py`, `permissions.py`,
`managers.py`): `TenancyMiddleware` reads `X-Workspace-Id`, requires membership (403 otherwise)
or falls back to personal workspace, attaches `request.membership`, sets `app.workspace_id` via
`SET LOCAL` inside a per-request `transaction.atomic()`. `WorkspacePermission` resolves
`view.action` → capability via `capability_map` → `has_permission(membership, capability)`
(role/capability frozenset matrix). Fully wired and tested; a TS client needs to log in, send
`X-Workspace-Id`, and know its workspace list.

**Users app** (`backend/users/models.py`): custom email-identified `User`. **No
`users/views.py`, `urls.py`, or `serializers.py` exist.** `backend/users/tests/test_auth.py`
proves Django's session+CSRF stack works, but via a throwaway `ROOT_URLCONF` override using
stock `LoginView`/`LogoutView` + a local `_WhoAmI` view — **not** anything mounted in
`config/urls.py`. There is no production login/logout/me endpoint.

**Workspaces app**: **no `workspaces/urls.py`, no `workspaces/views.py`** — service+model-only.
No `GET /api/workspaces/` (memberships list) endpoint exists.

**Dependencies** (`backend/pyproject.toml`): django, django-environ, djangorestframework,
drf-spectacular, pgvector, psycopg. No `django-cors-headers`. `uv`-managed backend; no root
`package.json`; no `frontend/` directory anywhere — genuinely greenfield.

## Backend Gaps (concrete)

1. No CORS support (`corsheaders` not installed/configured) — blocks cross-origin cookie-based
   fetch from a separate-origin SPA. **This is the blocking piece, not the cookie flags.**
2. No session login/logout/me endpoints — `users` app is models-only.
3. No CSRF-bootstrap endpoint — nothing forces the `csrftoken` cookie for an API-only backend.
4. No workspace-listing endpoint — **hard blocker for the workspace switcher.**
5. No `CSRF_TRUSTED_ORIGINS` configured for the frontend origin(s).

## CSRF/Session Flow

`CSRF_COOKIE_HTTPONLY=False` + `SameSite=Lax` is correctly set for an SPA to echo the token via
`X-CSRFToken`, but the actual cross-origin gate is CORS (`credentials: 'include'` client-side +
explicit `Access-Control-Allow-Origin` + `Access-Control-Allow-Credentials: true` server-side).
Cookie-domain sharing between `localhost:3000`/`localhost:8000` in dev vs `api.*`/`app.*` in prod
(needing `SESSION_COOKIE_DOMAIN`) needs live verification at design time, not static reading.

## Approaches (real forks — decide at design)

**CSRF bootstrap**: (1) dedicated `GET /api/auth/csrf/` — explicit, schema-visible, one extra
round trip; (2) piggyback `ensure_csrf_cookie` on `GET /api/auth/me/` — fewer round trips, less
discoverable. Both Low effort.

**TS client codegen**: (1) `openapi-typescript` + `openapi-fetch` — types only, hand-written call
sites, minimal generated surface, Low/Medium effort; (2) `orval` — full generated client +
optional TanStack Query hooks, less per-endpoint boilerplate, heavier config, Medium effort. Both
integrate into CI via a static schema dump (`manage.py spectacular --file schema.yaml`) +
drift-check, avoiding a live-server dependency.

## Frontend Stack

`frontend/` as a sibling subdirectory to `backend/` (own `package.json`, no Nx/Turborepo for one
app) mirrors the existing `uv`-managed `backend/` layout. `openspec/config.yaml` flags this layout
choice as still formally open — confirm at design. Node lives only in `frontend/`.

## Recommended Slicing (chained-PR delivery, 400-line budget)

1. **Backend auth-seam slice** — corsheaders, users login/logout/me + CSRF bootstrap, workspaces
   list endpoint, `CSRF_TRUSTED_ORIGINS`. Small, `pytest`-testable, no frontend dependency, lands
   first.
2. **Frontend scaffold slice** — Next.js/Tailwind/shadcn init, TS client codegen + CI drift check,
   auth/session bootstrap, workspace switcher. May need internal chaining (scaffold+codegen, then
   auth/session integration).
3. **CRUD-screens slice** — school/school_year/group/student screens over the generated client +
   TanStack Table; splits by entity pair if size risk appears.

## Risks / Unknowns

- CORS/cookie-domain dev-vs-prod behavior analyzed from static config only — needs live
  verification at `sdd-design`.
- Workspace-list endpoint gap is a hard switcher blocker — must be explicitly scoped into slice 1.
- `users/tests/test_auth.py`'s isolated-urlconf pattern needs reconciling once real endpoints land
  (rewrite vs keep as settings-proof) — currently ambiguous.
- TS client tool choice (`openapi-typescript` vs `orval`) affects scaffold-slice shape/line count;
  decide at `sdd-design`.
- Repo-root vs `backend/`-subdir layout for `frontend/` is an open decision in
  `openspec/config.yaml` from M2 — assumed sibling-subdirectory; design must confirm.
