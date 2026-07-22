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

---

**Source**: M2a — Tenancy Foundation Core (proposal: `2026-07-22-m2a-tenancy-core`)
