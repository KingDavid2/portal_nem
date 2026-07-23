# Service Health Specification

## Purpose

Provide a minimal, unauthenticated liveness endpoint so infra, uptime monitors, and
load-balancer probes can confirm the service process is up without depending on
auth, tenancy, or database availability.

## Requirements

### Requirement: Public Liveness Endpoint

The system MUST expose `GET /api/health/` that returns HTTP 200 with a JSON body
`{"status": "ok", "version": "<app version>"}` for anonymous callers.

The endpoint MUST use `AllowAny` permissions and MUST NOT require an authentication
token, session, or workspace/tenancy context.

The endpoint MUST NOT issue any database query while serving the request.

The `version` field MUST reflect the current application version string (e.g.
sourced from package/`pyproject` metadata).

#### Scenario: Anonymous request succeeds

- GIVEN no authentication credentials are provided
- WHEN a client sends `GET /api/health/`
- THEN the response status is 200
- AND the response body is `{"status": "ok", "version": "<app version>"}`

#### Scenario: No database access

- GIVEN the database connection is unavailable or intentionally not queried
- WHEN a client sends `GET /api/health/`
- THEN the response still returns HTTP 200
- AND no database query is executed while handling the request

#### Scenario: Authenticated request also succeeds

- GIVEN a client provides a valid authentication token
- WHEN the client sends `GET /api/health/`
- THEN the response status is 200
- AND the response body matches the anonymous response shape
