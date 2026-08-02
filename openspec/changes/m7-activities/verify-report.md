```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:533fd8465582bd84233bbea10838fa827272359e711da2af3ec80d15019f3ece
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 10/10
scenarios: 13/13
test_command: "cd backend && uv run pytest grades/ -q; cd frontend && npm run test -- --run 'src/app/(app)/actividades/'"
test_exit_code: 0
test_output_hash: sha256:b9d57d8589523cfc5c20d3d242d053352c8bea7629d5524856b457544c8421a7
build_command: "cd backend && uv run python manage.py migrate --check"
build_exit_code: 0
build_output_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Verification Report

**Change**: m7-activities  
**Version**: N/A (delta specs under `openspec/changes/m7-activities/specs/`)  
**Mode**: Strict TDD  
**Branch tip**: `feat/m7-activities-d5` (D1–D5 stacked)  
**Verified**: 2026-08-01 (independent runtime; apply self-reports not trusted)

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 26 |
| Tasks complete | 26 (`[x]`) |
| Tasks incomplete | 0 |
| Requirements | 10 |
| Scenarios | 13 |

### Build & Tests Execution

**Build** (`migrate --check`): ✅ Passed (exit 0; empty stdout)  
**Migrations dry-run** (`makemigrations --check --dry-run`): ✅ `No changes detected` (exit 0)  
Hash dry-run: `sha256:a2bfa7b376c38062f77ce2b1e703876aaa04662f96355cdf5dc9d0d075302b05`

**Tests**: ✅ 66 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
# Backend (from backend/)
uv run pytest grades/ -q
..............................................                           [100%]
46 passed in 4.16s
# hash: sha256:8a6ef0d5bda3ded72dd1651ac1f4e6d77ca78e90680a504b73e186e3ac761bb5

# Frontend (from frontend/)
npm run test -- --run 'src/app/(app)/actividades/'
Test Files  1 passed (1)
Tests  20 passed (20)
# hash: sha256:eaecbb292a5c8b7073e3b04815729ae6da837d691d43152a83f39789a243c1d4
```

**Coverage**: ➖ Not run (threshold 0; coverage tool not required for this verify)

**Type check** (`npx tsc --noEmit`, informational — not config `build_command`): ❌ exit 1  
Errors are **outside** m7-activities changed files:
- `.next/types/validator.ts` → missing `asistencia/page.js`
- `src/lib/school-context/storage.test.ts` → `cct: null` vs `string | undefined`  
Hash: `sha256:adc70902f26a5c6fa505f27f305a55a267883fd969bcd977cc8648eca9546888`

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Term Invariants and ensure_terms | Seeds three once | `test_services.py` > `test_ensure_terms_idempotent_seeds_one_through_three` | ✅ COMPLIANT |
| Term Invariants and ensure_terms | Duplicate rejected | `test_models.py` > `test_duplicate_term_school_year_number_raises` | ✅ COMPLIANT |
| Activity Invariants and Tipo | Bad tipo / empty subjects | `test_services.py` > `test_create_activity_rejects_bad_tipo` + `test_create_activity_rejects_empty_subjects`; models empty `subject_ids` | ✅ COMPLIANT |
| ActivityScore Invariants | Null ≠ zero; range enforced | `test_services.py` > `test_get_score_matrix_null_not_zero` + `test_bulk_upsert_rejects_score_above_ten_with_no_partial_write`; API OOB bulk | ✅ COMPLIANT |
| Catalog Validation | Subject outside field | `test_services.py` > `test_create_activity_rejects_subject_outside_field` | ✅ COMPLIANT |
| Activities List and Create | Create then list; foreign group denied | `test_api.py` > `test_create_then_list_activity` + `test_list_foreign_group_denied` (+ header/group+term required) | ✅ COMPLIANT |
| Scores Matrix Endpoint | Mixed cells | `test_api.py` > `test_matrix_mixed_cells_null_not_zero` | ✅ COMPLIANT |
| Bulk Score Upsert | Atomic success / wrong student rollback | `test_api.py` > `test_bulk_upsert_persists_all_entries` + `test_bulk_rejects_wrong_student_no_partial_write` | ✅ COMPLIANT |
| Draft Until Guardar + Screen | Draft + Periodo | `page.test.tsx` > draft without Guardar; Periodo required/blocks fetch; Exportar absent; modal create; Guardar on Por alumno | ✅ COMPLIANT |
| Grades Endpoints Map Custom Actions to Capabilities | Matrix/bulk mapping | `test_api.py` > `test_matrix_capability_maps_to_view_workspace` + `test_bulk_capability_maps_to_edit_content` | ✅ COMPLIANT |
| Grades Endpoints Map Custom Actions to Capabilities | Cap denials | `test_api.py` > `test_write_denied_without_edit_content` + `test_read_denied_without_view_workspace` | ✅ COMPLIANT |
| RLS Coverage Extends to Grades Tables | RLS on all three | `test_rls.py` > `test_rls_enabled_with_ws_isolation_nullif_policy` (term/activity/score) | ✅ COMPLIANT |
| RLS Coverage Extends to Grades Tables | Foreign-workspace rows denied | `test_rls.py` > `test_rls_blocks_foreign_workspace_activity_and_score` (+ no-context deny) | ✅ COMPLIANT |

**Compliance summary**: 13/13 scenarios compliant

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Term / Activity / ActivityScore models | ✅ Implemented | `backend/grades/models.py`; ScopedModel + constraints |
| ensure_terms + services | ✅ Implemented | `services.py` keyword services; catalog via `lesson_plans.core.catalog` |
| RLS migrations | ✅ Implemented | `0002_rls.py` enable/disable on three tables; reversible |
| Activities + matrix + bulk API | ✅ Implemented | `views.py` APIViews; urls under `/api/grades/` |
| Capability maps | ✅ Implemented | list/create/matrix/bulk → view_workspace / edit_content |
| FE hooks | ✅ Implemented | `frontend/src/lib/api/grades.ts` |
| `/actividades` screen | ✅ Implemented | toggle, modal, matrix draft Map, filters, stats, banner |
| Nav | ✅ Implemented | `NotebookPen` → `/actividades` in layout |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| New `grades` app + ScopedModel + NULLIF RLS | ✅ Yes | |
| APIView + capability_map; no `/terms/` URL | ✅ Yes | terms seeded + returned in payloads |
| Scores draft until Guardar; create immediate | ✅ Yes | Covered by FE tests |
| Full list (no server pagination) | ✅ Yes | Spec/API; FE CteCl footer pagination **deferred** |
| Local `role="dialog"` modal | ✅ Yes | |
| LWW bulk upsert | ✅ Yes | |
| Banner theme tokens (no invented info/warning) | ⚠️ Documented deviation | Uses primary/success/neutral — apply-progress notes intentional |
| Frame CteCl PROM. column | ⚠️ Deferred | Out of D5 polish; not in scenario G/W/T |
| Buscar only on Por actividad | ✅ Yes | Aligns with matrix API (no `q`) |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | `apply-progress` has D5 full cycle table + D1–D4 summary results |
| All tasks have tests | ✅ | 26/26; backend + `page.test.tsx` present |
| RED confirmed (tests exist) | ✅ | `test_{models,services,rls,api}.py` + `page.test.tsx` |
| GREEN confirmed (tests pass) | ✅ | 46 pytest + 20 vitest on independent re-run |
| Triangulation adequate | ✅ | Multi-case for null≠0, caps, filters/stats, draft/Guardar |
| Safety Net for modified files | ⚠️ | D5 reports 13/13; D1–D4 detailed per-task safety-net rows only summarized |

**TDD Compliance**: 5/6 checks fully verified (D1–D4 evidence abbreviated → WARNING)

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | ~35 | `test_models.py`, `test_services.py`, helpers in `page.test.tsx` | pytest / vitest |
| Integration | ~31 | `test_api.py`, `test_rls.py`, `page.test.tsx` (jsdom render) | pytest+APIClient, vitest |
| E2E | 0 | — | not installed for this route |
| **Total** | **66** | **5** | |

### Changed File Coverage
Coverage analysis skipped — no coverage tool run (threshold 0).

### Assertion Quality
| File | Line | Assertion | Issue | Severity |
|------|------|-----------|-------|----------|
| — | — | — | No tautologies, ghost loops, or production-less asserts found | — |

**Assertion quality**: ✅ All assertions verify real behavior (0 CRITICAL, 0 WARNING)  
Note: capability mapping tests use empty `class FakeRequest: pass` as stubs — not banned assertions; real `has_permission` path exercised.

### Quality Metrics
**Linter**: ➖ Not run on changed files  
**Type Checker**: ⚠️ 2 errors project-wide, **none** in `grades/**` or `actividades/**`  
**Migrations**: ✅ clean dry-run + migrate --check

### Issues Found
**CRITICAL**: None

**WARNING**:
1. Frame `CteCl` PROM. column / footer pagination still deferred (design/frame fidelity gap; scenario Draft+Periodo still COMPLIANT).
2. Banner/stats use theme primary/success/neutral instead of design-referenced info/warning tokens (documented intentional deviation).
3. Apply-progress D1–D4 TDD Cycle Evidence is summary-only (counts), not full per-task RED/GREEN rows — D5 is complete; independent GREEN re-run mitigates.
4. Pre-existing `tsc --noEmit` failures outside m7-activities scope (`asistencia` stub, `storage.test.ts` cct null).
5. Manual browser smoke deferred (Periodo/filters/banner/Exportar) — no E2E harness.

**SUGGESTION**:
1. Add a minimal Playwright smoke for `/actividades` Periodo-required + Guardar path when E2E lands.
2. Resolve orphan `asistencia` type validator / `cct: null` tsc debt so frontend typecheck is green project-wide.

### Verdict
**PASS WITH WARNINGS**

All 26 tasks complete; 10/10 requirements and 13/13 scenarios have passing covering tests; backend (46) and frontend (20) suites green; migrations clean. Warnings are documented scope/design deviations and out-of-scope typecheck debt — no CRITICAL gaps.

**Next recommended**: `sdd-archive` (do not archive in this phase; orchestrator/user decides).
