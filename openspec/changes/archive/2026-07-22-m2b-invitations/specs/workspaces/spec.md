# Delta for Workspaces

## ADDED Requirements

### Requirement: Signup-Time Invite Discovery

During signup provisioning, the system MUST look up pending
`WorkspaceInvitation` records matching the new user's email and surface them
as an association/discovery result. This lookup MUST NOT create any
`Membership` record; joining a workspace always requires a separate, explicit
accept step.

#### Scenario: Signup surfaces a matching pending invite

- GIVEN a `pending` invite exists for `newuser@example.com`
- WHEN a user signs up with email `newuser@example.com`
- THEN signup provisioning MUST discover the pending invite and include it in the signup result
- AND no Membership MUST be created for the invited workspace as a result of signup

#### Scenario: Signup with no matching invites is unaffected

- GIVEN no invite exists for `newuser2@example.com`
- WHEN a user signs up with email `newuser2@example.com`
- THEN signup provisioning MUST complete as before (personal Workspace, User, owner Membership)
- AND no invite-related side effects MUST occur

#### Scenario: Expired or terminal invites are not surfaced as actionable

- GIVEN an invite for `newuser@example.com` has `status` in `accepted|revoked|expired`, or `status=pending` with `expires_at` in the past
- WHEN a user signs up with email `newuser@example.com`
- THEN the system MUST NOT surface that invite as an actionable pending invite

---

**Source**: M2b — Invitations (proposal: `m2b-invitations`)
