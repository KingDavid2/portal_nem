# Delta for tenancy-isolation

## ADDED Requirements

### Requirement: RLS Coverage Extends to School Structure Tables

The system MUST enable Postgres row-level security, with the `ws_isolation` policy in the NULLIF form (mirroring the existing `0004` migration's pattern), on all four new workspace-scoped tables: `schools_school`, `schools_schoolyear`, `schools_group`, and `students_student`. Each table's RLS migration MUST be reversible.

#### Scenario: RLS enabled on all four new tables

- GIVEN the school-structure migrations have been applied
- WHEN RLS status is checked for `schools_school`, `schools_schoolyear`, `schools_group`, and `students_student`
- THEN each table MUST have row-level security enabled
- AND each MUST carry a `ws_isolation` policy using the NULLIF form

#### Scenario: Foreign-workspace row denied at the database layer for a new table

- GIVEN `app.workspace_id` is set to workspace A for the current transaction
- WHEN a raw query attempts to read a `Student` row belonging to workspace B
- THEN Postgres MUST exclude that row from the result, independent of any ORM-level filtering

### Requirement: TenancyMiddleware Attaches Resolved Membership to the Request

`TenancyMiddleware` MUST attach the resolved `Membership` object to `request.membership` for every request that resolves an active workspace. Downstream permission classes and views MUST be able to read `request.membership` without re-resolving it.

#### Scenario: Membership is available on the request after middleware runs

- GIVEN a request carries a valid `X-Workspace-Id` header resolving to an existing Membership
- WHEN `TenancyMiddleware` processes the request
- THEN `request.membership` MUST be set to that resolved `Membership` instance

#### Scenario: No membership resolved leaves request.membership unset or None

- GIVEN a request's `X-Workspace-Id` does not resolve to any Membership for the caller
- WHEN `TenancyMiddleware` processes the request
- THEN `request.membership` MUST NOT be set to a Membership belonging to a different caller or workspace
- AND downstream permission checks relying on `request.membership` MUST deny the request

---

**Source**: M3 — School Structure (proposal: `m3-school-structure`)
