# Frontend Foundation Specification

## Purpose

Behavior the Next.js frontend and its generated API client MUST exhibit: a
schema-driven TS client, a session/CSRF auth lifecycle, workspace-aware
requests, and end-to-end CRUD for the M3 school-structure entities. Describes
observable behavior only — client stack, codegen tool, and CSRF-bootstrap
endpoint shape are open design decisions.

## Requirements

### Requirement: Generated TypeScript Client Tracks the OpenAPI Schema

The generated TS client MUST be derived from the backend's OpenAPI schema, and
the schema MUST be the single source of truth for request/response shapes. CI
MUST fail when the committed generated client is out of sync with the current
schema.

#### Scenario: Client matches current schema

- GIVEN the backend OpenAPI schema and the committed generated TS client
- WHEN CI regenerates the client from the current schema and diffs it against the committed one
- THEN the diff MUST be empty and CI MUST pass

#### Scenario: Drift between schema and committed client fails CI

- GIVEN the backend OpenAPI schema has changed (e.g., a field renamed) since the client was last generated
- WHEN CI regenerates the client and diffs it against the committed one
- THEN CI MUST fail with a non-empty diff

### Requirement: Session/CSRF Auth Lifecycle

The client MUST authenticate using the httpOnly session cookie and CSRF-echo
flow (no token in localStorage). It MUST send credentials on every request and
attach the CSRF token on state-changing requests, obtained via whatever
CSRF-bootstrap path the backend exposes.

#### Scenario: Full login-session-logout lifecycle

- GIVEN an unauthenticated client
- WHEN the client obtains a CSRF token, submits valid credentials to log in, makes an authenticated data request, then logs out
- THEN each step MUST succeed in order
- AND after logout, a subsequent authenticated data request MUST be rejected

#### Scenario: Requests always include credentials

- GIVEN the client issues any request to the backend API
- WHEN the request is sent
- THEN it MUST include credentials (cookies) regardless of endpoint

#### Scenario: State-changing request without CSRF token is rejected

- GIVEN an authenticated session with no CSRF token attached to the client
- WHEN the client issues a state-changing request (POST/PATCH/DELETE)
- THEN the backend MUST reject the request with a CSRF failure

### Requirement: Active-Workspace Context on Every Data Request

The frontend MUST maintain an active-workspace switcher and MUST attach the
active workspace id as the `X-Workspace-Id` header on every data request.

#### Scenario: Switching workspace changes the header on subsequent requests

- GIVEN the user has memberships in workspace A and workspace B
- WHEN the user switches the active workspace from A to B
- THEN all subsequent data requests MUST carry `X-Workspace-Id: B`

#### Scenario: No active workspace selected blocks data requests

- GIVEN no active workspace has been selected yet
- WHEN the client would otherwise issue a data request
- THEN the client MUST NOT send that request without an `X-Workspace-Id` header

### Requirement: CRUD Screens Cover School Structure Entities

The frontend MUST provide create, list, edit, and delete flows for School,
SchoolYear, Group, and Student, each executed through the generated TS client.

#### Scenario: Full CRUD lifecycle for an entity

- GIVEN an authenticated, workspace-scoped session
- WHEN the user creates, lists, edits, and deletes a School (or SchoolYear/Group/Student) via its screen
- THEN each operation MUST succeed through the generated client
- AND the list view MUST reflect the created/edited/deleted state afterward

#### Scenario: Server-side validation error surfaces to the user

- GIVEN the user submits an invalid create/edit payload (e.g., missing required field)
- WHEN the generated client sends the request
- THEN the backend's validation error MUST be surfaced in the screen, not silently swallowed
