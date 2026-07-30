# Tasks: Quizzy P4 — MCP server over the scoped API

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1605 across 6 slices |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | S1 → S2a → S2b → S3 → S4 → S5 |
| Delivery strategy | force-chained |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

### Suggested Work Units

| Unit | Branch | Goal | Forecast | Focused test command | Runtime harness | Rollback boundary |
|------|--------|------|----------|----------------------|-----------------|-------------------|
| S1 | `feat/quizzy-p4-s1-api-token` | `WorkspaceApiToken` + `resolve_membership` + `create_mcp_token` | ~320 | `cd backend && uv run pytest mcp_server/tests/test_auth.py mcp_server/tests/test_create_mcp_token.py` | `cd backend && uv run manage.py create_mcp_token --membership <id> --name smoke` | `migrate mcp_server zero`; delete `backend/mcp_server/{models,auth}.py` + migration + command |
| S2a | `feat/quizzy-p4-s2a-registry` | Registry, typed errors, `CAPABILITY_MAP`, authz, import guard | ~250 | `cd backend && uv run pytest mcp_server/tests/test_registry.py mcp_server/tests/test_imports.py` | N/A — no process boundary yet; registry is in-process only | Drop `mcp_server` from `INSTALLED_APPS`; delete `registry.py` |
| S2b | `feat/quizzy-p4-s2b-async-bridge` | `dispatch_async` bridge + cold-context tenancy harness | ~230 | `cd backend && uv run pytest mcp_server/tests/test_tenancy_cold_context.py` | N/A — bridge exercised by `asyncio.run` in the cold-thread harness, no transport yet | Delete `dispatch_async` + `test_tenancy_cold_context.py` |
| S3 | `feat/quizzy-p4-s3-read-tools` | Five read-only tools + `catalog_group_payload` extraction | ~370 ⚠️ | `cd backend && uv run pytest mcp_server/tests/test_tools.py lesson_plans/tests -k catalog` | N/A — tools reachable only through dispatch until S4 | Delete `tools.py`; revert `viewsets.py:251` to its inline group dict |
| S4 | `feat/quizzy-p4-s4-stdio` | stdio transport + `run_mcp` + `mcp` dependency | ~220 | `cd backend && uv run pytest mcp_server/tests/test_server_stdio.py` | `PORTAL_NEM_MCP_TOKEN=<raw> uv run manage.py run_mcp` against a real MCP client | Delete `server.py` + `run_mcp.py`; drop `mcp` from `pyproject.toml` |
| S5 | `feat/quizzy-p4-s5-http-arm` | Flag-gated Streamable-HTTP mount | ~215 | `cd backend && uv run pytest mcp_server/tests/test_http.py` | `MCP_HTTP_ENABLED=1 uv run manage.py runserver` + bearer-token request | Delete `http.py` + the `urls.py` flag block; flag defaults off so removal is a no-op |

Each slice branches from `main`, merges to `main` in order, and carries a Chain Context block with a dependency diagram marking itself `📍`. Commits are conventional (`feat(mcp): …`), no AI attribution.

Dependencies: S1 → S2a → S2b → S3 → S4 → S5. S2a needs S1's `resolve_membership`; S2b needs S2a's `dispatch`; S3 needs S2a's registry and S2b's tenancy harness; S4 needs S3's tools; S5 needs S4's transport handlers.

**Per-slice verification (every slice, no exceptions):**

```
cd backend && uv run pytest
cd backend && uv run manage.py makemigrations --check --dry-run
```

**Must stay green untouched in every slice:** `backend/lesson_plans/test_tasks.py` (esp. ~:199, ~:510) and `backend/workspaces/tests/test_pooling_leak.py`.

---

## Slice 1 — API token model, resolver, mint command (`feat/quizzy-p4-s1-api-token`, ~320)

- [x] 1.1 RED `backend/mcp_server/tests/test_models.py`: minting stores `sha256(raw).hexdigest()` in `token_hash` and the raw string appears in **no** field of the row.
- [x] 1.2 RED same file: a `WorkspaceApiToken` lookup by `token_hash` returns the row with **no** workspace contextvar and no `app.workspace_id` active — it must not fail closed like a `ScopedModel`.
- [x] 1.3 GREEN `backend/mcp_server/models.py`: `WorkspaceApiToken` as a plain `models.Model` (never `ScopedModel`) with `membership` FK CASCADE, `name`, `token_hash` `CharField(64, unique=True)`, `created_at`, `last_used_at`, `revoked_at`. Docstring states the RLS-exclusion reason and cites the `WorkspaceInvitation`/`WorkspaceHistory` precedent in `backend/workspaces/models.py`.
- [x] 1.4 GREEN `backend/mcp_server/migrations/0001_initial.py`: `CreateModel` only. **No RLS migration** — this table is deliberately outside the per-app `ScopedModel` RLS set (`lesson_plans/migrations/0002_rls.py`).
- [x] 1.5 RED `backend/mcp_server/tests/test_auth.py`: a valid unrevoked token returns its `Membership` and updates `last_used_at`.
- [x] 1.6 RED same file: an unknown token and a revoked token both return `None`, raise no distinguishing error, and **neither touches `last_used_at`** — assert the revoked row's `last_used_at` is byte-identical after the call.
- [x] 1.7 RED same file: a failed resolution performs no workspace-scoped ORM read or write.
- [x] 1.8 GREEN `backend/mcp_server/auth.py`: `resolve_membership(raw) -> Membership | None`. `revoked_at__isnull=True` goes **inside the `.filter(...)` of the lookup itself**, never in a branch after it — structurally no code path can reach `last_used_at` on a revoked row. Touch via targeted `.update(last_used_at=...)`, not `save()`, strictly after a successful resolution.
- [x] 1.9 RED `backend/mcp_server/tests/test_create_mcp_token.py`: the command creates a row for a membership and prints the raw token **exactly once**; a demo-provisioned workspace's membership can mint and the token resolves.
- [x] 1.10 RED same file: the registered URLconf contains no route that creates a `WorkspaceApiToken` — issuance is command-only.
- [x] 1.11 GREEN `backend/mcp_server/management/commands/create_mcp_token.py`: mint, print the raw value once with an explicit "cannot be retrieved again" notice, never log or persist it.

## Slice 2a — Registry, typed errors, capability map (`feat/quizzy-p4-s2a-registry`, ~250)

Depends on S1.

- [x] 2a.1 RED `backend/mcp_server/tests/test_imports.py`: `import mcp` resolves to a `__file__` under `sys.prefix`, and `settings.BASE_DIR` is **not** one of its parents — proving no `backend/` top-level package shadows a dependency name. The app is `backend/mcp_server/`, never `backend/mcp/`.
- [x] 2a.2 RED `backend/mcp_server/tests/test_registry.py`: exactly five names are registered — `list_groups`, `list_lesson_plans`, `get_lesson_plan`, `get_quota`, `search_catalog`.
- [x] 2a.3 RED same file: an unregistered name raises `UnknownToolError` carrying the offending name — never a raw `KeyError`, `AttributeError`, or unhandled traceback.
- [x] 2a.4 RED same file: the raw tool name never reaches `has_permission` — patch `workspaces.permissions.has_permission` and assert it is called with `"view_workspace"`, never `"get_quota"`.
- [x] 2a.5 RED same file: a `Membership` whose role is absent from the capability matrix is denied all five tools, and no tool body executes a scoped read.
- [x] 2a.6 RED same file: a source-scan test over `backend/mcp_server/**.py` asserts **no module compares `membership.role` to a literal string** anywhere. Every decision goes through `workspaces.permissions.has_permission` + `CAPABILITY_MAP`.
- [x] 2a.7 GREEN `backend/mcp_server/registry.py`: `register`, sync `dispatch(name, arguments, membership) -> dict`, `CAPABILITY_MAP` (all five → `view_workspace`, mirroring `lesson_plans/viewsets.py:64`), and `ToolError` / `UnknownToolError` / `ToolNotFoundError` / `ToolInputError` / `ToolDenied`. Dispatch order: membership present → `CAPABILITY_MAP[name]` (miss ⇒ `UnknownToolError`) → `has_permission` (false ⇒ `ToolDenied`) → tool body. Unresolved identity and authz failure share the one `ToolDenied` shape.
- [x] 2a.8 GREEN `backend/config/settings.py`: add `"mcp_server"` to `INSTALLED_APPS`.

## Slice 2b — Async bridge and cold-context tenancy harness (`feat/quizzy-p4-s2b-async-bridge`, ~230)

Depends on S2a. **This is the highest-value slice in the change — do not compress it.**

- [x] 2b.1 RED `backend/mcp_server/tests/test_tenancy_cold_context.py` — write the module docstring **first**. It MUST state: `asgiref.sync_to_async` copies the caller's contextvars into the executor thread, so a test whose calling context already holds `active_workspace` leaks it across the bridge and passes **even with `workspace_scope` stripped from the tool body** — a test that proves nothing. Every test here therefore runs the entire `asyncio.run(...)` inside a fresh `ThreadPoolExecutor(max_workers=1)` thread, mirroring `lesson_plans/test_tasks.py::_run_task_in_cold_thread` (`:174`, `:186`).
- [x] 2b.2 RED same file: a `_dispatch_in_cold_thread(...)` helper that submits `asyncio.run(dispatch_async(...))` to a fresh `ThreadPoolExecutor(max_workers=1)`, under `@pytest.mark.django_db(transaction=True)`.
- [x] 2b.3 RED same file: a probe tool invoked through the cold thread sets its own `workspace_scope(membership.workspace_id)` and returns workspace A's rows, with no scope active in the calling context.
- [x] 2b.4 RED same file — **the fail-closed proof**: the same probe tool with its `workspace_scope` entry stripped reads **zero rows** while rows exist in more than one workspace. It must never fall back to an unscoped or wrong-workspace view. If this test passes before 2b.1's cold-thread harness exists, the harness is wrong.
- [x] 2b.5 RED same file: `test_dispatch_is_sync` — `not asyncio.iscoroutinefunction(dispatch)` and no registered tool is a coroutine function.
- [x] 2b.6 RED same file: `test_async_handler_does_not_raise_synchronous_only_operation` — a plain sync test calling `asyncio.run(dispatch_async(...))`; removing the bridge makes Django raise `SynchronousOnlyOperation`. Assert `DJANGO_ALLOW_ASYNC_UNSAFE` is unset (that is what makes the failure reachable). No `pytest-asyncio` dependency.
- [x] 2b.7 GREEN `backend/mcp_server/registry.py`: add `async def dispatch_async(name, arguments, membership)` = `await sync_to_async(dispatch, thread_sensitive=True)(...)`. The bridge sits **at dispatch only**, never per tool — per-tool wrapping gives every future tool its own chance to forget it.

## Slice 3 — The five read-only tools (`feat/quizzy-p4-s3-read-tools`, ~370 ⚠️ least headroom)

Depends on S2a + S2b.

> **Headroom instruction for the apply executor:** if this slice trends over 400 changed lines, defer **`search_catalog` and its tests** into a follow-on slice `feat/quizzy-p4-s3b-search-catalog` off `main`. Defer nothing else — the four workspace-scoped tools and the `catalog_group_payload` extraction must land together, because the extraction touches `viewsets.py` and splitting it strands a half-refactor.

- [x] 3.1 RED `backend/lesson_plans/tests/` : `catalog_group_payload(group)` returns the exact dict the `catalog` action builds inline at `viewsets.py:251`, including the `f"{group.grado}° {group.grupo}"` label.
- [x] 3.2 GREEN `backend/lesson_plans/serializers.py`: add `catalog_group_payload(group)`; `backend/lesson_plans/viewsets.py`: `catalog` calls it instead of its inline dict — one shape, no drift.
- [x] 3.3 RED `backend/mcp_server/tests/test_tools.py`: `list_groups` payload field set equals `CatalogGroupSerializer` / `catalog_group_payload`; it must not use `schools.serializers.GroupSerializer` (its `school_year`/`workspace` FK ids are meaningless conversationally and `workspace` is redundant — the token pins it).
- [x] 3.4 RED same file: `list_lesson_plans` and `get_lesson_plan` payload field sets equal `LessonPlanSerializer`, with no renamed or restructured field.
- [x] 3.5 RED same file: `get_quota` payload carries `period`, `used`, `limit`, `remaining` and equals `GET /api/lesson-plans/quota/` for the same workspace.
- [x] 3.6 RED same file — indistinguishability: a token for workspace A asking `get_lesson_plan` for (a) workspace B's plan id, (b) an id existing nowhere, and (c) a **malformed non-integer id** must produce three byte-identical `ToolNotFoundError("Lesson plan not found.")` outcomes. Fold the `int()` coercion failure into the **same catch as `DoesNotExist`** — left alone it surfaces as `ValueError` and becomes a third distinguishable outcome, defeating the requirement.
- [ ] 3.7 RED same file: `search_catalog(query="", field=None)` returns the whole catalog; a bad `field` id surfaces as `ToolInputError` (from `catalog.field_by_id`'s `KeyError`); matching is `catalog._normalize(needle) in catalog._normalize(haystack)` (`core/catalog.py:153`) over field/subject/theme/content/PDA text; a content matching via any PDA is rendered whole. **Deferred → `feat/quizzy-p4-s3b-search-catalog` (400-line headroom).**
- [ ] 3.8 RED same file: `search_catalog` serves a membership in an **empty** workspace — the result depends on no workspace-scoped row. **Deferred → `feat/quizzy-p4-s3b-search-catalog` (400-line headroom).**
- [x] 3.9 RED same file: no tool creates, updates, or deletes any row — assert across all five with a write-counting hook. *(S3 asserts the four shipped tools; `search_catalog` write-proof moves with S3b.)*
- [x] 3.10 GREEN `backend/mcp_server/tools.py`: the five sync tool bodies, each entering `workspace_scope(membership.workspace_id)` itself and reusing the serializers above. No new payload shape. *(Four tools fully implemented; `search_catalog` remains a budget-deferral stub raising `ToolInputError` until S3b.)*

## Slice 4 — stdio transport (`feat/quizzy-p4-s4-stdio`, ~220)

Depends on S3.

- [ ] 4.1 `backend/pyproject.toml`: add `mcp>=1.9,<2`. **Verify the exact minor against the installed wheel at apply time** — Streamable-HTTP needs ≥1.8; if the resolved wheel differs, adjust the lower bound and say so in the PR body.
- [ ] 4.2 RED `backend/mcp_server/tests/test_server_stdio.py`: with `PORTAL_NEM_MCP_TOKEN` holding a raw token for a membership in workspace A, `list_lesson_plans` over the stdio handler returns workspace A's plans.
- [ ] 4.3 RED same file: with `PORTAL_NEM_MCP_TOKEN` unset, and separately holding garbage, the call is denied and **no workspace rows** are returned — identical outcomes for both.
- [ ] 4.4 GREEN `backend/mcp_server/server.py`: MCP `Server`, `list_tools`/`call_tool` async handlers awaiting `dispatch_async`, identity from `PORTAL_NEM_MCP_TOKEN` via `resolve_membership`, and the stdio run loop. Render `ToolError` subclasses as MCP tool errors (`isError`) — `ToolNotFoundError` always with its fixed message, never a varying status or error type.
- [ ] 4.5 GREEN `backend/mcp_server/management/commands/run_mcp.py`: runs the stdio server.

## Slice 5 — Flag-gated Streamable-HTTP arm (`feat/quizzy-p4-s5-http-arm`, ~215)

Depends on S4.

- [ ] 5.1 RED `backend/mcp_server/tests/test_http.py`: with `MCP_HTTP_ENABLED` off, the MCP HTTP path returns 404 **and the route is absent from the resolved URLconf** — 404 by absence, not by rejection.
- [ ] 5.2 RED same file: flag on + no `Authorization` header, and flag on + a `Bearer` value resolving to no membership (unknown *and* revoked), all return 401 with no tool executed.
- [ ] 5.3 RED same file: flag on + a valid bearer for workspace A returns workspace A's groups from `list_groups`.
- [ ] 5.4 GREEN `backend/config/settings.py`: `MCP_HTTP_ENABLED = env.bool("MCP_HTTP_ENABLED", default=False)`.
- [ ] 5.5 GREEN `backend/mcp_server/http.py`: Streamable-HTTP ASGI mount, bearer identity via `resolve_membership`, dispatching through `dispatch_async` — no transport-local tool copy or variant.
- [ ] 5.6 GREEN `backend/config/urls.py`: `if settings.MCP_HTTP_ENABLED:` mount block, mirroring the existing `demo_mode.enabled()` block.
- [ ] 5.7 **Phase exit gate** (manual, recorded in the PR body): an MCP client answers a natural-language question over a demo tenant; a second token for a *different* demo tenant asking for the first tenant's plan by id comes back **empty**.
- [ ] 5.8 `docs/quizzy_roadmap.md`: add a **Results** section under Phase 4 (`:396`) in the same voice as the P0/P1/P2 results (`:99`, `:200`, `:299`) — what shipped, the `backend/mcp/` → `backend/mcp_server/` rename and why (`sys.path` shadowing of the PyPI SDK), the sync-tools/async-bridge decision, what the stdio smoke actually proved, and **P0 finding 7 marked resolved**. Flip the P4 status row at `:21`.
