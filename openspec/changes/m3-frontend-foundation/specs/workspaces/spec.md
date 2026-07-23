# Delta for workspaces

## ADDED Requirements

### Requirement: Workspace-List Endpoint Returns Only the Caller's Memberships

The system MUST expose `GET /api/workspaces/` returning the authenticated
caller's own memberships (workspace id, workspace name, workspace type, and
the caller's role), and MUST NOT include any other user's memberships or
workspaces the caller does not belong to.

#### Scenario: Returns the caller's own memberships

- GIVEN user U holds memberships in workspace A (role `owner`) and workspace B (role `member`)
- WHEN U sends `GET /api/workspaces/`
- THEN the response MUST include exactly A and B
- AND each entry MUST carry workspace id, name, type, and U's role in that workspace

#### Scenario: Never includes another user's workspaces

- GIVEN user U holds a membership only in workspace A
- AND another user holds a membership in workspace C, in which U has no membership
- WHEN U sends `GET /api/workspaces/`
- THEN the response MUST NOT include workspace C

#### Scenario: Anonymous request is denied

- GIVEN no valid session cookie is present
- WHEN a request is sent to `GET /api/workspaces/`
- THEN the system MUST deny the request with an authentication-required error
