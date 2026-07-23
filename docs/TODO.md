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

- [ ] **Run the judge scorecard.** `eval/lift.py` scores each planeación with Claude as an
      LLM-judge, but needs `ANTHROPIC_API_KEY` (absent from env). Set the key, then run
      `python -m lesson_plans.eval.lift` to get the baseline-vs-RAG fidelity table.

Neither blocks the RAG code — both block the final measured exit-gate number.

## M4 — AI planeaciones

- [ ] **RAG implementation** pending. M4 generation currently runs without retrieval —
      port the M1 Phase B RAG machinery (Fase 6 corpus retrieval + PDA grounding) into
      the tenant-scoped M4 generation service so planeaciones ground on real SEP
      contenido instead of pure model output.
