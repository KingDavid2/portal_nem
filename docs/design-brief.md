# portal_nem — Design Brief

> Administrative school platform for Mexico, aligned to the **Nueva Escuela Mexicana (NEM)**.
> Teachers and principals record student **grades** and **attendance**; future: AI-generated **planeaciones** (lesson plans).
> Status: greenfield. This brief captures architecture decisions made in design discussion, before code.

---

## 1. Domain — Nueva Escuela Mexicana (NEM)

NEM is not generic grading. It shapes the schema directly:

- **Evaluación formativa** — qualitative observations + numeric boleta (5–10 scale for primaria/secundaria).
- **3 periodos** trimestrales (not semesters).
- **4 campos formativos**: Lenguajes · Saberes y Pensamiento Científico · Ética Naturaleza y Sociedades · De lo Humano y lo Comunitario.
- **Niveles**: preescolar / primaria / secundaria — different rules each.
- **Fases 1–6** (phase-based, not grade-based): F2 preescolar · F3 1º-2º prim · F4 3º-4º · F5 5º-6º · F6 secundaria.
- **CURP** — 18-char national person ID, natural key for a student.
- **SEP/SIGED boleta** — eventual export target; design boleta as an exportable report from day one.
- **Planeaciones** (future AI): 7 ejes articuladores + PDA (Procesos de Desarrollo de Aprendizaje), sourced from official SEP curriculum.

---

## 2. Tenancy — personal + shared workspaces

Model is **Notion/GitHub-style workspaces**, NOT rigid school-as-tenant. Users are standalone by default and opt into shared groups.

- Every resource lives in exactly **one** `Workspace`. `type = personal | group`.
- **Personal workspace** auto-provisioned per user, transactionally at signup. Single-owner, non-shareable in v1.
- **Group workspace** created explicitly; members (Teacher A + Teacher B + Principal A) share students, grades, planeaciones.
- `Membership(user, workspace, role)`; roles `owner | admin | member`. Principal → admin, teacher → member.
- `workspace_id` is the tenancy key on **every** resource.
- **"Everything is a workspace"** — one uniform access path, no null-branching between personal/owned resources.

### Access & isolation (defense in depth)

- **App-level** workspace-scoped QuerySet/Manager = primary, review-visible mechanism.
- **Postgres RLS** = backstop. Set `app.workspace_id` via `set_config('app.workspace_id', id, true)` / `SET LOCAL` **inside the per-request transaction** (pool-safe; plain `SET` leaks across pooled connections).
- RLS policies shipped as **Django migrations**. App must connect as a **non-owner, non-`BYPASSRLS`** Postgres role.
- **Authorization** (can this role do X) routed through a single **capability matrix** / `has_permission(membership, action)` — never scattered inline role-string checks. Distinct from RLS **isolation** (can this session see workspace Y at all).
- Roles stored as `CharField choices`, not a DB enum type → future `tutor`/`viewer` = one-line addition.

### Sharing = move-based

- Sharing a resource = **move** it into a group workspace (no multi-share in v1).
- Denormalized `workspace_id` on every child table (Grade, Attendance), cascade-updated in one transaction on move → keeps every RLS policy the same trivial shape.
- Append-only **`workspace_history`** audit table: `resource_type, resource_id, from_workspace_id, to_workspace_id, moved_by, moved_at`.

### Invitations

- `WorkspaceInvitation(workspace, email, role, invited_by, token, status[pending|accepted|expired|revoked], created_at, expires_at)`.
- **Explicit accept** (not auto-join) — matters for student PII. On signup, match verified email to pending invites AND auto-provision personal workspace (both).

### Locked decisions

- ✅ "Everything is a workspace" — confirmed.
- ✅ Personal workspaces single-owner, non-shareable in v1 (structurally enforced, not convention).
- ✅ **No CURP uniqueness constraint in v1.** No `UNIQUE(workspace_id, curp)` yet → no move-collision to handle. Duplicate student rows tolerated. Add uniqueness + merge UX later when group convergence matters. (CURP lives on `Student`, out of scope for the tenancy slice regardless.)

---

## 3. Stack

**Two services: Django API + Next.js frontend.** Django serves no end-user HTML; every user-facing screen is Next.js.

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | **Django + DRF**, API-only | ORM fit for relational school model; admin panel for internal ops; DRF is the single API surface, Next.js its only consumer |
| Async | **Celery** | lesson-plan generation and report-card PDF export are long-running — jobs, not held HTTP requests |
| DB | **PostgreSQL + pgvector** | RLS tenancy; pgvector for RAG corpus of official SEP curriculum, queried in-process by Django |
| LLM | **self-hosted vLLM** on ASUS Ascent GX10 (GB10 Grace-Blackwell, 128GB unified, ARM64), OpenAI-compat endpoint | called directly from Django/Celery behind an `LLMProvider` port (`ClaudeProvider` \| `OpenAICompatProvider`) — vLLM/Claude swap by config; dev via Ollama |
| Frontend | **Next.js (App Router) + TS + Tailwind + shadcn/ui + TanStack Query/Table** | attendance, grades and activities are spreadsheet-style bulk-entry grids; lesson plans stream into an editable draft |
| Style | modular monolith | Screaming apps + Hexagonal ports at real boundaries; atomic design + container-presentational on the frontend |

### No separate AI service

An earlier draft placed a FastAPI service between Django and the model. Dropped:

- vLLM already exposes an OpenAI-compatible HTTP endpoint — that *is* the service. A FastAPI layer in front of it is a pass-through hop.
- Pydantic and `instructor` are libraries, not a reason for a service. They import fine inside Django.
- The real concern — long LLM calls starving request workers — is solved by Celery, not by another service.
- RAG retrieval is a pgvector query against the same Postgres Django already connects to, so it is a queryset, not a network call.

**Revisit if** Django ends up cloud-hosted in an MX region for PII residency while the GX10 sits on-prem. A thin service next to the GPU makes sense then, and not before.

### Architecture style — scope

- **Screaming**: Django apps named by domain — `workspaces`, `students`, `attendance`, `grades`, `lesson_plans`, `report_cards` — not `models/`, `views/`, `serializers/`. Name apps after the domain concept, never the screen (`grades`, not `grade_entry_form`) — screens change, concepts do not.
- **Hexagonal ports at real boundaries only**: `LLMProvider`, report-card PDF export, payments, SEP corpus ingestion. These have genuine swappable adapters.
- **No repository layer over the ORM** for school CRUD. Django's ORM is active-record; wrapping it discards querysets and the admin — the reasons Django was chosen. There is no second persistence adapter coming.
- **Atomic design + container-presentational** apply to the Next.js app.

### Naming — English codebase, Spanish product

**All code identifiers are English**: Django apps, models, fields, services, API payload keys, TS types, functions, variables. UI labels and copy stay Spanish — end users are Mexican NEM teachers. A form input labeled "Apellido paterno" binds to `last_name_paternal`.

Domain glossary — the canonical translation, use it consistently:

| NEM / Spanish | Code |
|---|---|
| alumno | `student` |
| asistencia | `attendance` |
| calificación | `grade` |
| actividad | `activity` |
| planeación | `lesson_plan` |
| boleta | `report_card` |
| escuela | `school` |
| grupo | `group` |
| ciclo escolar | `school_year` |
| periodo | `term` |
| campo formativo | `formative_field` |
| eje articulador | `articulating_axis` |
| fase | `phase` |
| nivel | `level` |

**Not translated — government/SEP acronyms, treated as proper nouns**: `CURP`, `PDA`, `SEP`, `SIGED`, `NEM`. These are the official identifiers in SEP source documents; translating them breaks the trace back to the curriculum.

Since the translations above are lossy (`lesson_plan` is the NEM artifact built from ejes + PDAs, not a generic lesson plan; `report_card` is the SEP-format boleta), each app's module docstring must state the NEM term it implements.

### Frontend seam — non-negotiables

- **Auth**: httpOnly session cookie on a shared parent domain (`api.*` / `app.*`), CORS with credentials, CSRF enabled. Not JWT in localStorage — student PII must not be readable by XSS.
- **Types**: DRF → OpenAPI (`drf-spectacular`) → generated TS client, wired into CI from day one. Manual codegen rots and frontend types become lies.
- **Admin**: Django admin stays, staff-only, restricted at the network/SSO layer. Internal ops surface, not a user surface.

### AI lesson plans (future) — RAG, not raw prompt

PDAs and articulating axes are fixed official text. Model must **retrieve real PDA** from embedded SEP corpus (pgvector), then only sequence activities around it. Human-in-loop always: AI = draft, teacher edits + approves. Corpus = global (public curriculum); generated lesson plans = workspace-scoped. Track cost/tokens per generation.

---

## 4. Build order

1. **Auth + RBAC + workspace/membership tenancy** ← current slice (first SDD proposal)
2. Escuela → ciclo → grupo → alumno CRUD (CURP as field)
3. Attendance (daily grid)
4. Grades (campos formativos + periodos + observaciones)
5. Boleta PDF export
6. AI planeaciones (RAG over SEP corpus) — future
7. Tutor/parent read-only portal — future

---

## 5. Slice 1 scope — tenancy foundation (in progress)

**In**: User + auth · `Workspace` (+ personal auto-provisioning) · `Membership` + capability matrix · `WorkspaceInvitation` + invite/accept · workspace-scoped base manager + DRF permission class + RLS migration scaffolding · move-between-workspaces service · `workspace_history` audit.

**Out (explicit)**: NEM domain models (Student/Grade/Attendance/Planeacion) · boleta export · AI planeaciones · frontend · CURP uniqueness/merge · personal-workspace sharing.

**Acceptance gates**:
- Signup transactionally creates user + personal workspace + owner membership.
- Cross-tenant leak test proves QuerySet + RLS both deny foreign-workspace reads **under connection pooling**.
- App verified connecting as non-owner, non-`BYPASSRLS` role.
- Invitation issue/accept/expire/revoke lifecycle works; accept explicit.
- Move service cascades `workspace_id` + writes `workspace_history`.
- All authorization routes through `has_permission`.

---

## 6. Open questions (for design phase)

- Auth mechanism: token (JWT) vs session — deferred to `sdd-design`.
- RLS `SET LOCAL` wiring: middleware + `contextvars` vs custom DB backend/cursor wrapper.
- Exact `workspace_history` schema fields + its own RLS scoping.
- Whether invitation email-match requires a verified email before linking.

---

## 7. Known risks

- **`SET LOCAL` discipline** — plain `SET` leaks tenants across pooled connections. Needs an active leak test, not just review.
- **Celery workers bypass request middleware** — background jobs (planeación generation, boleta export) never pass through the middleware that sets `app.workspace_id`, so they run with no workspace context. Every task must establish it explicitly, and the fail-closed sentinel must be verified for the worker path too. This is the classic leak route once async work exists.
- **Managed Postgres (RDS) roles** may bypass RLS even when not nominally superuser — verify the app role.
- **Data residency** — student PII + SEP data may require MX-hosted infra; verify before committing cloud region (could force cloud choice and rule out US LLM APIs → reinforces self-hosted vLLM).
- **Engram persistence** — MCP `mem_*` tools not exposed in current session; SDD artifacts held in-conversation + this brief until wired.
