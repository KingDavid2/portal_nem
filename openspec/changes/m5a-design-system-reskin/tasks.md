# Tasks: M5a Frontend Design System and Re-skin

## Delivery Evidence

| Delivery | Commit | Status | Evidence |
|---|---|---|---|
| D1 tokens + Inter | `fe02169` | Complete | token/font contracts; ≤400 lines |
| D2 sidebar/NavItem | `248454a` | Complete | gate-shell tests; ≤400 lines |
| D3 display primitives | `cf8342f` | Complete | render contracts; ≤400 lines |
| D4 data primitives | `9ba7495` | Complete | jsdom PDA callback; ≤400 lines |
| D5 composites | `d6b8baf` | Complete | real row composition; ≤400 lines |
| D6 login | `8cc5235` | Complete | render + auth success/error tests; ≤400 lines |
| D7a students | `1b28bf1` | Complete | filter reset/student form tests; ≤400 lines |
| D7b1 schools | `568e795` | Complete | school form test; ≤400 lines |
| D7b2 years/groups | `697eafa` | Complete | form tests; ≤400 lines |
| D8a list/generate | `c84f24a` | Complete | generation-form test; ≤400 lines |
| D8b1 viewer | `1a58d70` | Complete | PDA/step render test; ≤400 lines |
| D8b2 detail states + remediations | `c887008` → `04e5724` | Complete implementation; evidence pending | detail states, active-nav, data-truth, and viewer semantics fixes |

## Completed Requirements
- [x] D1 semantic CSS-first tokens, Inter, runtime card shadow, Pencil ink alpha/border semantics.
- [x] D2 preserves loading/auth/workspace returns before the 260px sidebar shell.
- [x] D3–D5 provide and compose all listed shared primitives.
- [x] D6 preserves `login(email,password)`, redirect, refresh, and error behavior.
- [x] D7a/D7b retain CRUD hooks, cascading selection resets, payloads, and errors.
- [x] D8a/D8b retain simple generation payload, export, regenerate, warning, and detail states.
- [x] Backend and `frontend/src/lib/api/*` remain protected.

## Verification and Pending Evidence
- `cd frontend && npm test` — **24 files / 64 tests passed**.
- `cd frontend && npx tsc --noEmit` — passed.
- `cd frontend && npm run lint` — **0 errors**; one pre-existing TanStack/React Compiler warning in `src/components/data-table.tsx`.
- `cd frontend && npm run build` — passed.
- Protected boundaries: no `backend/` or `frontend/src/lib/api/*` changes.
- Pencil nodes consulted: `ruhVX`, `DblqO`, `xzejZ`, `IOO7z`, `aetk6`, `Y0PBKM`, `ickGe`, `S4n9r`, `Dt8iE`, `L1tUtz`, `mhV91`, `al73`, `qeMf8`, `j8q40`, `FzQku`, `WDWqT`.

## Remaining Follow-ups
- Runtime-vs-Pencil visual comparison is still pending for the re-skinned routes; capture and compare authenticated screenshots before final SDD verification.
- Strict-TDD chronology/evidence remains pending reconciliation: several tests were strengthened after implementation and must not be represented as chronological RED evidence.
- Resolve the existing TanStack React Compiler warning in `frontend/src/components/data-table.tsx`, or explicitly accept it in the final review record.
- Run native review/lifecycle gates and record their informational findings with individual disposition before archive/release.

## Documentation Work Unit
- Focused check: `git diff --check -- openspec/changes/m5a-design-system-reskin/tasks.md openspec/changes/m5a-design-system-reskin/apply-progress.md` — expected clean.
- Rollback boundary: revert only these two OpenSpec evidence files; no application behavior changes.
