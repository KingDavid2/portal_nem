# portal_nem

Administrative school platform for Mexico, aligned to the **Nueva Escuela Mexicana (NEM)**.

Teachers and principals record student **grades** and **attendance**. Future scope adds AI-generated **planeaciones** (lesson plans) grounded in the official SEP curriculum.

> **Status:** early build. The Django backend tenancy foundation (auth, workspaces, RBAC, RLS) is implemented under [`backend/`](backend/). See [`backend/README.md`](backend/README.md) to run and test it.

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

1. Auth + RBAC + workspace/membership tenancy ← current slice
2. Escuela → ciclo → grupo → alumno CRUD
3. Attendance (daily grid)
4. Grades (campos formativos, periodos, observaciones)
5. Boleta PDF export
6. AI planeaciones (RAG over the SEP corpus)
7. Tutor/parent read-only portal

## Repository layout

| Path | Contents |
|------|----------|
| `backend/` | Django + DRF core backend (runnable — see its README) |
| `docs/design-brief.md` | Full architecture brief — domain, tenancy, stack, risks |
| `openspec/` | Spec-driven change proposals, specs, and archived designs |
| `designs/` | Pencil (`.pen`) UI design files |
| `.atl/` | Tooling metadata |

## Getting started

Run and test the backend:

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run pytest
```

Full prerequisites (Postgres + pgvector, env config, DB roles) are in
[`backend/README.md`](backend/README.md). For the architecture behind the
current slice, read [`docs/design-brief.md`](docs/design-brief.md).
