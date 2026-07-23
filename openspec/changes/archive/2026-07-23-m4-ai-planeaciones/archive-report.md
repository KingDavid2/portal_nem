# Archive Report: M4 — AI planeaciones

**Change**: `m4-ai-planeaciones`
**Project**: `portal_nem`
**Archive Date**: 2026-07-23
**Branch**: m4-ai-planeaciones (all 9 chained commits, D1a-D8)
**Artifact Store**: openspec

## Executive Summary

M4 — AI planeaciones has been successfully implemented, verified (PASS: 0 CRITICAL, 0 WARNING, 0 SUGGESTION), and archived. The change ports M1's AI lesson-plan generation engine into a workspace-scoped, Celery-backed backend application, fully integrated with the M3 tenancy and school-structure foundations. The frontend planeaciones screen enables teachers to generate, list, view, and export NEM/ABPC planeaciones directly from the app. All 8 delivery phases (D1a-D8) are complete and all 189 backend + 35 frontend tests pass with clean migrations and schema validation.

## Delivered Surface

### Backend (Django DRF + Celery)

**New Application**: `backend/lesson_plans/`
- **Models**: `LessonPlan(ScopedModel)` — workspace-scoped, Group-protected FK, JSON proyecto storage, status lifecycle (pending/ready/failed), provenance fields (provider, model, tokens, generated_at).
- **Core Port**: M1 hexagonal architecture (schema.py, generation.py, pdas.py, render/docx.py, render/markdown.py) ported verbatim into `core/` package.
- **LLM Providers**: `LLMProvider` port interface + adapters (OpenAICompatProvider for vLLM, ClaudeProvider for Anthropic), selected via `LLM_PROVIDER` env var (default: vLLM).
- **Async Generation**: Celery task `generate_lesson_plan_task` with workspace-context establishment (`SET LOCAL app.workspace_id` + contextvar), failure-surfacing (status=failed + reason), schema validation (Pydantic ABPC), and PDA-fidelity guard.
- **DRF Surface**: 
  - `POST /api/lesson-plans/` — creates pending row, enqueues task, returns 202 + id (edit_content gated).
  - `GET /api/lesson-plans/` — lists per group (group param, view_workspace gated, ScopedManager filtered).
  - `GET /api/lesson-plans/{id}/` — retrieve for polling (view_workspace gated, includes status/proyecto/failure_reason).
  - `DELETE /api/lesson-plans/{id}/` — soft delete (edit_content gated).
  - `GET /api/lesson-plans/{id}/export/` — docx or markdown export (view_workspace gated, rejects non-ready, streams binary).

**RLS & Tenancy**:
- New migration `lesson_plans/0002_rls.py` enables RLS on `lesson_plans_lessonplan` table.
- Extracted workspace-context helper `workspaces/scope.py::workspace_scope(workspace_id)` — reused by middleware and Celery task.
- Modified `TenancyMiddleware` to call `workspace_scope` instead of inlining SQL.

**Dependencies**: anthropic, openai, instructor, python-docx, numpy, pydantic, celery, redis.

### Frontend (Next.js)

**New Routes**:
- `/planeaciones` — list screen (per group, workspace-scoped, pagination).
- `/planeaciones/[id]` — detail screen (proyecto viewer + regenerate + export).

**Components**:
- `planeaciones/page.tsx` — group selector, list table, generate button.
- `generate-form.tsx` — campo/grado/theme form, campo limited to available_campos() fixture (RAG off).
- `proyecto-viewer.tsx` — read-only renderer for ABPC nested structure (stages → moments → sessions → rubric).
- `lesson-plan-export.ts` — credentialed fetch + Blob anchor (docx/markdown, outside typed client per design).

**Async Polling**: `refetchInterval` polls retrieve endpoint until status=ready or failed.

## Locked Decisions (Design Brief §3 + Proposal + Exploration)

1. **Async Mechanism**: Celery task chosen over in-process job-row. Rationale: Design-brief §3 pre-commits Celery; aligns with production-grade async infrastructure; required anyway for M6 boleta export.

2. **RAG**: OFF in first cut. Fixture PDAs only (lesson_plans/core/pdas.py::available_campos() — 2 of 4 campos). Deferred PR chain for pgvector activation. Rationale: Ships vertical slice faster; mirrors M1 Phase A → B sequencing.

3. **LessonPlan.group FK**: PROTECT, no dual FK with SchoolYear. Mirrors Student pattern. Rationale: School_year reachable via group.school_year if needed; simpler invariant, no product driver for dual FK yet.

4. **Proyecto Editor**: Regenerate-only viewer (no in-app partial editing first cut). Deferred rich editing. Rationale: MVP faster; edit flows through regenerate → poll → view cycle.

5. **Provider Env Config**: LLM_PROVIDER env var with default vLLM (OpenAI-compatible). Claude swap via LLM_PROVIDER=claude + ANTHROPIC_* settings. Rationale: Config-driven, no code redeploy.

6. **Workspace-Context in Celery**: Task MUST explicitly `SET LOCAL app.workspace_id` + set contextvar. Non-eager cold-thread test proves behavior. Rationale: Celery runs outside TenancyMiddleware; fail-closed isolation critical.

## Test Evidence

**Backend**: 189 tests passing (18.26s).
- `test_models.py` — workspace FK, PROTECT FK, direct workspace_id population.
- `test_tasks.py` — **CRITICAL**: cold-thread workspace-context leak test (non-eager, real execution context). Failure surfaces as status=failed.
- `test_services.py` — edit_content gate, workspace from membership, group-workspace invariant, PDA-fidelity guard.
- `test_viewsets.py` — 202 response, list scoping per group, cross-workspace isolation (404), polling status transitions.
- `test_export.py` — pending rejection, docx binary, markdown text, schema annotation.

**Frontend**: 35 tests passing (7 test files).
- Planeaciones list, generate form, async poll lifecycle.
- Proyecto viewer structure rendering, export download trigger, regenerate action.

**Schema & Migrations**:
- `makemigrations --check --dry-run` — PASS (no drift).
- `spectacular --validate` — PASS (docx export BINARY schema documented).
- `rg lesson-plans backend/schema.yaml` — PASS (all endpoints, formats, responses present).

## Carried-Forward Deferrals

1. **RAG / pgvector Activation**: Separate PR chain. First cut uses fixture PDAs. Corpus covers only 2 of 4 campos formativos; frontend gated to fixture-backed fields.

2. **Live End-to-End Exit-Gate Walkthrough**: Full manual test (generate → poll → view → export against running Redis + Celery worker + real model) deferred to local pre-merge step. Automated tests prove all paths; real LLM reliability unproven (instructor/vLLM JSON-mode for nested schema).

3. **Claude Fallback on Repeated vLLM Parse Failure**: status=failed first cut. Provider swap env-level; retries deferred to future slice.

4. **Rich In-App Proyecto Editing**: Regenerate-only MVP. Full edit UI deferred.

5. **AVAILABLE_CAMPOS Hardcoding**: Frontend mirrors backend fixture. No dedicated campos endpoint yet (RAG integration future).

6. **Redis Broker + Celery Worker Infra**: New runtime dependencies. Deployment task (not in this SDD).

## Change Folder Archive

**Source**: `/Users/davidnahumcrdz/projects/portal_nem/openspec/changes/m4-ai-planeaciones/`
**Destination**: `/Users/davidnahumcrdz/projects/portal_nem/openspec/changes/archive/2026-07-23-m4-ai-planeaciones/`

**Archival Status**: Files copied to archive directory. Original folder requires `git rm` (see Remaining Operations below).

**Contents Archived**:
- proposal.md
- explore.md
- design.md
- tasks.md (all 8 delivery phases complete, all tasks checked [x])
- verify-report.md (0 CRITICAL, 0 WARNING, 0 SUGGESTION)
- specs/ai-planeaciones/spec.md (NEW)
- specs/llm-provider/spec.md (NEW)
- specs/tenancy-isolation/spec.md (DELTA, now merged into main specs)

## Synced Main Specs

### `/Users/davidnahumcrdz/projects/portal_nem/openspec/specs/ai-planeaciones/spec.md`

NEW spec created. Defines LessonPlan entity, generation request/response lifecycle, Celery async flow, CRUD contracts, and export surface.

**Key Requirements**:
- LessonPlan workspace-scoped with own FK, Group-protected, JSON proyecto.
- Generation gated by edit_content, workspace from membership.
- PDA-fidelity guard (invented PDA flagging).
- Async Celery: pending → enqueue → 202; task sets ready/failed.
- CRUD endpoints workspace-scoped (ScopedManager + header validation).
- Export docx/md for ready rows only.

### `/Users/davidnahumcrdz/projects/portal_nem/openspec/specs/llm-provider/spec.md`

NEW spec created. Defines LLMProvider port as provider-agnostic, env-config-driven.

**Key Requirements**:
- Provider selection via LLM_PROVIDER env var (default vLLM/OpenAI-compatible).
- Switching to Claude config-only (no code change).
- Generation failures surface as status=failed (no uncaught exceptions).

### `/Users/davidnahumcrdz/projects/portal_nem/openspec/specs/tenancy-isolation/spec.md`

APPENDED new requirement. Celery generation tasks must establish their own workspace RLS context outside TenancyMiddleware.

**New Requirement**: "Celery Generation Tasks Must Establish Their Own Workspace RLS Context"
- Task must explicitly `SET LOCAL app.workspace_id` + set contextvar before scoped reads/writes.
- Fail closed on unset context (zero rows, denied writes).
- MUST be proven under real (non-eager) Celery execution via dedicated cold-thread test.
- Module docstring in test suite documents why eager mode is insufficient.

## Remaining Operations

**REQUIRED BEFORE COMPLETION**: Remove original change folder from active changes directory.

```bash
cd /Users/davidnahumcrdz/projects/portal_nem
git rm -r openspec/changes/m4-ai-planeaciones/
git commit -m "archive: move m4-ai-planeaciones to archive/2026-07-23-m4-ai-planeaciones"
```

This operation MUST be performed to complete the archive (original folder must not exist in active openspec/changes/).

## Traceability

**Change Artifacts** (all present in archive):
- Proposal (M1 spike → product integration)
- Exploration (M1 core portability analysis)
- Design (Celery-backed async, workspace-context, architecture decisions)
- Tasks (9 chained deliveries, D1a-D8, all complete)
- Verification (0 critical issues, all gates pass)

**Spec Artifacts** (all synced to main specs):
- ai-planeaciones/spec.md (LessonPlan, generation, CRUD, export)
- llm-provider/spec.md (provider-agnostic, config-driven)
- tenancy-isolation/spec.md (appended Celery task requirement)

**Review Receipt**: Verification PASSED (0 CRITICAL, 0 WARNING, 0 SUGGESTION). All 189 backend + 35 frontend tests pass. Clean migrations. Valid schema.

## Risks (Logged, Not Blocking)

1. **Live LLM reliability**: instructor/vLLM JSON-mode for full nested ABPC schema unproven against real model. Guarded by status=failed terminal-error path + fallback-to-Claude capability (future).

2. **AVAILABLE_CAMPOS hardcoding**: Frontend mirrors backend fixture. RAG integration (future PR chain) will enable dynamic campo availability.

3. **Celery/Redis infra**: New deployment runtime dependency. Not owned by this SDD (deployment task).

4. **Pre-merge manual exit-gate**: Live end-to-end test (generate → poll → view → export) against running worker + model not automated. Scheduled as pre-merge verification step.

---

**Archive Date**: 2026-07-23
**Status**: COMPLETE
**Next Phase**: Ready for deployment planning + M5 (attendance/grades)
