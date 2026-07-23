# Proposal: M4 — AI planeaciones (persisted + attached)

## Intent

M1 proved a model can produce a teacher-acceptable NEM/ABPC planeación, but as a throwaway standalone spike: no tenancy, no persistence, no UI. M4 turns it into the product's highest-value screen — a teacher generates a planeación from inside the app, it saves workspace-scoped against a Group, and they list, reopen, edit, and re-export it. Now: M2 tenancy + M3 school-structure + M3 frontend foundation are all done, so the AI path is unblocked and leads the product slices.

## Scope

### In Scope
- New `backend/lesson_plans/` screaming app: port M1 core (`schema.py`, `generation.py`, `ports/*`, `render/*`) behind the `LLMProvider` port, `Config` → Django settings.
- `LessonPlan` ScopedModel: own denormalized `workspace` FK + per-table RLS (M3 pattern); `group = FK("schools.Group", PROTECT)` (mirrors `Student`); ABPC proyecto stored as JSON; provenance (provider/model/tokens/generated_at) + status.
- Keyword-only atomic generation service, `edit_content`-gated, workspace from membership; validates against Pydantic schema before persist.
- Async generation mechanism (job-row + poll) so the ~10–30s LLM call does not block the request.
- DRF endpoints: generate + CRUD + docx/markdown export, `X-Workspace-Id`-gated (M3 viewset pattern).
- Env-driven provider selection (`LLM_PROVIDER`/`LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`), default self-hosted vLLM.
- Frontend planeaciones screen on the M3 foundation: list per group, generate form, async poll, proyecto viewer, docx export.

### Out of Scope
- RAG / pgvector activation (deferred PR chain; first cut uses fixture PDAs, M1 Phase A style).
- Celery / broker infra (job-row is the stepping stone).
- Rich in-app proyecto editing (regenerate-only viewer first).
- Methodologies beyond ABPC; attendance/grades (M5).

## Capabilities

### New Capabilities
- `ai-planeaciones`: LessonPlan model, generation service, async job lifecycle, CRUD + export DRF contracts.
- `llm-provider`: the `LLMProvider` port + env-driven provider selection/config, provider-agnostic contract.

### Modified Capabilities
- `tenancy-isolation`: background/async generation runs outside `TenancyMiddleware` and MUST explicitly set the active-workspace context, or RLS + scoped manager fail closed to empty.

## Approach

Port M1's hexagonal core unchanged behind the `LLMProvider` port; only the config source becomes Django settings. Mirror M3 exactly: ScopedModel + per-app single RLS migration + keyword-only services + ModelViewSet delegating writes to services. Generation is dispatched to a job row; a poll endpoint returns status/result. The frontend reuses the M3 auth seam + generated typed client — no new plumbing.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `lesson_plans/lesson_plans/*` | Modified | Source ported into backend app |
| `backend/lesson_plans/` | New | models/services/viewsets/serializers/migrations/urls |
| `backend/config/settings.py` | Modified | LLM_* settings + app registration |
| `backend/pyproject.toml` | Modified | anthropic, openai, instructor, python-docx, numpy, pydantic |
| `frontend/` | New | Planeaciones screens over M3 typed client |

## Open Design Decisions (lock in sdd-design)

1. Async: job-row + polling now (proposed) vs Celery — note design-brief §3 pre-commits Celery; document the tension.
2. RAG off for first cut (proposed) vs pgvector activation.
3. `LessonPlan.group = FK(schools.Group, PROTECT)` only (proposed) vs dual FK with SchoolYear.
4. Regenerate-only viewer (proposed) vs partial in-app editing.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Background job runs outside TenancyMiddleware → RLS silently empties reads/writes | High | MUST be a spec requirement + dedicated leak test: explicitly `SET app.workspace_id` in the job |
| In-process job lost on restart | Med | Stale-job sweep; status field surfaces failure |
| `instructor` JSON mode on default vLLM unproven for full nested schema | Med | Fallback-to-Claude on repeated parse failure; validate before persist |
| Docx binary export typing (spectacular → openapi-typescript) unexercised | Med | Small spike before committing frontend export scope |
| `ATOMIC_REQUESTS=True` holds DB txn for ~30s LLM call | Med | Async job moves the LLM call out of the request transaction |

## Rollback Plan

New app is additive: no changes to existing tables. Revert = remove `lesson_plans` from `INSTALLED_APPS`, drop its migrations, revert settings/pyproject/frontend commits. No data migration on existing entities to reverse. `PROTECT` FK means no cascade damage to Group.

## Dependencies

- Backend M2 tenancy, M3 school-structure, M3 frontend foundation (all done).
- Live vLLM endpoint (LAN Qwen) for default provider; Anthropic key for Claude swap.

## Success Criteria (exit gate)

- [ ] A logged-in teacher selects a group and generates a NEM/ABPC planeación through the Next.js screen via the config-selected provider.
- [ ] It persists workspace-scoped against that group; RLS + scoped manager enforced end-to-end (including the async job path).
- [ ] The teacher can reopen, edit (regenerate), and export it to docx.
- [ ] Cross-workspace isolation and background-job workspace-context tests pass.

## Delivery — Recommended Chained PRs (400-line budget: High)

1. Backend port + `LessonPlan` model + RLS migration.
2. Generation service + async generate/poll endpoint.
3. Full CRUD + docx/markdown export.
4. Frontend planeaciones screens.
5. (Deferred) RAG / pgvector activation.
