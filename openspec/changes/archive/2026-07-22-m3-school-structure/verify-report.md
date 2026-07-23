# Verification Report — m3-school-structure

**Mode**: full (proposal + specs + design + tasks present)
**Strict TDD**: active
**Verdict**: **PASS**

## Test / Build Evidence

| Command | Result | Exit |
|---|---|---|
| `uv run pytest` (from `backend/`) | 131 passed in 14.15s | 0 |
| `uv run python manage.py migrate --check` | clean | 0 |
| `uv run python manage.py makemigrations --check --dry-run` | "No changes detected" | 0 |

Test breakdown (all green): `schools/tests/{test_api,test_models,test_services,test_rls}.py` (7+7+13+6), `students/tests/{test_api,test_models,test_services,test_rls}.py` (6+3+6+2), `users/*`, `workspaces/*` (72 total, including `test_middleware.py`, `test_permissions.py` regression), `tests/test_scaffold.py`.

## Task Completeness (tasks.md)

D1-D6 all checked `[x]`, verified against real code (not just checkbox trust). D7 intentionally `[ ]` — deferred/optional per design ("WorkspaceResource fate") and explicit orchestrator instruction this run. Not flagged as incomplete.

## Spec Compliance Matrix

| Requirement | Evidence | Status |
|---|---|---|
| Workspace-scoped entities, own denormalized FK | `School`, `SchoolYear`, `Group` (`backend/schools/models.py`), `Student` (`backend/students/models.py`) all subclass `ScopedModel` (`workspaces/models.py:69` `workspace = ForeignKey(Workspace, CASCADE)`), each concrete model gets its own `workspace_id` column | PASS |
| Entity field shapes/constraints | `School.name` required, `cct` blank, `level` TextChoices enum; `SchoolYear` `UniqueConstraint(school,label)`; `Group.grado` `MinValueValidator(1)/MaxValueValidator(3)`, `UniqueConstraint(school_year,grado,grupo)`; `Student.curp` `CharField(18, blank=True, db_index=True)` no `unique=True`; `Student.group` `PROTECT` | Covered by `test_models.py` (both apps), all passing | PASS |
| CRUD gated by edit_content | `schools/services.py`, `students/services.py`: every mutator calls `_require_edit_content` → `PermissionDenied`; workspace-consistency check → `ValueError`; workspace always `membership.workspace` | Covered by `test_services.py` (both apps, 19 tests) | PASS |
| DRF CRUD endpoints workspace-scoped/isolated | `schools/viewsets.py`, `students/viewsets.py`: `get_queryset` relies on `ScopedManager`, `perform_create/update/destroy` delegate to services, `capability_map` present on every viewset | Covered by `test_api.py` (13 HTTP tests) | PASS |
| PROTECT clean 4xx on Group delete with students | `GroupViewSet.perform_destroy` catches `django.db.models.ProtectedError` → `rest_framework.exceptions.ValidationError` | Covered in `schools/tests/test_api.py` | PASS |
| GAP1 — TenancyMiddleware sets request.membership | `workspaces/middleware.py:50-72`: fetches real `Membership` object (not `.exists()`) on both header (`X-Workspace-Id`) and personal-workspace paths, sets `request.membership = membership` before `active_workspace.set(...)` | Covered by `test_middleware.py` | PASS |
| GAP2 — WorkspacePermission capability_map | `workspaces/permissions.py:57-70`: `_resolve_capability` reads `view.capability_map.get(view.action)`; `has_permission`/`has_object_permission` never pass raw DRF verbs into module-level `has_permission` | Covered by `test_permissions.py` (updated to assert capability_map resolution, deliberate behavior change per apply-progress) | PASS |
| RLS coverage — NULLIF form, no GRANT | `workspaces/rls.py` `enable_rls_sql`/`disable_rls_sql` produce `NULLIF(current_setting('app.workspace_id', true), '')::uuid` form; `schools/migrations/0002_rls.py` + `students/migrations/0002_rls.py` do only `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY`, no `GRANT`; migration deps correctly chain to `workspaces.0004_rls_fix_empty_setting` | Verified by direct file read | PASS |
| RLS backstop tests connect as portal_app | `schools/tests/test_rls.py` and `students/tests/test_rls.py` both define `_portal_app_connection()` connecting with `user="portal_app"` (not the Django owner role), mirroring `workspaces/tests/test_rls.py` exactly; each covers no-context-denies and foreign-workspace-invisible scenarios per table | PASS |

## Correctness / Design Coherence

No deviations found between design.md and implemented code: model field shapes, FK on_delete choices, migration dependency chain, services signatures (keyword-only, `transaction.atomic`), viewset shape, and capability_map values all match the design document exactly.

## Issues

**CRITICAL**: None.

**WARNING**: None.

**SUGGESTION**:
- D7 (retire `WorkspaceResource` test scaffold) remains open as an accepted, explicitly deferred follow-up — no action required to archive this change, but track it as a distinct follow-up SDD change before `WorkspaceResource` accumulates further test debt.

## Final Verdict

**PASS** — All D1-D6 required deliveries are complete, task-list state matches code state, full test suite (131 tests) is green, migration state is clean, and every spec requirement (school-structure, authorization delta, tenancy-isolation delta) has direct, currently-passing test coverage. Ready for `sdd-archive`.
