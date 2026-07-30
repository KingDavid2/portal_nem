# Spec: identity-auth

Core identity and authentication requirements for the Portal system.

## Requirements

### Requirement: Custom Email User Model

The system MUST use a custom user model identified by email (no username field), and `AUTH_USER_MODEL` MUST be configured before the first migration runs.

#### Scenario: User created with email as identifier

- GIVEN a fresh database with no migrations applied
- WHEN the initial migration for the custom user model runs
- THEN the `users` app owns the user table and no default `auth.User` table is created

#### Scenario: Duplicate email rejected

- GIVEN a user already exists with email `teacher@example.com`
- WHEN a second user is created with the same email
- THEN the system MUST reject the creation with a uniqueness error

### Requirement: Session-Cookie Authentication

The system MUST authenticate requests via an httpOnly session cookie with CSRF protection enabled. The system MUST NOT use JWT or any token stored in client-readable storage (e.g., localStorage) for authentication.

#### Scenario: Login issues httpOnly session cookie

- GIVEN a registered user with valid credentials
- WHEN the user submits a login request
- THEN the response MUST set a session cookie with the `httponly` flag
- AND the cookie MUST NOT be readable via client-side JavaScript

#### Scenario: State-changing request without CSRF token is rejected

- GIVEN an authenticated session
- WHEN a state-changing request (e.g., POST) is sent without a valid CSRF token
- THEN the system MUST reject the request with a CSRF failure

#### Scenario: Unauthenticated request denied

- GIVEN no valid session cookie is present
- WHEN a request is made to an authenticated endpoint
- THEN the system MUST deny the request with an authentication-required error

### Requirement: Session Login/Logout/Me Endpoints

The system MUST expose `POST /api/auth/login/`, `POST /api/auth/logout/`, and
`GET /api/auth/me/` as the production session-auth surface. These MUST use
the existing session-cookie mechanism (no JWT).

#### Scenario: Login with valid credentials

- GIVEN a registered user with valid credentials
- WHEN the client sends `POST /api/auth/login/` with those credentials
- THEN the response MUST be a 200-class status
- AND the response MUST set an httpOnly session cookie

#### Scenario: Login with invalid credentials

- GIVEN a set of credentials that do not match any user, or a wrong password
- WHEN the client sends `POST /api/auth/login/` with those credentials
- THEN the response MUST be a 4xx status
- AND no session cookie MUST be set

#### Scenario: Logout clears the session

- GIVEN an authenticated session
- WHEN the client sends `POST /api/auth/logout/`
- THEN the session MUST be cleared server-side
- AND a subsequent request to `GET /api/auth/me/` using the prior session cookie MUST be denied

#### Scenario: Me returns the current user when authenticated

- GIVEN an authenticated session
- WHEN the client sends `GET /api/auth/me/`
- THEN the response MUST return the current user's identity

#### Scenario: Me denies anonymous access

- GIVEN no valid session cookie is present
- WHEN the client sends `GET /api/auth/me/`
- THEN the response MUST be a 401 or 403 status

### Requirement: CSRF-Bootstrap Path Sets the CSRF Cookie

The system MUST expose a GET-able path that sets the `csrftoken` cookie for a
client that has none, regardless of whether this is a dedicated endpoint or
piggybacked on an existing GET endpoint.

#### Scenario: First unauthenticated GET establishes the CSRF cookie

- GIVEN a client with no `csrftoken` cookie
- WHEN the client issues a GET request to the CSRF-bootstrap path
- THEN the response MUST set the `csrftoken` cookie
- AND the cookie MUST be readable by client-side JavaScript (not httpOnly)

#### Scenario: Client echoes the bootstrapped token on a subsequent write

- GIVEN a client has obtained a `csrftoken` cookie via the bootstrap path
- WHEN the client sends a state-changing request with that token echoed in the CSRF header
- THEN the request MUST NOT be rejected for missing/invalid CSRF token

### Requirement: Hashed Per-Membership API Token Authentication

The system MUST support a second authentication path alongside session-cookie
auth, for non-browser callers (the MCP server) that never run
`TenancyMiddleware`. It MUST provide a `WorkspaceApiToken` model at
`backend/mcp_server/models.py` with the fields:

| Field | Contract |
|---|---|
| `membership` | FK to `Membership`, `on_delete=CASCADE` — the token authenticates a membership, not a user, so scope and role come from one row |
| `name` | human label, for the operator revoking it |
| `token_hash` | `CharField(max_length=64, unique=True)` holding `sha256(raw).hexdigest()` |
| `created_at` | mint timestamp |
| `last_used_at` | nullable; last successful resolution |
| `revoked_at` | nullable; set to revoke |

Only the SHA-256 hex digest MUST be stored. The raw token MUST be printed once
at mint time and MUST NOT be persisted, logged, or recoverable from the row.

`WorkspaceApiToken` MUST be a plain `models.Model`, **NOT** a `ScopedModel`. The
token row must be readable *before* any workspace scope exists — it is the row
that establishes scope — so a `ScopedManager` would fail closed on the very
lookup that resolves identity. This is the same documented-exclusion precedent
already carried by `WorkspaceInvitation` and `WorkspaceHistory` in
`backend/workspaces/models.py`, and the model MUST carry that reason in its
docstring.

Session-cookie authentication MUST remain the browser surface; this token path
MUST NOT be accepted by the DRF API surface, and MUST NOT be stored in
client-readable browser storage.

#### Scenario: Only the hash is persisted

- GIVEN a token is minted for a membership
- WHEN the stored `WorkspaceApiToken` row is inspected
- THEN `token_hash` MUST equal `sha256(raw).hexdigest()`
- AND the raw token string MUST NOT appear in any field of the row

#### Scenario: Token row is readable with no workspace scope active

- GIVEN no workspace contextvar is set and no `app.workspace_id` is active
- WHEN a `WorkspaceApiToken` is looked up by `token_hash`
- THEN the row MUST be returned
- AND the lookup MUST NOT fail closed the way a `ScopedModel` read would

### Requirement: Token Resolution Is Uniform for Unknown and Revoked Tokens

The system MUST provide `resolve_membership(raw_token) -> Membership | None`.
It MUST hash the raw token and look the row up by `token_hash`. It MUST return
`None` when the token matches no row, and MUST return `None` when the matched
row has a non-null `revoked_at`.

The two outcomes MUST be indistinguishable to the caller: no distinct error
type, no distinct message, no distinct status code, and no timing- or
side-effect-visible difference such as touching `last_used_at`. A caller MUST
NOT be able to learn that a token once existed.

Tokens are non-expiring in v1. Revocation is explicit, via `revoked_at`; there
is no TTL.

#### Scenario: Valid token resolves to its membership

- GIVEN an unrevoked token minted for a membership in workspace A
- WHEN `resolve_membership` is called with the raw token
- THEN it MUST return that `Membership`
- AND `last_used_at` MUST be updated

#### Scenario: Revoked and unknown tokens are indistinguishable

- GIVEN a token whose `revoked_at` is set, and a raw token matching no stored row
- WHEN `resolve_membership` is called with each
- THEN both MUST return `None`
- AND neither MUST raise a distinguishing error
- AND the two resulting transport responses MUST be identical

#### Scenario: A failed resolution touches no workspace data

- GIVEN a raw token that resolves to no membership
- WHEN `resolve_membership` is called
- THEN no workspace-scoped ORM read or write MUST occur
- AND no tool body MUST be executed

### Requirement: Tokens Are Issued Only by a Management Command

Token issuance MUST be available only through a `manage.py create_mcp_token`
command. The system MUST NOT expose a token-minting UI or API endpoint in v1.
The command MUST print the raw token exactly once, at mint time, and MUST make
clear it cannot be retrieved again. Any workspace MAY mint a token, including
demo workspaces.

#### Scenario: Command mints a token and prints the raw value once

- GIVEN an existing membership
- WHEN `manage.py create_mcp_token` is run for that membership with a name
- THEN a `WorkspaceApiToken` row MUST be created for it
- AND the raw token MUST be printed exactly once to the command output

#### Scenario: No HTTP surface mints tokens

- GIVEN the registered URLconf
- WHEN it is searched for a token-issuance route
- THEN no endpoint MUST exist that creates a `WorkspaceApiToken`

#### Scenario: A demo workspace can mint a token

- GIVEN a membership in a demo-provisioned workspace
- WHEN `manage.py create_mcp_token` is run for it
- THEN a token MUST be minted and resolve to that membership

---

**Source**: M2a — Tenancy Foundation Core (proposal: `2026-07-22-m2a-tenancy-core`); M3 — Frontend Foundation (proposal: `m3-frontend-foundation`); Quizzy P4 — MCP server (proposal: `quizzy-p4-mcp-server`)
