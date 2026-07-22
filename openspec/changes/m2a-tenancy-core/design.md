# Design: M2a — Tenancy Foundation Core

## Technical Approach

Defense-in-depth tenancy (brief §2). Primary, review-visible mechanism: a workspace-scoped
base manager reading an active-workspace `contextvar`, fail-closed. Backstop: Postgres RLS keyed
on `current_setting('app.workspace_id', true)`, set via `SET LOCAL` inside the `ATOMIC_REQUESTS`
transaction (pool-safe). Authorization (`can-do-X`) is a separate capability matrix, distinct from
isolation (`can-see-workspace-Y`). All locked decisions honored: session-cookie auth,
contextvars+middleware (no custom DB backend), no repository layer, screaming apps, roles as
`CharField` choices.

## Architecture Decisions

### D-1: Project layout & uv package
**Choice**: `backend/` subdirectory; uv project `portal-nem-backend`, package `config` +
apps at `backend/` root; settings module `config.settings`; `backend/manage.py`.
**Alternatives**: repo-root Django (rejected — collides with future `frontend/` Next.js service,
brief §3 "two services"); single-package src-layout (rejected — Django convention is app dirs).
**Rationale**: two-service repo needs a clean backend boundary; M0/M1 spikes stay untouched at root.

### D-2: Active-workspace resolution
**Choice**: `X-Workspace-Id` request header, validated against the authenticated user's
`Membership` set. Missing header → fall back to the user's **personal** workspace. Header present
but not a member → **403 fail-closed** (never silent fallback when a workspace is explicitly named).
Unauthenticated → no context set; sentinel denies all scoped rows.
**Alternatives**: URL path prefix (rejected — couples every route to tenancy, leaks into frontend
routing); server-side "current workspace" in session (rejected — stateful, breaks API idempotency,
harder to test). **Rationale**: header is stateless, explicit, trivially testable; personal-workspace
fallback matches "everything is a workspace" default. No server-remembered current workspace in M2a;
the frontend owns selection and sends the header.

### D-3: contextvars + middleware wiring
**Choice**: module-level `contextvar` in `workspaces/context.py`. `TenancyMiddleware` runs
*inside* the request cycle: resolve membership → `active_workspace.set(ws_id)` → within the
open ATOMIC_REQUESTS txn issue `set_config('app.workspace_id', str(ws_id), True)` → response →
`active_workspace.reset(token)` in `finally`. DRF auth resolves the user before this via
`request.user`; middleware reads it. See sequence below.
**Alternatives**: custom DB backend/cursor wrapper (rejected — locked out by brief §6 + config).
**Rationale**: contextvar reset per request prevents leakage across the worker's reused context;
`SET LOCAL` (`is_local=True`) auto-clears at txn end — double safety under pooling.

### D-4: Two Postgres roles
**Choice**: owner/migration role (`DATABASES['default']` used by `migrate`, DDL, RLS policy
creation, table ownership) vs runtime app role `portal_app` (`NOSUPERUSER NOBYPASSRLS`, only
table/sequence `GRANT`s). Runtime connection uses the app role; migrations run as owner via an
env-switched `DATABASE_URL` (or a `migrate` settings override). Test asserts
`SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user` returns `false`.
**Alternatives**: single superuser role (rejected — bypasses RLS, defeats backstop).
**Rationale**: RLS is only enforced against non-owner non-BYPASSRLS roles; owner writes policies.

### D-5: Connection-pooling leak test
**Choice**: simulated reuse — one connection/cursor, two workspace contexts in sequence.
Positive control: `set_config(..., True)` (SET LOCAL) inside a txn, assert context does **not**
survive into the next txn on the same connection → foreign rows denied. Negative control: plain
`set_config(..., False)` (session SET) → context leaks → proves the test can detect a leak.
Assert scoped QuerySet AND raw RLS both deny foreign-workspace reads.
**Alternatives**: real PgBouncer harness (deferred — CI-hardening follow-up; higher cost, same
code path). **Rationale**: exercises the exact `set_config(..., true)` path cheaply with an active
negative control (the failure mode brief §7 flags).

## Data Flow — request → RLS → query

    DRF request (session cookie, X-Workspace-Id)
      │ auth → request.user
      ▼
    TenancyMiddleware (inside ATOMIC_REQUESTS txn)
      │ resolve Membership → active_workspace.set(id) [token]
      │ SET LOCAL app.workspace_id = id   (set_config(..., True))
      ▼
    View → ScopedManager.get_queryset()
      │ reads active_workspace.get(SENTINEL) → filter(workspace_id=…)
      ▼
    Postgres: RLS USING (workspace_id = current_setting('app.workspace_id',true)::uuid)
      ▼
    response → finally: active_workspace.reset(token); txn commit clears SET LOCAL

Two independent gates deny foreign rows: the app filter and the RLS policy.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/pyproject.toml`, `manage.py` | Create | uv project `portal-nem-backend`, Django entrypoint |
| `backend/config/settings.py`, `urls.py`, `wsgi.py` | Create | ATOMIC_REQUESTS, DRF, spectacular, two-role DB, pgvector |
| `backend/users/` | Create | Custom email `User`, `AUTH_USER_MODEL`, session auth |
| `backend/workspaces/models.py` | Create | `Workspace`, `Membership`, `ScopedModel` base |
| `backend/workspaces/context.py` | Create | `active_workspace` contextvar + `WORKSPACE_UNSET` sentinel |
| `backend/workspaces/managers.py` | Create | `ScopedQuerySet`/`ScopedManager` fail-closed |
| `backend/workspaces/middleware.py` | Create | `TenancyMiddleware` |
| `backend/workspaces/permissions.py` | Create | capability matrix + `has_permission` + DRF class |
| `backend/workspaces/services.py` | Create | transactional signup provisioning |
| `backend/workspaces/migrations/000X_rls.py` | Create | `RunSQL` policies + reverse |
| `README.md` | Modify | Remove dropped FastAPI row from stack table |

## Interfaces / Contracts

```python
# context.py
WORKSPACE_UNSET = object()                      # fail-closed sentinel
active_workspace: ContextVar = ContextVar("active_workspace", default=WORKSPACE_UNSET)

# managers.py — sentinel denies ALL rows when no context (request or future Celery)
def get_queryset(self):
    ws = active_workspace.get()
    if ws is WORKSPACE_UNSET:
        return super().get_queryset().none()    # fail-closed, not error
    return super().get_queryset().filter(workspace_id=ws)

# permissions.py — matrix is a dict[role -> frozenset[action]]
CAPABILITIES = {"owner": {...}, "admin": {...}, "member": {...}}
def has_permission(membership, action: str) -> bool:
    return action in CAPABILITIES.get(membership.role, frozenset())

# models.py — roles stay CharField choices (future tutor/viewer = one line)
class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner"; ADMIN = "admin"; MEMBER = "member"
    role = models.CharField(max_length=20, choices=Role.choices)
```

RLS policy shape (per scoped table):
```sql
ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
CREATE POLICY ws_isolation ON <t> USING
  (workspace_id = current_setting('app.workspace_id', true)::uuid)
  WITH CHECK (workspace_id = current_setting('app.workspace_id', true)::uuid);
```
`, true` (missing_ok) → no context yields NULL → predicate false → deny (fail-closed).

The sentinel is an object identity (not `None`/`0`) so it never collides with a real workspace id
and generalizes to the M2b Celery task-context path (task sets/resets the same contextvar).

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | sentinel `.none()`; `has_permission` matrix; header resolution/403 | pytest, no DB context set |
| Integration | signup atomicity; middleware sets/reset contextvar + SET LOCAL | Django test client, txn assertions |
| Integration | RLS deny via raw cursor; `rolbypassrls=false` as app role | connect as `portal_app` |
| E2E-ish | cross-tenant leak under simulated pooling (D9) | one connection, two contexts, SET vs SET LOCAL controls |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. Tenancy isolation is enforced at the ORM/DB layer, covered above.

## Migration / Rollout

RLS migration is reversible `RunSQL` (reverse drops policies + `DISABLE ROW LEVEL SECURITY`).
`AUTH_USER_MODEL` is irreversible once the first migration runs → D2 must precede any
auth-adjacent migration; rollback for the greenfield DB is drop-and-remigrate.

## Open Questions

None blocking. Real-PgBouncer CI hardening and M2b Celery task-context wiring are deferred by design.
