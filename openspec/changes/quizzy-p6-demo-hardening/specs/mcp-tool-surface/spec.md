# Delta for MCP Tool Surface

## MODIFIED Requirements

### Requirement: Streamable-HTTP Arm Is Flag-Gated, Off by Default, and Per-Token Rate-Limited

The Streamable-HTTP mount MUST be gated by `settings.MCP_HTTP_ENABLED`, which
MUST default to **off**. When the flag is off, the route MUST NOT be registered
at all — following the `demo_mode.enabled()` pattern in `backend/config/urls.py`,
so the path 404s *by absence*, not because a check rejected the caller.

When the flag is on, the transport MUST take its identity from an
`Authorization: Bearer <token>` header and MUST resolve it to a membership. A
missing, malformed, unknown, or revoked bearer token MUST yield 401.

When the flag is on, the transport MUST apply a per-token rate limit to all tool
invocations. A caller whose token has exhausted the rate limit MUST receive 429.
No tool MUST be executed for a rate-limited request. The per-token rate ceiling
SHOULD be configurable via a dedicated setting.

(Previously: no per-token rate limit was applied when the HTTP arm was enabled)

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

#### Scenario: Token at the per-token rate limit receives 429

- GIVEN `MCP_HTTP_ENABLED` is on
- AND a caller's token has reached the per-token rate ceiling
- WHEN the caller makes another tool invocation
- THEN the response MUST be 429
- AND no tool MUST be executed
