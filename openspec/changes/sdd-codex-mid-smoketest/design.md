# Design: Public Liveness Health Endpoint

## Technical Approach

Add a minimal, unauthenticated `GET /api/health/` liveness endpoint to the existing
`core` app (already in `INSTALLED_APPS`, currently views/urls/tests-less). A DRF
`APIView` returns a static `{"status": "ok", "version": <app version>}` payload with
HTTP 200. The version string is resolved once at module import from installed package
metadata. The route is wired through a new `core/urls.py`, included under the existing
`/api/` prefix in `config/urls.py` alongside the other app URLconfs. No DB, no
serializer, no tenancy context, no side effects. This maps directly to the proposal's
`service-health` capability and its "no readiness, no DB, AllowAny" constraints.

## Architecture Decisions

### Decision: View style — DRF `APIView` vs plain Django view

**Choice**: DRF `APIView` with `permission_classes = [AllowAny]` and
`authentication_classes = []`.
**Alternatives considered**: Plain Django `JsonResponse` view; DRF `@api_view`
function view.
**Rationale**: The project's DRF defaults are `IsAuthenticated` +
`SessionAuthentication` (settings `REST_FRAMEWORK`). A plain Django view would bypass
DRF but sit inconsistently beside every other endpoint. `APIView` matches the repo's
class-based convention (e.g. `workspaces.views.WorkspaceListView`); explicit
`AllowAny` overrides the global auth default, and empty `authentication_classes`
fully decouples liveness from session/CSRF machinery.

### Decision: Version source

**Choice**: `importlib.metadata.version("portal-nem-backend")`, computed once at
import into a module-level constant, wrapped in `try/except PackageNotFoundError`
with a `"0.0.0"` fallback.
**Alternatives considered**: Hardcode `"0.1.0"`; read
`settings.SPECTACULAR_SETTINGS["VERSION"]`.
**Rationale**: `pyproject.toml` `[project].version` ("0.1.0") is the canonical single
source of truth; `importlib.metadata` reads the installed distribution
(`portal-nem-backend`) without duplicating the literal. The Spectacular setting is
semantically the API-schema version, and hardcoding drifts. The fallback keeps the
liveness probe resilient if metadata is unavailable (it must never 500).

### Decision: Route placement

**Choice**: New `core/urls.py` with `path("health/", ...)`, included via
`path("api/", include("core.urls"))` in `config/urls.py`.
**Alternatives considered**: Register `health/` directly in `config/urls.py`.
**Rationale**: Every app owns its URLconf and is mounted under `/api/`; `core` should
follow the same pattern for consistency and future core-level routes.

## Data Flow

    GET /api/health/ ──→ config.urls ──→ core.urls ──→ HealthView.get()
                                                            │
                                    (module constant APP_VERSION, no DB)
                                                            │
                              200 {"status":"ok","version":"0.1.0"}

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/core/views.py` | Create | `HealthView(APIView)`, AllowAny, empty auth, returns status+version |
| `backend/core/urls.py` | Create | `urlpatterns = [path("health/", HealthView.as_view(), name="health")]` |
| `backend/config/urls.py` | Modify | Add `path("api/", include("core.urls"))` |
| `backend/core/tests/__init__.py` | Create | Make tests a package |
| `backend/core/tests/test_health.py` | Create | Anonymous 200, JSON shape, no-DB assertions |

## Interfaces / Contracts

Response contract (HTTP 200, `application/json`):

    {"status": "ok", "version": "<app version string>"}

Module-level: `APP_VERSION: str` resolved at import. `HealthView` exposes only `get`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Integration | Anonymous caller gets 200 | pytest-django + DRF `APIClient` (no login), assert `status_code == 200` |
| Integration | JSON body shape | Assert `resp.json() == {"status": "ok", "version": APP_VERSION}` and `status == "ok"` |
| Integration | No DB access | Test declares NO `@pytest.mark.django_db`; pytest-django blocks DB by default, so any query fails the test — proving liveness is DB-free |
| Integration | AllowAny / no auth | Assert unauthenticated client is not 401/403 |

Framework: pytest + pytest-django (configured in `pyproject.toml [tool.pytest.ini_options]`).

## Threat Matrix

N/A — the only boundary touched is a Django URL route with no shell command,
subprocess, VCS/PR automation, executable-file classification, or process
integration. All matrix rows (git selection, commit/push state, PR commands,
documentation-like executable paths) are N/A for a read-only in-process HTTP view.

## Migration / Rollout

No migration required. Stateless, additive; rollback is reverting the single commit.

## Open Questions

- [ ] Confirm `portal-nem-backend` is installed as a resolvable distribution in the
      runtime env; if not, the metadata fallback path (`"0.0.0"`) governs and the
      version source decision may switch to `SPECTACULAR_SETTINGS["VERSION"]`.
