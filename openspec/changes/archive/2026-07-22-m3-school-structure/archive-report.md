# Archive Report: M3 School Structure

**Change**: `m3-school-structure`  
**Archived**: 2026-07-22  
**Status**: Complete

## Executive Summary

M3 School Structure is fully implemented, verified (131/131 tests green), and archived. Delivered schools + students apps with School/SchoolYear/Group/Student models, RLS coverage, services layer, and DRF CRUD endpoints. Closed two M2 authorization gaps (TenancyMiddleware.request.membership, WorkspacePermission.has_permission capability map). D7 (retire WorkspaceResource) deferred as an accepted follow-up.

## What M3 Delivered

### New Capabilities

**school-structure**: Complete CRUD data spine for the school hierarchy (School → SchoolYear → Group → Student). All four entities as workspace-scoped `ScopedModel` subclasses with denormalized `workspace_id` FK. Field constraints and validation rules enforced:
- `School`: name required, cct optional, level enum
- `SchoolYear`: uniqueness on (school, label)
- `Group`: grado 1–3 validated, grupo single letter, uniqueness on (school_year, grado, grupo)
- `Student`: curp indexed (no uniqueness), group FK with PROTECT delete semantics

Service layer (`schools/services.py`, `students/services.py`): keyword-only functions, `transaction.atomic`, `edit_content` capability gating, cross-entity workspace consistency validation.

DRF HTTP surface: ModelSerializer + ModelViewSet per entity, RESTful list/retrieve/create/update/destroy endpoints, workspace-scoped via `ScopedManager` + `X-Workspace-Id` header, clean 4xx on Group delete with Student rows.

### Modified Capabilities

**authorization**: 
- `WorkspacePermission` now implements `has_permission(request, view)` with an explicit `capability_map` mapping DRF view actions (list/retrieve/create/update/partial_update/destroy) to capabilities (view_workspace/edit_content).
- Raw DRF action verbs never reach `has_permission(membership, action)` — translation through capability_map is mandatory.

**tenancy-isolation**:
- RLS policies extended to four new tables (`schools_school`, `schools_schoolyear`, `schools_group`, `students_student`) using the NULLIF form via the new `workspaces/rls.py` helper.
- `TenancyMiddleware` now resolves and attaches the real `Membership` object to `request.membership` on both header-based and personal-workspace resolution paths.

## Implementation Summary

### Six Chained Commits

Strict TDD (RED→GREEN), one commit per delivery, ≤~400 changed lines each:

1. **c71e9a7**: D1 — `schools` app: School/SchoolYear/Group models, workspaces/rls.py extraction, 0001/0002_rls migrations, INSTALLED_APPS
2. **00a1d1c**: D2 — `students` app: Student model, 0001/0002_rls migrations
3. **92f8fd5**: D3 — Services layer: schools/services.py, students/services.py (atomic, capability gating, workspace validation)
4. **84c6af2**: D4 — Wiring fixes: TenancyMiddleware.request.membership, WorkspacePermission.has_permission + capability_map
5. **be268bc**: D5 — Schools DRF: serializers, viewsets, urls, config wiring (first real HTTP surface)
6. **e037d7f**: D6 — Students DRF: serializer, viewset, urls

### Test Results

- **Full pytest suite**: 131 passed, 0 failed
- **Migration checks**: `migrate --check` and `makemigrations --check --dry-run` both clean
- **Compliance**: All spec requirements verified against code (see verify-report.md for full matrix)

### Artifacts Archived

| Artifact | Status | Location |
|----------|--------|----------|
| proposal.md | Included | openspec/changes/archive/2026-07-22-m3-school-structure/proposal.md |
| specs/school-structure/spec.md | Included | openspec/changes/archive/2026-07-22-m3-school-structure/specs/school-structure/spec.md |
| specs/authorization/spec.md | Included (delta) | openspec/changes/archive/2026-07-22-m3-school-structure/specs/authorization/spec.md |
| specs/tenancy-isolation/spec.md | Included (delta) | openspec/changes/archive/2026-07-22-m3-school-structure/specs/tenancy-isolation/spec.md |
| design.md | Included | openspec/changes/archive/2026-07-22-m3-school-structure/design.md |
| tasks.md | Included | openspec/changes/archive/2026-07-22-m3-school-structure/tasks.md |
| verify-report.md | Included | openspec/changes/archive/2026-07-22-m3-school-structure/verify-report.md |

## Spec Merges to Main

All delta specs have been merged additively into the main specs (source of truth):

1. **school-structure** (NEW): Created `openspec/specs/school-structure/spec.md` — full new specification
2. **authorization** (ADDED): Merged new requirement "WorkspacePermission Implements has_permission via a Capability Map" into `openspec/specs/authorization/spec.md`
3. **tenancy-isolation** (ADDED): Merged two new requirements into `openspec/specs/tenancy-isolation/spec.md`:
   - "RLS Coverage Extends to School Structure Tables"
   - "TenancyMiddleware Attaches Resolved Membership to the Request"

## Task Completion Gate

All implementation tasks marked complete:
- D1–D6: [x] (implemented and verified)
- D7 (optional): [ ] (intentionally deferred; no stale checkboxes)

No unchecked implementation tasks remain.

## Deferred Work

**D7 — Retire WorkspaceResource** (~80 lines): Update `test_rls.py` and `test_pooling_leak.py` to target a real scoped model (e.g., `schools.School`) instead of the `WorkspaceResource` placeholder, then drop the table. **Status**: Deferred as an accepted follow-up per design decision § WorkspaceResource Fate. **Recommended**: Create a separate `/sdd-new` change (`m3-d7-retire-workspace-resource` or similar) to track this cleanup.

## Engram Artifact Traceability

Archive report persists with these linked observation IDs for full traceability:
- Proposal: #59 (sdd/m3-school-structure/proposal)
- Spec: #60 (sdd/m3-school-structure/spec)
- Design: #61 (sdd/m3-school-structure/design)
- Tasks: #62 (sdd/m3-school-structure/tasks)
- Verify Report: #65 (sdd/m3-school-structure/verify-report)

## SDD Cycle Closure

The M3 School Structure change has been fully planned (proposal), specified (3 specs merged to main), designed, tasked, implemented (6 commits, 131 tests), verified, and archived. The change is complete and the SDD cycle is closed.

**Ready for next change** or follow-up M3-D7 cleanup.

---

**Archive Date**: 2026-07-22  
**Archived By**: sdd-archive executor  
**Storage**: openspec (filesystem) + Engram (persistent memory)
