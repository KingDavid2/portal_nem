# Delta for tenancy-isolation

## ADDED Requirements

### Requirement: RLS Coverage Extends to Attendance Records

The system MUST enable Postgres row-level security with the `ws_isolation` policy in the NULLIF form (mirroring the existing `0004` migration pattern) on `attendance_attendancerecord`. The RLS migration MUST be reversible.

#### Scenario: RLS enabled on attendance table

- GIVEN the attendance migrations have been applied
- WHEN RLS status is checked for `attendance_attendancerecord`
- THEN row-level security MUST be enabled
- AND the table MUST carry a `ws_isolation` policy using the NULLIF form

#### Scenario: Foreign-workspace attendance row denied at database layer

- GIVEN `app.workspace_id` is set to workspace A for the current transaction
- WHEN a raw query attempts to read an `AttendanceRecord` belonging to workspace B
- THEN Postgres MUST exclude that row from the result, independent of ORM filtering

---

**Source**: M7 — Daily Attendance (proposal: `m7-attendance`)
