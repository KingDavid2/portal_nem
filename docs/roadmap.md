# portal_nem — Roadmap

> Global milestones for portal_nem. Sequenced to **de-risk the unknown first**: the single question that
> can kill the product is *"can a model produce a NEM planeación a secundaria teacher will accept?"* —
> everything else (auth, grids, CRUD, billing) is known-solvable engineering. So the AI path leads, and
> the platform scaffold follows. This intentionally reverses the tenancy-first order in `design-brief.md` §4.

## Global milestones

| # | Milestone | Proves | Status |
|---|---|---|---|
| **M0** | Provider-agnostic testing chat | The LLM pipe works end-to-end; provider swap is a config change | ✅ Done |
| M1 | AI lesson_plan generation — secundaria, standalone spike | The product is viable | ✅ Done (Phase A + B) |
| M2 | Tenancy foundation (auth + workspace + RLS) — the slice-1 spec | Multi-tenant boundary | 🔨 In progress — **M2a** (tenancy core) done, see `backend/` |
| M3 | School structure CRUD (school → school_year → group → student) | Data to attach plans/grades to | ⬜ Next |
| M4 | Attendance + grades entry grids | Daily-use core | ⬜ |
| M5 | report_card (boleta) PDF export | SEP deliverable | ⬜ |
| M6 | Billing + subscription | Revenue | ⬜ |
| M7 | Tutor/parent read-only portal | Future | ⬜ |

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

## Milestone 2 — Tenancy foundation (auth + workspace + RLS)

First real Django backend, under [`backend/`](../backend/). Split into commitable
deliveries, one commit each, strict TDD. Built via the SDD cycle; design lives in
`openspec/changes/archive/m2a-tenancy-core/`.

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

## Open questions (resolved during execution, not blockers)

- Exact Fase 6 SEP corpus source/format for Phase B ingestion.
- Which self-hosted model is the cheapest "good-logic" candidate — the eval scorecard answers this.
