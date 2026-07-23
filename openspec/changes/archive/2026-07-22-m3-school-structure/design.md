# Design: M3 School Structure

## Technical Approach

Two screaming apps (`schools`, `students`) add the `school → school_year → group → student`
hierarchy. Every entity subclasses `ScopedModel` with its own denormalized `workspace` FK, so
`ScopedManager` (fail-closed ORM filter) and per-table Postgres RLS (NULLIF backstop) both key
directly on `workspace_id` — never join-through. Writes go through keyword-only services under
`transaction.atomic()`; DRF viewsets stay thin (reads via `Model.objects.all()`, writes delegate
to services). M3 also promotes M2 tenancy into the first real HTTP surface and closes two
authorization gaps (`request.membership`, `has_permission`). See specs `school-structure`,
`authorization`, `tenancy-isolation`.

## Architecture Decisions

### Decision: Own `workspace` FK on every entity (no join-through)
**Choice**: Each of School/SchoolYear/Group/Student carries its own `workspace` FK (inherited from
`ScopedModel`, `on_delete=CASCADE`). **Alternatives**: derive workspace by joining up the hierarchy.
**Rationale**: RLS predicates and `ScopedManager` must filter one indexed column per row; a
join-through predicate cannot be expressed in a single-table RLS `USING`/`WITH CHECK`, and would
reopen the M2 isolation guarantee.

### Decision: Student FK `on_delete=PROTECT`; others CASCADE
**Choice**: `Student.group = FK("schools.Group", PROTECT)`; SchoolYear/Group use CASCADE up their
parent. **Alternatives**: CASCADE everywhere. **Rationale**: students are the leaf of record —
deleting a group that still holds students must fail loudly, not silently erase roster data. Parent
academic containers may cascade because they are structural, not records-of-people.

### Decision: CURP plain indexed, no uniqueness
**Choice**: `curp CharField(18, blank, db_index=True)`, NO unique constraint (design-brief §2, locked).
**Rationale**: real-world CURP collisions/corrections exist; dedup is out of scope. Index supports
lookup without enforcing a constraint that would reject legitimate rows.

### Decision: Extract `workspaces/rls.py` helper; freeze 0003/0004
**Choice**: New module exposes `enable_rls_sql(table)` / `disable_rls_sql(table)` in the **0004 NULLIF
form**. New `schools/0002_rls.py` and `students/0002_rls.py` call it. **Alternatives**: copy the SQL
inline per migration. **Rationale**: one source of truth prevents policy drift back to the pre-0004
`::uuid` bug. Historical `0003`/`0004` stay byte-frozen (never edit applied migrations).

### Decision: No new GRANT / role in the new RLS migrations
**Choice**: `schools/0002_rls` and `students/0002_rls` only `ENABLE RLS` + `CREATE POLICY`. **Rationale**:
`0003` already ran `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT … TO portal_app`, so every future
table created by the owner auto-grants to `portal_app`. Re-granting or recreating the role would be
redundant and risk divergence.

### Decision: Two M2 gap fixes are prerequisites, not features
**GAP1** — `TenancyMiddleware` fetches the `Membership` object (not `.exists()`) on BOTH the header and
personal-fallback paths and assigns `request.membership`. **GAP2** — `WorkspacePermission.has_permission(request, view)`
resolves `view.capability_map.get(view.action)` → `has_permission(membership, capability)`;
`has_object_permission` kept consistent. **Rationale**: without these, every capability check feeds a
DRF verb into a capability keyspace and always denies — no endpoint can function.

## Data Flow

    HTTP  ──X-Workspace-Id──►  TenancyMiddleware
                                 ├─ sets request.membership (Membership obj)
                                 └─ SET LOCAL app.workspace_id (atomic txn)
                                        │
    ViewSet ──has_permission(action→capability)──► WorkspacePermission
       │ read: Model.objects.all()  ──► ScopedManager filter (workspace_id)
       │ write: services.create/update/destroy(*, membership, …)
       │            └─ transaction.atomic + edit_content check + ws-consistency
       ▼
    Postgres ──► RLS ws_isolation (NULLIF backstop, per table)

Workspace is always taken from `request.membership.workspace` — never from client payload.
Cross-entity writes assert the parent's `workspace_id` matches the caller's before persisting.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/workspaces/rls.py` | Create | `enable_rls_sql`/`disable_rls_sql` (0004 NULLIF form) |
| `backend/schools/models.py` | Create | School, SchoolYear, Group (`ScopedModel`) |
| `backend/schools/migrations/0001_initial.py` | Create | Three tables, unique constraints |
| `backend/schools/migrations/0002_rls.py` | Create | RLS for school/schoolyear/group (dep schools/0001 + workspaces/0004) |
| `backend/students/models.py` | Create | Student (`ScopedModel`, group FK PROTECT) |
| `backend/students/migrations/0001_initial.py` | Create | Student table (dep schools/0001) |
| `backend/students/migrations/0002_rls.py` | Create | RLS for student |
| `backend/schools/services.py`, `backend/students/services.py` | Create | Keyword-only atomic writers |
| `backend/schools/serializers.py`, `views.py`, `urls.py` | Create | 3 serializers/viewsets + DefaultRouter |
| `backend/students/serializers.py`, `views.py`, `urls.py` | Create | 1 serializer/viewset + router |
| `backend/workspaces/middleware.py` | Modify | GAP1 — set `request.membership` |
| `backend/workspaces/permissions.py` | Modify | GAP2 — `has_permission` + action→capability map |
| `backend/config/settings.py` | Modify | `schools`, `students` in INSTALLED_APPS (schools before students) |
| `backend/config/urls.py` | Modify | `path("api/", include(...))` — first real routes |

## Interfaces / Contracts

**Models** (exact): `School(name CharField(200); cct CharField(10, blank); level CharField(choices
Level.PREESCOLAR/PRIMARIA/SECUNDARIA); db_table schools_school; no compound unique)`.
`SchoolYear(school FK CASCADE related_name=school_years; label CharField(9); UniqueConstraint(school,
label))`. `Group(school_year FK CASCADE related_name=groups; grado PositiveSmallInteger validators
MinValueValidator(1)/MaxValueValidator(3); grupo CharField(1); UniqueConstraint(school_year, grado,
grupo))`. `Student(group FK("schools.Group", PROTECT, related_name=students); first_name(100);
last_name_paternal(100); last_name_maternal(100, blank); curp CharField(18, blank, db_index))`.
Cross-app FK uses string ref; `students/0001` depends on `schools/0001`; INSTALLED_APPS orders
schools before students.

**DRF**: one `ModelSerializer` + `ModelViewSet` per entity; `workspace` read-only. `permission_classes =
[IsAuthenticated, WorkspacePermission]`; each viewset defines a `capability_map`
(`list/retrieve → view_workspace`, `create/update/partial_update/destroy → edit_content`).
`get_queryset` returns `Model.objects.all()`; `perform_create/update/destroy` delegate to services.

**Services**: `create_*(*, membership, …)` — keyword-only, `transaction.atomic()`, assert
`has_permission(membership, "edit_content")` → else `PermissionDenied`, assert parent
`workspace_id == membership.workspace_id` → else `ValueError`, set `workspace=membership.workspace`.

## WorkspaceResource Fate

Kept through M3 (RLS/pooling tests still target it). Optional **D7** retires it — touches
`test_rls.py` (retarget to a real entity) and `test_pooling_leak.py`; deferred so the M2 backstop
stays green until real scoped tables are proven.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Service unit | edit_content denial, ws-consistency `ValueError`, FK PROTECT | `django_db`, inline fixtures, assert `PermissionDenied`/`ValueError` |
| RLS backstop | foreign-workspace row invisible; no-context = deny (not error) | `django_db(transaction=True)` + `_portal_app_connection()` mirroring `test_rls.py` |
| HTTP | CRUD scoped, capability allow/deny per action | `APIClient` + `X-Workspace-Id` header |

## Threat Matrix

N/A — no shell, subprocess, VCS/PR automation, executable-file classification, or OS process
integration. HTTP URL routing is in-framework DRF, covered by the authorization + RLS test layers.

## Migration / Rollout

Chained PRs, one commit each, RED→GREEN, ≤~400 lines. D1 schools models+0001+0002_rls+rls.py helper
(~230). D2 students model+0001+0002_rls (~110). D3 services (~180). D4 wiring fixes GAP1+GAP2 (~90).
D5 schools DRF+urls+config wiring (~220). D6 students DRF (~120). D7 optional retire WorkspaceResource
(~80). Order D1 → D2 → D3/D4 → D5 → D6 → D7. All migrations reversible (`migrate <app> zero`);
`rls.py` is append-only; middleware/permission fixes are two-file reverts; apps are additive.

## Open Questions

- None — architecture is user-approved and locked.
