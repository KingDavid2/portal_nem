# Exploration: m3-school-structure

## Milestone (docs/roadmap.md M3)

School structure CRUD establishing the hierarchy `school → school_year → group → student`.
This is the data spine that lesson plans (M4), grades, and attendance (M5) attach to, and the
first real HTTP surface exposed by the backend.

## Inherited foundation (M2, archived on `main`)

M2 shipped tenancy at the **service layer only** (no HTTP):
- `ScopedModel` — each tenant table carries its OWN denormalized `workspace` FK plus a
  `ScopedManager`. RLS never joins through a parent; every scoped row is filtered directly.
- Postgres RLS backstop via `SET LOCAL app.workspace_id` inside the per-request transaction.
- Service-layer conventions and a capability matrix for authorization.

## Verified M2 gaps (must close in M3 — first HTTP consumer exposes them)

- **GAP 1 — membership never wired**: `TenancyMiddleware`
  (`backend/workspaces/middleware.py:50`) resolves the active workspace but never sets
  `request.membership`. `WorkspacePermission` (`backend/workspaces/permissions.py:54`) reads
  `request.membership`, so it is always absent.
- **GAP 2 — permission always denies at the collection level**: `WorkspacePermission` only
  implements `has_object_permission`, and its `has_permission` path feeds `view.action` (a DRF
  verb like `list`/`create`) into a keyspace of capabilities. Verb never matches capability →
  every request denied. Needs a DRF-action→capability map and a real
  `has_permission(self, request, view)`.
- **RLS form**: new policies MUST mirror migration `0004`'s NULLIF form —
  `NULLIF(current_setting('app.workspace_id', true), '')::uuid`.

## Model shape (locked, design-brief §2)

- `schools.School(ScopedModel)`: name; cct (max 10, blank, NO unique); level TextChoices
  (PREESCOLAR/PRIMARIA/SECUNDARIA). workspace CASCADE. No compound unique.
- `schools.SchoolYear(ScopedModel)`: school FK CASCADE; label ("2024-2025").
  unique(school, label).
- `schools.Group(ScopedModel)`: school_year FK CASCADE; grado (PositiveSmallInt 1-3);
  grupo (1 char). unique(school_year, grado, grupo).
- `students.Student(ScopedModel)`: group FK PROTECT; first_name; last_name_paternal;
  last_name_maternal (blank); curp (max 18, blank, NO unique, indexed). workspace CASCADE.

## Key decisions carried in

- Two new screaming apps: `schools` (School, SchoolYear, Group) + `students` (Student).
- CURP is a plain indexed field with NO uniqueness constraint (honors design-brief §2 locked
  decision — CURP collisions occur in real data; dedup is a later product concern).
- Scope includes DRF HTTP surface (viewsets/serializers/urls), not just services.

## Delivery shape

Seven deliveries D1–D7, one commit each, strict TDD, 400-line review budget, chained PRs.
Order: D1 (schools models + migrations + RLS helper) → D2 (students) → D3 (services) /
D4 (wiring fixes) → D5 (schools DRF) → D6 (students DRF) → D7 (optional cleanup).
