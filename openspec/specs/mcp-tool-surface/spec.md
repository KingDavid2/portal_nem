# Spec: mcp-tool-surface

MCP tool surface over the scoped API: transport-agnostic sync registry,
read tools plus school-structure CRUD, stdio and flag-gated Streamable-HTTP
transports. Update/delete tools require an explicit confirmation gate.

## Requirements

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

### Requirement: School-Structure Tools and Read Tools Are Registered

The MCP tool surface MUST register the original read tools
(`list_groups`, `list_lesson_plans`, `get_lesson_plan`, `get_quota`,
`search_catalog`) plus teaching-context and school-structure tools:

| Tool | Capability | Mode |
|---|---|---|
| `list_groups`, `list_lesson_plans`, `get_lesson_plan`, `get_quota`, `search_catalog` | `view_workspace` | read |
| `get_teaching_context`, `list_school_years`, `list_students` | `view_workspace` | read |
| `create_school`, `create_school_year`, `create_group`, `create_student` | `edit_content` | create |
| `update_school`, `update_school_year`, `update_group`, `update_student` | `edit_content` | update |
| `delete_school`, `delete_school_year`, `delete_group`, `delete_student` | `edit_content` | delete |

Lesson-plan mutation tools are out of scope for this surface.

#### Scenario: Read and school-structure tools share one registry

- GIVEN the MCP tool registry is loaded
- WHEN the registered tool names are listed
- THEN they MUST include the five original read tools and the school-structure CRUD tools above
- AND create tools MUST map to `edit_content`
- AND read tools MUST map to `view_workspace`

### Requirement: Update and Delete Require Confirmation

Every update and delete tool MUST accept a boolean `confirm` argument. When
`confirm` is absent or not strictly `true`, the tool MUST return a
`needs_confirmation` payload carrying `status`, `action`, and `preview`, and
MUST NOT create, update, or delete any database row. When `confirm` is `true`,
the tool MUST perform the mutation via the existing school/student service layer
and return the HTTP serializer shape for the affected resource (or a deleted
acknowledgement for deletes).

Create tools MUST NOT require `confirm`.

#### Scenario: Delete without confirm does not write

- GIVEN an authenticated caller with `edit_content`
- WHEN `delete_student` is invoked without `confirm: true`
- THEN the response MUST have `status` equal to `needs_confirmation`
- AND the student row MUST still exist

#### Scenario: Delete with confirm removes the row

- GIVEN an authenticated caller with `edit_content`
- WHEN `delete_student` is invoked with `confirm: true` for an existing student
- THEN the student row MUST be deleted
- AND the response MUST acknowledge the deletion

### Requirement: Teaching Context Defaults to Last School Year

The system MUST expose `get_teaching_context`, which resolves the workspace's
último ciclo escolar as the maximum lexicographic `SchoolYear.label` and lists
all groups whose school year has that label. When exactly one such group
exists, `default_group_id` MUST be that group's id; otherwise
`default_group_id` MUST be null.

#### Scenario: Single group in last cycle yields default_group_id

- GIVEN a workspace whose latest school-year label has exactly one group
- WHEN `get_teaching_context` is invoked
- THEN `group_count` MUST be 1
- AND `default_group_id` MUST equal that group's id

#### Scenario: Multiple groups leave default_group_id null

- GIVEN a workspace whose latest school-year label has two or more groups
- WHEN `get_teaching_context` is invoked
- THEN `group_count` MUST be greater than 1
- AND `default_group_id` MUST be null

### Requirement: Tool Payloads Reuse the Existing HTTP Shapes

Each tool MUST return the payload shape already served by the corresponding HTTP
surface, rather than defining a second shape for the same concept:

| Tool | Shape |
|---|---|
| `list_lesson_plans`, `get_lesson_plan` | `LessonPlanSerializer` |
| `get_quota` | the `GET /api/lesson-plans/quota/` payload (`period`, `used`, `limit`, `remaining`) |
| `search_catalog` | the frozen-catalog records already exposed by the catalog surface |
| `list_groups` | the group identity fields the catalog surface already labels a group with |
| `list_school_years`, school year create/update | `SchoolYearSerializer` |
| school create/update | `SchoolSerializer` |
| group create/update | `GroupSerializer` |
| `list_students`, student create/update | `StudentSerializer` |

A tool MUST NOT introduce a divergent field name or a parallel representation of
a concept that already has one (except the confirm-gate envelope, which wraps
`preview` using those shapes).

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

### Requirement: create_student Defaults to Último Ciclo

`create_student` MUST resolve the target group against the último ciclo escolar
(max lexicographic `SchoolYear.label`) unless the caller passes an explicit
`school_year_label`. When `group_id` is omitted and that cycle has exactly one
group, the tool MUST use that group. When `group_id` points at a group outside
the resolved cycle, the tool MUST reject the call without writing a row.

#### Scenario: Omit group_id with a single last-cycle group

- GIVEN a workspace whose latest school-year label has exactly one group
- WHEN `create_student` is invoked with name fields and no `group_id`
- THEN a student MUST be created in that group
- AND the response MUST include `school_year_label` equal to the latest label

#### Scenario: group_id from an older cycle is rejected

- GIVEN a workspace with groups in both `2022-2023` and `2025-2026`
- WHEN `create_student` is invoked with a `group_id` from `2022-2023` and no `school_year_label`
- THEN the call MUST fail with a tool input error
- AND no student row MUST be created

### Requirement: Person-Name Create/Update Pause on Orthography Issues

`create_student` and `update_student` MUST check person-name fields for common
Spanish accent omissions (e.g. `Perez` → `Pérez`, `Martinez` → `Martínez`).
When issues are found and neither `apply_suggested` nor `keep_as_typed` is
strictly `true`, the tool MUST return
`status: needs_orthography_clarification` with `typed`, `suggested`, and
`issues`, and MUST NOT write a row. When `apply_suggested` is `true`, the tool
MUST persist the suggested spelling. When `keep_as_typed` is `true`, the tool
MUST persist the typed spelling unchanged.

#### Scenario: Missing accents pause create_student

- GIVEN a workspace with a creatable group in the last cycle
- WHEN `create_student` is invoked with `last_name_paternal=Perez` and no
  orthography flag
- THEN the response MUST have `status` equal to `needs_orthography_clarification`
- AND `suggested.last_name_paternal` MUST be `Pérez`
- AND no student row MUST be created

#### Scenario: apply_suggested writes accented names

- GIVEN the same workspace
- WHEN `create_student` is invoked with `Perez` / `Martinez` and
  `apply_suggested=true`
- THEN a student MUST be created with `Pérez` / `Martínez`

---

**Source**: Quizzy P4 — MCP server over the scoped API (proposal: `quizzy-p4-mcp-server`); Quizzy MCP tenant CRUD
