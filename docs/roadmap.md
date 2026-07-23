# portal_nem — Roadmap

> Global milestones for portal_nem. Sequenced to **de-risk the unknown first**: the single question that
> can kill the product is *"can a model produce a NEM planeación a secundaria teacher will accept?"* —
> everything else (auth, grids, CRUD, billing) is known-solvable engineering. So the AI path leads, and
> the platform scaffold follows. This intentionally reverses the tenancy-first order in `design-brief.md` §4.

## Global milestones

### Shipped (backend-only foundations)

| # | Milestone | Proves | Status |
|---|---|---|---|
| **M0** | Provider-agnostic testing chat | The LLM pipe works end-to-end; provider swap is a config change | ✅ Done |
| M1 | AI lesson_plan generation — secundaria, standalone spike | The product is viable | ✅ Done (Phase A + B) |
| M2 | Tenancy foundation (auth + workspace + RLS) — the slice-1 spec | Multi-tenant boundary | ✅ Done — M2a tenancy core + M2b invitations + M2c move/history; 76/76 tests, see `backend/` |

### Product slices (backend + frontend per milestone)

| # | Milestone | Backend | Frontend (Next.js) |
|---|---|---|---|
| M3 | School structure CRUD (school → school_year → group → student) | ✅ Done — schools + students apps, RLS, services, first DRF HTTP surface; 131/131 tests | ✅ Done — Next.js foundation (see M3 — Frontend below): auth seam + generated TS client + school/year/group/student CRUD screens; 142 backend / 22 frontend tests |
| M4 | **AI planeaciones** (persisted + attached to group / school_year) | ✅ Done — `lesson_plans` app: ported M1 core behind `LLMProvider` port, `LessonPlan` ScopedModel + RLS, Celery generation task, DRF generate/CRUD/export; 189 backend tests | ✅ Done — Planeaciones screen: generate form + async poll + proyecto viewer + docx export; 35 frontend tests |
| M5 | Attendance + grades entry grids (daily-use core) | ⬜ | ⬜ Attendance + grades entry grids (TanStack Table) |
| M6 | report_card (boleta) PDF export (SEP deliverable) | ⬜ | ⬜ Boleta preview/download surface |
| M7 | Billing + subscription | ⬜ | ⬜ Plan/checkout + billing settings screens |
| M8 | Tutor/parent read-only portal | ⬜ | ⬜ Read-only tutor/parent portal |

**Frontend is interleaved, not a trailing phase.** From M3 onward every milestone ships its own Next.js
surface in the same slice as its API. Reason: the daily-use value (M5 attendance, M6 grades) IS the grid UI —
building the API and bolting the UI on later means re-deriving the auth seam and type pipeline under pressure.
M3 carries the one-time **frontend foundation** (auth seam + generated TS client); M4–M8 build screens on it.

**M4 pulls the AI path forward.** The M1 spike proved a model can produce an acceptable NEM planeación;
M4 turns that into a real, tenant-scoped, persisted product feature (the highest-value screen) before the
daily-use grids. All later milestones shift down one number.

M0/M1 code is throwaway-tolerant: the `LLMProvider` port, the Pydantic output schema, and the prompt/eval
assets carry forward into M2+; the standalone project wiring does not have to.

---

## Milestone 0 — Provider-agnostic testing chat

**Goal:** confirm the LLM pipe works end-to-end and lock in a provider abstraction that is swappable by
config, before any planeación logic. Deliberately tiny and standalone — no Django, no schema, no RAG.

**Live endpoint (probed 2026-07-21):** `http://192.168.1.241:8000/v1` — vLLM, OpenAI-compatible, serving
`nvidia/Qwen3.6-35B-A3B-NVFP4` (35B MoE, ~3B active params, NVFP4-quantized, 262k context).

**Agnostic by construction.** vLLM speaks the OpenAI wire protocol, so M0 uses the official `openai`
Python client pointed at a configurable `base_url`. Nothing in the code names Qwen, vLLM, or an IP —
model and URL come from config. Pointing at a different vLLM box, Ollama, or an OpenAI-compat proxy is a
`.env` edit, never a code change. (Claude is not OpenAI-compat — it lives behind the `LLMProvider` port
introduced in M1; M0 only exercises the OpenAI-compat side, which is what this endpoint speaks.)

**Build:**
1. **Config** — env vars: `LLM_BASE_URL` (default `http://192.168.1.241:8000/v1`), `LLM_MODEL`
   (default `nvidia/Qwen3.6-35B-A3B-NVFP4`), `LLM_API_KEY` (dummy — vLLM ignores it, but the client
   requires a non-empty string). LAN endpoint, no secrets.
2. **Model discovery** — a `list-models` command hitting `GET {base_url}/models`, so the served id is
   never hardcoded; if `LLM_MODEL` is unset, default to the first served model.
3. **Chat CLI** — `chat.py`: a streaming terminal REPL. In-process message history, token streaming
   (`stream=True`), a `--system` prompt flag, a `/reset` command, and per-turn token usage if returned.
4. **Smoke mode** — `--once "prompt"` for scripted/CI checks, so M0 doubles as the connectivity probe
   M1 depends on.

**Exit gate:**
`python chat.py --once "Responde en español: ¿qué es la Nueva Escuela Mexicana?"` returns a coherent
Spanish answer; the interactive streaming REPL works; changing `LLM_BASE_URL` to a different OpenAI-compat
endpoint requires zero code change.

**Carries forward:** the config-driven client construction and the streaming call become the guts of
`OpenAICompatProvider` in M1. `instructor` (schema-locked output) wraps this same client later; M0 proves
the raw transport first.

---

## Milestone 1 — AI lesson_plan generation (secundaria / Fase 6)

Standalone spike: no tenancy, no auth, no frontend. Just enough Django to generate a `lesson_plan` for
Fase 6, inspect quality by hand, and compare providers on quality vs cost.

**Baseline-first (decided):** prompt-only generation (real PDAs hardcoded) as a quality floor, then add
pgvector RAG and measure the lift — so RAG is proven to earn its cost instead of assumed.

### Target artifact — the NEM proyecto schema

Verified against `designs/examples/Ejemplo proyecto ETICA NATURALEZA Y SOCIEDADES.docx`. Output is an
**ABPC** (Aprendizaje Basado en Proyectos Comunitarios) project:

- **datos**: school_name, cct (teacher-filled), phase = 6, grade, campo_formativo, methodology, date
- **title**, **purpose**
- **articulating_axes[]**: name + justification
- **problem_or_theme**
- **contents_and_pdas[]** — the RAG anchor. Real SEP contenido + PDAs; the model must NOT invent these.
- **stages[]** (3: Planeación / Acción / Intervención) → **moments[]** (11, ABPC-canonical) →
  **sessions[]** (duración + numbered **steps[]**)
- **rubric**: criteria[] × 4 achievement levels

**Scope lock:** ABPC methodology only. The 3-fase/11-momento skeleton is methodology-specific; ABI,
Aprendizaje Servicio, and ABPr have different structures — out of M1 scope.

### Phase A — Baseline (quality floor + provider comparison)

1. Minimal Django scaffold: `config/` + `lesson_plans/` app, Postgres with pgvector enabled now.
2. **Output schema** — `lesson_plans/schema.py`: Pydantic models mirroring the proyecto skeleton. The
   `instructor` response model, and the contract that survives into production.
3. **`LLMProvider` port** — `lesson_plans/ports/llm.py`: interface + two adapters:
   - `ClaudeProvider` (Anthropic SDK) = **quality ceiling**. If even this can't produce an acceptable
     planeación, the product is dead — stop.
   - `OpenAICompatProvider` (vLLM/Ollama, seeded by M0's `chat.py`) = **what we can self-host/afford**.
4. **Prompt assembly** — `lesson_plans/generation.py`: system prompt encoding NEM/ABPC rules + the fixed
   skeleton; hardcoded real Fase 6 PDAs inlined (no retrieval yet).
5. **Driver** — `manage.py generate_lesson_plan` (campo, grade, theme, `--provider`); renders the schema
   to `.md`/`.docx` under `designs/export/` for review.
6. **Eval harness** — `lesson_plans/eval/`: 3–4 teacher-realistic requests, LLM-judge scoring output
   against the Planeabot golden docx on PDA fidelity, structural completeness, coherence, and Spanish
   register. Records tokens/cost per generation.

**Exit gate:** a side-by-side scorecard (Claude vs self-hosted Qwen) on the evals, plus a human yes/no on
≥1 generated project being teacher-acceptable with light edits.

### Phase B — Add RAG, measure the lift

7. **Corpus + ingestion** — `lesson_plans/corpus.py`: `FormativeField`, `ArticulatingAxis`, `Content`,
   `Pda` rows + pgvector embeddings. Ingest real Fase 6 SEP curriculum.
8. **Retrieval** — replace hardcoded PDAs with a pgvector similarity query; add a hallucination detector
   that flags any output PDA absent from the corpus.
9. **Re-run the Phase A evals** unchanged → measure baseline-vs-RAG delta.

**Exit gate:** RAG run shows measurably higher PDA fidelity than baseline, with zero invented PDAs.

### Provider economics

- `ClaudeProvider` bills the **Anthropic API** per token — a real per-unit cost, separate from any Claude
  Code subscription. Per-planeación estimate (~3–4k input + ~8–9k output; Spanish tokenizes heavy):
  **Opus 4.8 ≈ $0.24**, **Sonnet 5 ≈ $0.14 ($0.10 intro)**, **Haiku 4.5 ≈ $0.05**. This is why the
  self-hosted vLLM path exists — on the GX10, marginal cost per planeación drops to electricity.
- Claude's role in M1 is the **viability gate**, not the production engine: prove an acceptable planeación
  is achievable, then find the cheapest thing that clears the same bar. The eval scorecard turns "least
  viable open-weight model" from a guess into a measurement — and the served `Qwen3.6-35B-A3B` sits right
  in the expected ~30B floor.

---

## Milestone 2 — Tenancy foundation (auth + workspace + RLS) ✅ Complete

First real Django backend, under [`backend/`](../backend/). Split into commitable
deliveries, one commit each, strict TDD. Built via the SDD cycle; designs live under
`openspec/changes/archive/` (`m2a-tenancy-core`, `2026-07-22-m2b-invitations`,
`2026-07-22-m2c-move-history`). All three sub-milestones done; 76/76 tests green.

### M2a — Tenancy core ✅ Done

Defense-in-depth multi-tenancy proven safe under connection pooling **before** any
NEM domain data attaches to it:

- Custom email-identified `User` (identity-auth).
- `Workspace` (`personal`/`group`) + `Membership(user, workspace, role)`; personal
  workspace auto-provisioned at signup.
- Workspace-scoped querysets at the application layer (primary boundary) +
  Postgres **RLS** via `SET LOCAL app.workspace_id` inside `ATOMIC_REQUESTS`
  (backstop), enforced through a restricted `portal_app` role.
- Cross-tenant leak test under pooling; 39/39 tests green.

Run and test: see [`backend/README.md`](../backend/README.md).

### M2b — Invitations ✅ Done

Member discovery and invite-by-email for group workspaces; service-layer only, no HTTP yet:

- `WorkspaceInvitation` model (plain FK, excluded from RLS — invitee not yet a member).
- `invite_member` service (owner/admin-gated; 7-day expiry).
- `accept_invitation` service (atomic Membership creation; email and expiry guards; idempotent if already member).
- `revoke_invitation` service (owner/admin-gated; rejects terminal).
- `discover_pending_invites` hook in signup (surfaces pending invites by email; never creates Membership).
- `list_invitations` service (owner/admin-gated; explicit workspace filter, not RLS).
- 62 passing tests (baseline 39 + 23 new), migrations clean, all spec scenarios covered.

SDD artifacts: [`openspec/changes/archive/2026-07-22-m2b-invitations/`](../openspec/changes/archive/2026-07-22-m2b-invitations/).
Specs merged into main: `openspec/specs/invitations/spec.md` (new), `openspec/specs/workspaces/spec.md` (updated).

### M2c — Move service + workspace history ✅ Done

Atomic member relocation between workspaces + auditable membership trail; service-layer only, no HTTP:

- `WorkspaceHistory` audit model (plain FKs, `on_delete=SET_NULL` to retain rows, excluded from RLS — a `moved` row spans two workspaces).
- `move_member_to_workspace` service — single `transaction.atomic()`: delete source `Membership`, create target with role forced to `member`, write a `moved` history row; full rollback on failure.
- Authorization: `manage_members` required in BOTH source and target, plus a same-actor-user guard (both actor memberships must belong to the same user).
- Edge-case rejections: workspace-owner move, personal/non-group target, duplicate target membership.
- RLS backstop test writes a `moved` row as `portal_app` with no scoped context; 76 passing tests (baseline 62 + 14 new), migrations clean.

SDD artifacts: `openspec/changes/archive/<date>-m2c-move-history/` (after archive).
Commits on `main`: `dfbcc62` model+migration, `45babe1` move core, `869dec5` auth+guards, `9f69dee` RLS backstop.

---

## Milestone 3 — School structure CRUD ✅ Complete

The NEM domain hierarchy `school → school_year → group → student` — the data that lesson
plans (M4), grades, and attendance (M5) attach to. Also the backend's **first real HTTP
surface**. Built via the SDD cycle; designs archived under
`openspec/changes/archive/2026-07-22-m3-school-structure/`. 6 deliveries, one commit each,
strict TDD; 131/131 tests green.

- Two screaming apps: **`schools`** (`School`, `SchoolYear`, `Group`) + **`students`** (`Student`),
  all `ScopedModel` subclasses with their own denormalized `workspace` FK (never join-through
  for RLS). `Group→Student` FK is `PROTECT`; `curp` is a plain field, no uniqueness (design-brief §2).
- Uniqueness: `SchoolYear(school, label)`, `Group(school_year, grado, grupo)`; `grado` bounded 1–3.
- Per-app RLS migrations enable the `ws_isolation` policy on the four new tables in the `0004`
  NULLIF form, via an extracted `workspaces/rls.py` helper (`0003`/`0004` stay frozen).
- Keyword-only atomic services (`schools/services.py`, `students/services.py`): `edit_content`-gated,
  cross-entity workspace-consistency checks, workspace taken from membership never the client.
- DRF `ModelViewSet` per entity — reads via `ScopedManager`, writes delegate to services;
  `X-Workspace-Id` gating, cross-workspace isolation, `PROTECT` surfaces a clean 4xx.
- Closed two latent M2 auth gaps: `TenancyMiddleware` now attaches `request.membership`; and
  `WorkspacePermission` maps DRF actions → capabilities via a `capability_map` (was feeding raw
  verbs into the capability matrix → always-deny).

Specs merged into main: `openspec/specs/school-structure/spec.md` (new),
`openspec/specs/authorization/spec.md` + `openspec/specs/tenancy-isolation/spec.md` (updated).
Deferred follow-up: retire the `WorkspaceResource` placeholder model (M2 scaffold), now that
real scoped models exist.

### M3 — Frontend (Next.js foundation) ✅ Complete

The one-time frontend bootstrap, shipped as M3's frontend slice because M3 is the first API worth
consuming. Everything M4–M7 UI depends on lands here once. Built via the SDD cycle (8 deliveries,
one commit each); designs archived under `openspec/changes/archive/2026-07-23-m3-frontend-foundation/`.
142 backend / 22 frontend tests green, zero schema drift. Resolved forks: dedicated
`GET /api/auth/csrf/` bootstrap; `openapi-typescript` + `openapi-fetch` (types-only) codegen;
`frontend/` sibling subdir; same-site cookie topology (`SameSite=Lax`, env-gated dev/prod domains).
Backend added: corsheaders + `CSRF_TRUSTED_ORIGINS`, session `login`/`logout`/`me` + CSRF-bootstrap
endpoints, `GET /api/workspaces/` (RLS-excluded caller memberships). **Pending:** the manual browser
exit-gate walkthrough is code-complete and test-verified but not yet run live locally.

- **App scaffold** — Next.js (App Router) + TS + Tailwind + shadcn/ui + TanStack Query/Table, as a
  separate service (`frontend/`). Django serves no end-user HTML.
- **Auth seam (non-negotiable, design-brief §3)** — httpOnly session cookie on a shared parent domain
  (`api.*` / `app.*`), CORS with credentials, CSRF enabled. Not JWT in localStorage — student PII must
  not be XSS-readable. Backend work: DRF session-auth login/logout endpoints + CORS/CSRF config.
- **Type pipeline (non-negotiable)** — DRF → OpenAPI (`drf-spectacular`, already installed) → generated
  TS client, wired into CI from day one. Manual codegen rots; generated types are the contract.
- **Workspace context** — the active-workspace switcher sends `X-Workspace-Id` on every request.
- **First screens** — school / school_year / group / student CRUD, proving the whole pipe end-to-end
  (auth → typed client → scoped data → grid). Thin on purpose; the real grids are M5/M6.

**Exit gate:** a logged-in teacher can create a school → ciclo → grupo → alumno through Next.js screens
backed by the generated TS client, with the session cookie + CSRF + workspace scoping all live.

---

## Milestone 4 — AI planeaciones (persisted + attached) ✅ Complete

Built via the SDD cycle (9 deliveries D1a–D8, one commit each); designs archived under
`openspec/changes/archive/2026-07-23-m4-ai-planeaciones/`. 189 backend / 35 frontend tests green.
**Locked decisions:** Celery async (broker-backed, per design-brief §3, over the job-row alternative);
RAG **off** for the first cut (fixture PDAs; pgvector activation deferred); `LessonPlan.group` FK PROTECT;
regenerate-only viewer; provider env-config-driven (`LLM_PROVIDER`), default self-hosted vLLM. The
critical tenancy guarantee — the Celery task runs outside `TenancyMiddleware` and establishes its own
`app.workspace_id` via a shared `workspace_scope()` primitive — is proven by a cold-context leak test.
**Pending:** the live end-to-end walkthrough (generate → poll → view → export against a running Redis +
Celery worker + model) is code-complete and test-verified but not yet run locally; `instructor` JSON-mode
reliability on vLLM for the full nested schema is unproven (guarded by `status=failed`). New runtime infra:
Redis broker + Celery worker.

Turn the M1 standalone spike into a real, tenant-scoped, persisted product feature: a teacher generates a
NEM/ABPC planeación from within the app, it saves against a group / school_year in their workspace, and
they can list, edit, and re-export it. This is the highest-value screen — the reason the product exists —
so it leads the product slices.

**Carry-forward from M1** (`lesson_plans/` standalone project): the `LLMProvider` port
(`ports/llm.py` + `claude.py` + `openai_compat.py`), the Pydantic ABPC proyecto schema (`schema.py`), the
prompt assembly (`generation.py`), the RAG corpus (`corpus.py` + `data/fase6_corpus.json`), and the docx
renderer (`render/docx.py`). The standalone project wiring (its own `.venv`, `cli.py`, `config.py`) does
**not** carry forward — the core is ported into a real `backend/` Django app.

**Backend — new `lesson_plans` screaming app in `backend/`:**
- **`LessonPlan` ScopedModel** — workspace-scoped (own denormalized `workspace` FK + per-table RLS, per
  the M3 pattern), FK to `Group` and/or `SchoolYear` (`PROTECT`), storing the generated proyecto (the
  ABPC schema as JSON) + provenance (provider, model, tokens/cost, generated_at) + status.
- **Generation service + DRF endpoint** — port `generation.py` behind the `LLMProvider` port; a
  keyword-only atomic service (`edit_content`-gated, workspace from membership) that calls the provider,
  validates against the Pydantic schema, and persists. LLM latency (~10-30s) means generation is **async**
  (job + poll or task) rather than blocking the request — design decides the exact mechanism.
- **CRUD endpoints** — list / retrieve / update / delete `LessonPlan` via `ScopedManager` + services,
  `X-Workspace-Id`-gated like the M3 viewsets; plus a docx/markdown export endpoint over `render/`.
- **Provider config** — selection is **config-driven via env** (`LLM_PROVIDER`, `LLM_BASE_URL`,
  `LLM_MODEL`, `LLM_API_KEY`), **default self-hosted vLLM for now** (the LAN Qwen endpoint); Claude
  remains a config swap through the same port. No provider name hardcoded.

**Frontend — planeaciones screen (`frontend/`):** over the generated TS client + TanStack Query:
a list of planeaciones per group, a generate form (campo formativo, grado, theme/PDAs), an async
generate-and-poll flow, a proyecto viewer/editor (stages → moments → sessions → rubric), and a docx export
action. Built on the M3 foundation (auth seam + typed client + workspace scoping) — no new plumbing.

**Exit gate:** a logged-in teacher selects a group, generates a NEM/ABPC planeación through the Next.js
screen (via the config-selected provider), it persists workspace-scoped against that group, and they can
reopen, edit, and export it to docx — with tenancy + RLS enforced throughout.

**Open decisions for design:** async mechanism (Django task/queue vs simple job-row polling — no Celery
assumed yet); RAG on/off for the first cut (M1 corpus is available); exact `LessonPlan` ↔ hierarchy FK
shape (Group vs SchoolYear vs both); how much of the proyecto is editable vs regenerate-only.

### Frontend per milestone (M5–M8) ⬜

Each builds on the M3 foundation — no new auth/type plumbing, just screens + the milestone's API.

- **M5 — Attendance + grades:** the daily-use entry grids (TanStack Table) — attendance bulk-mark and
  grades (campos formativos × periodos + observaciones).
- **M6 — Boleta:** the report_card preview/download surface over the PDF export endpoint.
- **M7 — Billing:** plan selection / checkout + billing-settings screens over the subscription API.
- **M8 — Tutor/parent portal:** read-only portal (attendance + grades + boleta) for a restricted role.

---

## Open questions (resolved during execution, not blockers)

- Exact Fase 6 SEP corpus source/format for Phase B ingestion.
- Which self-hosted model is the cheapest "good-logic" candidate — the eval scorecard answers this.
