# Quizzy — the AI trust layer for portal_nem

> portal_nem generates NEM/ABPC planeaciones with an LLM and persists them against a teacher's
> workspace. The pipe works (M4), the screen is designed (M6), the demo path exists (M5). **Quizzy is
> everything *around* the generation that makes its output trustworthy, affordable, measurable and
> reachable** — plus the conversational surface where all of it becomes visible to a teacher.
>
> Sequenced so that **nothing is optimized before it is measured**: the grounding audit trail and the
> eval harness come before the cost work, because a provider comparison that prices tokens while
> ignoring output quality recommends the cheapest model regardless of whether it produces usable
> planeaciones.

## Phases

| # | Phase | Proves | Status |
| - | ----- | ------ | ------ |
| **P0** | Live smoke | The stack actually runs end to end — the acceptance test M4, M5 and M6 all still owe | ✅ |
| P1 | Grounding audit trail | A teacher can see *which* PDA is unofficial, and what it was checked against | ✅ |
| P2 | Eval harness | Generation quality is a number, so prompt and model changes stop shipping blind | 🟡 harness built, first scorecard deferred |
| P3 | Cost · latency · prompt version · failure taxonomy | A generation can be priced, timed, attributed and categorized | ⬜ |
| P4 | MCP server over the scoped API | The workspace is reachable conversationally, without weakening tenancy | ⬜ |
| P5 | Targeted edit | Fixing one rubric criterion stops costing a full regeneration | ⬜ |
| P6 | Demo hardening + showcase persona | The demo link can be handed to a stranger safely | ⬜ |

**Design:** [`designs/quizzy.pen`](../designs/quizzy.pen) — the conversational surface. Sibling to
[`designs/teachers.pen`](../designs/teachers.pen) and built on the same visual language.

---

## What is already solid — do not rebuild it

**Tenancy-in-async.** The Celery worker never runs `TenancyMiddleware`, so the generation task
resolves its workspace from its enqueue arguments and enters `workspace_scope()` itself — three
separate times (`lesson_plans/tasks.py:141` read, `:196` write, `:100` fail) rather than once around
the body, so no DB transaction is held open across the minutes-long provider call. `workspace_scope`
(`workspaces/scope.py:23-38`) sets both the contextvar and the Postgres GUC via `SET LOCAL`, for
pooled-connection safety.

Two cold-context tests prove it: `test_tasks.py:199` (fresh thread → fresh contextvars → asserts no
row in a second workspace was touched) and `test_tasks.py:510` (fail-closed — no scope means zero
rows, never a wrong-workspace read). Plus `workspaces/tests/test_pooling_leak.py` carries a negative
control and a `BYPASSRLS` gate test.

**P4 must extend this guarantee, not assume it.** It is the pattern every new non-request-cycle
surface has to follow.

---

## Locked decisions

**No RAG, no pgvector activation.** The extension is enabled
(`core/migrations/0001_enable_pgvector.py`) with **zero consumers**; `corpus.py` exists only in the
M1 spike and was never ported. The backend grounds on a **frozen catalog**
(`lesson_plans/core/catalog.py:102-150`) that the teacher *explicitly selects*, the server resolves
to verbatim official text (`tasks.py:75-96` — internal ids are never shown to the model), and
`find_invented_pdas` audits afterwards. A plan with no selection **fails** rather than falling back
(`tasks.py:38-41`).

An explicit selection is auditable; a similarity score is not. Building RAG would spend weeks making
the guarantee *weaker*. Recorded here as a deliberate non-goal so the idle pgvector migration stops
reading as unfinished work.

**No push-alert layer.** M7 attendance/grades is not built, so there is nothing to watch yet.

---

## Baselines

Carried forward from M1 and M6 (`roadmap.md:152-158`, `:434`):

| | |
| - | - |
| Full nested `Proyecto`, self-hosted (M1, vLLM · NVFP4 35B) | **114.1 s**, 8413 output tokens (DGX Spark) |
| Same, re-measured at P0 (llama.cpp · 27B GGUF Q8) | **223 s / 402 s / >541 s** across three attempts — see Phase 0 results |
| Cloud estimate, per generation | Opus ≈ $0.24 · Sonnet ≈ $0.14 · Haiku ≈ $0.05 |
| Self-hosted cost | electricity |
| Celery budget | 600 s soft / 660 s hard |
| HTTP client timeout | 540 s — deliberately *below* Celery, so it always fails first with something the adapter can translate (`core/ports/llm.py:25`) |

---

## Phase 0 — Gate zero: run the live smoke

**Goal:** verify the stack below the API boundary. **M4, M5 and M6 all still owe this same
walkthrough** (`roadmap.md:351`, `:449`) and it has never been run — everything below the API
boundary is currently verified only by pytest and vitest.

Bring up Redis + `manage.py runserver` + a Celery worker + `npm run dev`, then walk:

`/demo` → pick `teacher_full` → provisioning polls → lands signed in → `/planeaciones/nueva` → pick
campo formativo, asignatura, contenidos, PDAs → **Generar proyecto** → poll → viewer → docx export.

Budget ~2 minutes for the generation leg. **Expect breakage — that is the point of running it
first.** Every later phase inherits whatever this finds.

**Exit gate:** completes twice in a row from a cold `/demo` click. Record per-leg wall-clock; P3
needs it as a baseline.

### Results — run 2026-07-28

Both passes reached `status: ready` and exported a valid docx, so the gate is **met** — but only
because the second pass was rescued by a retry. Driven below the API boundary with curl against
Redis + Celery + `runserver`; the browser legs are still unwalked.

| leg | pass 1 | pass 2 |
| --- | ------ | ------ |
| `POST /api/demo/sessions/` → `ready` | 1.3 s | 1.3 s |
| catalog fetch | 0.1 s | 0.1 s |
| `POST /api/lesson-plans/` → 202 | 0.1 s | 0.1 s |
| **generation** | **402 s** | **541 s timeout → 180 s backoff → 223 s retry = 944 s** |
| docx export | 40,725 B | 40,036 B |
| tokens (in/out) | 2698 / 5671 | 2698 / 3588 |

**The provider timeout is marginal on this hardware.** Three generations of the *same* payload took
223 s, 402 s and >541 s. The 540 s HTTP client timeout fired exactly as designed — below Celery's
600 s soft limit, translated into `TransientProviderError`, retried, recovered — but a teacher
waiting 944 s for a plan is a failure in every sense except the technical one. Note the provider on
`:8000` is now **llama.cpp serving `Qwen3.6-27B-…Q8_0.gguf`**, not the vLLM NVFP4 35B the M1 baseline
was measured on.

**Findings that change later phases:**

1. **`invented_pdas: False` on a pedagogically incoherent plan.** Theme *"Cuidado del agua en nuestra
   comunidad"* against the only content `ethics-nature-societies` offers — *"Las gestas de
   resistencia y los movimientos independentistas"* — produced *"Agua que nos une: resistencia
   histórica y cuidado comunitario del recurso hídrico."* Grounding passed because it checks **PDA
   fidelity, not topical fit**. The trust signal reads ✓ on an unusable document. This is the
   strongest available argument for **P2**, and it is a direct consequence of the catalog-coverage
   ceiling recorded under *Adjacent*.
2. **Recorded provenance is wrong.** `model_name` persisted as `nvidia/Qwen3.6-35B-A3B-NVFP4` — the
   settings value — while the 27B GGUF answered. llama.cpp ignores the request's `model` field and
   echoes back whatever it is sent. **P3 must record the model the server reports, not the one the
   client asked for**, or the provenance strip will state a falsehood confidently.
3. **`instructor` JSON-mode succeeded 2/2** on the full nested `Proyecto` against llama.cpp — all
   eight top-level keys, ~11 KB. First evidence against `roadmap.md:280`'s "unproven". Output is
   thin, though: 3 stages and a **single** rubric row. P2's scorecard should measure depth, not just
   parse success.
4. **A retrying plan is indistinguishable from a queued one.** Status stays `pending` across the
   whole timeout + backoff + retry window with `failure_reason` empty, so the UI cannot explain a
   15-minute wait. P3's `failure_kind` should be written on the *attempt*, not only the terminal
   outcome.
5. **The declared retry backoff is dead config.** `tasks.py:110-111` sets `retry_backoff=True,
   retry_backoff_max=60`, but `:160` calls `self.retry(exc=exc)` explicitly, which bypasses backoff
   and uses Celery's `default_retry_delay` — the log shows `Retry in 180s`, not the declared 60 s
   cap. Fix alongside the two provider-swap bugs in P3.
6. **Quota is charged once at create, and retries do not double-charge** — verified against
   `GenerationUsage`. That narrows open decision 1: the refund question is live only for *terminal*
   failures.
7. **Writes require CSRF** (`GET /api/auth/csrf/` → `X-CSRFToken` + `Referer`); the demo endpoints
   skip it. **P4's MCP surface has no CSRF cookie**, so it needs an auth path that is not session
   auth — settle that at design time, not during implementation.

**Still unwalked at the time of this run:** every browser leg — all of the above is HTTP. The
`/demo` picker, the polling page, the `nueva planeación` form and the viewer were all walked later,
during the P1 browser run below; the one leg still never driven from a browser is **Generar
proyecto** itself, which remains HTTP-only.

---

## Phase 1 — The grounding audit trail

**Goal:** when the product warns that a planeación may not be grounded, say *where*.

**Why it matters:** the central product claim is that a planeación is grounded in official SEP
curriculum. Today a teacher is told that claim may be broken without being told which line broke it
— which invalidates the whole document in their mind rather than one PDA, and gives them nothing to
act on. That document goes into a classroom, or to a director.

**The data already exists, twice over, and the UI discards both.** `find_invented_pdas`
(`core/ports/llm.py:80-83`) runs on every generation inside `BaseProvider.generate()`, so every
provider gets it free, and its normalization collapses whitespace and case so mere reformatting is
not flagged. Then `tasks.py:204` collapses the result to `bool(result.invented_pdas)` — **the list
of offending PDAs is thrown away.** Separately `content_selections` (the authoritative
`{content_id, pda_ids}` grounding, migration `0003_project_context`) persists but is read only to
rebuild the regenerate payload (`frontend/src/lib/api/lesson-plans.ts:50-71`); the viewer renders
the model's echoed plain strings, which carry no ids at all
(`frontend/.../proyecto-types.ts:24-27` — which is why React keys fall back to
`` `${group.content}-${index}` ``).

**Backend**
- `lesson_plans/models.py:64` — **keep** `invented_pdas: BooleanField` (it is in the public schema
  and rendered today; do not break it) and add `invented_pda_texts: JSONField(default=list)` beside
  it. New migration.
- `tasks.py:204` — persist `result.invented_pdas`, the list, alongside the bool. It already flows out
  of `BaseProvider.generate()` on `GenerationResult` (`core/ports/llm.py:68-72`); nothing upstream
  changes.
- `serializers.py` — add both to `Meta.fields` + `read_only_fields`, per the pattern at `:47-99`.
- Embed the teacher's resolved selections in the plan payload. **Embed rather than re-fetch:** the
  viewer must faithfully render a plan whose catalog entry may have changed since it was generated.

**Frontend**
- `npm run gen:all` (`package.json:11-13`).
- `planeaciones/[id]/page.tsx:104-112` — name the offending PDA instead of asserting one exists.
- `proyecto-viewer.tsx:44` — mark each rendered PDA ✓ *oficial, seleccionado por ti* or ⚠ *fuera de
  tu selección*. Reuse `ContenidoCard` / `PdaRow`; both already support `readOnly`.

**Exit gate:** a plan carrying an invented PDA names it and shows what it was checked against.
`test_tasks.py:357` still passes.

### Results — run 2026-07-28

Implemented as `core/grounding.py` (one normalization rule, one home), two new columns
(`invented_pda_texts`, `grounding_selections`) with migration `0006_grounding_audit`, typed
serializer fields, grounding-aware docx/markdown renderers, and a viewer that marks every PDA.

**Automated:** backend 417 passed, `makemigrations --check` clean, ruff at the HEAD baseline;
frontend 187 passed, `tsc --noEmit` clean, lint 0 errors. `test_tasks.py:357` passes unmodified in
its original assertions.

**Live, against the running stack** (Redis + Celery + `runserver`, demo mode on). The ⚠ path was
forced deterministically the way `test_tasks.py:357` does — select `languages-accentuation` only,
have the provider echo `languages-coherent-texts` (official Phase 6 text in the same field, outside
the selection) — writing a real browsable row rather than a test-DB row:

- **DB:** `invented_pda_texts` holds the verbatim offending PDA; `grounding_selections` holds the
  verbatim official snapshot it was checked against.
- **API** `GET /api/lesson-plans/22/`: both fields present and correctly typed.
- **docx** `GET …/export/?format=docx`: `✓` on the in-selection PDA, `⚠ FUERA DE TU SELECCIÓN —` on
  the offender, and a `Fundamentación oficial (SEP)` section carrying the official text verbatim.

**The browser legs, walked.** The earlier note that no browser driver was available was wrong —
Playwright resolves and drives the installed Chrome directly (`channel: "chrome"`, no download). The
walk ran from a throwaway scratchpad script, not a committed e2e suite; adding an e2e harness is its
own decision, not part of this gate.

Route: `/demo` picker → `teacher_full` → `/demo/[id]` provisioning poll → signed in → `/planeaciones`
→ the viewer → `/planeaciones/nueva`. **13/13 assertions passed**, and the three P1 claims are now
confirmed visually *and* in the accessibility tree:

- the `role="alert"` card names the offending PDA verbatim as an `<li>`, and does **not** fall back to
  the anonymous "al menos un PDA" wording;
- the in-selection row renders a `Star`, the offender an `AlertTriangle` — and the offender's sr-only
  text `fuera de tu selección` reaches the accessibility tree, which a screenshot alone cannot prove;
- `Fundamentación oficial (SEP)` carries the selected PDA verbatim and does not list the offender.

**Seeded, not generated.** The ⚠ row was written directly into the DB, mirroring the persist block of
`tasks.py` and reusing `core/grounding.py` for the fidelity rule so the fixture cannot drift from the
production check. This gate is about *display*; the generation leg is already green from P0.

**`/planeaciones/nueva` was walked up to but not through Generar proyecto.** The form filled end to
end — grupo, campo, materia, tema, diagnóstico, fechas, eje, contenidos + PDAs — and the summary panel
enabled **Generar proyecto** with nothing outstanding. The button was deliberately not clicked: that
leg is P0's and costs 223–541 s.

**One defect the walk caught, and fixed.** `ContenidoCard`'s header rendered a filled green `Star`
unconditionally — so a card whose only PDA was flagged ⚠ still carried an "official" mark on its
title, the exact class of unearned green this phase exists to remove. The header mark now derives
from its rows: any unofficial row turns it into an `AlertTriangle` with sr-only *contiene PDAs fuera
de tu selección*; otherwise the `Star` stays. Two tests, mutation-proved in both directions, and
re-confirmed in the browser — card 0 star / card 1 warning, and the `Fundamentación oficial (SEP)`
cards keep their star.

Two observations left unfixed, both outside this gate: (1) the `ContenidoCard` header checkbox in the
contents picker is inert (`onChange={() => {}}`) — it looks interactive and does nothing, selection is
driven by the PDA rows; (2) the seeded plan shows "se creó antes del formulario actual, por eso no
puede regenerarse", a fixture artifact (the seed omits `subject_id` / `methodology_id` /
`duration_weeks` / dates / `scenario`), not a product defect.

**Deploy note the smoke surfaced.** The first provisioning attempt failed with
`null value in column "grounding_selections" … violates not-null constraint`. Not a code defect: the
Celery worker predated migration `0006`, so its in-memory model omitted the column from every
INSERT, and the new column is `NOT NULL` with no DB-level default. **Workers must be restarted
alongside this migration**, or every insert they perform fails.

---

## Phase 2 — Port the eval harness

**Goal:** make generation quality a number.

**Why it comes before the cost work:** nothing currently measures whether a generated plan is any
good. Every prompt edit, catalog addition and model swap ships blind. And `roadmap.md:280` already
records that *"`instructor` JSON-mode reliability on vLLM for the full nested schema is unproven"* —
so even the structured-output **failure rate** is unknown. P3 exists to make provider choice a
measured decision, but comparing providers on cost and latency alone is comparing price tags with
the product hidden.

The M1 harness was left behind with `corpus.py`. Port `lesson_plans/lesson_plans/eval/` into
`backend/lesson_plans/eval/`:

- `cases.py` — teacher-realistic generation requests
- `golden.py` — the Planeabot reference docx
- `judge.py` — LLM-judge on PDA fidelity, structural completeness, coherence, Spanish register
- `run.py` — scorecard + tokens/cost

**Drop `lift.py`** — it measures baseline-vs-RAG, and RAG is a locked non-goal.

Run it as a `manage.py` command, **not a pytest test**: it costs real tokens and real minutes, so it
is an on-demand gate, not something CI runs per commit. Commit scorecards so regressions show up as
a diff.

**Add a schema-failure-rate case specifically:** N generations against the full nested `Proyecto`,
counting how often `instructor` fails to parse on the self-hosted model. That number decides whether
the vLLM path is production-viable at all.

**Exit gate:** `manage.py run_evals` produces a scorecard for at least two providers, and the
self-hosted schema-failure rate is a known number rather than an open question.

### Results — harness landed, first scorecard deliberately deferred

The harness is built and its token-free parts are under test (42 tests; full suite 459 green). No
scorecard exists, and that is a decision rather than an oversight: `ANTHROPIC_API_KEY` is unset in
`.env`, `backend/.env` and the shell, and the first paid sweep is being held until there is a change
worth measuring. The gate stays open until a committed scorecard exists.

**What shipped**

| Piece | Where |
| --- | --- |
| Eval cases from the frozen catalog | `backend/lesson_plans/eval/cases.py` |
| Committed golden references, one per campo | `backend/lesson_plans/eval/golden/*.md` |
| LLM judge, four axes 1–5 | `backend/lesson_plans/eval/judge.py` |
| Scorecard assembly, cost, schema probe | `backend/lesson_plans/eval/run.py` |
| On-demand command | `manage.py run_evals` |

`lift.py` was not ported, as planned.

**Three decisions worth carrying forward**

1. **The judge takes three inputs, not M1's two.** The committed goldens are form references whose
   PDAs are *not* the catalog's — the Lenguajes docx is about identity and literary texts, not
   accentuation, and the Ética one says "mapas mentales" where the catalog says "recursos gráficos".
   Grading fidelity against them would penalize a plan for quoting the teacher's actual selection.
   So the official selection is passed as its own block, the golden calibrates form and depth only,
   and the deterministic `invented_pdas` count stays the hard fidelity signal.
2. **`EVAL_JUDGE_MODEL` is separate from `ANTHROPIC_MODEL`.** Swapping the generation model must not
   silently swap the judge, or every previously committed scorecard stops being comparable. Both
   models are recorded in the scorecard header, alongside the same-family-bias caveat: Claude judging
   Claude is self-preference, and pinning the judge separately is what makes it swappable later.
3. **Providers are built in the command, not through `core/factory.py`.** The factory reads one
   global `LLM_PROVIDER`; a scorecard needs several arms live in one process.

**Scope stated honestly.** Both arms are behind `--provider`, but Claude is the P2 baseline by
decision and the self-hosted arm is deferred. A Claude-only run therefore satisfies the scorecard
half of the gate and leaves the self-hosted schema-failure rate — the half that decides whether the
vLLM path is production-viable — still unmeasured.

**Remaining to close P2** — one sitting, whenever the first paid sweep is wanted:

```
export ANTHROPIC_API_KEY=...
cd backend && python manage.py run_evals --provider claude --schema-runs 10
```

Then commit the scorecard, re-run once to confirm the diff is readable, and flip the status above.
Until that happens the harness is infrastructure, not evidence — nothing here has yet scored a real
generation, so no claim about generation quality rests on it.

---

## Phase 3 — Cost, latency, prompt version, failure taxonomy

**Goal:** make a generation something you can price, time, attribute and categorize.

**Why it is a hard dependency for M9:** billing is priced **per ciclo** while `GenerationUsage.period`
is **per month** — `roadmap.md:455-458` flags this unresolved and defers the "Límite alcanzado" modal
because of it. You cannot price a quota whose unit cost you have never measured. The row stores token
counts but **no cost and no duration**, and `generated_at` minus `created_at` conflates queue wait
with provider time, so it is not a substitute.

- `lesson_plans/models.py` — add `duration_ms: IntegerField(null=True)` and
  `cost_micros: BigIntegerField(null=True)`. **Integer micros, never a float**, for money.
- New `lesson_plans/core/pricing.py` — a frozen `{(provider, model): (in_price, out_price)}` table
  plus `cost_micros(usage, provider, model) -> int | None`, returning **`None`** for an unpriced
  self-hosted model rather than implying zero. Pure and framework-free, matching the other `core/`
  modules.
- `tasks.py:148` — measure wall-clock around the provider call **only**. It sits deliberately
  *between* two `workspace_scope` blocks, so this does not touch tenancy.
- **`prompt_version`** — hash the assembled system prompt at generation time and store it. Without
  it, provenance says which *model* produced a plan but not which *prompt*, so a quality complaint
  can never be correlated to a prompt change. Cheap now, impossible to backfill later.
- **`failure_kind`** — a small enum column beside the existing `failure_reason: TextField` (truncated
  to 2000 chars). Today you cannot answer *"what percentage of generations fail, and why."* This
  matters specifically because `instructor` raises the **same exception class** for a network timeout
  and a schema-parse failure — only `__cause__` separates them (`core/ports/llm.py:37-59`). A
  category column turns that from forensics into a metric.
- Serializer + `npm run gen:all`, then a provenance strip in the viewer:
  provider · model · tokens · cost · latency · grounded ✓/⚠.

**One live bug to fix while here** — it surfaces on a provider swap:

| bug | effect |
| --- | ------ |
| `lesson_plans/core/factory.py:30-36` is not an exhaustive match | anything not the literal `"claude"` silently falls through to vLLM, so a typo in `LLM_PROVIDER` is invisible |

A second entry here previously claimed `ANTHROPIC_MODEL`'s default `"claude-opus-4-8"`
(`config/settings.py:243`) was not a valid model id. It is valid and current; the claim was wrong and
the entry is dropped.

**Exit gate:** a completed plan reports its own cost, latency, prompt version and failure category;
an unpriced self-hosted model reports `null` cost, **not `0`**. Combined with P2's scorecard,
provider choice becomes a defensible decision rather than a preference.

---

## Phase 4 — MCP server over the scoped API

**Goal:** make a workspace reachable conversationally, and give every future integration one typed,
scoped door instead of bespoke endpoints. This is the backend of the Quizzy chat surface in
`designs/quizzy.pen` — design the tool list against those screens.

**Confirmed absent:** no MCP, no JSON-RPC, no tool registry anywhere in the repo. The only
tool-calling today is inbound and internal — `instructor` using tool-use purely to enforce the
`Proyecto` schema.

New `backend/mcp/` app (screaming-architecture convention), launched via a `manage.py` command so it
shares settings and the ORM. Read-only tools for v1: `list_groups`, `list_lesson_plans`,
`get_lesson_plan`, `get_quota`, `search_catalog`.

**The non-negotiable constraint:** the MCP process, like the Celery worker, never runs
`TenancyMiddleware`. Every tool call MUST resolve its workspace from the authenticated caller and
enter `workspace_scope(workspace_id)` (`workspaces/scope.py:23`) itself before any ORM access —
never trusting anything ambient. Mirror the fail-closed test at `test_tasks.py:510`: a tool invoked
with no scope established returns **zero rows**, never an unscoped read.

**Exit gate:** an MCP client answers a natural-language question over a demo tenant, and a
cold-context test proves a cross-tenant read returns empty.

---

## Phase 5 — Targeted edit instead of wholesale regenerate

**Goal:** stop charging a full regeneration to fix one line.

**Why:** the viewer is **strictly read-only** and there is **no PATCH/PUT for lesson plans anywhere**
— "regenerar" is a re-`POST` that creates a *new* plan from the persisted context. Fixing one rubric
criterion costs 114 seconds, a quota unit, and produces a second row. That is the sharpest usability
defect on the highest-value screen in the product.

Scope to **one** mutation first — a single rubric criterion, or one stage's session count. The flow:
agent proposes → server renders a diff against the persisted `proyecto` JSON → teacher approves →
write + audit row. Follow the `WorkspaceHistory` precedent (M2c) for the audit trail, and the
keyword-only atomic service pattern in `lesson_plans/services.py`.

The chat is its natural home — propose → review → approve is a conversation, not a form. See the
**Edición propuesta** screen in `designs/quizzy.pen`.

Decide the exact scope at the P4 exit gate, not before. **Do not half-build it:** a partial mutation
path on the product's most important screen is worse than none.

**Exit gate:** one mutation lands end to end with an audit row, and the plan's provenance survives
the edit.

---

## Phase 6 — Demo hardening, then the showcase persona

**Goal:** make the demo link safe to hand to a stranger. **This blocks doing so.** Three findings, in
severity order.

### a. Unthrottled tenant provisioning

`REST_FRAMEWORK` (`config/settings.py:181-189`) configures **no throttle classes at all**. Three
`AllowAny` / `authentication_classes = []` views (`demo/views.py`) are therefore unlimited, and each
`POST /api/demo/sessions/` provisions a real workspace + school + ciclo + 2 grupos + 20 alumnos + 2
planeaciones.

Add DRF `AnonRateThrottle` scoped to the demo views. **Throttle both surfaces, not just session
creation:** a `teacher_minimal` guest can then *generate*, which reaches the real LLM — so the demo
is also an unauthenticated path to GPU time.

### b. No cleanup

Nothing in `demo/` expires or reaps anything; demo tenants accumulate forever. Add a periodic task
deleting `DemoSession`s and their workspaces past a TTL. **Mind the `PROTECT` FKs**
(`Group→Student`, `LessonPlan→Group`) — deletion order matters and a naive cascade will fail.

### c. The DEBUG tension — decide this explicitly

`demo_mode.enabled()` returns `False` unless `settings.DEBUG`, and boot fails if `DEMO_MODE` is on
with `DEBUG` off (`config/demo_mode.py`, `config/settings.py:36-37`). **That gate is what makes the
`AllowAny` endpoints acceptable.** But hosting the demo publicly means running `DEBUG=True` on a
reachable host, which leaks tracebacks and settings.

*The gate that makes demo mode safe is what makes hosting it unsafe.* Either introduce a separate
`DEMO_DEPLOY` flag with its own hardening, or accept demo mode as local-only and record that. **Do
not leave it implicit.**

### Then the persona

M5's registry makes it nearly free: write a `DemoProvisioner` subclass in `demo/provisioning/`
overriding `seed(self, *, membership)`, then append one `Persona(...)` entry to the frozen
`_REGISTRY` tuple (`demo/personas.py:51`) with its dotted import path. Nothing else changes — the
picker endpoint, `ChoiceField(choices=personas.keys())` (`demo/serializers.py:29`) and
`persona.resolve_provisioner()()` all pick it up.

Seed a workspace where the Quizzy work is immediately visible: one clean grounded plan, one carrying
a real grounding warning, both with cost and latency populated. Follow `TeacherFull`'s documented
exception (`demo/provisioning/teacher_full.py:137-141`) — seed `LessonPlan` rows **directly** rather
than through `lesson_plans.services`, because the real create path triggers the LLM, which is exactly
what the visitor should do themselves. Side effect: directly-seeded plans do not consume quota, which
is why `quota_exhausted` needs its own explicit `GenerationUsage` write.

**Exit gate:** the demo endpoints are throttled, demo tenants expire, the hosting posture is written
down, and the showcase persona renders grounding and provenance without a single generation.

---

## Decisions this work forces

None of these are code-only. Record each here as it resolves.

1. **Quota refund on failure** (`roadmap.md:453`, currently open). P3 makes it decidable: refunding a
   transient timeout is arguably fair since no useful tokens were spent, while refunding a
   schema-parse failure is not — the model burned output tokens producing garbage. Exactly-once is
   not Celery's to give, so whatever policy is chosen **must tolerate double-fire**. *P0 narrowed
   this:* quota is charged once at create and retries do not double-charge, so only **terminal**
   failures are in question.
2. **PII boundary on provider swap.** `context_diagnosis` and `scenario` are free-text teacher input
   about a real group of minors, and the catalog response carries `teacher {email}` plus the school
   CCT. With `LLM_PROVIDER=vllm` that stays on hardware you own; flipping one `.env` value sends it
   to a third party. `design-brief.md` §3 already treats student PII as a hard constraint. Decide and
   document what may cross that boundary — **a config swap should not silently move it.**
3. **Provenance exposure.** `provider`, `model_name` and raw token counts are already public to any
   authenticated teacher in the workspace (`serializers.py:47-99`); P3 adds cost. Confirm that is
   intended.

---

## Adjacent — deliberately not in Quizzy

Each affects Quizzy's value but deserves its own milestone.

- **Catalog coverage is the real ceiling.** Two of the four campos formativos —
  `scientific-thinking` and `human-community` — have **zero contents**
  (`lesson_plans/core/catalog.py:5`, `:102-150`). Half the curriculum cannot produce a grounded plan
  at all. A trust layer over a catalog covering half the subject areas is a well-audited hole. This
  is arguably higher product value than any phase above; it is excluded only because it is
  curriculum data work, not AI work.
- **Streaming.** 114 seconds of watching a poll is the biggest perceived-latency lever in the
  product, and M0 already proved token streaming works against the same endpoint. UX, not trust.

---

## Verification

Per phase, and again at the end:

```bash
cd backend  && uv run pytest
cd frontend && npm test
cd frontend && npx tsc --noEmit
cd frontend && npm run lint
cd frontend && npm run gen:all && git diff --exit-code src/lib/api/schema.d.ts   # zero schema drift
cd backend  && uv run manage.py makemigrations --check --dry-run
```

On demand only, because it costs real tokens: `uv run manage.py run_evals`.

**Re-run the P0 live smoke after every phase.** It is the acceptance test M4/M5/M6 all still owe, and
the only thing that verifies below the API boundary.

**The tenancy tests are load-bearing** and must stay green throughout, extended to the MCP surface in
P4: `lesson_plans/tests/test_tasks.py:199`, `:510`, and `workspaces/tests/test_pooling_leak.py`.

---

## Open questions

1. ~~What does "Quizzy" name — the initiative, the MCP server, or a user-facing assistant?~~
   **Resolved:** a user-facing assistant inside portal_nem. The P4 MCP tools are therefore this
   chat's backend, not only an external door.
2. **Phase cut.** P0–P1 are days. P2 is the highest-leverage single phase and unblocks trusting
   everything after it. P4–P6 are each a week-ish. Decide the cut before starting P4.
3. **P5 scope** — which single mutation goes first.
4. **Demo hosting posture** — P6c, local-only vs a hardened deploy flag.
5. ~~**Which provider is the baseline.**~~ **Resolved: Claude.** P0 measured llama.cpp with the 27B
   GGUF, where the 540 s client timeout is a coin flip — a timeout firing on roughly a third of
   generations makes every number P2 and P3 produce unreproducible. Claude is the P2 baseline; the
   self-hosted arm stays coded behind `--provider vllm` and gets measured once the local model is
   settled. The consequence is recorded in the P2 results: the self-hosted schema-failure rate, which
   decides whether the vLLM path is production-viable, remains unknown until then.
