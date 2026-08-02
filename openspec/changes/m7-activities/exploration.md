# Exploration: m7-activities (Actividades — full section)

Change: `m7-activities` · Project: `portal_nem` · Phase: explore  
Scope: **Actividades only** (Calificaciones OUT) — frames `qkWxk`, `CteCl`, `nd704`

## Current State

**No grades/activities domain exists.** `INSTALLED_APPS` has `attendance` but no `grades`. No Activity/Score/Term models, no `/actividades` route, no OpenAPI grades types. Roadmap M7 marks grades open; attendance half archived.

**School spine ready (M3).** `School → SchoolYear → Group → Student` are workspace-scoped `ScopedModel`s with RLS. `Group` is grado 1–3 + grupo letter under a `SchoolYear` (secundaria-shaped). `Student.group` is PROTECT.

**Attendance analogue shipped (pattern to mirror).**

| Layer | Pattern |
|-------|---------|
| App | Screaming `attendance` app |
| Model | `AttendanceRecord(ScopedModel)` — no group FK; validate in services |
| API | Custom `APIView`s: `GET …/roster/` + `PUT …/bulk/` (+ week follow-up) |
| Caps | read → `view_workspace`, write → `edit_content` |
| UX | Local draft Map; explicit **Guardar**; defaults until save; `SchoolTeachingContext` for grupo |
| Delivery | D1 model/RLS/services → D2 API/OpenAPI → D3 frontend (force-chained, ≤400 authored lines) |

**Frontend plumbing ready.** `SchoolTeachingProvider` (Escuela/Ciclo/Grupo), TanStack Query/Table, `DataTable`, `Select`, `FormField`, `StatCard`, `Input`, `ChoiceChip`. **No shared Dialog primitive** — closest pattern is `planeaciones/nueva/contents-picker.tsx` (`role="dialog"` + scrim). Nav has Asistencia; no Actividades entry.

**Static NEM catalog already exists (reuse, not invent).** `backend/lesson_plans/core/catalog.py` exposes immutable Phase 6:

- 4 `Field`s (Lenguajes; Saberes y Pensamiento Científico; Ética, Naturaleza y Sociedades; De lo Humano y lo Comunitario)
- 13 `Subject`s keyed by `field_id`
- API today: `GET /api/lesson-plans/fields/` (+ field-scoped `catalog` for PDAs)

Locked product rule: **static catalog for v1, no SEP corpus ingestion.**

**No `Term` model anywhere.** Attendance deliberately deferred Periodo. Actividades design shows **Periodo 1 de 3** in subtitles and a Periodo filter on both views — propose must lock minimal Term (or equivalent).

### Design frames (`designs/teachers.pen`)

#### `qkWxk` — Actividades — Teacher (Por actividad)

| Region | Elements |
|--------|----------|
| Header | Title "Actividades"; subtitle `grupo · nivel · Periodo N de 3 · …`; toggle **Por actividad / Por alumno**; **Nueva actividad** |
| Banner | Informational: grades feed Calificaciones via simple average per asignatura/periodo (Calificaciones OUT — copy-only) |
| Filters | Grupo, Campo formativo, Asignatura, Tipo, Periodo, Buscar |
| Stats | Actividades del periodo · Calificadas · Pendientes por calificar · Promedio de actividades |
| Table | ACTIVIDAD, CAMPO FORMATIVO, ASIGNATURAS, TIPO, ENTREGA, CALIFICADAS (n/total + bar), PROM. |
| Types in mock | Tarea, Actividad, Proyecto, Examen |
| Footer | Range + page chips (pagination) |
| Guardar | **Absent** on this view (list/browse + create entry point) |

#### `CteCl` — Actividades — Por alumno

| Region | Elements |
|--------|----------|
| Header | Same toggle + Nueva actividad + **Guardar** |
| Filters | Grupo, Campo formativo, Asignatura, Tipo, Periodo (no Buscar) |
| Matrix | Rows = alumnos; columns = activities (date, short title, asignatura abbrev, type color bar) + PROM. |
| Cells | Numeric score inputs (mock values ~5.0–9.5) |
| Footer | Range + page chips |

#### `nd704` — Nueva actividad — Modal

| Field | Notes |
|-------|-------|
| Título de la actividad | Required text |
| Tipo | Select (Tarea / Actividad / Proyecto / Examen) |
| Fecha de entrega | Date |
| Campo formativo | Select → drives asignatura list |
| Asignaturas | Multi-checkbox + "Seleccionar todas las asignaturas del campo"; helper: score applies to each selected subject (Calificaciones rollup later) |
| Descripción / instrucciones | Optional textarea |
| Footer | Cancelar · **Crear actividad** |

## Affected Areas

| Path | Why |
|------|-----|
| `backend/grades/` (new) | Screaming app per design-brief: Activity, ActivityScore, minimal Term; services; RLS; tests |
| `backend/config/{settings,urls}.py` | Register app + `/api/grades/` routes |
| `backend/lesson_plans/core/catalog.py` | Reuse FIELDS/SUBJECTS IDs (or extract shared module later) |
| `openspec/specs/` (via sdd-spec) | New `grades` capability; likely authz/tenancy deltas |
| `frontend/src/lib/api/schema.d.ts` | Regenerated after OpenAPI |
| `frontend/src/lib/api/grades.ts` (new) | TanStack hooks: list/create activity, matrix, bulk scores |
| `frontend/src/app/(app)/actividades/` (new) | Page: toggle + list + matrix + modal |
| `frontend/src/app/(app)/layout.tsx` | Nav item Actividades |
| `designs/teachers.pen` (`qkWxk`, `CteCl`, `nd704`) | Visual contract — no edits in explore |

**Reuse without forking:** `SchoolTeachingContext`, student roster-by-group patterns from attendance services, `StatCard`/`Select`/`Input`/`DataTable`, contents-picker dialog pattern.

## Approaches

### 1. New `grades` app — Activity + Score + minimal Term + bulk matrix (recommended)

Mirror attendance: keyword services + `APIView`s; draft-until-Guardar on Por alumno; static catalog IDs as CharFields / JSON subject list (no catalog tables).

- **Pros:** Matches design-brief screaming name; Periodo filter has a real entity for stats "del periodo"; clear attendance isomorphism; Calificaciones can later roll up Activities without renaming apps.
- **Cons:** Larger than attendance (~1.5–2× UI surface: list + modal + matrix); Term seeding policy needed; multi-subject storage + future Calificaciones semantics need careful v1 boundaries.
- **Effort:** High (but chainable)

### 2. Nested under `students` / thin activity-only app without Term

Store `term_number` 1–3 on Activity; skip Term model; put code in `students` or `activities` app.

- **Pros:** Fewer tables; faster first PR.
- **Cons:** Violates locked "screaming `grades` + minimal Term"; Periodo filter becomes a magic int with no school_year binding; harder Calificaciones later.
- **Effort:** Medium

### 3. Full REST ViewSet CRUD per score cell

Standard ModelViewSet for Activity + ActivityScore without bulk matrix endpoint.

- **Pros:** Familiar DRF pattern.
- **Cons:** Por alumno Guardar becomes N requests; poor fit for spreadsheet UX (same rejection as attendance approach 1).
- **Effort:** Medium–High frontend pain

## Recommendation

**Approach 1.** New `grades` Django app with:

```text
Term(ScopedModel): school_year FK, number ∈ {1,2,3}, unique(school_year, number)
Activity(ScopedModel): group FK, term FK, title, activity_type, due_date,
                       formative_field_id, subject_ids (JSON list of catalog ids),
                       description blank; ordered by due_date
ActivityScore(ScopedModel): activity FK PROTECT, student FK PROTECT,
                            score DecimalField null=True (blank cell),
                            unique(activity, student)
```

**Catalog:** Validate `formative_field_id` / `subject_ids` against `lesson_plans.core.catalog` (FIELDS/SUBJECTS). Do not ingest SEP corpus. Do not duplicate catalog tables in v1. Propose should decide whether to keep the import from `lesson_plans` or extract a tiny shared `curriculum` module (prefer import-for-now to stay under budget).

**API surface (attendance-shaped):**

| Endpoint | Cap | Role |
|----------|-----|------|
| `GET /api/grades/activities/?group=&term=&…` | `view_workspace` | Por actividad list + filterable stats inputs |
| `POST /api/grades/activities/` | `edit_content` | Create from modal (Crear actividad) |
| `GET /api/grades/scores/matrix/?group=&term=&…` | `view_workspace` | Students × filtered activities + scores (null = unset) |
| `PUT /api/grades/scores/bulk/` | `edit_content` | Atomic upsert `{ group, entries:[{student, activity, score}] }` |

Optional later (OUT unless budget allows): `PATCH` activity, delete, pagination. v1 can return full group lists (≤~40 students; activity count filtered by term/campo).

**UX locks for propose:**

- Route `/actividades` with Por actividad / Por alumno toggle
- Score capture: **local draft until Guardar** (Por alumno only — matches `CteCl`; `qkWxk` has no Guardar)
- Modal fields design-faithful; Crear actividad persists Activity immediately (not draft)
- Periodo: real Term (seed 1–3 per school year on first use or explicit service) — do **not** repeat attendance's "omit Periodo"
- Banner about Calificaciones: static copy OK; no write path into Calificaciones
- Pagination page chips: defer (same as attendance) unless cheap client-side slice
- Score range: propose must lock (design implies numeric ~5–10 with one decimal; blank allowed)

**Delivery forecast (force-chained, stacked-to-main, 400-line budget, Strict TDD):**

| Slice | Scope | Budget risk |
|-------|-------|-------------|
| D1 | `grades` models (Term, Activity, ActivityScore) + RLS + domain services + unit/RLS tests | Medium |
| D2 | Activity list/create API + filters/stats serialization + API tests + OpenAPI | Medium–High |
| D3 | Score matrix GET + bulk PUT + API tests + schema regen | Medium |
| D4 | Frontend: hooks + `/actividades` Por actividad list + filters/stats + nav | High |
| D5 | Frontend: Nueva actividad modal + Por alumno matrix + draft Guardar + vitest | High |

Attendance D1–D3 already blew past 400 *total* lines when counting generated schema/docs; authored risk was managed by splitting. Actividades needs **≥5 chained PRs**; if D4/D5 exceed 400, split modal vs matrix or tones/helpers.

`Decision needed before apply: Yes` (Term seeding + score bounds + catalog ownership)  
`Chained PRs recommended: Yes`  
`400-line budget risk: High`

## Risks

- **Scope creep into Calificaciones** — banner + multi-asignatura helper imply rollup; keep OUT; store subject_ids only.
- **Term seeding** — first Actividades use needs 3 periodos per school year; unclear if auto-create vs admin/setup.
- **Catalog coupling** — importing from `lesson_plans` couples grades to planeaciones app; extract may be cleaner but adds a delivery.
- **Primaria vs secundaria subjects** — catalog is Phase 6 secundaria; design mock is Secundaria; primaria groups exist via School.level but subject list may be wrong — lock "secundaria catalog for v1".
- **No Dialog primitive** — modal must copy contents-picker pattern or add a thin Dialog; easy to over-build in D5.
- **Por actividad without Guardar** — product locked "draft-until-Guardar"; clarify only score matrix drafts (create is immediate).
- **Matrix width** — many activities × 32 students is heavy; filters (campo/tipo/periodo) are load-bearing, not cosmetic.
- **Concurrent LWW** — same as attendance; no versioning in v1.
- **Score semantics** — blank vs 0 vs null; one-decimal Decimal; min/max — must be spec-locked before TDD.
- **Generated OpenAPI noise** — schema.d.ts diffs inflate PR size; exclude from 400 authored budget counting (same lesson as attendance D2).

## Open Questions (propose must lock)

1. Term: auto-seed `{1,2,3}` per `SchoolYear` on first activities API call, or require explicit create?
2. Score bounds/precision: `Decimal(3,1)` in `[5.0, 10.0]` with null blank, or allow full 0–10?
3. Catalog source of truth: import `lesson_plans.core.catalog` vs new shared module?
4. Activity update/delete in v1, or create+list+score only?
5. Client-side pagination vs full render for activity list and student matrix?
6. Selecting a row on Por actividad "filters its campo formativo" — client-only filter sync?

## Ready for Proposal

**Yes.** sdd-propose should lock: Actividades-only scope (Calificaciones OUT), `grades` app with Activity + ActivityScore + minimal Term, static catalog IDs, list/create + matrix/bulk API, draft-until-Guardar on Por alumno, design frames `qkWxk`/`CteCl`/`nd704`, and D1–D5 force-chained stacked-to-main under the 400-line budget.
