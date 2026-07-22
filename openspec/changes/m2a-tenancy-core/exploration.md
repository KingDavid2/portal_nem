# Exploration — m2a-tenancy-core

> SDD phase: sdd-explore. Persisted by the orchestrator (the explore sub-agent had no write
> tools). Source of record also in Engram topic `sdd/m2a-tenancy-core/explore`.

## What

Explored M2a (Django scaffold + tenancy core, deliveries D1–D9 of `docs/design-brief.md` and
`plan-for-milestone-2-zesty-candle.md`). Exploration only — no code changes.

## Why

First real Django backend for portal_nem. Confirm the plan is proposal-ready and surface open
design questions before `sdd-propose` / `sdd-design`.

## Where (areas to be created)

- `config/` — Django settings (`ATOMIC_REQUESTS=True`, DRF, drf-spectacular, pgvector Postgres).
- `users/` app — custom email user; `AUTH_USER_MODEL` set **before first migration**; session-cookie auth.
- `workspaces/` app — `Workspace`, `Membership`, transactional signup provisioning, workspace-scoped
  manager + contextvar, capability matrix, RLS middleware, RLS `RunSQL` migration, restricted app
  Postgres role.
- `README.md` stack table (line ~33) still lists the **dropped FastAPI** service — fix in D1.
- No `openspec/` directory existed in the repo before this change (scaffolded by the orchestrator now).

## Learned

1. **Session-cookie auth is LOCKED** (not actually open), per brief §3 non-negotiable + plan D2.
   Brief §6 lists it as "deferred", but the plan supersedes.
2. **contextvars + middleware** (not a custom DB backend) is the locked wiring approach. Open
   sub-detail: how the **active workspace** is chosen when a user has multiple memberships
   (request header / session / URL) — resolve in `sdd-design`.
3. **BYPASSRLS verification:** `SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user`
   while connected as the app role — direct, cheap test.
4. **Connection-pooling leak test (D9):** recommended approach is *simulated* connection reuse
   (same connection/cursor, two workspace contexts, `SET` vs `SET LOCAL` as negative/positive
   control) rather than standing up real PgBouncer — lower cost, still exercises the exact
   `set_config(..., true)` code path. Real PgBouncer is a CI-hardening follow-up, not blocking.
5. **M0/M1 are separate uv packages** at repo root (hatchling build, `pytest testpaths=["tests"]`).
   Their LLM code does **not** carry into M2a — only tooling conventions (uv, pytest, dataclass
   `Config.from_env` pattern). M2a likely needs its own project layout / uv package (name + repo-root
   vs `backend/` subdir TBD in `sdd-design`, given a future Next.js service = two services).

## Open questions for propose/design

- **(a)** Session vs token auth → session-cookie (already leaning locked).
- **(b)** contextvars middleware wiring detail + active-workspace resolution across memberships.
- **(c)** Two-Postgres-role setup + how to verify BYPASSRLS absence in a test.
- **(d)** Connection-pooling setup for the leak test (simulated reuse vs real pooler).
- **(e)** Project layout: repo-root vs `backend/` subdir; uv package name.

## Risks

- `SET LOCAL` vs `SET` pooling leak (brief §7) — the gate that matters; needs an active negative control.
- Managed-Postgres role BYPASSRLS must be verified in the real CI/deploy Postgres, not only locally.
- `AUTH_USER_MODEL` sequencing is irreversible — D2 must land before any auth-adjacent migration.
- Celery bypass is out of M2a scope (M2b), but the fail-closed sentinel design should anticipate it.

## Next

`sdd-propose`.
