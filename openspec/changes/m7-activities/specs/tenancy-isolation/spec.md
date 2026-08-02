# Delta for tenancy-isolation

## ADDED Requirements

### Requirement: RLS Coverage Extends to Grades Tables

MUST enable Postgres RLS + `ws_isolation` (NULLIF form, mirror `0004`) on `grades_term`, `grades_activity`, `grades_activityscore`. Migrations MUST be reversible.

#### Scenario: RLS on all three

- GIVEN grades migrations applied
- WHEN RLS checked
- THEN each table MUST have RLS + NULLIF `ws_isolation`

#### Scenario: Foreign-workspace rows denied

- GIVEN `app.workspace_id`=A
- WHEN raw read of workspace-B `Activity` or `ActivityScore`
- THEN Postgres MUST exclude those rows

---

**Source**: M7 Actividades (`m7-activities`)
