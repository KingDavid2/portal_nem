# Proposal: Quizzy P4 — MCP server over the scoped API

## Intent

A workspace is reachable only through bespoke DRF endpoints driven by a browser session. Quizzy's chat surface (`designs/quizzy.pen`) and every future integration need **one typed, scoped door**. P4 opens it read-only, without weakening tenancy.

The MCP process, like the Celery worker, **never runs `TenancyMiddleware`**. Every tool must resolve its workspace from the authenticated caller and enter `workspace_scope()` itself.

## Scope

### In Scope
- New Django app **`backend/mcp_server/`** (not `mcp/` — see Approach) with a transport-agnostic sync tool registry.
- Hashed per-membership **API token** model + resolver (`identity-auth`); P0 finding 7 rules out session auth here.
- Five read-only tools: `list_groups`, `list_lesson_plans`, `get_lesson_plan`, `get_quota`, `search_catalog`.
- stdio transport via a `manage.py` command; **Streamable-HTTP mount behind a flag, default off**.
- Fail-closed cold-context tenancy tests mirroring `test_tasks.py` (no scope → zero rows).

### Out of Scope
- Mutation tools (P5), the Quizzy web chat UI, HTTP-arm throttling (P6), anything from P3.
- RAG / pgvector — locked non-goal.

## Capabilities

### New Capabilities
- `mcp-tool-surface`: tool registry, the five read-only tools, transports, and their payload contracts.

### Modified Capabilities
- `tenancy-isolation`: add an MCP-surface sibling to *"Celery Generation Tasks Must Establish Their Own Workspace RLS Context"*.
- `identity-auth`: add hashed API-token authentication alongside session-cookie auth.
- `authorization`: extend the capability-map requirement to MCP tools.

## Approach

| Decision | Rationale |
|---|---|
| App named `mcp_server` | `backend/` is on `sys.path`; a local `mcp` package shadows the PyPI `mcp` SDK. |
| Tool bodies stay **sync**; async handler wraps them in `sync_to_async(..., thread_sensitive=True)` | `workspace_scope` opens `transaction.atomic()` + `SET LOCAL`; the contextvar and GUC are coherent only inside one sync call on one connection. Same shape as Celery. |
| Token resolves a `Membership`, not a user | Scope and role come from one row; no ambient state. |
| Authorization via `workspaces.permissions.has_permission` + a capability map | Standing rule: never an inline role-string comparison. |
| Reuse `LessonPlanSerializer`, the `quota` payload, the `catalog` group label | One shape per concept, not a second one. |

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/mcp_server/` | New | App, registry, tools, transports, `manage.py` command |
| `backend/mcp_server/models.py` + migration | New | API token model — lives with its surface, not in `workspaces/` |
| `backend/config/settings.py` | Modified | `INSTALLED_APPS`, HTTP-arm flag |
| `backend/lesson_plans/serializers.py` | Read-only reuse | No shape changes |

## Delivery — chained PRs, stacked to main (400 lines/slice)

1. API token model + resolver + tests.
2. `mcp_server` app skeleton: registry, tool context (scope entry + authz), fail-closed tests.
3. The five read-only tools.
4. stdio transport + `manage.py` command + async→sync bridge.
5. Streamable-HTTP mount behind flag (default off).

Each slice lands independently; strict TDD.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Async handler leaks scope across the sync boundary | High | `thread_sensitive=True`; cold-context test asserts zero rows |
| Token leaks grant standing workspace access | Med | Store hash only; per-membership revocation; read-only v1 |
| HTTP arm reachable before throttling exists | Med | Flag default off; throttling gated to P6 |
| `mcp` SDK import shadowing | Med | App named `mcp_server`; import test |

## Rollback Plan

Slices 2–5 are additive: remove `mcp_server` from `INSTALLED_APPS` and no request path changes. Slice 1 needs a reverse migration dropping the token table; nothing else references it.

## Dependencies

- PyPI `mcp` SDK (new). P3 is **not** a dependency — `get_lesson_plan` simply omits its columns.

## Success Criteria

- [ ] An MCP client answers a natural-language question over a demo tenant.
- [ ] A cold-context test proves a cross-tenant read returns **empty**, never a wrong-workspace row.
- [ ] No tool compares a role string inline.
- [ ] HTTP arm off by default; stdio works with the flag unset.
- [ ] `uv run pytest` green; `makemigrations --check` clean.

## Proposal question round

Interactive asking was unavailable. These assumptions need user review:

1. **Token issuance path** — assumed a `manage.py` command only (no UI, no API endpoint) for v1. Confirm.
2. **Token lifetime** — assumed non-expiring + explicitly revocable. Should it carry a TTL?
3. **`search_catalog` scope** — the catalog is frozen and global, not workspace data. Assumed it still requires a valid token (no anonymous curriculum reads). Confirm.
4. **Demo tenants** — assumed demo workspaces can mint tokens like any other. If not, the exit gate needs a different tenant.
5. **Quota visibility** — `get_quota` exposes usage counters conversationally. Roadmap open decision 3 (provenance exposure) is adjacent; assumed intended.
