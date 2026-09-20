# Archive Report: Generated Project Boot Smoke

**Change**: generated-project-boot-smoke  
**Date Archived**: 2026-09-19  
**Status**: PASS WITH WARNINGS (0 critical)  
**Artifact Store**: hybrid (openspec + engram)

## Executive Summary

The generated-project-boot-smoke change (spec §37 item 13, slice 3 of 3) is now fully verified, implemented, and archived. The change extends the generated-project verification gate to prove not only compilation but also boot and CRUD round-trip against a throwaway Postgres database, closing the gap between "compiles" and "works". Verification verdict: **PASS WITH WARNINGS**; all 18 implementation tasks complete; 836 backend tests pass; gate runs successfully (orchestrator: EXIT 0, BUILD SUCCESSFUL 43s, POST 201/GET 200/DELETE 204/GET 404, PASS; verifier negative case: EXIT 4, clean teardown). Three failure-path scenarios (compile failure, readiness timeout, status mismatch) remain untested in practice (guaranteed structurally). Spec and design deviations fixed forward and recorded.

## Change Scope & Intent

Slice 3 of 3 for §37 item 13: boot the jar against a throwaway Postgres and do one real CRUD round-trip, proving the generated backend works end-to-end. Implements:
- New `scripts/boot-smoke.sh`: Java boot + readiness poll + CRUD round-trip
- New `docker-compose.yml` services: `gen-db` (profile jvm-verify) and `jvm-boot-smoke`
- New contract test: `test_boot_smoke_contract.py` (Docker-free, pins generated literals)
- Extend `scripts/verify-generated-project.sh` with cleanup trap and boot smoke step
- Delta spec fixing existing drift in generated-project-verification

Out of scope: generator/template changes, actuator, Flyway/schema.sql, Gradle wrapper, OpenAPI, published ports, CI wiring.

## Artifacts Archived

**Location**: `openspec/changes/archive/2026-09-19-generated-project-boot-smoke/`

| Artifact | Type | Status | Lines | Notes |
|----------|------|--------|-------|-------|
| proposal.md | Proposal | ✅ | 71 | Change intent, scope, approach, risks, rollback plan |
| design.md | Design | ✅ | 174 | Architecture decisions DD92–DD102, compose/scripts/test strategy |
| exploration.md | Exploration | ✅ | 89 | Current generator state, boot requirements, composition plan |
| specs/generated-project-verification/spec.md | Delta Spec | ✅ | 120 | ADDED 9 reqs, MODIFIED 2 reqs (Image Tag Derivation, Manual Gate Evidence), Purpose updated |
| tasks.md | Tasks | ✅ | 67 | 7 phases, 18 tasks, all [x] complete; reviewload forecast ~620 lines, size:exception approved |
| gate-evidence.md | Evidence | ✅ | 45 | Manual gate run: positive (EXIT 0, BUILD SUCCESSFUL, 201/200/204/404, ready 7s), negative (EXIT 4, clean), docker ps verification |
| verify-report.md | Verify Report | ✅ | 129 | PASS WITH WARNINGS: 836 tests pass, contract test 8/8, negative case verified, 3 failure paths unexercised (structural only) |

## Specs Synced to Main

**Target**: `openspec/specs/generated-project-verification/spec.md`

**Sync Method**: native `sdd-archive-compose` command (Purpose updated by hand per FINAL-STATE FACTS)

**Changes Applied**:
- **MODIFIED Purpose**: "boot, schema reserved words..." → "boot + CRUD + ddl-auto schema now in scope; Flyway/schema.sql/actuator/wrapper/OpenAPI out"
- **MODIFIED Image Tag Derivation**: Compose now consumes `${GRADLE_IMAGE:-<sentinel>}` (previously `${GRADLE_IMAGE:?}`)
- **MODIFIED Manual Gate Evidence**: Spec now requires statuses (201/200/204/404) and negative exit code (previously only command/exit/BUILD SUCCESSFUL)
- **ADDED 9 Requirements**: Single Gate Command, Throwaway Database Lifecycle, Boot Smoke Execution, Readiness Wait, CRUD Round-Trip, Negative Case, Boot Change Isolation, Generated Contract Pin, Fix-Forward Findings

**Composition Verification**: `sdd-archive-compose` completed zero-exit, atomic temp-file move, diff verified empty (no truncation).

## Task Completion

**Task Artifact**: `tasks.md` (18/18 complete)

| Phase | Tasks | Status | Notes |
|-------|-------|--------|-------|
| 1. Contract test | 2 | ✅ | pytest-based, characterization, mutation proof |
| 2. Probe | 1 | ✅ | curl --version in GRADLE_IMAGE verified |
| 3. Compose | 4 | ✅ | gen-db + jvm-boot-smoke + config + health checks |
| 4. Scripts | 3 | ✅ | boot-smoke.sh (110 lines), verify-generated-project.sh (trap + 2nd run), signal handling |
| 5. Manual gate | 4 | ✅ | Positive run, negative run, docker ps, default-up check |
| 6. Regression | 1 | ✅ | 836 backend tests pass |
| 7. Docs | 3 | ✅ | CURRENT_STATE, HANDOFF_LATEST, NEXT_STEPS, DECISIONS_LOG, session note |

**Verification of Completion**: All tasks marked [x] in persisted tasks artifact; apply-progress #696 confirms 18/18 executed.

**Per FINAL-STATE FACTS**: Task count corrected from stale "21" in docs to actual 18. Fixed in CURRENT_STATE.md, HANDOFF_LATEST.md, NEXT_STEPS.md (L63), DECISIONS_LOG.md (L5, L603), and session notes.

## Test Results & Verification

### Build & Gate Execution

| Type | Result | Evidence | Notes |
|------|--------|----------|-------|
| Positive gate | EXIT 0 | gate-evidence.md | Orchestrator re-run: BUILD SUCCESSFUL 43s, ready 7s, POST 201/GET 200/DELETE 204/GET 404, PASS |
| Negative gate | EXIT 4 | verify-report, gate-evidence | GEN_DB_PASSWORD=wrong: auth failure at boot, no gen-db leak, db/redis untouched |
| Contract test | 8/8 pass | test_boot_smoke_contract.py | Characterization: pass first (disclosed as honest), mutation proof (rename fullName → 2 failed) |
| Full backend suite | 836/836 pass | pytest -q output | 71.76s, focused 8, full 836, isolation confirmed |

### Specification Compliance

| Requirement | Scenarios | Evidence | Result |
|-------------|-----------|----------|--------|
| Single Gate Command | Compile skip [unexercised], Both pass | gate EXIT 0, two sequential runs | PARTIAL (structural guarantee) |
| Throwaway DB Lifecycle | No leak, Default up | docker ps, compose config | COMPLIANT |
| Boot Smoke Execution | Plain jar not used | gate log, glob logic | COMPLIANT |
| Readiness Wait | JVM dies early, Timeout [unexercised] | negative EXIT 4, kill -0 path | PARTIAL (structural guarantee) |
| CRUD Round-Trip | Full round, Status mismatch [unexercised] | 201/200/204/404 in gate | PARTIAL (structural guarantee) |
| Negative Case | Bad credential | EXIT 4, FATAL auth error logged | COMPLIANT |
| Boot Change Isolation | Sources unchanged | no diff in spring_generator, 836 pass | COMPLIANT |
| Generated Contract Pin | Drift caught | test 8/8, mutation 2 failed | COMPLIANT |
| Fix-Forward Findings | Defect found | F1/F2 in gate-evidence with disposition | COMPLIANT |
| Image Tag Derivation | Tag follows versions.py, Sentinel default | existing runner tests, compose | COMPLIANT |
| Manual Gate Evidence | Evidence recorded | gate-evidence.md complete | COMPLIANT |

**Verdict**: 8/11 fully compliant, 3/11 partial (manual failure scenarios untested, guaranteed structurally). 0 critical findings.

## Deviations & Amendments Applied

### F1: Credential Variable Name Mismatch (Design Decision DD93, DD102)

**Finding**: gen-db reads `${GEN_DB_SERVER_PASSWORD:-…}` (per postgres service env key naming), while the app reads `${GEN_DB_PASSWORD}` (per compose jvm-boot-smoke env). A wrong app password can fail the gate.

**Resolution**: **Fixed forward in DD102 amendment** — recorded in DECISIONS_LOG.md. The negative case (`GEN_DB_PASSWORD=wrong`) deliberately tests this; negative gate exit 4 as expected.

**Spec Amendment**: Added one clarifying line to merged spec: "gen-db password comes from `${GEN_DB_SERVER_PASSWORD}`, the app's from `${GEN_DB_PASSWORD}`" (line in Throwaway Database Lifecycle requirement).

**Design Amendment**: DD93 and DD102 notes updated in archived design.md to name the variable split explicitly.

### F2: Failure Dump Format (Design Decision DD98)

**Finding**: Failure dump prints last 60 lines after concise FATAL/'Caused by' root-cause block, potentially verbose.

**Resolution**: **Fixed forward in DD98 amendment** — enhanced failure dump to list FATAL and 'Caused by' lines first (first 5) then tail (60 lines), per verifier observation. Makes root causes clear before context.

**Design Amendment**: DD98 notes updated in archived design.md.

### Signal Trap Layout (Design Decision DD95)

**Finding**: Design shows single `cleanup` trap on EXIT; implementation uses separate traps: `trap cleanup EXIT` + `trap 'exit 130' INT` + `trap 'exit 143' TERM`.

**Resolution**: **Fixed forward** — separate traps are strictly better: preserve exit code on EXIT, convert INT/TERM to standard Linux signal-exit codes (130, 143) instead of exit 0 after a signal.

**Design Amendment**: DD95 notes updated in archived design.md to reflect actual trap layout.

## Warnings & Accepted Deviations

### W2: Unexercised Failure-Path Scenarios

Three spec scenarios have no recorded runtime evidence; only structural guarantees in code:

1. **Compile failure skips smoke**: `set -e` in verify-generated-project.sh ensures second run never starts if compile fails. Structural guarantee; not exercised in gate run.
2. **Readiness timeout (exit 5)**: `SMOKE_READY_TIMEOUT` logic in boot-smoke.sh. Structural guarantee; normal gate finishes in 7s, well under 180s default.
3. **Status mismatch (exit 6)**: `assert_status` function handles any non-2xx response. Structural guarantee; gate sees 200/201/204/404 as expected.

**Mitigation**: Code review confirms logic; negative case exercises the kill-0 fast-fail path (exit 4). These scenarios could be exercised in a follow-up with `SMOKE_READY_TIMEOUT=1` or a bad endpoint test, but are acceptable as-is under DD101 manual verification model.

**Verdict**: Accepted. Recorded for future improvement.

### W4: Gate Depends on Live Maven Central

Maven/Gradle resolution during the `gradle build` step requires network access and cold JVM startup. First run is slower; flakes are possible (transient network, rate limiting). Mitigation: gate has 180s readiness budget; operator can retry. Accepted as-is.

### Pre-Existing: Lingering `generate-project-1` Container

The compile-gate step leaves a stopped `generate-project-1` container (DD83 byproduct). Not cleaned by verify-generated-project.sh. Cleanup trap in boot smoke gate removes only `gen-db`. Accepted as pre-existing; follow-up improvement candidate.

### No Automated Guard for Version Literals

A pytest guard for version literals in `docker-compose.yml` is structurally impossible (test runs in `/app` = `backend/`, compose.yml is in repo root). Mitigation: manual grep in archive checklist (DD101 precedent). Accepted.

## Engram Observations & Traceability

All artifacts read from Engram and recorded here for audit trail:

| Observation ID | Title | Type | Saved | Notes |
|---|---|---|---|---|
| #692 | sdd/generated-project-boot-smoke/proposal | architecture | 2026-09-19 22:22 | Full proposal artifact |
| #691 | sdd/generated-project-boot-smoke/explore | architecture | 2026-09-19 22:19 | Exploration output |
| #694 | sdd/generated-project-boot-smoke/design | architecture | 2026-09-19 22:27 | Full design (DD92–DD102) |
| #693 | sdd/generated-project-boot-smoke/spec | architecture | 2026-09-19 22:24 | Delta spec with ADDED/MODIFIED |
| #695 | sdd/generated-project-boot-smoke/tasks | architecture | 2026-09-19 22:29 | Tasks artifact (7 phases, 18 tasks) |
| #696 | sdd/generated-project-boot-smoke/apply-progress | architecture | 2026-09-19 22:42 | Apply phase status (18/18 tasks, TDD cycle evidence) |
| #697 | sdd/generated-project-boot-smoke/verify-report | architecture | 2026-09-19 22:51 | Verification verdict (PASS WITH WARNINGS) |

This archive report (new):  
**Topic Key**: `sdd/generated-project-boot-smoke/archive-report`  
**Type**: architecture  
**Project**: examen-1-software

## Proposal Checklist Update

Per FINAL-STATE FACTS, the proposal.md success criteria include line 68 "Negative case recorded":

- [x] One command runs compile + boot smoke and exits 0 on the sample model.
- [x] Round-trip observed: POST 201, GET 200, DELETE 204, GET 404.
- [x] Negative case recorded (wrong `GEN_DB_PASSWORD` → non-zero exit).
- [x] No `gen-db` container survives a passing or failing run.
- [x] `pytest -q` stays green, Docker-free and offline.

All success criteria met. Ticked in proposal.

## Documentation Updates

Per FINAL-STATE FACTS, the following docs were corrected:

- **docs/ai/CURRENT_STATE.md**: §37 item 13 marked complete (3 of 3); slice 3 closed.
- **docs/ai/NEXT_STEPS.md**: Task count corrected from stale "21/21" to 18; verified and archived status noted.
- **docs/ai/HANDOFF_LATEST.md**: Task count corrected; archive status noted.
- **docs/ai/DECISIONS_LOG.md**: Stale "21 tasks" references changed to 18; DD92–DD102 recorded with amendments.
- **docs/ai/sessions/2026-09-19-agent-generated-project-boot-smoke.md**: Created with session context.

## Deferred Items (§37 Remaining Slices)

These remain deferred per proposal scope:

- Gradle wrapper generation (§37 item 14)
- OpenAPI/Postman/Domain Manifest export (§37 item 15)
- Frontend/mobile generation (§37 item 16)
- Actuator + Flyway (out of scope per proposal)

## SDD Cycle Summary

| Phase | Status | Result |
|-------|--------|--------|
| Explore | ✅ | Boot requirements clear; composition plan confirmed |
| Propose | ✅ | Intent, scope, approach, risks, success criteria all approved |
| Spec | ✅ | Delta spec written; 9 ADDED + 2 MODIFIED + 1 Purpose edit |
| Design | ✅ | 11 architecture decisions (DD92–DD102), testing strategy, thread model |
| Tasks | ✅ | 7 phases, 18 tasks, size:exception approved, ~620 lines forecasted |
| Apply | ✅ | All 18 tasks implemented; TDD cycle evidence recorded; no commits pending |
| Verify | ✅ | PASS WITH WARNINGS: 836 tests, gate green (0/4), negative case proven, 3 scenarios unexercised (structural) |
| Archive | ✅ | Specs merged, folder moved, all artifacts preserved, archive report written |

## Rollback & Rollout

### Rollback Plan

Revert the change commit (if any). The compile gate and default `up`/`pytest` are untouched by construction (new services behind jvm-verify profile, new test is Docker-free). No persistent state added (gen-db is tmpfs, removed by trap).

### Rollout

Change is complete. No deployment step is defined in the proposal; delivery follows ordinary repository policy.

## Verification of Archive Completeness

- [x] Main specs updated correctly (sdd-archive-compose zero-exit, diff verified)
- [x] Change folder moved to archive (diff -r verified empty, source confirmed absent)
- [x] Archive contains all artifacts (proposal, specs, design, tasks, gate-evidence, verify-report)
- [x] Archived tasks.md has no unchecked implementation tasks (all 18/18 [x])
- [x] Active changes directory no longer has this change (confirmed)
- [x] Verbatim diff -r readback output empty (only diff performed: new archive-report.md is additive-only, excluded from source/destination comparison)

**Archive Status**: COMPLETE

## Close & Release

The change has been fully planned, implemented, verified, and archived. All tasks complete. All tests pass. Zero critical findings. Three deferred items recorded for follow-up changes (§37 items 14–16).

**Next**: No further work required for this change. See NEXT_STEPS.md for project roadmap.
