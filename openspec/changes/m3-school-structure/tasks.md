# Tasks: M3 School Structure

Delivery strategy: `force-chained` (chain_strategy=feature-branch-chain). One commit per delivery, strict TDD (RED test → GREEN implementation), each delivery ≤~400 changed lines, budget check via `gentle-ai review` at 400 lines/delivery.

Test command: `uv run pytest`
Migration check command: `uv run python manage.py makemigrations --check --dry-run`

Every delivery MUST end with both commands green before moving to the next delivery.

---

## D1 — `schools` app: School / SchoolYear / Group models + RLS helper extraction

Satisfies: school-structure §Entity Field Shapes and Constraints; tenancy-isolation §RLS Coverage Extends to School Structure Tables.

Sequential (must run before D2-D6). ~230 lines.

- [x] D1.1 RED: write failing tests for `School`, `SchoolYear`, `Group` model shape/constraints (name required, cct optional, level enum; SchoolYear unique(school,label); Group grado validators 1-3 + unique(school_year,grado,grupo)) in `backend/schools/tests/test_models.py`.
- [x] D1.2 RED: write failing RLS backstop tests for `schools_school`, `schools_schoolyear`, `schools_group` using `_portal_app_connection()` pattern from `backend/workspaces/tests/test_rls.py` (foreign-workspace row invisible; no-context denies, not errors) in `backend/schools/tests/test_rls.py`.
- [x] D1.3 GREEN: create `backend/schools/` app (`apps.py`, `models.py`) — `School(ScopedModel)`, `SchoolYear(ScopedModel)`, `Group(ScopedModel)` per design exact field shapes; `db_table` per spec (`schools_school`, `schools_schoolyear`, `schools_group`).
- [x] D1.4 GREEN: extract `backend/workspaces/rls.py` with `enable_rls_sql(table)` / `disable_rls_sql(table)` helpers in NULLIF form, refactored out of existing `0004` migration (0003/0004 stay frozen — only extract, do not alter their emitted SQL).
- [x] D1.5 GREEN: `backend/schools/migrations/0001_initial.py` (models) + `backend/schools/migrations/0002_rls.py` (ENABLE RLS + CREATE POLICY only, via `rls.py` helper, for all three tables).
- [x] D1.6 GREEN: register `schools` in `INSTALLED_APPS` (before `students`, added in D2).
- [x] D1.7 Verify: `uv run pytest backend/schools/ backend/workspaces/` green; `uv run python manage.py makemigrations --check --dry-run` clean.

---

## D2 — `students` app: Student model + RLS

Satisfies: school-structure §Entity Field Shapes and Constraints (Student.curp indexed non-unique, Student.group PROTECT); tenancy-isolation §RLS Coverage Extends to School Structure Tables.

Sequential, depends on D1. ~110 lines.

- [x] D2.1 RED: write failing tests for `Student` model — curp non-unique (two students same curp allowed), `group` FK is `PROTECT` (deleting a `Group` with students raises `ProtectedError`), field shapes — in `backend/students/tests/test_models.py`.
- [x] D2.2 RED: write failing RLS backstop test for `students_student` (foreign-workspace row invisible, no-context denies) in `backend/students/tests/test_rls.py`.
- [x] D2.3 GREEN: create `backend/students/` app — `Student(ScopedModel)` with `group` FK (string ref `"schools.Group"`, `on_delete=PROTECT`, `related_name="students"`), `curp = CharField(18, blank=True, db_index=True)` (no `unique=True`), name fields per design.
- [x] D2.4 GREEN: `backend/students/migrations/0001_initial.py` (depends on `schools.0001_initial`) + `backend/students/migrations/0002_rls.py` (reuse `rls.py` helper) for `students_student`.
- [x] D2.5 GREEN: register `students` in `INSTALLED_APPS` after `schools`.
- [x] D2.6 Verify: `uv run pytest backend/students/ backend/schools/` green; migrations check clean.

---

## D3 — Services layer (schools + students)

Satisfies: school-structure §CRUD Gated by edit_content Capability; §Cross-Entity Workspace Consistency Validation.

Sequential, depends on D1+D2. ~180 lines.

- [ ] D3.1 RED: write failing unit tests for `schools/services.py` (`create_school`, `update_school`, `delete_school`, `create_school_year`, `update_school_year`, `delete_school_year`, `create_group`, `update_group`, `delete_group`) — keyword-only args, `PermissionDenied` when membership lacks `edit_content`, `ValueError` when parent's workspace does not match `membership.workspace`, workspace assigned from `membership.workspace` (never client input) — in `backend/schools/tests/test_services.py`.
- [ ] D3.2 RED: write failing unit tests for `students/services.py` (`create_student`, `update_student`, `delete_student`) with same permission/consistency contract, including group-must-belong-to-membership-workspace check, in `backend/students/tests/test_services.py`.
- [ ] D3.3 GREEN: implement `backend/schools/services.py` — each function keyword-only, wrapped in `transaction.atomic`, asserts `has_permission(membership, "edit_content")` else raises `PermissionDenied`, asserts parent `workspace_id == membership.workspace_id` else raises `ValueError`.
- [ ] D3.4 GREEN: implement `backend/students/services.py` with same pattern, validating `group.workspace_id == membership.workspace_id`.
- [ ] D3.5 Verify: `uv run pytest backend/schools/ backend/students/` green; migrations check clean (no model changes expected, so this step is a no-op guard).

---

## D4 — Wiring fixes: TenancyMiddleware membership + WorkspacePermission capability map

Satisfies: tenancy-isolation §TenancyMiddleware Attaches Resolved Membership to request.membership; authorization §WorkspacePermission Implements has_permission via a Capability Map.

Sequential, depends on D1-D3 conceptually independent but ordered before D5/D6 (viewsets need both fixes). ~90 lines.

- [ ] D4.1 RED: write failing test asserting `TenancyMiddleware` sets `request.membership` to the resolved `Membership` object (not merely checking `.exists()`) on both the header-based (`X-Workspace-Id`) and personal-workspace resolution paths, in `backend/workspaces/tests/test_middleware.py`.
- [ ] D4.2 RED: write failing test asserting `WorkspacePermission.has_permission(request, view)` reads `view.capability_map.get(view.action)` and calls `has_permission(membership, capability)` — verify `list`/`retrieve` map to `view_workspace` and `create`/`update`/`partial_update`/`destroy` map to `edit_content`, and that raw DRF action verbs are never passed directly into `has_permission`, in `backend/workspaces/tests/test_permissions.py`.
- [ ] D4.3 GREEN: update `TenancyMiddleware` to fetch and attach the `Membership` object to `request.membership` on both resolution paths.
- [ ] D4.4 GREEN: update `WorkspacePermission.has_permission` (and `has_object_permission` for consistency) to resolve via `capability_map`.
- [ ] D4.5 Verify: run the FULL `backend/workspaces/` test suite (`uv run pytest backend/workspaces/`) to prove no regression against M1/M2 behavior; migrations check clean.

---

## D5 — `schools` DRF surface (serializers, viewsets, urls)

Satisfies: school-structure §DRF CRUD Endpoints Are Workspace-Scoped and Isolated; §PROTECT Surfaces a Clean 4xx on Group Delete With Students.

Sequential, depends on D1-D4. ~220 lines.

- [ ] D5.1 RED: write failing HTTP tests (APIClient + `X-Workspace-Id` header) for School/SchoolYear/Group CRUD — create/list/retrieve/update/destroy scoped to workspace, cross-workspace request returns empty list / 404, `edit_content`-lacking membership gets 403 on write actions, deleting a `Group` with `Student` rows returns a clean 4xx (not a 500) — in `backend/schools/tests/test_api.py`.
- [ ] D5.2 GREEN: `backend/schools/serializers.py` — `SchoolSerializer`, `SchoolYearSerializer`, `GroupSerializer` (workspace field read-only/excluded from input).
- [ ] D5.3 GREEN: `backend/schools/viewsets.py` — `SchoolViewSet`, `SchoolYearViewSet`, `GroupViewSet` (`ModelViewSet`, `permission_classes=[IsAuthenticated, WorkspacePermission]`, `capability_map`, `get_queryset` returns `Model.objects.all()` relying on `ScopedManager`, `perform_create`/`perform_update`/`perform_destroy` delegate to `schools/services.py`); catch `ProtectedError` on `Group` destroy and translate to a clean 4xx response.
- [ ] D5.4 GREEN: `backend/schools/urls.py` with `DefaultRouter` registering all three viewsets; wire into `backend/config/urls.py` via `path("api/", include(...))` (first real API routes in the project).
- [ ] D5.5 Verify: `uv run pytest backend/schools/` green; migrations check clean.

---

## D6 — `students` DRF surface (serializer, viewset, urls)

Satisfies: school-structure §DRF CRUD Endpoints Are Workspace-Scoped and Isolated.

Sequential, depends on D1-D5. ~120 lines.

- [ ] D6.1 RED: write failing HTTP tests for Student CRUD (same pattern as D5.1: scoped isolation, capability gating, cross-workspace 404/empty) in `backend/students/tests/test_api.py`.
- [ ] D6.2 GREEN: `backend/students/serializers.py` — `StudentSerializer`.
- [ ] D6.3 GREEN: `backend/students/viewsets.py` — `StudentViewSet` (same shape as D5.3, delegating to `students/services.py`).
- [ ] D6.4 GREEN: `backend/students/urls.py` registered via `DefaultRouter`; include into `backend/config/urls.py` under `api/`.
- [ ] D6.5 Verify: `uv run pytest` (full suite) green; migrations check clean.

---

## D7 (optional) — Retire `WorkspaceResource` test scaffold

Satisfies: cleanup / tech debt noted in design (`WorkspaceResource fate`); no new spec requirement, follow-up only.

Sequential, depends on D1-D6. ~80 lines. Optional — may be deferred to a follow-up change.

- [ ] D7.1 RED: update `backend/workspaces/tests/test_rls.py` and `backend/workspaces/tests/test_pooling_leak.py` to target a real scoped model (e.g. `schools.School`) instead of `WorkspaceResource`; expect these to fail against the still-present `WorkspaceResource`-based fixtures until migration lands.
- [ ] D7.2 GREEN: add a migration disabling RLS on and dropping the `WorkspaceResource` table; remove the model and its RLS policy from `workspaces/models.py`.
- [ ] D7.3 GREEN: repoint the two test files fully to the new scoped model fixtures.
- [ ] D7.4 Verify: `uv run pytest` (full suite) green; migrations check clean; confirm `WorkspaceResource` has zero remaining references.

---

## Review Workload Forecast

Chained PRs: **Yes** (feature-branch-chain; each delivery is its own branch/PR stacked on the previous).

| Delivery | Est. changed lines | 400-line budget risk |
|---|---|---|
| D1 | ~230 | Low — comfortably under budget |
| D2 | ~110 | Low |
| D3 | ~180 | Low |
| D4 | ~90 | Low |
| D5 | ~220 | Low-Medium — first real HTTP surface + urls wiring; watch for test bloat pushing over budget if all CRUD+edge-case tests land in one file |
| D6 | ~120 | Low |
| D7 (optional) | ~80 | Low, but touches shared test fixtures (`test_rls.py`, `test_pooling_leak.py`) used by earlier deliveries — coordinate carefully to avoid conflicts with D1/D2 RLS backstop tests |

No delivery is forecast to exceed the 400-line review budget. D5 is the closest to risk because it is the first delivery introducing DRF routing (serializers + viewsets + urls + config wiring) alongside a full HTTP test matrix (CRUD × isolation × capability gating × PROTECT 4xx); if test volume grows, split D5 into D5a (School+SchoolYear) / D5b (Group) rather than exceeding budget.
