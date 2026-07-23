# Design: m3-frontend-foundation — Next.js frontend foundation + backend auth seam

## Technical Approach

Deliver the one-time frontend bootstrap and the backend seam it needs. Backend adds a browser
auth surface (`corsheaders` + session `login/logout/me` + CSRF bootstrap) and a workspace-list
endpoint, reusing the existing `TenancyMiddleware` / `WorkspacePermission` / `ScopedManager`
stack untouched. Frontend is a sibling `frontend/` Next.js service consuming a TS client
generated from the committed `drf-spectacular` schema. Maps to proposal slices 1–3; specs
`identity-auth`, `workspaces`, `tenancy-isolation`.

## Architecture Decisions

### Decision: dedicated `GET /api/auth/csrf/`

**Choice**: dedicated `AllowAny` view with `@ensure_csrf_cookie`, not piggyback on `/me/`.
**Alternatives**: `ensure_csrf_cookie` on `/me/`.
**Rationale**: the login POST itself needs the `csrftoken` cookie *before* any session exists;
`/me/` is `IsAuthenticated` (403 for anonymous) so it cannot bootstrap CSRF for the login call.
A dedicated anonymous endpoint is the only shape that works pre-login; it is also schema-visible
and idempotent.

### Decision: `openapi-typescript` + `openapi-fetch` (types-only)

**Choice**: types-only client; hand-written thin TanStack Query hooks.
**Alternatives**: `orval` (generated client + generated Query hooks).
**Rationale**: `openapi-fetch` is ~6 kB and fully path/param/response-typed; generated output is a
single `schema.d.ts`, so schema changes produce tiny, reviewable diffs (400-line budget). `orval`
emits large generated hook code that churns every schema change and locks hook shape. M4/M5 hooks
are few per entity and one-liners over the typed client (`client.GET("/api/schools/")`), matching
the codebase's thin-service style.

### Decision: `frontend/` sibling subdir, own `package.json`, no monorepo tooling

**Choice**: `frontend/` beside `backend/`; Node lives only there.
**Alternatives**: repo-root Next.js; Nx/Turborepo.
**Rationale**: mirrors the `uv`-managed `backend/` layout; one app needs no monorepo runner.
Resolves the layout question left open in `openspec/config.yaml` since M2.

### Decision: same-site cookie topology (Lax preserved)

**Choice**: keep frontend and backend on the same registrable domain in every environment.
- **Dev**: `localhost:3000` → `localhost:8000`. `CORS_ALLOWED_ORIGINS=["http://localhost:3000"]`,
  `CORS_ALLOW_CREDENTIALS=True`, `CSRF_TRUSTED_ORIGINS=["http://localhost:3000"]`. No
  `SESSION_COOKIE_DOMAIN` (host-only cookie on `localhost`, port-agnostic).
- **Prod**: `app.example.com` → `api.example.com`. `SESSION_COOKIE_DOMAIN=CSRF_COOKIE_DOMAIN=".example.com"`,
  `SESSION_COOKIE_SECURE=CSRF_COOKIE_SECURE=True`, origins pinned to `https://app.example.com`.
**Rationale**: both hops are same-site (shared eTLD+1), so the existing `SameSite=Lax` cookies are
sent on credentialed cross-origin fetch with no move to `SameSite=None`. All origin/domain values
are env-driven. If ever split across registrable domains, Lax breaks → would force `None`+`Secure`;
we deliberately avoid that.

## Data Flow

    Browser(app) ──GET /api/auth/csrf/──▶ csrftoken cookie
        │  login POST (X-CSRFToken) ─────▶ sessionid cookie
        │  GET /api/workspaces/ ─────────▶ [{workspace_id,type,role}]  (unscoped Membership read)
        └─ GET/POST /api/schools/ (credentials:'include', X-CSRFToken, X-Workspace-Id)
                        │
             TenancyMiddleware(SET LOCAL) ▶ WorkspacePermission ▶ ScopedManager/RLS

**Workspace-list & RLS**: `GET /api/workspaces/` reads `Membership.objects.filter(user=request.user)`.
`Membership` uses the default `Manager` (not `ScopedManager`) and is RLS-excluded exactly like
`WorkspaceInvitation`/`WorkspaceHistory` — the middleware already reads memberships cross-workspace
this way. The view carries no `capability_map` and does not use `WorkspacePermission` (you always
list your own memberships); it must not require `X-Workspace-Id`.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/pyproject.toml` | Modify | add `django-cors-headers` |
| `backend/config/settings.py` | Modify | corsheaders app+middleware, CORS/CSRF trusted origins, env-gated prod cookie domain/secure |
| `backend/users/{serializers,views,urls}.py` | Create | Login/User serializers; `login`/`logout`/`me`/`csrf` views |
| `backend/workspaces/{views,urls}.py` | Create | membership-list view + serializer |
| `backend/config/urls.py` | Modify | include `users.urls`, `workspaces.urls` under `api/` |
| `backend/schema.yaml` | Create | committed `spectacular` dump (drift source) |
| `backend/users/tests/test_auth.py` | Modify | retarget from throwaway urlconf to real `/api/auth/` routes |
| `frontend/**` | Create | Next.js App Router + TS + Tailwind + shadcn + TanStack; `openapi-fetch` client, login, switcher, CRUD |
| `.github/workflows/*` (or CI cfg) | Modify | schema-drift + type-drift checks |

## Interfaces / Contracts

| Method/Path | Auth | Body → Response |
|---|---|---|
| `GET /api/auth/csrf/` | AllowAny, `ensure_csrf_cookie` | → 204 |
| `POST /api/auth/login/` | AllowAny | `{email,password}` → 200 `{id,email}` |
| `POST /api/auth/logout/` | IsAuthenticated | → 204 |
| `GET /api/auth/me/` | IsAuthenticated | → 200 `{id,email}` |
| `GET /api/workspaces/` | IsAuthenticated | → 200 `[{workspace_id,type,role}]` |

**Frontend fetch layer**: `createClient({baseUrl, credentials:"include"})` + a middleware that
adds `X-CSRFToken` (read from `csrftoken` cookie) on unsafe methods and `X-Workspace-Id` from the
active-workspace store. TanStack Query hooks wrap the typed client.

**Schema/drift**: `manage.py spectacular --file schema.yaml --validate` committed; CI regenerates
and `git diff --exit-code schema.yaml`, then regenerates `frontend/…/schema.d.ts`
(`openapi-typescript schema.yaml`) and diffs — no live-server dependency.

## Deliveries (D1–D8)

| D | Slice | Scope |
|---|---|---|
| D1 | 1 backend | corsheaders + CORS/CSRF/cookie settings |
| D2 | 1 backend | auth endpoints login/logout/me/csrf + urls + test retarget |
| D3 | 1 backend | workspace-list endpoint |
| D4 | 1 backend | schema dump + CI drift check |
| D5 | 2 frontend | Next.js scaffold + codegen + type-drift CI |
| D6 | 2 frontend | auth/session/CSRF/`X-Workspace-Id` fetch layer + login + switcher |
| D7 | 3 frontend | school + school_year CRUD screens |
| D8 | 3 frontend | group + student CRUD screens |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | serializers, csrf cookie set | pytest (strict TDD, backend half) |
| Integration | login→me→logout, csrf-reject, workspace-list cross-workspace, CORS credentialed preflight | pytest DRF `APIClient` against real `/api/` routes |
| E2E | teacher creates school→ciclo→grupo→alumno via generated client | manual/Playwright exit gate |

## Threat Matrix

N/A — no runtime shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. CORS-with-credentials, CSRF echo, and session auth are standard
Django surfaces; CI `spectacular`/`git diff` runs in CI, not app runtime.

## Migration / Rollout

No data migration. `corsheaders` and endpoints are additive. Prod cookie domain/secure are
env-gated (`SESSION_COOKIE_DOMAIN` unset in dev). Rollback = revert settings + drop new urls.

## Open Questions (flag to sdd-spec)

- [ ] `tenancy-isolation` spec MUST state the credentialed cross-origin path and record the
  workspace-list endpoint's unscoped `Membership` read as an explicit RLS exclusion (mirror
  Invitation/History wording).
- [ ] `identity-auth` spec MUST cover the four auth endpoints incl. anonymous CSRF bootstrap and
  the `test_auth.py` retarget (throwaway urlconf → real routes).
- [ ] `workspaces` spec MUST define the membership-list contract (no `X-Workspace-Id`, no
  `WorkspacePermission` gate).
