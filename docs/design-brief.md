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

| Layer | Choice | Why |
|-------|--------|-----|
| Core backend | **Django + DRF** | ORM fit for relational school model, free admin panel for school ops, DRF permissions map to workspace roles |
| AI service | **FastAPI** (separate) | async/streaming, Pydantic, `instructor` for schema-locked output; isolated at a clean HTTP seam |
| DB | **PostgreSQL + pgvector** | RLS tenancy; pgvector for RAG corpus of official SEP curriculum |
| LLM | **self-hosted vLLM** on ASUS Ascent GX10 (GB10 Grace-Blackwell, 128GB unified, ARM64), OpenAI-compat endpoint | behind `LLMProvider` interface (`ClaudeProvider` \| `OpenAICompatProvider`) — vLLM/Claude swap by config; dev via Ollama |
| Frontend | **Next.js (App Router) + TS + Tailwind + shadcn/ui + TanStack Query/Table** | data-grid-heavy grade/attendance entry |
| Style | modular monolith core + isolated FastAPI AI | Clean/Hexagonal/Screaming architecture, atomic design, container-presentational |

### AI planeaciones (future) — RAG, not raw prompt

PDAs and ejes are fixed official text. Model must **retrieve real PDA** from embedded SEP corpus (pgvector), then only sequence activities around it. Human-in-loop always: AI = draft, teacher edits + approves. Corpus = global (public curriculum); generated planeaciones = workspace-scoped. Track cost/tokens per generation.

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
- **Managed Postgres (RDS) roles** may bypass RLS even when not nominally superuser — verify the app role.
- **Data residency** — student PII + SEP data may require MX-hosted infra; verify before committing cloud region (could force cloud choice and rule out US LLM APIs → reinforces self-hosted vLLM).
- **Engram persistence** — MCP `mem_*` tools not exposed in current session; SDD artifacts held in-conversation + this brief until wired.
