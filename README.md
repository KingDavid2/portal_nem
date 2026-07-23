# portal_nem

Administrative school platform for Mexico, aligned to the **Nueva Escuela Mexicana (NEM)**.

Teachers and principals record student **grades** and **attendance**, and generate AI **planeaciones** (lesson plans) grounded in the official SEP curriculum.

> **Status:** active build — not production-ready. Milestone progress and what
> is shipped vs. pending live in [`docs/roadmap.md`](docs/roadmap.md), the
> single source of truth. See [`backend/README.md`](backend/README.md) to run
> and test the API.

## Domain

NEM shapes the data model directly:

- **Evaluación formativa** — qualitative observations plus a numeric boleta (5–10 scale for primaria/secundaria).
- **3 periodos** trimestrales.
- **4 campos formativos** — Lenguajes · Saberes y Pensamiento Científico · Ética Naturaleza y Sociedades · De lo Humano y lo Comunitario.
- **Niveles** — preescolar, primaria, secundaria, each with distinct rules.
- **Fases 1–6** — phase-based rather than grade-based.
- **CURP** — 18-character national person ID, the natural key for a student.
- **Boleta** — designed as an exportable report from day one, targeting SEP/SIGED.

## Tenancy

Notion/GitHub-style workspaces, not school-as-tenant. Every resource belongs to exactly one `Workspace` (`personal` or `group`), keyed by `workspace_id`. Personal workspaces are auto-provisioned at signup; group workspaces are created explicitly and shared through `Membership(user, workspace, role)`.

Isolation is defense in depth: workspace-scoped querysets at the application layer, Postgres RLS as a backstop. Authorization routes through a single capability matrix.

## Stack

| Layer | Choice |
|-------|--------|
| Core backend | Django + DRF |
| Database | PostgreSQL + pgvector |
| LLM | Self-hosted vLLM behind an `LLMProvider` interface |
| Frontend | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui |

Architecture style: modular monolith core with an isolated FastAPI AI service at a clean HTTP seam.

## Build order

Work is sliced into numbered milestones. The ordering principle: tenancy first
(every later model is workspace-scoped), then school structure, then the
daily-use teaching surfaces. From M3 onward each milestone ships its API and its
Next.js screens in the same slice rather than deferring the frontend to a
trailing phase — the daily-use value *is* the UI.

**[`docs/roadmap.md`](docs/roadmap.md) holds the milestone list and their
current state.** It is the single source of truth; this README deliberately does
not duplicate it.

## Repository layout

| Path | Contents |
|------|----------|
| `backend/` | Django + DRF core backend (runnable — see its README) |
| `frontend/` | Next.js (App Router) web client |
| `docs/design-brief.md` | Full architecture brief — domain, tenancy, stack, risks |
| `openspec/` | Spec-driven change proposals, specs, and archived designs |
| `designs/` | Pencil (`.pen`) UI design files |
| `.atl/` | Tooling metadata |

## Getting started

Prerequisites: PostgreSQL + pgvector, Redis (Celery broker/result backend),
Node.js, and [`uv`](https://docs.astral.sh/uv/).

### 1. Backend (Django API)

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver   # http://localhost:8000
```

Run the test suite with `uv run pytest`.

### 2. Celery worker (lesson-plan generation)

Lesson-plan generation runs asynchronously, so a worker is required for those
endpoints to complete. From `backend/`, in a separate terminal:

```bash
uv run celery -A config worker -l info
```

The broker and result backend default to `redis://localhost:6379/0`; override
with `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`. Under pytest, tasks run
eagerly and no worker is needed.

### 3. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

The client calls `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.

Full backend prerequisites (env config, DB roles, RLS setup) are in
[`backend/README.md`](backend/README.md). For the architecture behind the
current slice, read [`docs/design-brief.md`](docs/design-brief.md).
