# portal_nem

Administrative school platform for Mexico, aligned to the **Nueva Escuela Mexicana (NEM)**.

Teachers and principals record student **grades** and **attendance**. Future scope adds AI-generated **planeaciones** (lesson plans) grounded in the official SEP curriculum.

> **Status:** greenfield. No application code yet — the repository currently holds design artifacts only.

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
| AI service | FastAPI (separate) |
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
| `docs/design-brief.md` | Full architecture brief — domain, tenancy, stack, risks |
| `designs/` | Pencil (`.pen`) UI design files |
| `.atl/` | Tooling metadata |

## Getting started

There is no runnable application yet. Start with [`docs/design-brief.md`](docs/design-brief.md) for the architecture decisions behind the first slice.
