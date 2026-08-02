# Attendance Specification

## Purpose

Daily and weekly attendance for a teacher group. Daily: one roster read and one atomic bulk save per group+date. Weekly: Mon–Fri matrix read and notes-preserving bulk status save. Grades, Term/Periodo, export, auto-save, and pagination are out of scope.

## Requirements

### Requirement: AttendanceRecord Invariants

`AttendanceRecord` MUST subclass `ScopedModel` with a denormalized `workspace` FK. It MUST reference `Student` with `on_delete=PROTECT`. It MUST store `date` as a date-only `DateField` (no datetime). `status` MUST be one of `present`, `absent`, `late`, or `excused`. `notes` MUST be optional, MUST NOT exceed 500 characters, and MUST default to empty. The table MUST enforce uniqueness on `(student, date)`. It MUST NOT carry a `group` FK — group membership is derived from `student.group`.

#### Scenario: Duplicate student+date rejected

- GIVEN an `AttendanceRecord` exists for student S on date D
- WHEN a second record for `(S, D)` is persisted
- THEN the system MUST reject it with a uniqueness violation

#### Scenario: Student with attendance history cannot be deleted

- GIVEN student S has one or more `AttendanceRecord` rows
- WHEN deletion of S is attempted
- THEN the `PROTECT` constraint MUST block deletion

### Requirement: Status Enum and UI Labels

The API MUST use `present`, `absent`, `late`, and `excused`. The `/asistencia` UI MUST label them Presente, Ausente, Retardo, and Justificado respectively.

#### Scenario: Invalid status rejected on bulk save

- GIVEN a bulk payload includes `status = "tardy"`
- WHEN the bulk upsert is processed
- THEN the request MUST be rejected with a validation error
- AND no rows MUST be persisted

### Requirement: Roster Read Endpoint

The system MUST expose `GET /api/attendance/roster/?group=<uuid>&date=<YYYY-MM-DD>`. The endpoint MUST require a valid `X-Workspace-Id` resolving to an active Membership. It MUST return every student in the requested group, merged with any existing `AttendanceRecord` for that date. Students without a saved record MUST appear with default status `present`. When the group has no students, the response MUST be an empty list. A group outside the active workspace MUST NOT be returned (404 or empty list per existing DRF isolation patterns). `date` MUST be interpreted as a calendar date in `YYYY-MM-DD` form, not a datetime.

#### Scenario: Mixed saved and unsaved students

- GIVEN group G has students A and B on date D
- AND only A has a saved record with status `absent`
- WHEN roster is fetched for `(G, D)`
- THEN A MUST appear with status `absent`
- AND B MUST appear with default status `present`

#### Scenario: Empty group roster

- GIVEN group G has zero students
- WHEN roster is fetched for `(G, D)`
- THEN the response MUST be an empty array

### Requirement: Bulk Upsert Endpoint

The system MUST expose `PUT /api/attendance/bulk/` accepting `{ group, date, entries: [{ student, status, notes? }] }`. The operation MUST run in a single database transaction and MUST be all-or-nothing — a validation failure MUST roll back every entry. The service MUST verify every `student` belongs to the supplied `group` and the caller's active workspace. Client-supplied `workspace_id` MUST be ignored; workspace MUST come from the active Membership.

#### Scenario: Whole roster saved atomically

- GIVEN a valid bulk payload for group G and date D with N entries
- WHEN bulk upsert succeeds
- THEN exactly N `AttendanceRecord` rows MUST exist for date D covering those students
- AND subsequent roster fetch MUST reflect the saved statuses and notes

#### Scenario: Student from wrong group rejected with no partial write

- GIVEN bulk payload references a student not in group G
- WHEN bulk upsert is processed
- THEN the request MUST be rejected
- AND no attendance rows for that request MUST persist

#### Scenario: Notes exceeding max length rejected

- GIVEN an entry includes notes longer than 500 characters
- WHEN bulk upsert is processed
- THEN the request MUST be rejected with a validation error

### Requirement: Week Roster Endpoint

The system MUST expose `GET /api/attendance/week/?group=<id>&week_start=<YYYY-MM-DD>`. `week_start` MUST be a Monday; a non-Monday MUST be rejected with 400. The response MUST include `week_start`, `dates` (exactly Mon–Fri), and `students` with `student`, `first_name`, `last_name_paternal`, and `days` (status per date). Students without a saved record for a date MUST default to `present`. The response MUST NOT include `curp` or `notes`. A group outside the active workspace MUST NOT be returned (404 or empty list per existing DRF isolation patterns).

#### Scenario: Non-Monday week_start rejected

- GIVEN a week roster request with `week_start` that is not a Monday
- WHEN the endpoint is called
- THEN the system MUST respond with 400

#### Scenario: Mixed saved and default week cells

- GIVEN group G has students A and B and week starting Monday M
- AND only A has a saved record on M with status `absent`
- WHEN week roster is fetched for `(G, M)`
- THEN A's `days[M]` MUST be `absent`
- AND B's `days[M]` MUST be `present`
- AND both students MUST have five weekday keys in `days`

### Requirement: Week Bulk Upsert Endpoint

The system MUST expose `PUT /api/attendance/week/bulk/` accepting `{ group, week_start, entries: [{ student, date, status }] }`. `week_start` MUST be a Monday. Every entry `date` MUST fall in the Mon–Fri window for that week; otherwise the request MUST be rejected with no partial write. The operation MUST run in a single database transaction. On create, `notes` MUST default to empty. On update, the service MUST update only `status` and `workspace` and MUST NOT overwrite existing `notes`. Workspace MUST come from the active Membership.

#### Scenario: Week bulk preserves existing notes

- GIVEN student S has a saved record on Monday M with notes `"Keep me"` and status `absent`
- WHEN week bulk sets status to `late` for `(S, M)`
- THEN the record status MUST be `late`
- AND notes MUST remain `"Keep me"`

#### Scenario: Date outside Mon–Fri window rejected

- GIVEN a week bulk payload with an entry date outside Mon–Fri of `week_start`
- WHEN the upsert is processed
- THEN the request MUST be rejected
- AND no attendance rows for that request MUST persist

### Requirement: No Persisted Row Until Explicit Save

The UI MUST treat status and notes changes as local draft state until the user activates **Guardar asistencia**. The system MUST NOT persist attendance rows on individual toggle or select change. Draft defaults for unsaved students MUST be `present`.

#### Scenario: Toggle without save leaves database unchanged

- GIVEN no saved records exist for group G on date D
- WHEN a teacher changes statuses in the grid but does not press Guardar
- THEN roster fetch MUST still show default `present` for every student
- AND no `AttendanceRecord` rows MUST exist for `(G, D)`

### Requirement: Daily Attendance Screen

The frontend MUST provide `/asistencia` reachable from app navigation. The page body MUST follow design frame **`LXprh`** (Asistencia — Teacher) for the daily view. It MUST offer a **Diaria** / **Semanal** view toggle. In **Diaria** mode it MUST offer Grupo and Fecha filters, live stat counts (Presentes, Ausentes, Retardos, Justificados), a roster grid with P/A/R/J controls and observación per row, **Marcar todos presentes** (client-side only), and an explicit **Guardar asistencia** action. Periodo MUST be omitted or disabled with no backend persistence. Exportar MUST NOT be offered. Auto-save MUST NOT occur. The full roster MUST render without server pagination (groups ≤ ~40 students).

#### Scenario: Save updates counts and persisted state

- GIVEN a teacher edits statuses and presses Guardar asistencia
- WHEN bulk save succeeds
- THEN stat cards MUST match saved statuses
- AND a subsequent roster load MUST show the persisted values

#### Scenario: Deferred features absent

- GIVEN the attendance screen renders
- WHEN the user inspects filters and header actions
- THEN Periodo MUST NOT perform a functional filter
- AND Exportar MUST NOT be available

### Requirement: Weekly Attendance Screen

In **Semanal** mode, `/asistencia` MUST show Grupo filter, Mon–Fri week navigation (prev/next), a matrix with alumnos as rows and weekday dates as columns, and a status combobox (Presente / Ausente / Retardo / Justificado) per cell. The weekly table MUST NOT show CURP or Observación. Stat cards MUST count all cells in the visible week. **Marcar todos presentes** MUST set every cell in the week draft to `present` client-side only. **Guardar asistencia** MUST save via the week bulk endpoint. Draft-until-save MUST apply.

#### Scenario: Weekly matrix omits CURP and Observación

- GIVEN the teacher switches to Semanal
- WHEN the matrix renders
- THEN CURP and Observación columns MUST NOT appear
- AND weekday column headers MUST be present

#### Scenario: Weekly cell change does not auto-save

- GIVEN Semanal mode with a loaded week
- WHEN the teacher changes a cell status via the combobox
- THEN no week bulk request MUST be sent until Guardar asistencia

---

**Source**: M7 — Daily Attendance (proposal: `m7-attendance`); weekly matrix extension
