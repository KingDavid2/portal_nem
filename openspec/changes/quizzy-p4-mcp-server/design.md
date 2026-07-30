# Design: Quizzy P4 — MCP server over the scoped API

One sync tool registry behind two transports. A token resolves a `Membership`; a single
`sync_to_async(..., thread_sensitive=True)` bridge crosses into `dispatch()`, which authorizes
via the capability map and calls a tool body that enters `workspace_scope()` itself.

## Data flow

    stdio (env token) ─┐                                      ┌─ has_permission(membership, cap)
                       ├→ resolve_membership(raw) ─→ dispatch ┤
    HTTP (bearer) ─────┘   [sync_to_async]        [sync_to_async]  └─ tool(membership, **args)
                                                                        └─ workspace_scope(ws_id)
                                                                             └─ ScopedManager + RLS

Two ORM-touching entry points, two bridges, both `thread_sensitive=True`. Everything to the right
of `dispatch` is plain sync code.

## Architecture decisions

### D1 — `search_catalog` matches normalized substrings over the frozen catalog

| Aspect | Choice |
|---|---|
| Signature | `search_catalog(query: str = "", field: str \| None = None)` — `field` **optional** |
| Matched text | Field names, subject names, theme names, content text, PDA text |
| Matching | `catalog._normalize(needle) in catalog._normalize(haystack)` — accent-, case- and punctuation-insensitive |
| Empty query | Returns the whole catalog (optionally narrowed by `field`) — not an error |
| Bad `field` id | `catalog.field_by_id` raises `KeyError` → dispatcher renders `ToolInputError` |

**Rejected**: requiring `field` (the caller would need the answer to ask the question); a DB or
pgvector index (locked non-goal, and the catalog is 4 fields / 13 subjects / 2 contents / 5 PDAs —
a linear scan of a frozen tuple is correct at this size); returning partially-rendered contents
that carry only the matching PDAs (that would be a second content shape).

**Rationale**: `_normalize` already exists at `core/catalog.py:153` and is the id-resolution
primitive — reusing it means search and lookup agree on what "the same string" is. A content is
included when its own text *or* any of its PDA texts match, and it is then rendered whole.

### D2 — payload reuse, one shape per concept

| Tool | Shape | Symbol |
|---|---|---|
| `list_lesson_plans`, `get_lesson_plan` | lesson plan | `lesson_plans.serializers.LessonPlanSerializer` |
| `get_quota` | quota card | `lesson_plans.serializers.GenerationQuotaSerializer` over the `quota` action's dict |
| `list_groups` | group identity | `lesson_plans.serializers.CatalogGroupSerializer` — **confirmed** |
| `search_catalog` | `{fields, subjects, cross_cutting_themes, contents}` | the same keys and element serializers `LessonPlanCatalogSerializer` already uses |

**`list_groups` rejects `schools.serializers.GroupSerializer`**: its `school_year`/`workspace` FK
ids are meaningless to a conversational client, and `workspace` is redundant — the token pins it.

The `catalog` action builds its group dict inline (`viewsets.py:251`), including
`f"{group.grado}° {group.grupo}"`. Slice 3 extracts that to
`lesson_plans.serializers.catalog_group_payload(group)` and calls it from both places — the same
anti-drift move `quota.format_period` (`quota.py:46`) exists to make.

### D3 — one not-found path for `get_lesson_plan`

Inside `workspace_scope`, `LessonPlan.objects.get(pk=...)` already raises `DoesNotExist` for both a
scoped miss and an id that exists nowhere — `ScopedManager` makes them the same query. The tool
catches `DoesNotExist` **and** the `int()` coercion failure of a malformed id, and raises one
`ToolNotFoundError("Lesson plan not found.")` carrying no distinguishing payload. Folding the
malformed-id case in is load-bearing: left alone it would surface as a `ValueError` and become a
third, distinguishable outcome. The transport renders it as an MCP tool error (`isError`) with that
fixed message — never a status code or error type that varies by cause.

### D4 — resolve-then-touch, with the revoked check inside the lookup

```python
row = (WorkspaceApiToken.objects
       .filter(token_hash=sha256(raw.encode()).hexdigest(), revoked_at__isnull=True)
       .select_related("membership__workspace").first())
if row is None:
    return None                       # unknown and revoked exit here, identically
WorkspaceApiToken.objects.filter(pk=row.pk).update(last_used_at=timezone.now())
return row.membership
```

`revoked_at__isnull=True` is part of the **filter**, not a branch after it, so there is structurally
no code path on which a revoked row can be touched. The touch is a targeted `update()` (not
`save()`) placed strictly after a successful resolution and before the return. Unknown and revoked
share one query, one return, zero writes.

### D5 — the bridge sits at `dispatch()`, not per tool

`server.py` / `http.py` do `await sync_to_async(dispatch, thread_sensitive=True)(name, args, membership)`.
`registry.dispatch` is sync end to end. Per-tool wrapping was rejected: it gives every future tool
its own chance to forget the wrapper, and it would leak async concerns into the registry.

Caught by tests, not by review:
- `test_dispatch_is_sync` — `not asyncio.iscoroutinefunction(dispatch)` and no registered tool is a coroutine function.
- `test_async_handler_does_not_raise_synchronous_only_operation` — a sync test calling `asyncio.run(handle_call_tool(...))`; removing the bridge makes Django raise `SynchronousOnlyOperation`. No `pytest-asyncio` dependency needed. The suite asserts `DJANGO_ALLOW_ASYNC_UNSAFE` is unset, which is what makes that failure reachable.

**Gotcha the tenancy tests must respect**: `asgiref.sync_to_async` *copies the caller's contextvars*
into the executor thread. A test whose calling context already holds `active_workspace` would leak
it across the bridge and pass even with `workspace_scope` stripped from the tool. The tenancy tests
therefore run the whole `asyncio.run(...)` inside a cold `ThreadPoolExecutor` thread with
`@pytest.mark.django_db(transaction=True)`, exactly as `test_tasks.py::_run_task_in_cold_thread`
does, and the module docstring states this reason.

### D6 — `mcp_server`, never `mcp`

`backend/` is on `sys.path`, so `backend/mcp/` would shadow the PyPI SDK. Dependency:
`mcp>=1.9,<2` in `backend/pyproject.toml` (Streamable-HTTP needs ≥1.8; pin the major, resolve the
exact minor at apply time). Guard test in `mcp_server/tests/test_imports.py`: import `mcp`, assert
its `__file__` resolves under `sys.prefix` and that `settings.BASE_DIR` is not one of its parents.

## File changes

| File | Action | Description |
|---|---|---|
| `backend/mcp_server/models.py` | Create | `WorkspaceApiToken` — plain `models.Model`; docstring carries the RLS-exclusion reason, citing the `WorkspaceInvitation`/`WorkspaceHistory` precedent |
| `backend/mcp_server/migrations/0001_initial.py` | Create | `CreateModel` only: FK `membership` CASCADE, `token_hash` `CharField(64, unique=True)`, `name`, `created_at`, `last_used_at`, `revoked_at`. **No RLS migration** — RLS policies are written per-app for `ScopedModel` tables (`lesson_plans/migrations/0002_rls.py`); this table is deliberately outside that set. Reverse: `migrate mcp_server zero` drops the table; nothing else FKs into it |
| `backend/mcp_server/auth.py` | Create | `resolve_membership(raw) -> Membership \| None` (D4) |
| `backend/mcp_server/registry.py` | Create | `register`, `dispatch`, `CAPABILITY_MAP`, typed errors |
| `backend/mcp_server/tools.py` | Create | The five sync tool bodies, each entering `workspace_scope` |
| `backend/mcp_server/server.py` | Create | MCP `Server`, async handlers, the `sync_to_async` bridge, stdio run loop |
| `backend/mcp_server/http.py` | Create | Streamable-HTTP ASGI mount, bearer-token identity |
| `backend/mcp_server/management/commands/{run_mcp,create_mcp_token}.py` | Create | stdio server; token minting (prints the raw value once) |
| `backend/config/settings.py` | Modify | `INSTALLED_APPS += ["mcp_server"]`; `MCP_HTTP_ENABLED = env.bool("MCP_HTTP_ENABLED", default=False)` |
| `backend/config/urls.py` | Modify | `if settings.MCP_HTTP_ENABLED:` mount — mirrors the `demo_mode.enabled()` block; off ⇒ route absent ⇒ 404 by absence |
| `backend/lesson_plans/serializers.py` | Modify | Add `catalog_group_payload(group)` (D2) |
| `backend/lesson_plans/viewsets.py` | Modify | `catalog` calls `catalog_group_payload` instead of its inline dict |
| `backend/pyproject.toml` | Modify | `mcp>=1.9,<2` |

## Interfaces

```python
# registry.py
CAPABILITY_MAP = {                      # mirrors lesson_plans/viewsets.py:64
    "list_groups": "view_workspace", "list_lesson_plans": "view_workspace",
    "get_lesson_plan": "view_workspace", "get_quota": "view_workspace",
    "search_catalog": "view_workspace",
}

class ToolError(Exception): ...
class UnknownToolError(ToolError):  ...  # carries the offending name
class ToolNotFoundError(ToolError): ...  # fixed message, no cause detail (D3)
class ToolInputError(ToolError):    ...
class ToolDenied(ToolError):        ...  # authz + unresolved identity, one shape

def dispatch(name: str, arguments: dict, membership) -> dict: ...
```

`dispatch` order: membership present → `CAPABILITY_MAP[name]` (miss ⇒ `UnknownToolError`) →
`has_permission(membership, capability)` (false ⇒ `ToolDenied`) → tool body. The raw tool name never
reaches `has_permission`; no module in `mcp_server` compares `membership.role` to a literal, and a
grep-style test asserts that.

## Testing strategy (strict TDD — RED first, per slice)

| Slice | RED tests |
|---|---|
| 1 | Only the hash is persisted; token row readable with no scope active; unknown ≡ revoked (same return, no `last_used_at` touch); valid token touches it; `create_mcp_token` prints the raw value once; demo workspace can mint; no URLconf route mints tokens |
| 2a | Exactly five names registered; unknown name ⇒ `UnknownToolError`, never `KeyError`; raw name never reaches `has_permission`; role outside the matrix denied on all five; no inline role-string comparison; `mcp` import not shadowed |
| 2b | Cold-thread + `asyncio.run` harness; tool sets its own scope; scope-stripped tool reads zero rows; `dispatch` is sync; no `SynchronousOnlyOperation` |
| 3 | Per-tool payload equals the reused serializer's field set; `get_quota` equals `GET /api/lesson-plans/quota/`; cross-workspace id ⇒ not-found identical to nowhere-id; malformed id ⇒ same error; `search_catalog` serves an empty workspace; no tool writes |
| 4 | stdio serves with a valid `PORTAL_NEM_MCP_TOKEN`; unset/garbage token serves no results |
| 5 | Flag off ⇒ 404 and route absent from the URLconf; flag on + missing/garbage bearer ⇒ 401; flag on + valid bearer ⇒ result |

## Delivery — line forecast

The proposal's slice 2 breaches 400: registry plus the verbose cold-context tenancy harness lands
around 450–480. Split it, and move the ~10-line `dispatch_async` coroutine forward into 2b so the
slice that *claims* the tenancy proof can actually run it (slice 4 shrinks to stdio wiring only).

| Slice | Content | Forecast |
|---|---|---|
| 1 | Token model + migration + resolver + `create_mcp_token` + tests | ~320 |
| 2a | Registry, typed errors, capability map, `INSTALLED_APPS`, import guard, authz tests | ~250 |
| 2b | `dispatch_async` bridge + cold-context harness + fail-closed tenancy tests | ~230 |
| 3 | The five tools + `catalog_group_payload` extraction + payload tests | ~370 |
| 4 | stdio transport + `run_mcp` + `mcp` dependency + tests | ~220 |
| 5 | Streamable-HTTP mount behind `MCP_HTTP_ENABLED` + urls + tests | ~215 |

`Decision needed before apply: No` · `Chained PRs recommended: Yes` · `400-line budget risk: Medium`

## Threat matrix

Applicable — this change adds a process-integration boundary (stdio subprocess, ASGI mount).

| Row | Status | Safe behavior | RED test |
|---|---|---|---|
| Routing | Applicable | HTTP route registered only when `MCP_HTTP_ENABLED`; 404 by absence | Flag-off URLconf test |
| Process integration | Applicable | stdio takes identity from `PORTAL_NEM_MCP_TOKEN`; unresolvable ⇒ serves nothing | stdio no-token test |
| Untrusted input | Applicable | Tool arguments reach only ORM kwargs and frozen-tuple scans; no eval, no SQL string building | Malformed-id ⇒ `ToolNotFoundError` |
| Secret handling | Applicable | Raw token printed once, never persisted or logged; only the SHA-256 digest stored | Hash-only persistence test |
| Shell / subprocess spawn | N/A | The server *is* the subprocess; it spawns nothing | — |
| VCS/PR automation, executable-file classification | N/A | Not touched | — |

## Migration / rollout

Additive. Slices 2–5 roll back by dropping `mcp_server` from `INSTALLED_APPS` — no request path
changes while `MCP_HTTP_ENABLED` is false. Slice 1 rolls back with `migrate mcp_server zero`.

## Open questions

- [ ] Proposal question round 1–5 (issuance path, no TTL, authenticated catalog reads, demo tenants, quota visibility) are designed as assumed and still want a human yes.
- [ ] Exact `mcp` SDK minor to pin — resolve at apply time against the installed wheel.
