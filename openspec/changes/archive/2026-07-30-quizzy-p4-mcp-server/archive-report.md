# Archive Report: quizzy-p4-mcp-server

**Change**: `quizzy-p4-mcp-server`
**Project**: `portal_nem`
**Archive Date**: 2026-07-30
**Branch tip**: `feat/quizzy-p4-s5-http-arm` @ `955d81c` (stacked on S4)
**Artifact Store**: openspec (+ Engram archive-report upsert)
**Status**: COMPLETE — SDD cycle closed (intentional-with-warnings)

---

## Executive Summary

Quizzy Phase 4 (read-only MCP server over the scoped API) is archived. Verify
envelope `gentle-ai.verify-result/v1` reports **PASS**, **0 blockers**,
**0 CRITICAL**. Tasks **49/49** complete. Post-apply review lineage
`review-f4b1727400b22e80` is **approved** and bound via bind-sdd. Delta specs
synced to main; change folder moved to
`openspec/changes/archive/2026-07-30-quizzy-p4-mcp-server/`.

---

## Gate Checklist

| Gate | Result |
|---|---|
| Tasks complete | 49/49 `[x]` — no unchecked implementation tasks |
| Verify envelope | `verdict: pass`, `blockers: 0`, `critical_findings: 0` |
| Review receipt | `terminal_state: approved` (`review-f4b1727400b22e80`) |
| bind-sdd | `.git/gentle-ai/sdd-review-bindings/v1/quizzy-p4-mcp-server/binding.json` present; post-apply gate |
| Action context | `repo-local`; edits inside `allowedEditRoots` |
| CRITICAL in verify | None — archive allowed |

---

## Residual WARNINGs (carried into archive)

1. **5.7 live NL demo not driven** — Phase exit gate required an MCP client
   answering a natural-language question over a real demo tenant (plus
   cross-tenant plan-id isolation smoke). Automated tenancy proofs pass;
   the live NL demo over demo tenants was **not** exercised. Operational
   follow-up; not an archive blocker.

2. **5.3 happy path does not exercise Django/ASGI mount (helper-only)** —
   From review `review-f4b1727400b22e80`: 
   `test_flag_on_valid_bearer_list_groups_returns_workspace_a` calls
   `handle_http_call_tool` on a cold thread, not
   `mcp_http_view` → `StreamableHTTPSessionManager` → ContextVar `call_tool`.
   Workspace A vs B isolation is proven on the helper path; a mount/ContextVar
   wiring regression would not be caught. Non-blocking WARNING; follow-up
   mount-path test desirable.

Archive marked **intentional-with-warnings** for these two residual WARNINGs
(explicitly required by the archive action context).

---

## Engram Observation Traceability

| Artifact | Observation ID | Topic Key |
|---|---|---|
| proposal | `#280` | `sdd/quizzy-p4-mcp-server/proposal` |
| spec | `#282` | `sdd/quizzy-p4-mcp-server/spec` |
| design | `#283` | `sdd/quizzy-p4-mcp-server/design` |
| tasks | `#284` | `sdd/quizzy-p4-mcp-server/tasks` |
| verify-report | `#300` | `sdd/quizzy-p4-mcp-server/verify-report` |
| archive-report | *(this save)* | `sdd/quizzy-p4-mcp-server/archive-report` |

### Review lineage (filesystem)

| Artifact | Path |
|---|---|
| Receipt | `.git/gentle-ai/review-transactions/v2/review-f4b1727400b22e80/review-receipt.json` |
| State | `.git/gentle-ai/review-transactions/v2/review-f4b1727400b22e80/review-state.json` (`state: approved`) |
| Binding | `.git/gentle-ai/sdd-review-bindings/v1/quizzy-p4-mcp-server/binding.json` |

---

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| `mcp-tool-surface` | **Created** | 6 ADDED requirements (registry, read-only surface, payload reuse, auth required, stdio env identity, flag-gated HTTP) |
| `tenancy-isolation` | **Updated** | 1 ADDED requirement — MCP tools establish own workspace RLS context (Celery sibling) |
| `identity-auth` | **Updated** | 3 ADDED requirements — hashed per-membership API token, uniform resolve, manage.py issuance |
| `authorization` | **Updated** | 1 ADDED requirement — MCP capability map via `has_permission` |

No REMOVED or RENAMED requirements. No destructive merge.

### Source of Truth Updated

- `openspec/specs/mcp-tool-surface/spec.md` *(new)*
- `openspec/specs/tenancy-isolation/spec.md`
- `openspec/specs/identity-auth/spec.md`
- `openspec/specs/authorization/spec.md`

---

## Archive Contents

**Source**: `openspec/changes/quizzy-p4-mcp-server/`
**Destination**: `openspec/changes/archive/2026-07-30-quizzy-p4-mcp-server/`

- proposal.md ✅
- design.md ✅
- tasks.md ✅ (49/49 complete, no unchecked)
- verify-report.md ✅ (`gentle-ai.verify-result/v1`, PASS, 0 blockers)
- specs/ ✅ (`mcp-tool-surface`, `tenancy-isolation`, `identity-auth`, `authorization`)
- archive-report.md ✅ *(this file)*

Active changes directory no longer contains `quizzy-p4-mcp-server`.

---

## Delivery Summary

Six stacked-to-main slices under a 400-line review budget:

| Slice | Branch | Focus |
|---|---|---|
| S1 | `feat/quizzy-p4-s1-api-token` | `WorkspaceApiToken` + `resolve_membership` + `create_mcp_token` |
| S2a | `feat/quizzy-p4-s2a-registry` | registry, typed errors, capability map, import guard |
| S2b | `feat/quizzy-p4-s2b-async-bridge` | `dispatch_async` + cold-context tenancy harness |
| S3 | `feat/quizzy-p4-s3-read-tools` | five read-only tools + payload reuse |
| S4 | `feat/quizzy-p4-s4-stdio` | stdio transport + `run_mcp` |
| S5 | `feat/quizzy-p4-s5-http-arm` @ `955d81c` | flag-gated Streamable-HTTP |

**Test evidence (verify)**: `499 passed`; migrations clean; `39` mcp_server tests; guarded Celery/pooling suites green.

---

## SDD Cycle Complete

The change has been fully planned, implemented, verified, reviewed (approved),
and archived. Ready for the next change (e.g. Quizzy P5 mutation tools, or a
focused follow-up for live NL demo / ASGI mount happy-path coverage).

**Commit note**: Archive skill does not require a commit; filesystem changes
are left staged/ready for a conventional `docs(sdd): archive quizzy-p4-mcp-server…`
commit by the orchestrator/user. No force-push; no merge to main by archive.
