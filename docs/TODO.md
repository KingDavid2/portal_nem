# TODO

## M1 Phase B — close the exit gate

The RAG machinery is built, tested (31 green), and proven live (4/4 themes retrieve
the correct contenido, 0 invented PDAs). Two items remain before the roadmap exit gate
— *"RAG run shows measurably higher PDA fidelity than baseline, with zero invented PDAs"*
— produces a real measured number instead of a demo.

- [ ] **Full Fase 6 SEP corpus** (roadmap open Q#1). `data/fase6_corpus.json` currently
      holds a 6-entry seed — too small for a meaningful baseline-vs-RAG lift; retrieval
      has almost nothing to choose from. Drop in the real SEP Fase 6 program (all campos,
      every contenido + PDA). Open sub-question: source/format of that curriculum data
      (SEP PDF? structured export? manual transcription?).
      The production planning catalog also needs:
      - every official contenido and PDA, with source document, edition, and page;
      - stable IDs that survive wording or accent corrections;
      - the complete campo-to-subject relationships for secundaria;
      - the official cross-cutting themes and supported methodology metadata;
      - provenance, transcription review, licensing, and completeness checks.
      Until this is complete, catalog fields without verified curriculum text must
      remain available only as empty official-content subsets—never filled from seed
      or model-generated examples.

- [ ] **Run the judge scorecard.** `eval/lift.py` scores each planeación with Claude as an
      LLM-judge, but needs `ANTHROPIC_API_KEY` (absent from env). Set the key, then run
      `python -m lesson_plans.eval.lift` to get the baseline-vs-RAG fidelity table.

Neither blocks the RAG code — both block the final measured exit-gate number.

## M4 — AI planeaciones

- [ ] **RAG implementation** pending. M4 generation currently runs without retrieval —
      port the M1 Phase B RAG machinery (Fase 6 corpus retrieval + PDA grounding) into
      the tenant-scoped M4 generation service so planeaciones ground on real SEP
      contenido instead of pure model output.

## M5 — Nueva planeación follow-ups

Left open by the twelve-unit alignment (`a4dd883`..`118ad72`). Full context:
`docs/archive/2026-07-25-nueva-planeacion-progress.md`.

- [ ] **Smoke `/planeaciones/nueva` against a live stack.** Never driven end to end —
      Redis + runserver + Celery + `npm run dev`, then `/planeaciones` → Nueva planeación
      → a secundaria group + "Lenguajes" or "Ética, Naturaleza y Sociedades" → Generar
      proyecto → pending → ready. Quota smoke: set
      `LESSON_PLAN_MONTHLY_GENERATION_LIMIT=1` in `backend/.env`, create twice, expect 429.

- [ ] **`Proyecto.Datos` lacks `subject` and the date range** (`core/schema.py`), so
      rendered DOCX/Markdown headers omit them even though the model now receives them.
      Ripples into `core/render/docx.py`, `markdown.py`, `test_render.py`.

- [ ] **Migrate the six remaining hand-rolled selects** to the `Select` primitive, zero
      visual delta: `school-context-filters.tsx` (3), `workspace-switcher.tsx`,
      `schools/school-form.tsx`, `groups/group-form.tsx`, `school-years/page.tsx`,
      `groups/page.tsx`.

- [ ] **Legacy plans render with regenerate disabled and no explanation.** Blank
      `field_id` / null dates predate the create contract, so `lessonPlanCreateInput`
      returns `null`. A one-line hint next to the button would be honest.

- [ ] **Root `.env.example` is not the file Django loads.** `config/settings.py` reads
      `backend/.env`; anyone copying the root file to the root gets nothing.

- [ ] **No refund-on-failure path for quota.** A generation the provider later fails
      still counts. Product decision, flagged not built — refunding needs an
      exactly-once guarantee Celery does not offer.

- [ ] **`find_invented_pdas`' cross-content guard is unreachable** — each catalog field
      has exactly one content. Goes live when a field gains a second.

## M8 — carried in from M5

- [ ] **"Límite alcanzado" modal** (frame `ImG3U`) deliberately unbuilt. Prices per
      **ciclo** ("60 planeaciones por ciclo", "+$1,000") while the backend quota is per
      **month**. Reconcile the period first, then build it; the 429 currently surfaces
      as one inline sentence carrying the server's own limit.


# NEXT FEATURES — AI teacher workflow

## Planeación (extend M4)

- [ ] **RAG grounding** — (see M4 TODO above) ground planeaciones in real NEM programa
      sintético + libros SEP. Kills hallucinated content, cites source page.
- [ ] **Adapt existing plan** — "make this plan for a multigrade group" / "shorten to
      30 min" / "add adequation for a student with dyslexia." One-click variants, no
      regen from scratch.
- [ ] **Weekly/unit sequencer** — generate a coherent multi-week arc, not isolated
      lessons. Each plan aware of the prior ones.

## Evaluación

- [ ] **Rubric generator** — from a planeación, emit a rubric aligned to NEM PDA
      (Procesos de Desarrollo de Aprendizaje).
- [ ] **Feedback drafter** — teacher pastes student work, AI drafts constructive
      feedback the teacher edits. Never auto-grades.
- [ ] **Report-card comments** — "observaciones" per student from raw notes. Big time
      sink, high value.

## Comunicación

- [ ] **Parent message drafts** — behavior/progress note → polite parent-ready message.
      Spanish, tone-controlled.
- [ ] **Translate** — same message to an indigenous language / simplified Spanish for
      parents.

## Admin / carga administrativa (biggest NEM complaint)

- [ ] **Expediente auto-fill** — draft required docs (diagnóstico grupal, informe) from
      attendance + grade data already in the app.
- [ ] **Meeting/CTE summarizer** — paste notes → action items.

## In-context assistant

- [ ] **Chat over own data** — "which students dropped below 7 this month?"
      Natural-language query over their workspace data (RLS-scoped, safe).
- [ ] **Material generator** — worksheets, exit tickets, exam items from a planeación's
      PDAs.

---

**Highest leverage next:** RAG planeaciones (already on roadmap, fixes trust) +
report-card/observaciones drafter (pure time-save, teachers hate it).
