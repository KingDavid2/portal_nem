# Nueva planeación — progress and handoff (archived 2026-07-25)

> **Archived.** Historical record of the twelve-unit alignment, closed at `118ad72`.
> Live status is `docs/roadmap.md` (M5); open work is `docs/TODO.md`
> ("M5 — Nueva planeación follow-ups"). Do not update this file.

Aligning the lesson plan creation flow with the `Nueva planeación — Teacher` screen
(frame `IA35k`) in `designs/teachers.pen`.

Full plan: `~/.claude/plans/align-planeacion-creation-with-quiet-heron.md`.

## State

**All 12 units are committed.** Backend: 6 units, all reviewed, full suite green
(288 backend tests). Frontend: units 7, 8, A, B, 9, 10 and 11 committed.
`/planeaciones/nueva` renders the designed screen end to end — context, ejes,
contenidos/PDAs, summary panel and submit — and `Generar proyecto` POSTs and
lands on `/planeaciones/{id}`, where the existing pending→ready poll takes over.

The tree is **green**: 288 pytest, 147 vitest (29 files), `npx tsc --noEmit`
clean, `npm run lint` at its 1 pre-existing warning (`data-table.tsx:32`,
TanStack Table). The blocking finding that stood between unit 8 and unit 9 is
resolved — see "Units A and B" below.

What is left is the end-to-end smoke in "Verification", which has never been
driven against a live stack.

Its follow-ups now live in `docs/TODO.md`; the milestone-level summary lives in
`docs/roadmap.md` under "M5 progress — Nueva planeación".

| # | Unit | State |
|---|---|---|
| 1 | localize methodology and enrich catalog response | `a4dd883` |
| 2 | persist project context on lesson plans | `e4028b2` |
| 3 | validate catalog-backed generation requests | `7fb3b54` |
| 4 | ground generation on selected catalog PDAs | `57f78e0` |
| 5 | enforce monthly generation quota | `3e46f35` |
| 6 | expose monthly generation quota endpoint | `868be76` |
| 7 | extract shared select primitive | `97c1123` |
| 8 | add choice chip primitive | `f5a17c1` |
| A | type catalog selections in the read schema | `78fb2ea` |
| B | align the client with the create contract | `44d9feb` |
| C | add lesson plan catalog queries | `e371b9f` |
| D | add nueva planeacion form state | `ce587e1` |
| 9 | add nueva planeacion route | `411c707` |
| 10 | add ejes and contenidos selection | `7f0ce04` |
| 11 | add summary panel and submit flow | `118ad72` |
| 12 | ~~route new plan creation to its own page~~ | folded into B and 9 |

Units 9-11 were split into four deliveries, one commit each: the reducer and
its validation/payload helpers (`ce587e1`, already written and green when the
work resumed) came out ahead of the route itself.

## Units A and B — the blocking finding, resolved

The chosen ordering was "fix types first". Both units are committed.

**Unit A — `78fb2ea`.** `cross_cutting_theme_ids` and `content_selections` are
bare `JSONField`s, which drf-spectacular emitted untyped and the generated
client received as `unknown`. Fixed by *declaring* both on
`LessonPlanSerializer` (a `ListField` and `ContentSelectionSerializer(many=True,
read_only=True)`) rather than by `@extend_schema_field` — real DRF fields, so
the read schema now reuses the same `ContentSelection` component as the write
contract. `ContentSelectionSerializer` moved above `LessonPlanSerializer` to
allow it. New `lesson_plans/test_schema.py` asserts the two emitted shapes.

**Unit B — `44d9feb`.** `LessonPlanInput` is now the generated
`LessonPlanCreate`; `asWriteBody` and its obsolete comment are gone.

- New pure helper `lessonPlanCreateInput(plan)` rebuilds a create body from the
  persisted context, so regenerate replays the original request instead of
  approximating it. It returns `null` for rows predating the contract (blank
  `field_id`, null dates) and both regenerate buttons disable on `null`.
- The inline `GenerateForm` is **deleted** with its test — it could not build a
  valid body, so it was dead either way. This is what unit 12 was for.
- The campo filter no longer reads `AVAILABLE_CAMPOS` (whose docstring pointed
  at the since-deleted `core/pdas.py`); options are derived from the loaded
  plans, which is what a filter should offer anyway.

**Loose end unit 9 must close:** the "Nueva planeación" button now does
`router.push('/planeaciones/nueva?group=<id>')` and **that route does not exist
yet** — it 404s until unit 9 lands. The button is still disabled while no group
is selected.

## Units 7 and 8 — review closed

Both committed and green at the time. The tree has since moved on — current
counts live in "State" above; the `tsc` breakage referenced in earlier versions
of this section was the type regen, closed by units A and B.

**Unit 7 — `select.tsx` (`97c1123`).** Pinned to `h-10 rounded-md bg-card px-3
text-sm` — the Pencil geometry (~40px, radius 6), deliberately not `input.tsx`'s
`h-8 rounded-lg`, which had silently shrunk the index selects in an earlier attempt.
Focus-visible, disabled, aria-invalid and dark-mode utilities added on top; none
paint at rest. `disabled:bg-input/50` and `dark:bg-input/30` correctly not adopted.

The open `bg-background` → `bg-card` question was a **real regression** and is fixed.
The index filters live inside a `Card`, which is itself `bg-card` (pure white in
light mode), so the primitive default rendered them white-on-white with only the
border to delimit them. Fixed at the call site, not in the primitive: `SelectField`
in `page.tsx` passes `className="bg-background"`. The primitive keeps the Pencil
default, which is correct for the nueva planeación page's grey surface. Different
surfaces, one primitive, override at the edge.

**Unit 8 — `choice-chip.tsx` (`f5a17c1`).** The three open review questions, answered:

- **`onSelectedChange` and single-select.** Yes, an already-selected chip reports
  `false`. Acceptable, not a defect: the primitive owns no group and cannot enforce
  "one always selected". Escenario call sites ignore the argument and set their own
  id — `onSelectedChange={() => setScenario(id)}`. Documented in the JSDoc.
- **`aria-pressed` on the single flavour.** Honest. Toggle-button semantics, announced
  as "pressed". `role="radio"` outside an owning `radiogroup` would be invalid ARIA
  and strictly worse. The `{...props}` spread lands after the defaults, so a call site
  that does own the group can override.
- **Token mappings, verified against `globals.css`.** `#666CFF` ≈
  `oklch(0.607 0.214 276)` vs `--primary: oklch(0.6082 0.2141 276.21)` — exact.
  `#262B43` ≈ `oklch(0.296 0.044 274)` vs `--foreground: oklch(0.2960 0.0443 274.39)`
  — exact. `#666CFF29` is alpha `0x29` = 16.1% against `bg-primary/15` = 15%, a
  1.1pp delta, imperceptible.

Also cleared earlier: `cn(variants, className)` puts caller `className` last so
tailwind-merge overrides work, and the disabled-click test fails on regression.

## Type regen — done, committed

`schema.yaml` landed with unit A, `schema.d.ts` with unit B. The client now has
`GenerationQuota`, `LessonPlanCreate`, `ContentSelection`, `ScenarioEnum`, the
enriched catalog response and `lesson_plans_quota_retrieve`.

The 4 spectacular errors in `npm run gen:all` output are the pre-existing
`HealthView` "unable to guess serializer" fallback, unrelated.

## What the backend now offers the new screen

`GET /api/lesson-plans/catalog/?group=<id>&field=<field_id>` → `phase`, `grade`,
`field`, `methodology`, `subjects`, `cross_cutting_themes`, `contents[].pdas[]`, plus
new `group` (`id`, `label` like `"3° A"`, `grade`, `school_name`, `school_cct`,
`school_year_label`) and `teacher` (`email`) blocks — everything the "Datos
automáticos" banner needs in one request.

`GET /api/lesson-plans/quota/` → `{"period": "2026-07", "used": 7, "limit": 30,
"remaining": 23}`. Needs `view_workspace`, creates no ledger row.

`POST /api/lesson-plans/` now takes:

```json
{
  "group": 12,
  "field_id": "languages",
  "subject_id": "spanish",
  "methodology_id": "community-based-project-learning",
  "theme": "La independencia contada por la comunidad",
  "context_diagnosis": "El grupo requiere fortalecer la producción escrita.",
  "scenario": "community",
  "duration_weeks": 4,
  "start_date": "2026-01-12",
  "end_date": "2026-02-06",
  "cross_cutting_theme_ids": ["critical-thinking", "inclusion"],
  "content_selections": [
    {"content_id": "languages-text-resources",
     "pda_ids": ["languages-accentuation", "languages-coherent-texts"]}
  ]
}
```

`subject_id` is the only optional key. `campo` and `grade` are server-derived and
ignored if sent. Returns 202 + the pending row, or 429 with
`{"detail", "code": "generation_quota_exceeded", "used", "limit", "period"}`.

Nested errors are indexed: `{"content_selections": [{}, {"pda_ids": ["PDA does not
belong to the selected content."]}]}`.

## Decisions made, do not re-litigate

- Catalog selections stored as **JSON ids** on `LessonPlan`, validated at the write
  boundary — not FK tables. `core/catalog.py` is code, not data; FK tables would need
  a seed migration duplicating the source of truth and an RLS migration per table.
- Quota is an **append-only ledger** per `(workspace, period)`, not a count over
  lesson plans: deriving it would let a teacher delete a plan to win quota back.
- Quota is charged on **accepted** requests. A generation the provider later fails
  still counts. Refunding needs an exactly-once guarantee Celery does not offer.
- `core/pdas.py` deleted — it was a second copy of the curriculum text keyed by
  display name. The separate top-level `lesson_plans/` RAG package keeps its own
  independent copy; that is out of scope.
- Methodology scoped to ABP Comunitario only. `"ABP Comunitario"` is a frontend
  display alias for the catalog's `"Aprendizaje Basado en Proyectos Comunitarios"`.
- Technical artifacts in English; UI copy in Spanish, verbatim from the design.
- Each unit ≤400 authored changed lines, own tests, own Conventional Commit, reviewed
  before committing.

## Design gaps accepted

- **Docente** in the banner renders the user's email — `users.models.User` has no
  display name. Adding one is a separate change.
- `scientific-thinking` and `human-community` have no verified contenidos. They stay
  selectable with an honest empty state ("Aún no hay contenidos verificados para este
  campo.") and a disabled CTA. The write contract already rejects them, cleanly, with
  a 400.
- `"3 fases · 11 momentos"` in the summary panel is a UI constant of the ABPC
  skeleton (`core/generation.py:16`), not derived data.
- The design's **"Límite alcanzado" modal (frame `ImG3U`) was deliberately not
  built.** It is a billing surface — "Docente Pro · 60 planeaciones por ciclo",
  "+$1,000", "Mejorar plan" — with no endpoint behind it, and its per-**ciclo**
  limit contradicts the backend, whose quota is per **month**
  (`GenerationUsage.period` is the first of the month). Building it would put a
  price and a period on screen that nothing can honour. The 429 is surfaced
  instead as one inline sentence carrying the server's own `limit`: *"Ya usaste
  tus {limit} generaciones de este mes. El contador se reinicia el próximo mes."*
  Whoever reconciles ciclo-vs-month owns that modal.
- **"Falta por completar"** in the summary panel is not in the design. The plan
  called for field errors shown "after attempted submit", but the CTA is disabled
  while the form is incomplete, so that submit can never happen — the flag was
  dead code. The panel lists the outstanding requirements from
  `validateNewPlanForm` as pending steps instead of colouring a pristine form red.
- The quota meter's progress bar is hand-rolled (`role="progressbar"` + a filled
  child div). `components/ui/` has no progress primitive; one use does not justify
  inventing one.

## Follow-ups found along the way, not done

- `Proyecto.Datos` (`core/schema.py`) still lacks `subject` and the date range, so
  rendered DOCX/Markdown headers omit them even though the model now receives them.
  Ripples into `core/render/docx.py`, `markdown.py`, `test_render.py`.
- The repo-root `.env.example` is **not** the file Django loads —
  `config/settings.py` reads `backend/.env`. Anyone copying the root file to the root
  gets nothing.
- `find_invented_pdas`' cross-content guard is currently unreachable: each catalog
  field has exactly one content. It goes live when a field gains a second.
- Legacy plans (blank `field_id`, null dates) render with regenerate disabled and
  no explanation of why. A one-line hint next to the button would be honest.
- Six more files hand-roll the same select styling and would now migrate to the
  primitive with zero visual delta: `school-context-filters.tsx` (3 instances),
  `workspace-switcher.tsx`, `schools/school-form.tsx`, `groups/group-form.tsx`,
  `school-years/page.tsx`, `groups/page.tsx`.
- ~~`ContenidoCard`'s content-level checkbox has an inert `onChange={() => {}}`.~~
  Done in unit 10: `contents-picker.tsx` passes `selected={pdaIds.length > 0}` and
  leaves the checkbox inert, so content selection is derived from "≥1 PDA checked",
  matching the backend contract where a content with no PDAs is invalid.
- No refund-on-failure path for quota. Product decision, flagged not built.

## Verification

```bash
cd backend
uv run manage.py migrate            # local dev DB; the suite runs migrate --check
uv run pytest -q                    # 288 passed
uv run manage.py makemigrations lesson_plans --check --dry-run

cd frontend
npm run gen:all                     # regenerate schema.yaml + schema.d.ts
npm test && npm run lint && npx tsc --noEmit   # 147 passed (29 files)

# drive it
redis-server
cd backend && uv run manage.py runserver
cd backend && uv run celery -A config worker -l info
cd frontend && npm run dev
# Walkthrough — drivable since 411c707. Never yet run against a live stack;
# everything below unit 11 is verified only by vitest.
# /planeaciones -> Nueva planeación -> pick a secundaria group and either
# "Lenguajes" or "Ética, Naturaleza y Sociedades" (the two fields with verified
# contenidos) -> Generar proyecto -> /planeaciones/{id}, pending -> ready
```

Quota smoke without waiting a month: set `LESSON_PLAN_MONTHLY_GENERATION_LIMIT=1` in
`backend/.env`, create twice, expect 429 and "1 de 1" in the side panel.
