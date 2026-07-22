# Design: m2b-invitations — WorkspaceInvitation + invite/accept/revoke

## Technical Approach

Service-layer only, mirroring M2a's `provision_signup` (no HTTP). Add one plain-FK
`WorkspaceInvitation` model, three service functions, and an in-place discovery hook
on the signup path. Business rules (token, expiry, state guards, capability checks)
live in `services.py`; the model stays a dumb record. Follows Approach 1 (extend
signup in place), locked in the proposal.

## Architecture Decisions

### Decision: Plain `ForeignKey(Workspace)`, NOT `ScopedModel` / NOT in `SCOPED_TABLES`
| Option | Tradeoff | Decision |
|--------|----------|----------|
| `ScopedModel` + RLS | Uniform with domain models, but `ScopedManager.none()` and RLS hide the invitee's own pending invite (they are not yet a member; `TenancyMiddleware` 403s non-members) | Rejected |
| Plain FK, excluded from RLS | Invitee reaches own invite by token; inviter side filters explicitly | **Chosen** |

Same bootstrap class as `Membership` (must be reachable before/without `app.workspace_id`).
`0005` migration MUST NOT append to `0003_rls.py::SCOPED_TABLES`. Document inline so no
reviewer "fixes" it.

### Decision: Authorize by two distinct paths
- Inviter (create/revoke): `has_permission(membership, "manage_members")` (owner+admin, no
  `permissions.py` change) + explicit `filter(workspace=membership.workspace)`.
- Invitee (accept): `get(token=…, status=PENDING)` + `user.email == invite.email` ownership
  (capability-token semantics, not tenancy).

### Decision: Lazy expiry, no Celery
`expires_at < now()` evaluated at every read/accept; service persists `status=expired` as a
side effect. Never trust raw `status="pending"` without the time check.

## Data Flow

    invite_member ── manage_members? ──> create PENDING (token, expires_at=now+7d)
    accept_invitation ── token+email+not-terminal+not-expired ──> [atomic] Membership + status=accepted
    revoke_invitation ── manage_members? + pending ──> status=revoked
    provision_signup ── [atomic] Workspace+User+Membership ──> discover pending invites by email (read-only)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/workspaces/models.py` | Modify | Add `WorkspaceInvitation` (plain FK, `Status` TextChoices, indexes) |
| `backend/workspaces/services.py` | Modify | `invite_member`, `accept_invitation`, `revoke_invitation`, `discover_pending_invites` + hook |
| `backend/workspaces/migrations/0005_workspaceinvitation.py` | Create | New table; depends on `0004`; NO `SCOPED_TABLES` change |
| `backend/workspaces/tests/test_invitations.py` | Create | RED tests, reuse atomicity pattern |

## Interfaces / Contracts

```python
class WorkspaceInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"; ACCEPTED = "accepted"
        REVOKED = "revoked"; EXPIRED = "expired"
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=Membership.Role.choices)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sent_invitations")
    token = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    class Meta:
        db_table = "workspaces_workspaceinvitation"
        indexes = [models.Index(fields=["workspace", "status"]),
                   models.Index(fields=["email", "status"])]
    # objects = default Manager (NOT ScopedManager)

# services.py — token = secrets.token_urlsafe(32); expires_at = timezone.now()+timedelta(days=7)
def invite_member(*, inviter_membership, email, role) -> WorkspaceInvitation
def accept_invitation(*, user, token) -> Membership            # atomic
def revoke_invitation(*, actor_membership, invitation) -> WorkspaceInvitation
def discover_pending_invites(*, user) -> QuerySet              # read-only, no Membership
```

Guards (service-layer): capability check raises `PermissionDenied`; terminal/expired invite
rejects further transition; accept when already a member = idempotent/conflict guard (per spec);
accept ownership mismatch rejected. `accept_invitation` wraps Membership create + status flip in
`transaction.atomic()`.

## Testing Strategy (RED first — strict TDD)

| Layer | What to Test |
|-------|-------------|
| Unit | owner/admin invite succeeds; member cannot (`PermissionDenied`); token unique + 7d expiry |
| Unit | accept creates Membership(role=invite.role) + status→accepted atomically; rollback leaves no Membership on forced failure |
| Unit | accept rejects: email mismatch, terminal status, `expires_at < now` (lazy expiry → expired) |
| Unit | revoke pending→revoked; revoke on terminal rejected |
| Unit | `discover_pending_invites` returns pending-by-email and creates NO Membership |
| Integration | invitation reachable by token with no active workspace / as non-member (RLS-exclusion proof); absent from `SCOPED_TABLES` |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. Pure Django ORM/service change.

## Migration / Rollout

Single additive migration `0005_workspaceinvitation` (depends on `0004`). No data backfill, no
`SCOPED_TABLES`/RLS-policy edit, no `AUTH_USER_MODEL` impact.

**Rollback**: `manage.py migrate workspaces 0004` drops the table cleanly (reverse of a plain
`CreateModel`); revert model/service edits. No RLS state touched.

## Open Questions

- [ ] Accept-when-already-member: idempotent no-op vs. raise conflict — spec must pin the exact
  behavior (design allows either; service enforces whichever spec chooses).
- [ ] Whether `discover_pending_invites` persists lazy `expired` transitions on discovered rows
  or leaves them untouched (read-only) — leaning read-only; confirm in spec.
