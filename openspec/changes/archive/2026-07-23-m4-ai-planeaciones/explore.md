# Exploration: M4 AI planeaciones — port M1 core into tenant-scoped backend + Next.js screen

Change: `m4-ai-planeaciones` · Project: portal_nem · Phase: explore

Turn the M1 standalone lesson-plan generator into a real, tenant-scoped, PERSISTED + ATTACHED
backend app + a Next.js planeaciones screen. Authoritative intent: `docs/roadmap.md`
"## Milestone 4 — AI planeaciones". Confirmed (do not relitigate): scope = persisted + attached to
group/school_year; provider = config-driven via env, DEFAULT self-hosted vLLM for now.

## Current State

**M1 standalone core** (`lesson_plans/lesson_plans/`) is largely portable as-is:
- `schema.py` — Pydantic `Proyecto` (datos → title/purpose → articulating_axes[] → problem_or_theme →
  contents_and_pdas[] → stages[3]→momentos[11]→sessions[]→steps[] → rubric.criteria[]×4 levels). This
  is the `instructor` response_model and the intended JSONField shape.
- `generation.py` — prompt assembly, `GenerationRequest(campo, grade, theme)`. Portable.
- `ports/llm.py` — `LLMProvider` Protocol + `BaseProvider.generate()` + PDA-fidelity hallucination
  guard (`find_invented_pdas`). The hexagonal port. Portable unchanged.
- `ports/claude.py`, `ports/openai_compat.py`, `ports/embeddings.py` — adapters via `instructor`
  (Anthropic tool-calling / OpenAI JSON mode), each `from_config(config)`. Portable; only the `Config`
  source becomes Django settings.
- `config.py` — env vars `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`/`ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL`/
  `EMBED_BASE_URL`/`EMBED_MODEL`. Becomes Django settings using the same var names (+ `LLM_PROVIDER`).
- `corpus.py`/`pdas.py`/`data/fase6_corpus.json` — RAG seam (`Corpus.build(embedder).retrieve(query, k,
  campo)`), in-memory numpy over a 6-entry seed corpus flagged incomplete. `pgvector` is already an
  unused backend dep — M4 is when it would activate.
- `render/docx.py`/`render/markdown.py` — pure functions, zero Django coupling; docx export needs to
  stream bytes for an HTTP response instead of writing to a path.
- Deps to add to `backend/pyproject.toml`: `anthropic`, `openai`, `instructor`, `python-docx`, `numpy`,
  `pydantic` (backend currently only has pgvector/psycopg/DRF stack).
- NOT portable: standalone `.venv`, `cli.py`, `config.py` wiring — throwaway per roadmap.

**Backend M3 patterns to mirror exactly**: `ScopedModel`+`ScopedManager` (fail-closed contextvar
scoping), per-app single-migration RLS via `workspaces/rls.py`, keyword-only atomic services with
explicit cross-entity workspace-consistency checks (`fk.workspace_id != membership.workspace_id`),
`ModelViewSet` + `WorkspacePermission` + `capability_map`, `Student.group = FK(PROTECT)` as the FK
precedent for `LessonPlan.group`. **No Celery/task-queue infra exists in `backend/` today**;
`ATOMIC_REQUESTS=True` globally makes in-request blocking LLM calls doubly costly (holds a DB
transaction for the whole ~30s call).

**Design-brief vs roadmap tension**: design-brief §3 stack table pre-commits Celery for long jobs;
roadmap M4 explicitly reopens "async mechanism… no Celery assumed yet." Real fork.

## Affected Areas
- `lesson_plans/lesson_plans/{schema,generation,ports/*,corpus.py,pdas.py,render/*,data/fase6_corpus.json}`
  — source to port into new `backend/lesson_plans/`.
- `backend/lesson_plans/` (new) — models/services/viewsets/serializers/migrations/urls.
- `backend/config/settings.py` — `LLM_PROVIDER`/`LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`/`ANTHROPIC_*`
  settings + app registration.
- `backend/pyproject.toml` — new deps.
- `frontend/` — new screens over the M3 generated-client/TanStack-Query foundation; drf-spectacular
  annotation needed for the binary docx export endpoint (openapi-typescript/openapi-fetch don't natively
  type binary bodies).

## Approaches (real forks — decide at propose/design)

1. **Async mechanism: job-row + polling (no Celery) vs Celery + broker.**
   - Job-row: zero new infra, ships in-slice; naive in-process threads lose jobs on restart (needs
     stale-job sweep) and MUST explicitly `SET app.workspace_id` since it runs outside
     `TenancyMiddleware` (design-brief's own documented Known Risk). Effort Low–Medium.
   - Celery: matches locked stack choice, production-grade, but real new infra (broker, worker, deploy) —
     bigger than the rest of M4's DRF-CRUD-shaped work. Effort Medium–High.

2. **RAG on (pgvector corpus) vs off (hardcoded fixture, M1 Phase A style) for first cut.**
   - On: matches design-brief non-negotiable but needs a net-new Django-modeled embeddings/pgvector table +
     ingestion command; current corpus is a 6-entry seed. Effort Medium–High.
   - Off: reuses `pdas.py` fixtures, ships the full vertical slice faster, defers RAG to its own PR chain —
     mirrors M1's own Phase A→B sequencing. Effort Low.

3. **LessonPlan↔hierarchy FK: Group-only (PROTECT, mirrors Student) vs dual FK (Group + SchoolYear).**
   - Group-only simplest, matches precedent, `school_year` reachable via `group.school_year`.
   - Dual FK adds a consistency invariant with no identified product driver yet.

## Recommendation
- Async: **job-row + polling now**, explicitly as a stepping stone to Celery later (same DRF surface,
  swap only fulfillment) — needed anyway for M6 boleta export.
- RAG: **off for the first cut**, fixture-based PDAs; RAG/pgvector activation as its own deferred PR chain.
- FK: `LessonPlan.group = FK("schools.Group", PROTECT)`, mirroring `Student` exactly.
- Editability: **regenerate-only** proyecto viewer for the first frontend cut (in-app rich editing deferred).

Recommended chained-PR slicing (400-line budget): (1) backend port + model, (2) generation service +
async endpoint, (3) full CRUD + docx/markdown export, (4) frontend screens, (5, deferred) RAG/pgvector.

## Risks / Unknowns
- Background-execution workspace-context leak / silent-empty-read outside `TenancyMiddleware` — needs a
  dedicated test, not assumed.
- RAG corpus covers only 2 of 4 campos formativos today — frontend must gate the campo selector or handle
  empty retrieval gracefully.
- `instructor` JSON mode against self-hosted vLLM is NOT proven reliable for the full nested schema in
  M1's own notes — the DEFAULT provider (vLLM) is the less-proven path; consider fallback-to-Claude on
  repeated parse failure.
- Docx binary export typing through drf-spectacular → openapi-typescript → openapi-fetch is unexercised —
  worth a small spike before committing frontend scope.
- `rg` missing in the explore environment; file discovery used direct Read (migration filenames not
  exhaustively enumerated).
