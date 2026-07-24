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
