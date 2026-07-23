# Tasks: Public Liveness Health Endpoint

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~60-90 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (D1) |
| Delivery strategy | single small slice (auto) |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Ship `GET /api/health/` (RED→GREEN) | PR 1 | `cd backend && uv run pytest -q core/tests/test_health.py` | `cd backend && uv run manage.py runserver` then `curl -i http://localhost:8000/api/health/` | Revert `core/views.py`, `core/urls.py`, `core/tests/test_health.py`, `core/tests/__init__.py`, and the one-line include in `config/urls.py` |

## Phase 1: RED — Failing Tests First

- [x] 1.1 Create `backend/core/tests/__init__.py` (empty, makes `core/tests` a package).
- [x] 1.2 Create `backend/core/tests/test_health.py` with anonymous-client tests (no `@pytest.mark.django_db`): assert `GET /api/health/` returns 200; assert JSON body `== {"status": "ok", "version": APP_VERSION}` imported from `core.views`.
- [x] 1.3 Add scenario test: assert response is not 401/403 for an unauthenticated client (AllowAny scenario).
- [x] 1.4 Add scenario test: assert an authenticated client (DRF `APIClient.force_authenticate`) also gets 200 with the same body shape.
- [x] 1.5 Run `cd backend && uv run pytest -q core/tests/test_health.py` and confirm all new tests FAIL (RED) — route/view do not exist yet.

## Phase 2: GREEN — Minimal Implementation

- [x] 2.1 Create `backend/core/views.py`: resolve `APP_VERSION` at module import via `importlib.metadata.version("portal-nem-backend")` wrapped in `try/except PackageNotFoundError` falling back to `"0.0.0"`.
- [x] 2.2 In `backend/core/views.py`, add `HealthView(APIView)` with `permission_classes = [AllowAny]`, `authentication_classes = []`, and `get()` returning `Response({"status": "ok", "version": APP_VERSION})` (no DB access).
- [x] 2.3 Create `backend/core/urls.py` with `urlpatterns = [path("health/", HealthView.as_view(), name="health")]`.
- [x] 2.4 Modify `backend/config/urls.py` to add `path("api/", include("core.urls"))` alongside existing app URLconf includes.
- [x] 2.5 Run `cd backend && uv run pytest -q core/tests/test_health.py` and confirm all tests PASS (GREEN).

## Phase 3: Verification

- [x] 3.1 Run `cd backend && uv run pytest -q` (full suite) to confirm no regressions and pytest-django's default DB block still holds (no query executed by the health test).
- [x] 3.2 Manually verify: `cd backend && uv run manage.py runserver`, then `curl -i http://localhost:8000/api/health/` returns `200` and `{"status":"ok","version":"..."}`.
- [x] 3.3 Confirm each spec scenario is covered: anonymous 200, no-DB, authenticated-also-200.

## Phase 4: Cleanup

- [x] 4.1 Confirm no stray imports/unused code in `core/views.py` and `core/urls.py`.
- [x] 4.2 Re-read `openspec/changes/sdd-codex-mid-smoketest/design.md` File Changes table to confirm every listed file was created/modified as planned.

## Deviation Note (discovered during apply)

Global `DATABASES["default"]["ATOMIC_REQUESTS"] = True` in `backend/config/settings.py`
wraps every view in a per-request DB transaction, which triggers a DB connection
attempt on entry even for query-free views — this tripped pytest-django's DB-block
guard on the first GREEN attempt. Fixed by adding
`@method_decorator(non_atomic_requests, name="dispatch")` to `HealthView` in
`backend/core/views.py` (not listed in the original design's File Changes table, but
required to satisfy the "no DB query" spec requirement). No `config/settings.py`
changes were made; `ATOMIC_REQUESTS` remains global and unchanged.
