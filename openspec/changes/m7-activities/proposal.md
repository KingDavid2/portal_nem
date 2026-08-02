# Proposal: M7 Actividades (grades)

## Intent

Ship teacher Actividades: create, list, score-by-student with one Guardar.
Calificaciones deferred.

## Scope

### In Scope
- Frames `qkWxk`/`CteCl`/`nd704`; `/actividades` toggle + modal + draft scores.
- App `grades`: Term + Activity + ActivityScore; Phase-6 catalog IDs.
- Authz read=`view_workspace`, write=`edit_content`; force-chained ≤400 TDD.

### Out of Scope
- Calificaciones, boleta, tutor, auto-save, Exportar, SEP ingestion,
  PATCH/delete, server pagination, Dialog DS, row→campo sync.

## Capabilities

### New Capabilities
- `grades`: models/invariants, list/create + matrix/bulk API, `/actividades` UX.

### Modified Capabilities
- `authorization`: grades read→`view_workspace`, write→`edit_content`.
- `tenancy-isolation`: RLS for Term, Activity, ActivityScore.

## Locked Decisions (auto — do not re-litigate)

1. Actividades-only (Calificaciones OUT; banner copy OK).
2. Screaming `grades` + Term + Activity + ActivityScore; frames authoritative.
3. **Term**: SchoolYear-scoped, 1–3, unique(year,number); `ensure_terms` seeds
   three on first use; Periodo filter required.
4. **Score**: Decimal 0.0–10.0 (1dp); null=unscored≠0; unique(activity,student).
5. **Subjects**: validated `subject_ids` for field; one Activity row; scores
   Activity×Student until Calificaciones.
6. **Catalog**: import `lesson_plans.core.catalog`; no tables; secundaria v1.
7. **Tipo**: `task|activity|project|exam` → Tarea/Actividad/Proyecto/Examen.
8. **Guardar**: none on Por actividad (modal create immediate); scores on Por alumno only.
9. **API**: `GET/POST …/activities/`; `GET …/scores/matrix/`; `PUT …/scores/bulk/`.
10. Full client list (≤~40); local contents-picker dialog; stacked-to-main Strict TDD.

## Approach — Delivery Outline (D1–D5)

| # | Deliverable |
|---|-------------|
| D1 | Models + RLS + services (`ensure_terms`, create/list, matrix/bulk) + tests |
| D2 | DRF APIs + tests + OpenAPI (schema regen may own slice) |
| D3 | Catalog hooks + Por actividad list/create modal + nav |
| D4 | Por alumno matrix + draft Map + Guardar + vitest |
| D5 | Stats/filters/banner/Periodo polish; split if >400 |

Mirror attendance `APIView`s + services; LWW; schema.d.ts not in authored count.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/grades/` | New | Models, RLS, services, DRF, tests |
| `backend/config/{settings,urls}.py` | Modified | App + `/api/grades/` |
| `lesson_plans/core/catalog.py` | Reuse | Field/Subject IDs |
| `frontend/.../actividades/` + layout + `lib/api` | New/Mod | Page, hooks, OpenAPI |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Calificaciones creep | Med | subject_ids only; no rollup |
| Matrix width / >400 FE | High | Required filters; split modal/matrix |

## Rollback Plan

Reversible migrations/RLS; additive routes/page/nav — revert per slice.

## Dependencies

M3 spine + SchoolTeachingContext; M2 ScopedModel/RLS; attendance; catalog.

## Success Criteria

- [ ] Modal create + Por actividad list with Periodo/filters/stats.
- [ ] Por alumno draft → Guardar bulk-upsert; null≠0; 0.0–10.0.
- [ ] `ensure_terms` → 3 terms; RLS blocks cross-workspace; frames matched.
