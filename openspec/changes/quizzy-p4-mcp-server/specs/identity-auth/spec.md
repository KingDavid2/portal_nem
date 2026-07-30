# Delta for identity-auth

## ADDED Requirements

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
