# Archive Report: m7-attendance

**Change**: `m7-attendance`
**Project**: `portal_nem`
**Archive Date**: 2026-08-01
**Branch tip**: `feat/m7-attendance-d3` @ `9c90d7d`
**Artifact Store**: hybrid (openspec + Engram archive-report upsert)
**Status**: COMPLETE — SDD cycle closed (intentional-with-warnings)

---

## Executive Summary

M7 Daily Attendance (attendance app, roster/bulk API, `/asistencia` UI) is
archived. Verify envelope `gentle-ai.verify-result/v1` reports **PASS WITH
WARNINGS**, **0 blockers**, **0 CRITICAL**. Tasks **22/22** complete across
deliveries D1–D3 (force-chained, stacked-to-main). Post-apply review lineage
`review-m7-attendance-verify-artifacts` (generation 3) is **approved** and
bound via gate-context `result: allow`. Delta specs synced to main; change
folder moved to `openspec/changes/archive/2026-08-01-m7-attendance/`.

---

## Gate Checklist

| Gate | Result |
|---|---|
| Tasks complete | 22/22 `[x]` in filesystem `tasks.md` — no unchecked implementation tasks |
| Verify envelope | `verdict: pass`, `blockers: 0`, `critical_findings: 0` |
| Review receipt | `terminal_state: approved` (`review-m7-attendance-verify-artifacts`, gen 3) |
| Post-apply gate | `gate-context.json` → `result: allow`, `allowed: true` |
| Action context | `repo-local`; openspec/hybrid archive inside workspace |
| CRITICAL in verify | None — archive allowed |

---

## Residual WARNINGs (carried into archive)

1. **Mock-heavy frontend tests** — `page.test.tsx` relies on `vi.mock` for
   context and API; behavior verified at integration boundary, not E2E.

2. **CSS class tone assertions** — `attendance-tones.test.tsx` asserts CSS
   class strings (acceptable for design-token verification).

3. **Accepted API follow-ups** — unbounded bulk entries, error-message
   conflation, notes round-trip not covered by dedicated API assertion.

Archive marked **intentional-with-warnings** for these non-blocking items.

---

## Engram Observation Traceability

| Artifact | Observation ID | Topic Key |
|---|---|---|
| proposal | `#340` | `sdd/m7-attendance/proposal` |
| spec | `#341` | `sdd/m7-attendance/spec` |
| design | `#342` | `sdd/m7-attendance/design` |
| tasks | `#343` | `sdd/m7-attendance/tasks` |
| verify-report | `#345` | `sdd/m7-attendance/verify-report` |
| archive-report | *(this save)* | `sdd/m7-attendance/archive-report` |

### Review lineage (filesystem)

| Artifact | Path |
|---|---|
| Receipt | `openspec/changes/archive/2026-08-01-m7-attendance/reviews/receipt.json` |
| Transaction | `openspec/changes/archive/2026-08-01-m7-attendance/reviews/transaction.json` (`state: approved`) |
| Gate context | `openspec/changes/archive/2026-08-01-m7-attendance/reviews/gate-context.json` (`result: allow`) |
| Predecessor lineage | `review-m7-attendance-remediation-78fd994` (recovery gen 3, scope-changed) |

---

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| `attendance` | Created | 6 requirements, 11 scenarios (full spec copied to main) |
| `authorization` | Updated | 1 ADDED requirement, 3 scenarios (Attendance Endpoints Map Custom Actions to Capabilities) |
| `tenancy-isolation` | Updated | 1 ADDED requirement, 2 scenarios (RLS Coverage Extends to Attendance Records) |

### Source of Truth Updated

- `openspec/specs/attendance/spec.md` *(new)*
- `openspec/specs/authorization/spec.md`
- `openspec/specs/tenancy-isolation/spec.md`

---

## Archive Contents

| Artifact | Status |
|---|---|
| `proposal.md` | ✅ |
| `exploration.md` | ✅ |
| `specs/` (3 domains) | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (22/22 complete) |
| `apply-progress.md` | ✅ |
| `verify-report.md` | ✅ |
| `reviews/` (receipt, transaction, gate-context, chain-bundle) | ✅ |
| `archive-report.md` | ✅ |

Active changes directory no longer contains `m7-attendance`.

---

## Implementation Summary

| Delivery | Scope | Tests |
|---|---|---|
| D1 | Model + RLS + services | 18 unit (models, RLS, services) |
| D2 | DRF roster/bulk API + OpenAPI | 12 integration (API + capabilities) |
| D3 | `/asistencia` page + hooks + nav + tones | 9 frontend (page + tones) |

**Total**: 39 tests green; 16/16 spec scenarios compliant.

---

## SDD Cycle Complete

The change has been fully planned, implemented, verified, reviewed, and archived.
Ready for the next change.
