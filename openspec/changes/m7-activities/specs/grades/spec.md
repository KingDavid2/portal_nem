# Grades Specification

## Purpose

Actividades: Term + Activity + ActivityScore. Calificaciones/PATCH/delete/auto-save/Exportar OUT.

## Requirements

### Requirement: Term Invariants and ensure_terms

`Term` MUST be `ScopedModel` (workspace FK), `PROTECT`→`SchoolYear`, `number`∈{1,2,3}, unique`(school_year,number)`. `ensure_terms(school_year)` MUST idempotently seed 1–3. Filters MUST require Periodo (`term`).

#### Scenario: Seeds three once

- GIVEN year Y has no Terms
- WHEN `ensure_terms(Y)` runs twice
- THEN exactly Terms 1–3 MUST exist for Y

#### Scenario: Duplicate rejected

- GIVEN `(Y,1)` exists
- WHEN second `(Y,1)` persists
- THEN uniqueness MUST reject

### Requirement: Activity Invariants and Tipo

`Activity` MUST be `ScopedModel`, `PROTECT`→`Group`+`Term`; required `title`; optional `description`; date-only `due_date`; `formative_field_id`; non-empty `subject_ids`. `activity_type` MUST be `task|activity|project|exam` (UI Tarea/Actividad/Proyecto/Examen). One row per activity; no Calificaciones rollup.

#### Scenario: Bad tipo / empty subjects

- GIVEN create with `activity_type="homework"` or `subject_ids=[]`
- WHEN create runs
- THEN validation MUST fail; no Activity MUST persist

### Requirement: ActivityScore Invariants

`ActivityScore` MUST be `ScopedModel`, `PROTECT`→`Activity`+`Student`, unique`(activity,student)`. `score` nullable `Decimal(3,1)`: `null`=unscored≠`0.0`; set values MUST be 0.0–10.0 (1dp).

#### Scenario: Null ≠ zero; range enforced

- GIVEN unscored `(A,S)` and a bulk entry `score=10.5`
- WHEN matrix fetched / bulk run
- THEN cell MUST be `null` (not 0.0); bulk MUST reject with no partial writes

### Requirement: Catalog Validation

Create MUST validate field/subjects via `lesson_plans.core.catalog` (Phase-6); subjects MUST belong to field. No catalog tables/SEP ingest.

#### Scenario: Subject outside field

- GIVEN subject of F2 under field F1
- WHEN create runs
- THEN validation MUST fail

### Requirement: Activities List and Create

MUST expose `GET/POST /api/grades/activities/`. GET: group+term required; optional campo/asignatura/tipo/search; full list (no server pagination). POST persists immediately. Require Membership via `X-Workspace-Id`; ignore client `workspace_id`.

#### Scenario: Create then list; foreign group denied

- GIVEN valid create `(G,T)` in workspace A
- WHEN create+list under A, then list with workspace-B group
- THEN Activity appears for A; foreign group denied

### Requirement: Scores Matrix Endpoint

MUST expose `GET /api/grades/scores/matrix/?group=&term=&…` → students×activities with scores (`null` unscored).

#### Scenario: Mixed cells

- GIVEN only `(A1,S1)=8.5`
- WHEN matrix for `(G,T)`
- THEN that cell `8.5`; others `null`

### Requirement: Bulk Score Upsert

MUST expose `PUT /api/grades/scores/bulk/` `{group, entries:[{student,activity,score}]}` (null|in-range). Single-txn all-or-nothing; students in group; activities in group+workspace; LWW `(activity,student)`.

#### Scenario: Atomic success / wrong student rollback

- GIVEN valid N entries vs one student not in G
- WHEN bulk runs
- THEN success MUST match matrix; bad student MUST reject with no partial writes

### Requirement: Draft Until Guardar + Screen

Por alumno drafts MUST NOT persist until **Guardar**; Por actividad has no score Guardar (modal create immediate). `/actividades` MUST match frames `qkWxk`/`CteCl`/`nd704`: toggle, required Periodo, filters, stats, matrix Guardar, local create dialog. Calificaciones banner MAY; write/Exportar/auto-save MUST NOT.

#### Scenario: Draft + Periodo

- GIVEN null cell edited without Guardar
- WHEN refetch; inspect `/actividades` filters
- THEN cell still `null`; Periodo required; Exportar absent

---

**Source**: M7 Actividades (`m7-activities`)
