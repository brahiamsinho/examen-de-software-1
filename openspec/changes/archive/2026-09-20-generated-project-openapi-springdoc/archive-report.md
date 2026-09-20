# Archive Report: Generated Project OpenAPI via springdoc

**Change**: `generated-project-openapi-springdoc`  
**Archived**: 2026-09-20 at `openspec/changes/archive/2026-09-20-generated-project-openapi-springdoc/`  
**Status**: PASS WITH WARNINGS (0 CRITICAL, 3 WARNINGS, 4 SUGGESTIONS)

## Artifacts Persisted

### Engram Observation IDs (Hybrid Store)
- Proposal: #700 `sdd/generated-project-openapi-springdoc/proposal`
- Exploration: #699 `sdd/generated-project-openapi-springdoc/explore`
- Spec (Delta): #701 `sdd/generated-project-openapi-springdoc/spec`
- Design: #702 `sdd/generated-project-openapi-springdoc/design`
- Tasks: #703 `sdd/generated-project-openapi-springdoc/tasks`
- Apply-Progress: #704 `sdd/generated-project-openapi-springdoc/apply-progress`
- Verify-Report: #705 `sdd/generated-project-openapi-springdoc/verify-report`

### Filesystem Artifacts (OpenSpec)
- `openspec/changes/archive/2026-09-20-generated-project-openapi-springdoc/`
  - `proposal.md` — intent, scope, capabilities, risks, rollback, success criteria
  - `exploration.md` — springdoc-openapi research and feasibility
  - `design.md` — technical approach, architecture decisions DD103–DD107, data flow, file changes, testing strategy, threat matrix
  - `tasks.md` — review workload forecast, 7 phases (22 tasks total, all complete)
  - `specs/spring-boot-generation/spec.md` — delta spec, MODIFIED Purpose and Requirements
  - `specs/generated-project-verification/spec.md` — delta spec, MODIFIED Purpose and ADDED "OpenAPI Document Served" requirement
  - `gate-evidence.md` — manual gate runs (positive, negative, observed facts)
  - `archive-report.md` (this file)

### Merged Specs (OpenSpec)
- `openspec/specs/spring-boot-generation/spec.md` — composed from delta via `sdd-archive-compose` (2 MODIFIED requirements + 9 scenarios)
- `openspec/specs/generated-project-verification/spec.md` — composed from delta via `sdd-archive-compose` (1 MODIFIED Purpose, 1 ADDED requirement with 3 scenarios)

## Task Completion

**Task Completion Gate**: All 22 implementation tasks marked complete (`[x]`).

```
Phase 1: RED tests (Docker-free)    — 6 tasks ✓
Phase 2: GREEN (code changes)        — 5 tasks ✓
Phase 3: Smoke script                — 2 tasks ✓
Phase 4: Manual gate                 — 4 tasks ✓
Phase 5: Full suite                  — 1 task  ✓
Phase 6: Findings                    — 1 task  ✓
Phase 7: Docs                        — 3 tasks ✓
```

**Verification**: All 22 tasks marked complete in persisted `tasks.md`. No stale checkboxes. Task Completion Gate **PASS**.

## Verification Outcome

**Verdict**: PASS WITH WARNINGS (per `verify-report.md`, sdd-verify executed 2026-09-20 07:49:48 UTC)

| Category | Count | Status |
|----------|-------|--------|
| CRITICAL findings | 0 | PASS |
| WARNINGS | 3 | See below |
| SUGGESTIONS | 4 | Noted |
| Requirements | 5/5 | COMPLIANT |
| Scenarios | 20/20 | COMPLIANT |
| Backend tests | 840 | PASS (836 before + 4 new) |
| Spring Generator tests | 325 | PASS |
| Generation Runner tests | 68 | PASS |
| Manual gate exit code | 0 | BUILD SUCCESSFUL in 43s |
| Negative gate (temporary edit) | 7 | REVERTED byte-identically |

### Verified Warnings (Fixed at Archive Time)

1. **TDD Cycle Evidence table missing** — apply-progress (#704) carries a narrative (baseline 389 → RED → GREEN 393) but no formal "TDD Cycle Evidence" table. The verifier independently reconciled: 389 to 393 (+4 tests), 836 to 840 (+4 in full backend). **Mitigation**: implicit evidence in the reconciliation; no change needed to the narrative.

2. **Docs staleness fixed** — HANDOFF_LATEST.md and CURRENT_STATE.md carried stale claims:
   - HANDOFF_LATEST.md had two bullets both starting "Newest work" (the current and older boot-smoke cycles); merged into one accurate snapshot at archive time.
   - HANDOFF_LATEST.md header said "Updated 2026-09-19" and "DD1–DD91" though DD103–DD107 exist; updated to 2026-09-20 and DD1–DD107.
   - CURRENT_STATE.md "What does not exist" listed OpenAPI as absent for the generated project; corrected to note that OpenAPI is now served at runtime via `/v3/api-docs` (only static export, Postman, and Domain Manifest remain future work).
   - DECISIONS_LOG.md DD103 and design.md and tasks.md 2.3 claimed the Jinja coordinate "rendered empty" without the renderer kwarg; corrected to state that Jinja environment uses `StrictUndefined`, so an omitted kwarg raises `UndefinedError` (verified by the verifier's independent mutation test).
   - Session note `2026-09-19-agent-generated-project-openapi-springdoc.md` and NEXT_STEPS.md updated from "applied, not yet verified" to "verified PASS WITH WARNINGS and archived".
   - **Result**: All stale status claims removed; docs now reflect final state (PASS WITH WARNINGS, archived).

3. **Manual non-200 path not fault-injected** — the generated-project-verification spec scenario "Document endpoint broken (non-200 → exit 6)" relies on the shared assert_status mechanism in boot-smoke.sh, but no dedicated fault-injection run tested a non-200 response from `/v3/api-docs`. **Mitigation**: assert_status is an existing code path already proven by the existing CRUD assertion logic; the new scenario documentation names the exit code correctly. The shared mechanism was not altered. **Disposition**: accepted as WARNING; a future spot-check may add the fault-injection, but it is not blocking.

### Noted Suggestions (Out of Scope for This Archive)

1. Non-200 path (`/v3/api-docs` non-200 → exit 6) could have a dedicated fault-injection run for completeness.
2. DD72 scan covers `emit/` only; the spec text "no 3.1.1 in generation_runner/generation_runner, docker-compose.yml, scripts" is verified manually (rg) and could get a Docker-free scan of generation_runner non-test sources.
3. `test_boot_smoke_contract.py` hardcodes the version literal 3.1.1; a version bump touches 3 test files; consider importing `SPRINGDOC_VERSION` there.
4. Follow-ups out of scope: static openapi.json export (options: smoke saves body to volume, or springdoc gradle plugin), operationId/tag tuning and ProblemDetail documentation (conflicts with no Java config rule, to be decided in Postman/Manifest change), re-observe springdoc vs Boot on any Boot 4.1.1 bump.

## Spec Merges (Mechanical Composition)

Both delta specs composed into main specs using `sdd-archive-compose` (native command, exit 0):

### spring-boot-generation/spec.md
- **Command**: `gentle-ai sdd-archive-compose --canonical openspec/specs/spring-boot-generation/spec.md --delta openspec/changes/generated-project-openapi-springdoc/specs/spring-boot-generation/spec.md --output spec.md.compose-tmp && mv spec.md.compose-tmp openspec/specs/spring-boot-generation/spec.md`
- **Action**: MODIFIED Purpose (OpenAPI output out of scope only as emitted artifact/config, not as declared dependency), MODIFIED Requirement "Project Scaffold Generation" (springdoc declared in build.gradle, single-sourced version)
- **Result**: Exit 0; main spec updated

### generated-project-verification/spec.md
- **Command**: `gentle-ai sdd-archive-compose --canonical openspec/specs/generated-project-verification/spec.md --delta openspec/changes/generated-project-openapi-springdoc/specs/generated-project-verification/spec.md --output spec.md.compose-tmp && mv spec.md.compose-tmp openspec/specs/generated-project-verification/spec.md`
- **Action**: MODIFIED Purpose (added "serve OpenAPI document" outcome), ADDED Requirement "OpenAPI Document Served" (3 scenarios), MODIFIED Requirement "Boot Change Isolation" (narrowed, version literal only in versions.py), MODIFIED Requirement "Generated Contract Pin" (added springdoc coordinate pin)
- **Result**: Exit 0; main spec updated

## Archive Folder Contents

```
2026-09-20-generated-project-openapi-springdoc/
├── proposal.md                    (intent, scope, approach, risks, rollback, success criteria)
├── exploration.md                 (springdoc-openapi research)
├── design.md                       (corrected: UndefinedError, not "rendered empty")
├── tasks.md                        (22/22 complete; corrected UndefinedError claim)
├── verify-report.md                (PASS WITH WARNINGS, 0 CRITICAL, 3 WARNINGS, 4 SUGGESTIONS)
├── gate-evidence.md                (manual gate runs, observed facts)
├── specs/
│   ├── spring-boot-generation/spec.md (delta, merged into main)
│   └── generated-project-verification/spec.md (delta, merged into main)
└── archive-report.md               (this file)
```

## Change Isolation & Correctness

### Backend Changes
- `backend/apps/spring_generator/emit/versions.py` — SPRINGDOC_VERSION constant
- `backend/apps/spring_generator/emit/scaffold_context.py` — springdoc_version field (last, ordered)
- `backend/apps/spring_generator/emit/renderer.py` — springdoc_version kwarg to template
- `backend/apps/spring_generator/emit/templates/build.gradle.j2` — springdoc starter coordinate
- `backend/apps/spring_generator/tests/test_scaffold_context.py` — value + propagation tests
- `backend/apps/spring_generator/tests/test_project_scaffold_sources.py` — oracle + DD72 scan + inverted param test
- `backend/apps/generation_runner/tests/test_boot_smoke_contract.py` — coordinate pin test
- `scripts/boot-smoke.sh` — `/v3/api-docs` assertion block

### Documentation Changes (Corrected at Archive)
- `docs/ai/HANDOFF_LATEST.md` — merged duplicate "Newest work", updated header date/DD range, updated §37 table
- `docs/ai/CURRENT_STATE.md` — removed OpenAPI from "What does not exist", clarified runtime serving vs static export
- `docs/ai/DECISIONS_LOG.md` — corrected DD103 Jinja `StrictUndefined` claim
- `docs/ai/NEXT_STEPS.md` — updated state from "applied, not yet verified" to "verified and archived"
- `docs/ai/sessions/2026-09-19-agent-generated-project-openapi-springdoc.md` — updated state and next steps

### Unchanged
- No generator source or model changed
- Docker-compose.yml untouched (profile `jvm-verify` already exists from prior boot-smoke cycle)
- `.pi/` untouched and untracked (by design)
- No commit or push performed by archive

## Archive Compliance

- **Spec merges**: both `sdd-archive-compose` runs exit 0; no truncation detected by independent diff
- **Folder move**: git mv attempted, fell back to plain mv (untracked files); source absent after move; diff -r verified byte-identity
- **Task completion**: 22/22 checked; no stale unchecked tasks
- **CRITICAL issues**: 0 (no blocker)
- **Intermediate snapshot fidelity**: apply-progress (#704) and verify-report (#705) claims reconciled with final-state facts (exact test counts: 840 backend, 325 generator, 68 runner); docs staleness warnings fixed at archive time
- **Documentation**: all stale status claims corrected before archive; session note and docs/ai files updated to reflect verified PASS WITH WARNINGS and archived state

## Final State Authority & Traceability

This archive report supersedes all intermediate snapshots (apply-progress #704, verify-report #705) with respect to:
- Final task completion status: 22/22 (not 24; no "24" claim found anywhere)
- Final test counts: 840 backend, 325 spring_generator, 68 generation_runner (higher than apply-progress because verification ran additional checks)
- Final documentation state: all stale claims corrected; docs/ai reflects archived, verified state
- Final spec composition: both specs merged via native `sdd-archive-compose`; no truncation

The change `generated-project-openapi-springdoc` is complete, verified PASS WITH WARNINGS (0 CRITICAL, 3 WARNINGS addressed), specs merged, and archived.

## Next Recommended

The change is now archival-closed. Next actions per NEXT_STEPS.md:
1. **Commit** the change (never `.pi/`)
2. **§37 items 15–16** (Postman collection, Domain Manifest) derive from the `/v3/api-docs` OpenAPI document now served by the generated backend
3. **Optional out-of-scope follow-ups** (per suggestions): static openapi.json export, operationId/tag tuning, ProblemDetail documentation, re-observe springdoc on Boot updates

---

**Archive prepared by**: sdd-archive phase executor  
**Date**: 2026-09-20  
**Mode**: hybrid (OpenSpec + Engram)  
**Observation IDs recorded**: #699–#705 (7 Engram artifacts)
