# Delta for tenancy-isolation

## ADDED Requirements

### Requirement: Cross-Origin Credentialed Requests Restricted to Trusted Origins

The system MUST permit cross-origin, credentialed (cookie-bearing) requests
only from an explicit allowlist of trusted origins (CORS allowlist and
`CSRF_TRUSTED_ORIGINS`). Requests from origins outside the allowlist MUST NOT
receive `Access-Control-Allow-Credentials` and MUST NOT be able to complete a
credentialed CSRF-protected write.

#### Scenario: Trusted origin can complete a credentialed request

- GIVEN a request originates from an origin present in the CORS/CSRF trusted-origin allowlist
- WHEN the client sends a credentialed request with the CSRF token echoed
- THEN the response MUST include CORS headers permitting that origin with credentials
- AND the request MUST be processed normally

#### Scenario: Untrusted origin is rejected

- GIVEN a request originates from an origin NOT present in the trusted-origin allowlist
- WHEN the client sends a credentialed cross-origin request
- THEN the system MUST NOT grant that origin `Access-Control-Allow-Credentials`
- AND a state-changing request from that origin MUST be rejected

### Requirement: Workspace-List Read Exposes Only the Caller's Own Membership Rows

The workspace-list read (`GET /api/workspaces/`) necessarily queries across
membership rows spanning multiple workspaces to find the caller's own
memberships. This query MUST still be scoped to rows where the membership's
user is the requesting caller, and MUST NOT leak membership or workspace rows
belonging only to other users.

#### Scenario: Cross-workspace read stays scoped to the caller's own rows

- GIVEN memberships exist for multiple users across multiple workspaces
- WHEN the workspace-list read executes for caller U
- THEN only membership rows where the user is U MUST be returned
- AND no membership row belonging to a different user MUST be returned, regardless of workspace
