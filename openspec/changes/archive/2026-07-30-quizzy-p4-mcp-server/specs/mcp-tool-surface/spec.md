# Delta for mcp-tool-surface

## ADDED Requirements

### Requirement: Transport-Agnostic Sync Tool Registry

The system MUST expose its MCP tools through a single registry that maps a tool
name to a plain **synchronous** callable. Every transport (stdio, Streamable-HTTP)
MUST dispatch through this one registry; a transport MUST NOT define, wrap, or
special-case a tool of its own.

Tool bodies MUST remain synchronous. `workspace_scope()` opens a
`transaction.atomic()` block and issues `SET LOCAL app.workspace_id`, so the
contextvar and the Postgres GUC are coherent only inside one synchronous call on
one connection — the same constraint the Celery task path lives under. An async
MCP handler MUST therefore cross into a tool body via
`sync_to_async(..., thread_sensitive=True)` and MUST NOT execute ORM work on the
event loop.

Dispatching a name that is not in the registry MUST raise a typed, named error
that the transport can render as an MCP tool error. It MUST NOT surface as a
raw `KeyError`, an `AttributeError`, or an unhandled traceback.

#### Scenario: Both transports dispatch through the same registry

- GIVEN a tool registered once in the MCP tool registry
- WHEN the tool is invoked over stdio, and separately over the Streamable-HTTP arm
- THEN both transports MUST resolve the callable from the same registry
- AND neither transport MUST hold its own copy or variant of the tool body

#### Scenario: Tool invoked through the async handler does not raise SynchronousOnlyOperation

- GIVEN the async MCP handler receives a tool call
- WHEN the handler dispatches to the synchronous tool body
- THEN the body MUST execute via `sync_to_async(..., thread_sensitive=True)`
- AND the call MUST NOT raise `SynchronousOnlyOperation`
- AND the tool MUST return its result payload

#### Scenario: Unknown tool name yields a typed error

- GIVEN an authenticated caller
- WHEN a tool call names a tool that is not present in the registry
- THEN the dispatcher MUST raise a typed unknown-tool error carrying the offending name
- AND the caller MUST NOT observe a `KeyError` or an unhandled traceback

### Requirement: MCP Surface Is Read-Only in v1

The MCP tool surface MUST expose exactly five tools, all read-only:
`list_groups`, `list_lesson_plans`, `get_lesson_plan`, `get_quota`, and
`search_catalog`. No registered tool MAY create, update, or delete any row.
Mutation tools are out of scope for this change.

#### Scenario: Exactly the five read-only tools are registered

- GIVEN the MCP tool registry is loaded
- WHEN the registered tool names are listed
- THEN they MUST be exactly `list_groups`, `list_lesson_plans`, `get_lesson_plan`, `get_quota`, and `search_catalog`

#### Scenario: No tool performs a write

- GIVEN any tool in the registry
- WHEN the tool is invoked with valid arguments
- THEN it MUST NOT create, update, or delete any database row

### Requirement: Tool Payloads Reuse the Existing HTTP Shapes

Each tool MUST return the payload shape already served by the corresponding HTTP
surface, rather than defining a second shape for the same concept:

| Tool | Shape |
|---|---|
| `list_lesson_plans`, `get_lesson_plan` | `LessonPlanSerializer` |
| `get_quota` | the `GET /api/lesson-plans/quota/` payload (`period`, `used`, `limit`, `remaining`) |
| `search_catalog` | the frozen-catalog records already exposed by the catalog surface |
| `list_groups` | the group identity fields the catalog surface already labels a group with |

A tool MUST NOT introduce a divergent field name or a parallel representation of
a concept that already has one.

#### Scenario: get_lesson_plan returns the serializer shape

- GIVEN a lesson plan readable by the caller
- WHEN `get_lesson_plan` is invoked for its id
- THEN the returned payload MUST match the `LessonPlanSerializer` field set
- AND MUST NOT rename or restructure any of its fields

#### Scenario: get_quota returns the quota-card payload

- GIVEN a workspace with recorded generation usage for the current period
- WHEN `get_quota` is invoked
- THEN the payload MUST carry `period`, `used`, `limit`, and `remaining`
- AND the values MUST equal those served by `GET /api/lesson-plans/quota/` for that workspace

### Requirement: Every Tool Requires an Authenticated Identity

Every tool, without exception, MUST require a resolvable caller identity before
executing. `search_catalog` reads the frozen, global curriculum catalog rather
than workspace data, but it MUST still require a valid token: the door is
uniform, and there is no anonymous curriculum read.

#### Scenario: search_catalog denies an unauthenticated caller

- GIVEN a tool call for `search_catalog` carrying no resolvable identity
- WHEN the call is dispatched
- THEN the call MUST be denied
- AND no catalog records MUST be returned

#### Scenario: search_catalog serves an authenticated caller regardless of workspace contents

- GIVEN a caller whose identity resolves to a membership in an empty workspace
- WHEN `search_catalog` is invoked with a query
- THEN the matching frozen-catalog records MUST be returned
- AND the result MUST NOT depend on any workspace-scoped row

### Requirement: stdio Transport Takes Its Identity From the Environment

The system MUST expose the MCP server over stdio through a `manage.py`
command. The stdio transport MUST read the caller's raw API token from the
`PORTAL_NEM_MCP_TOKEN` environment variable and MUST resolve it to a membership
before serving any tool call. With no resolvable token, the process MUST NOT
serve tool results.

#### Scenario: stdio serves tools with a valid environment token

- GIVEN `PORTAL_NEM_MCP_TOKEN` holds a raw token resolving to a membership in workspace A
- WHEN an MCP client invokes `list_lesson_plans` over stdio
- THEN the response MUST contain workspace A's lesson plans

#### Scenario: stdio with no resolvable token serves no tool results

- GIVEN `PORTAL_NEM_MCP_TOKEN` is unset, or holds a value that resolves to no membership
- WHEN an MCP client invokes any tool over stdio
- THEN the call MUST be denied
- AND no workspace rows MUST be returned

### Requirement: Streamable-HTTP Arm Is Flag-Gated and Off by Default

The Streamable-HTTP mount MUST be gated by `settings.MCP_HTTP_ENABLED`, which
MUST default to **off**. When the flag is off, the route MUST NOT be registered
at all — following the `demo_mode.enabled()` pattern in `backend/config/urls.py`,
so the path 404s *by absence*, not because a check rejected the caller.

When the flag is on, the transport MUST take its identity from an
`Authorization: Bearer <token>` header and MUST resolve it to a membership. A
missing, malformed, unknown, or revoked bearer token MUST yield 401.

#### Scenario: Flag off leaves the route absent

- GIVEN `MCP_HTTP_ENABLED` is off
- WHEN a request is made to the MCP HTTP path
- THEN the response MUST be 404
- AND the URLconf MUST NOT contain the MCP HTTP route

#### Scenario: Flag on with missing or garbage bearer token is rejected

- GIVEN `MCP_HTTP_ENABLED` is on
- WHEN a request arrives with no `Authorization` header, or with a `Bearer` value that resolves to no membership
- THEN the response MUST be 401
- AND no tool MUST be executed

#### Scenario: Flag on with a valid bearer token returns the tool result

- GIVEN `MCP_HTTP_ENABLED` is on
- AND the request carries `Authorization: Bearer <token>` resolving to a membership in workspace A
- WHEN the request invokes `list_groups`
- THEN the response MUST return workspace A's groups
