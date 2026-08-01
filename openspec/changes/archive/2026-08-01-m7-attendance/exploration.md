# Exploration: m7-attendance (daily attendance — backend + UI)

Change: `m7-attendance` · Project: portal_nem · Phase: explore · Scope: **attendance only** (grades/Calificaciones/Actividades OUT)

## Current State

**No attendance domain exists yet.** `INSTALLED_APPS` has `schools`, `students`, `lesson_plans`, `quizzy` — no `attendance` app, no attendance routes, no OpenAPI types, no frontend screen.

**Data spine is ready (M3).** `School → SchoolYear → Group → Student` are workspace-scoped `ScopedModel`s with RLS, services gated by `edit_content`, and DRF viewsets (`backend/schools/`, `backend/students/`). The school-structure spec explicitly positions this spine as the foundation for M7 attendance.

**Frontend plumbing is ready (M3/M6).** TanStack Query + Table are installed; `DataTable` wraps TanStack Table for list screens. `SchoolTeachingProvider` persists Escuela → Ciclo → Grupo selection across screens. Design-system primitives needed by the attendance screen already exist: `EstadoButton`, `StatusChip`, `StatCard`, `Select`, `FormField`, `Avatar`.

**Nav gap.** `frontend/src/app/(app)/layout.tsx` lists Escuelas, Ciclos, Grupos, Alumnos, Planeaciones, Quizzy — no Asistencia entry yet.

**Design source.** Frame **`Asistencia — Teacher`** (`designs/teachers.pen`, node id **`LXprh`** — the prompt's `y4w3Hb` id is not present in the current file; treat `LXprh` as authoritative). Screen structure:

| Region | Elements |
|--------|----------|
| Header | Title "Asistencia diaria", context subtitle (grupo · nivel · ciclo · periodo), **Exportar** + **Guardar asistencia** |
| Filters card | **Grupo**, **Fecha**, **Periodo** selects + **Marcar todos presentes** action |
| Stat row | Four `StatCard`s: Presentes, Ausentes, Retardos, Justificados (counts + captions) |
| Roster table | Columns: #, ALUMNO (+ avatar), CURP, ESTADO (P/A/R/J `EstadoButton` group), OBSERVACIÓN; legend chips (Presente/Ausente/Retardo/Justificado) in card header |
| Table footer | Range text + page chips (pagination) |

Status codes in design map to English enums: **P** → `present`, **A** → `absent`, **R** → `late`, **J** → `excused` (UI labels stay Spanish).

**Design tensions to resolve in proposal (not blockers):**
- Caption says "guardado automático cada cambio" but scope locks an explicit **Guardar** — pick one save UX.
- **Periodo** filter appears in design but no `Term` model exists anywhere in the codebase; grades (OUT of this change) normally own periodos.
- **Exportar** is in design but not in locked IN scope — defer unless trivial CSV.

## Affected Areas

| Path | Why |
|------|-----|
| `backend/attendance/` (new) | Domain app: model, services, serializers, viewsets, urls, migrations, RLS, tests |
| `backend/config/settings.py` | Register `attendance` in `INSTALLED_APPS` |
| `backend/config/urls.py` | Include `attendance.urls` under `/api/` |
| `openspec/specs/` (later via sdd-spec) | New `attendance/spec.md` delta |
| `frontend/src/lib/api/schema.d.ts` | Regenerate from OpenAPI after backend ships |
| `frontend/src/lib/api/attendance.ts` (new) | TanStack Query hooks for roster + bulk save |
| `frontend/src/app/(app)/asistencia/` (new) | Attendance grid page |
| `frontend/src/app/(app)/layout.tsx` | Add Asistencia nav item (clipboard-check icon per design) |
| `frontend/src/components/ui/estado-button.tsx` | May need tone variants (success/danger/warning/info) for P/A/R/J selected states |
| `frontend/src/components/ui/stat-card.tsx` | May need warning/info tones for Retardos/Justificados stat cards |
| `designs/teachers.pen` (`LXprh`) | Visual contract — no file changes in explore |

**Reuse without modification (expected):** `SchoolTeachingContext`, `studentsForGroup` / `useStudentsQuery`, `Select`, `FormField`, `DataTable` or a thin attendance-specific table wrapper.

## Approaches

### 1. Per-record REST CRUD (mirror students)

One `AttendanceRecord` row per student per date; standard `ModelViewSet` list/create/update/destroy filtered by `group` + `date`.

- **Pros:** Matches existing M3 DRF patterns exactly; simplest mental model; no custom actions.
- **Cons:** Saving a 32-student roster = 32 PATCH/POST round trips (or N+1 on "Guardar"); poor fit for bulk-mark UX; heavy CSRF/session overhead.
- **Effort:** Medium backend, Medium frontend

### 2. Roster read + bulk upsert (recommended)

Custom endpoints:
- `GET /api/attendance/roster/?group=<id>&date=<YYYY-MM-DD>` → students in group merged with existing records (default status `present` or `null` for unset).
- `PUT /api/attendance/bulk/` → atomic upsert of `{ group, date, entries: [{ student, status, notes }] }` in one transaction; service validates every student belongs to group + workspace.

Optional thin `AttendanceRecordViewSet` for retrieve/list-by-date if tutor portal (M10) needs it later — not required for v1 grid.

- **Pros:** One save for whole class; matches "Marcar todos" + "Guardar asistencia"; fewer race conditions; aligns with spreadsheet-style grids in design-brief §3.
- **Cons:** First bulk endpoint in the codebase (no existing precedent); must document idempotency and partial-failure behavior in spec.
- **Effort:** Medium backend, Medium frontend

### 3. Client-only draft + single bulk POST

Frontend holds dirty state locally; only bulk POST on Guardar; no per-change API calls (despite design caption mentioning auto-save).

- **Pros:** Minimal API surface; clear dirty/saved UX; works offline-tolerant until save.
- **Cons:** Same backend as (2) for save; loses multi-teacher concurrent edit detection until refresh.
- **Effort:** Low–Medium (backend same as 2; simpler frontend mutation logic)

## Recommendation

**Approach 2 + 3 combined:** roster GET + bulk PUT upsert on explicit **Guardar asistencia**; local draft state for P/A/R/J toggles and observaciones; **Marcar todos presentes** is a client-side bulk set before save. Defer auto-save and Exportar to a follow-up unless product insists.

**Model sketch (proposal to lock):**

```python
class AttendanceRecord(ScopedModel):
    student = models.ForeignKey("students.Student", on_delete=PROTECT, related_name="attendance_records")
    date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices)  # present|absent|late|excused
    notes = models.CharField(max_length=500, blank=True)
    class Meta:
        constraints = [UniqueConstraint(fields=["student", "date"], name="unique_student_date")]
```

- `workspace` denormalized on record (ScopedModel) — honors design-brief §2 move semantics for future grade/attendance cascade.
- `student` PROTECT — deleting a student with history blocked cleanly (same as group PROTECT pattern).
- No `group` FK on record — group is derived from `student.group`; bulk save validates homogeneity.

**Periodo filter:** Omit from functional v1 (display-only in subtitle from school context) OR static select (1–3) with no persistence until grades introduce `Term`. Do **not** block attendance on a Term model.

**Pagination:** Groups are ≤~40 students in NEM primaria — render full roster without server pagination; footer range text can reflect total count (skip page chips for v1).

**Delivery forecast (force-chained, 400-line budget):**

| Slice | Scope | Budget risk |
|-------|-------|-------------|
| PR-1 | `attendance` app: model, migration, RLS, services, unit tests | Low |
| PR-2 | Roster + bulk DRF, API/RLS tests, OpenAPI | Medium |
| PR-3 | Frontend hooks + `/asistencia` page (filters, grid, stats, save) + nav + vitest | High |

`Decision needed before apply: Yes` · `Chained PRs recommended: Yes` · `400-line budget risk: Medium`

## Risks

- **Design id mismatch:** Prompt references `y4w3Hb`; file uses `LXprh` — confirm with design owner before implementers chase wrong frame.
- **Periodo without Term entity:** Filter in design has no backend counterpart; scope must explicitly defer or stub.
- **Auto-save vs Guardar:** Design caption contradicts locked scope; unresolved UX may cause rework.
- **EstadoButton variants:** Current component is generic (primary tint only); P/A/R/J need distinct selected colors per design (#72E128, #FF4D49, #FDB528, #26C6F9) — small UI extension, easy to miss.
- **StatCard tones:** Only `brand|success|neutral` today; Retardos/Justificados need warning/info colors.
- **Concurrent edits:** Two teachers saving same group+date last-write-wins unless spec adds versioning or conflict response.
- **Date timezone:** `date` field must be interpreted in school-local calendar day (Mexico) — document in spec to avoid UTC off-by-one.
- **No server-side group filter on students API:** Roster endpoint should join server-side, not re-fetch all workspace students client-side (performance + correctness).
- **M6 design alignment incomplete:** Attendance nav/layout in `teachers.pen` uses product sidebar (Inicio, Asistencia active) vs current dev sidebar (Escuelas…Quizzy) — page body should match `LXprh`; shell may differ until broader M6 nav realignment.

## Ready for Proposal

**Yes.** sdd-propose should lock: attendance-only scope, bulk upsert API shape, status enum mapping, Periodo/Exportar/auto-save deferrals, chained PR slices, and design frame `LXprh` as visual source.
