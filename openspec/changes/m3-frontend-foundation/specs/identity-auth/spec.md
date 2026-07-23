# Delta for identity-auth

## ADDED Requirements

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
