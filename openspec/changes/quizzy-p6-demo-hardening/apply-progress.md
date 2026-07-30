# Apply Progress: quizzy-p6-demo-hardening

**Mode**: Strict TDD  
**Batch**: Slice 1a (Phase 1, tasks 1.1–1.5)  
**Branch**: `feat/quizzy-p6-s1a-demo-throttle`  
**Updated**: 2026-07-30

## Completed Tasks

- [x] 1.1 RED `backend/demo/tests/test_throttling.py`
- [x] 1.2 GREEN `CACHES` + `DEFAULT_THROTTLE_RATES` (demo scopes only)
- [x] 1.3 GREEN `backend/conftest.py` autouse `cache.clear()`
- [x] 1.4 GREEN demo views `ScopedRateThrottle` + scopes
- [x] 1.5 VERIFY focused + full suite

## Remaining (not this batch)

- [ ] Phase 2 Slice 1b (2.1–2.9)
- [ ] Phase 3 Slice 2 (3.1–3.5)
- [ ] Phase 4 Slice 3 (4.1–4.6)
- [ ] Phase 5 Slice 4 (5.1–5.5)

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `demo/tests/test_throttling.py` | Integration | ✅ 10/10 `demo/tests/test_api.py` | ✅ Written (6 fail: no throttle) | ✅ Deferred to 1.2–1.4 | ✅ 6 cases (3 ceilings + 2 independence + provision cycle) | ➖ N/A (test-only) |
| 1.2 | same | Integration | ✅ settings load | ✅ Covered by 1.1 | ✅ Passed after CACHES + rates | ➖ Structural (config) | ➖ None needed |
| 1.3 | same | Integration | N/A (new) | ✅ Covered by 1.1 (leak risk) | ✅ Passed with autouse clear | ➖ Structural (fixture) | ➖ None needed |
| 1.4 | same | Integration | ✅ 10/10 demo API | ✅ Covered by 1.1 | ✅ Passed after view attrs | ✅ All three views scoped | ➖ None needed |
| 1.5 | same | Integration | — | — | ✅ 6/6 focused; ✅ 505 passed full suite | — | — |

### Work Unit Evidence

| Evidence | Value |
|----------|-------|
| Focused test command | `cd backend && uv run pytest demo/tests/test_throttling.py` → **6 passed** |
| Full suite | `cd backend && uv run pytest` → **505 passed in 37.35s** |
| Runtime harness | N/A — pytest LocMem override replaces Redis; no live broker needed |
| Rollback boundary | Remove `backend/conftest.py`, `CACHES`/`DEFAULT_THROTTLE_RATES` demo keys from settings, throttle attrs from `demo/views.py`, and `demo/tests/test_throttling.py` |

### Workload / PR Boundary

- Mode: stacked PR slice (`stacked-to-main`)
- Current work unit: Slice 1a — Redis CACHES + conftest + demo throttle scopes
- Boundary: stops before GenerationRateThrottle / MCP HTTP throttle (Slice 1b)
- Estimated review budget: Low–Medium (well under 400 authored lines)

### Deviations from Design

None — implementation matches design Slice 1 / throttle+cache sections.

### Issues Found

None. Note: demo views keep `authentication_classes = []`, so poll throttle stays IP-keyed even after `django_login` on a ready session (provision-cycle test relies on this).
