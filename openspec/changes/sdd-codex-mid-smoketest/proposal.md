# Proposal: Public Liveness Health Endpoint

## Intent

Infra, uptime monitors, and load-balancer health probes need a cheap, unauthenticated
way to confirm the service process is up. Today no such endpoint exists, so probes must
hit authenticated or DB-backed routes, coupling liveness to auth/tenancy/DB availability
and producing noisy false negatives. Add a minimal `GET /api/health/` liveness check.

## Scope

### In Scope
- New endpoint `GET /api/health/` in the existing `core` app.
- Public access (DRF `AllowAny`), no authentication, no workspace/tenancy context.
- JSON response `{"status": "ok", "version": <app version string>}`, HTTP 200.
- Version sourced from the app version string (e.g. `pyproject`/package metadata).

### Out of Scope
- Readiness checks, DB/cache/broker connectivity probes (explicit non-goal).
- Metrics, tracing, or Prometheus-style exposition.
- Auth, rate limiting, tenancy scoping, or side effects of any kind.

## Capabilities

### New Capabilities
- `service-health`: unauthenticated liveness endpoint exposing service up-state and version.

### Modified Capabilities
- None.

## Approach

Add a lightweight DRF view (or plain view) in `core` with `permission_classes = [AllowAny]`
and no authentication classes, returning a static JSON payload plus the app version resolved
once at import/startup. Register the route under the existing `/api/` URL namespace. No DB
query, no middleware dependence on tenancy, no serializer needed.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/core/views.py` | New | Health view returning status + version |
| `backend/core/urls.py` (or project urls) | Modified | Register `health/` under `/api/` |
| `backend/core/tests/` | New | Test 200, JSON shape, AllowAny, no DB access |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Version string exposed publicly | Low | Version is non-sensitive; already shippable metadata |
| Endpoint accidentally guarded by global auth/tenancy middleware | Med | Explicit `AllowAny` + test asserting anonymous 200 with no DB hit |
| Route collision under `/api/` | Low | Confirm `health/` path is unused before registering |

## Rollback Plan

Revert the single commit: remove the view, its URL registration, and its test. No migration,
no data, no persisted state — rollback is stateless and immediate.

## Dependencies

- Access to the app version string (existing `pyproject` version `0.1.0` / package metadata).

## Success Criteria

- [ ] `GET /api/health/` returns HTTP 200 with `{"status": "ok", "version": "<x>"}`.
- [ ] Endpoint responds for anonymous callers (no auth token required).
- [ ] No database query is issued while serving the request.
- [ ] No readiness/metrics logic added (non-goals respected).
