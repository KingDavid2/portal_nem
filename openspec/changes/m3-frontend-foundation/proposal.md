# Proposal: m3-frontend-foundation — Next.js frontend foundation + backend auth seam

## Why now

Backend M2 tenancy + M3 school-structure CRUD are done (131/131 tests, first real DRF HTTP surface
at `/api/`), but there is no frontend and no browser-usable auth seam. Per `docs/roadmap.md`
(Milestone 3 — Frontend), the frontend is interleaved, not trailing: M3 carries the **one-time
frontend bootstrap** — auth seam + generated TS client — so M4–M7 build screens with zero new
auth/type plumbing. This change delivers that bootstrap plus the backend session/CSRF/CORS/workspace
endpoints it requires. Bounded by `docs/roadmap.md` (M3 + exit gate) and `docs/design-brief.md` §3
(httpOnly session cookie, CORS-with-credentials, CSRF echo — **not** JWT-in-localStorage, so student
PII is never XSS-readable).

## Scope (in)

- **Backend auth seam** — session `login`/`logout`/`me` endpoints + a CSRF-bootstrap endpoint;
  `django-cors-headers` (CORS with credentials) + `CSRF_TRUSTED_ORIGINS`.
- **Workspace-list endpoint** — `GET /api/workspaces/` returning the user's memberships (hard
  blocker for the switcher; none exists today).
- **`frontend/` service** — Next.js App Router + TS + Tailwind + shadcn/ui + TanStack Query/Table,
  sibling to `backend/`.
- **Type pipeline** — DRF → OpenAPI (`drf-spectacular`, already wired) → generated TS client, with a
  CI drift check.
- **Workspace context** — active-workspace switcher sends `X-Workspace-Id` on every request.
- **CRUD screens** — school / school_year / group / student, end-to-end over the generated client.

## Non-goals

Rich data-entry grids (M4/M5), billing (M6), tutor/parent portal (M7), any JWT/localStorage token,
Django-rendered end-user HTML.

## Capabilities (contract for sdd-spec)

- **New**: `frontend-foundation`.
- **Modified**: `identity-auth` (session + CSRF-bootstrap endpoints), `workspaces` (workspace-list
  endpoint), `tenancy-isolation` (cross-origin credentialed path + cross-workspace membership read).

## Open decisions (resolve in sdd-design — do not decide here)

- CSRF-bootstrap endpoint shape: dedicated `GET /api/auth/csrf/` vs `ensure_csrf_cookie` on `/me/`.
- TS-codegen tool: `openapi-typescript`+`openapi-fetch` vs `orval`.
- `frontend/` layout (open in `openspec/config.yaml` since M2).
- Dev-vs-prod cookie domain (`localhost:3000↔:8000` vs `app.*`/`api.*`, `SESSION_COOKIE_DOMAIN`) —
  verify live.

## Delivery (force-chained @ 400-line budget)

Three chained-PR slices: (1) backend auth-seam — corsheaders, login/logout/me + CSRF bootstrap,
workspace-list, `CSRF_TRUSTED_ORIGINS` (pytest-testable, lands first); (2) frontend scaffold +
codegen (may chain internally); (3) CRUD screens (splittable by entity pair). Each slice splits into
one-commit deliveries, strict TDD on the backend half.

## Exit gate

A logged-in teacher creates school → ciclo → grupo → alumno through the Next.js app via the
generated TS client, with session cookie + CSRF echo + workspace scoping all live.
