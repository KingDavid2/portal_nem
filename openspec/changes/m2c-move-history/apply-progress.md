# Apply Progress: M2c — Move Member + Workspace History

Status: all 4 deliveries complete, all tasks `[x]`, full suite green (76 passed),
`manage.py migrate --check` clean.

## Deliveries

- D1 `feat(workspaces): WorkspaceHistory model + migration` — commit `dfbcc62`
  - `backend/workspaces/models.py`: `WorkspaceHistory` model (default `Manager`,
    NOT `ScopedModel`), `Action` TextChoices, `SET_NULL` on actor/from/to with
    audit-retention docstring rationale.
  - `backend/workspaces/migrations/0006_workspacehistory.py`: plain
    `CreateModel`, RLS-exclusion comment (mirrors 0005 style).
  - `backend/workspaces/tests/test_move.py` created (D1 tests).
- D2 `feat(workspaces): move_member_to_workspace atomic core` — commit `45babe1`
  - `backend/workspaces/services.py`: `move_member_to_workspace` happy-path
    mechanics (no auth/edge checks yet) inside one `transaction.atomic()`.
  - Rollback test patches `WorkspaceHistory.objects.create` to raise.
- D3 `feat(workspaces): move authorization + edge-case guards` — commit `869dec5`
  - Extended `move_member_to_workspace` with the 6-step pre-write validation
    block in design order: (1) same-actor-user guard (critical security
    guard, kept), (2) dual `manage_members` check, (3) source-workspace
    match, (4) owner-move rejection, (5) group-type-only target, (6)
    duplicate-target-membership rejection.
- D4 `test(workspaces): RLS backstop for move history writes` — commit `9f69dee`
  - Raw-psycopg `portal_app` test inserting a `moved` row spanning two
    workspaces with no `app.workspace_id` set — passes, proving
    `WorkspaceHistory`'s exclusion from `SCOPED_TABLES`.
  - `manage.py migrate --check` confirmed clean.

## Notes / Deviations

- None from design/spec. Applied a local migration during D1 (`python manage.py
  migrate workspaces`) so the `test_migrate_check_reports_no_pending_migrations`
  scaffold test stays green — this is a dev-environment DB sync step, not a
  code change.
- No HTTP/DRF, no invite/accept/revoke history retrofit — out of scope, not
  touched.

## Test file

`backend/workspaces/tests/test_move.py` — 14 tests total (3 model, 3 happy-path
move-core, 7 authorization/edge-case, 1 RLS backstop).
