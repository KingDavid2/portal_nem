# Invitations Specification

## Purpose

Enable owners/admins of a group workspace to invite members by email and let
invitees join via an explicit accept step — never auto-join. Governs the
`WorkspaceInvitation` model, its status state machine, and the
invite/accept/revoke service lifecycle.

## Requirements

### Requirement: WorkspaceInvitation Model Shape

The system MUST provide a `WorkspaceInvitation` model with fields:
`workspace` (`ForeignKey(Workspace)`, plain FK — NOT a `ScopedModel`), `email`,
`role` (constrained to the same choices as `Membership.role`), `invited_by`
(FK to inviting user), `token` (unique, generated via
`secrets.token_urlsafe(32)`), `status` (`pending|accepted|expired|revoked`),
`created_at`, `expires_at`.

#### Scenario: Token is unique and unguessable

- GIVEN a new invite is created
- WHEN the invite record is persisted
- THEN `token` MUST be generated via `secrets.token_urlsafe(32)`
- AND `token` MUST be unique across all `WorkspaceInvitation` rows

#### Scenario: Expiry computed at creation

- GIVEN a new invite is created via the invite service
- WHEN the record is persisted
- THEN `expires_at` MUST be set to `now() + 7 days` by the service (not the model default)

### Requirement: RLS Exclusion

`WorkspaceInvitation` MUST NOT be listed in `SCOPED_TABLES` and MUST NOT
inherit `ScopedModel`. Authorization MUST be enforced in the service layer via
explicit filters, not RLS or `ScopedManager`.

#### Scenario: Invitee reaches own pending invite without workspace membership

- GIVEN a user is invited to a workspace they are not yet a member of
- WHEN that user looks up the invite by its token
- THEN the system MUST return the invite without requiring an active `Membership`-derived workspace context

#### Scenario: Inviter-side access is filtered explicitly, not by RLS

- GIVEN an owner or admin lists pending invites for their workspace
- WHEN the list query executes
- THEN the system MUST filter by an explicit `workspace=` clause scoped to the caller's membership, not rely on RLS

### Requirement: Invite Creation Authorization

The system MUST allow creating an invite only when the inviter's `Membership`
in the target workspace satisfies `has_permission(membership, "manage_members")`.

#### Scenario: Owner creates an invite

- GIVEN a user with an `owner` Membership in workspace W
- WHEN they invite `newuser@example.com` with role `member`
- THEN the system MUST create a `WorkspaceInvitation` with `status=pending`

#### Scenario: Admin creates an invite

- GIVEN a user with an `admin` Membership in workspace W
- WHEN they invite an email with role `member`
- THEN the system MUST create a `WorkspaceInvitation` with `status=pending`

#### Scenario: Member is denied invite creation

- GIVEN a user with a `member` Membership in workspace W
- WHEN they attempt to create an invite
- THEN the system MUST reject the request
- AND no `WorkspaceInvitation` record MUST be created

### Requirement: Accept Flow

The system MUST allow an invitee holding a valid, non-terminal, non-expired
token whose authenticated email matches `invite.email` to accept the invite.
Accepting MUST atomically create a `Membership(user, workspace, invite.role)`
and set `invite.status = accepted`.

#### Scenario: Valid accept creates Membership and flips status

- GIVEN a `pending` invite for `invitee@example.com` to workspace W with role `member`
- WHEN the authenticated user with email `invitee@example.com` accepts using the invite token
- THEN a `Membership(user, workspace=W, role="member")` MUST be created
- AND the invite `status` MUST become `accepted`
- AND both changes MUST occur in a single atomic transaction

#### Scenario: Email mismatch rejects accept

- GIVEN a `pending` invite for `invitee@example.com`
- WHEN a user authenticated as `someone-else@example.com` attempts to accept it
- THEN the system MUST reject the accept
- AND no Membership MUST be created
- AND the invite `status` MUST remain `pending`

#### Scenario: Accepting an expired invite is rejected

- GIVEN a `pending` invite whose `expires_at` is in the past
- WHEN the matching invitee attempts to accept it
- THEN the system MUST reject the accept as expired
- AND MUST persist `status = expired` as a side effect
- AND no Membership MUST be created

#### Scenario: Accepting a terminal invite is rejected

- GIVEN an invite with `status` in `accepted|revoked|expired`
- WHEN the matching invitee attempts to accept it
- THEN the system MUST reject the accept
- AND MUST NOT change `status` or create a Membership

### Requirement: Idempotent Accept for Existing Members

If the invitee already holds a `Membership` in the target workspace at accept
time, the system MUST treat accept as an idempotent no-op: it MUST flip the
invite to `accepted` without creating a duplicate `Membership`, and MUST NOT
raise a conflict error.

#### Scenario: Accept when already a member succeeds without duplication

- GIVEN a `pending` invite for `invitee@example.com` to workspace W
- AND the invitee already holds a `Membership` in workspace W
- WHEN the invitee accepts the invite
- THEN the invite `status` MUST become `accepted`
- AND no second `Membership` row MUST be created for that user/workspace pair

### Requirement: Revoke

The system MUST allow a caller whose `Membership` satisfies
`has_permission(membership, "manage_members")` to revoke a `pending` invite in
their workspace, setting `status = revoked`. Revoking a terminal invite MUST
be rejected.

#### Scenario: Owner revokes a pending invite

- GIVEN a `pending` invite in workspace W
- WHEN an owner of W revokes it
- THEN the invite `status` MUST become `revoked`

#### Scenario: Revoking a terminal invite is rejected

- GIVEN an invite with `status` in `accepted|revoked|expired`
- WHEN an owner or admin attempts to revoke it
- THEN the system MUST reject the revoke
- AND `status` MUST remain unchanged

#### Scenario: Member without manage_members cannot revoke

- GIVEN a `pending` invite in workspace W
- WHEN a user with a `member` Membership in W attempts to revoke it
- THEN the system MUST reject the revoke
- AND `status` MUST remain `pending`

### Requirement: Lazy Expiry

The system MUST treat a `pending` invite whose `expires_at` has passed as
expired for all read and accept operations, regardless of its persisted
`status`. The system MUST persist `status = expired` as a side effect of
evaluating an expired invite. A `pending` row past `expires_at` MUST NEVER be
acceptable.

#### Scenario: Reading a stale pending invite surfaces it as expired

- GIVEN an invite with `status=pending` and `expires_at` in the past (not yet lazily evaluated)
- WHEN the invite is read by token
- THEN the system MUST report it as `expired`
- AND MUST persist `status = expired` on the record

#### Scenario: Expired invite cannot be accepted even before lazy read

- GIVEN an invite with `status=pending` and `expires_at` in the past
- WHEN the invitee attempts to accept it directly
- THEN the system MUST reject the accept as expired

### Requirement: Terminal State Machine

`accepted`, `revoked`, and `expired` are terminal states. The system MUST NOT
allow any further status transition once an invite reaches a terminal state.

#### Scenario: No transition out of a terminal state

- GIVEN an invite with `status` in `accepted|revoked|expired`
- WHEN any service operation (accept or revoke) is attempted on it
- THEN the system MUST reject the operation
- AND the `status` MUST remain unchanged

---

**Source**: M2b — Invitations (proposal: `m2b-invitations`)
