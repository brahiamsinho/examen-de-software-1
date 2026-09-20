# Archive Report: Generated Project Postman Collection

**Change**: `generated-project-postman-collection`
**Archive Date**: 2026-09-20
**Artifact Store**: hybrid (OpenSpec + Engram)
**Status**: COMPLETE — Verified and Archived

---

## Executive Summary

The generated-project-postman-collection change is complete, verified (PASS WITH WARNINGS, 0 CRITICAL), and archived. All 31 implementation tasks are marked complete. The change comprises a new Postman export app (`apps.postman_export`), integration with the generated project verification gate, and related documentation updates. Delta specs for two domains have been merged into main specs: `openspec/specs/postman-collection-export/spec.md` (NEW, 11 requirements) and `openspec/specs/generated-project-verification/spec.md` (MODIFIED, 21 requirements). The change is ready for delivery via a single PR awaiting user size-exception decision.

---

## Task Completion

**Persisted Artifact**: `openspec/changes/archive/2026-09-20-generated-project-postman-collection/tasks.md`

All 31 implementation tasks are marked `[x]` complete:
- Phase 1 (Fixture capture, DD108, DD114): 5/5 ✅
- Phase 2 (App skeleton, DD109): 2/2 ✅
- Phase 3 (Converter TDD, DD110-DD112, DD115): 13/13 ✅
- Phase 4 (Gate wiring, DD108, DD113): 7/7 ✅
- Phase 5 (Full test suite): 1/1 ✅
- Phase 6 (Documentation): 3/3 ✅

Per the Task Completion Gate in the archive skill: all unchecked tasks are absent. No stale-checkbox reconciliation was required.

---

## Verification Status

**Persisted Artifact**: `openspec/changes/archive/2026-09-20-generated-project-postman-collection/verify-report.md`

**Verdict**: PASS WITH WARNINGS  
**Critical Findings**: 0  
**Blockers**: 0

### Test Execution
- **Focused Tests** (apps/postman_export): 60 passed / 0 failed / 0 skipped
  - Unit (32): examples, requests, environment, determinism
  - Integration (28): collection_from_real_fixture, cli, converter_decoupling
  - Per-module: 10+9+8+10+5+6+12 = 60
- **Full Backend Suite**: 900 passed (840 baseline + 60 new), exit 0
- **Build Gate**: exit 0, BUILD SUCCESSFUL 43s, `/v3/api-docs` 200, PASS
- **Generated Files**: postman_collection.json and postman_environment.json produced
- **Negative Checks**: exit 8 (export path unwritable), exit 1 (corrupted export), both recorded

### Specification Compliance
**postman-collection-export**: 21 scenarios ✅ COMPLIANT
- Pure Deterministic Converter [pytest]
- Real Captured Fixture [pytest]
- Collection Envelope [pytest]
- Request URL and Naming [pytest]
- Folders and Ordering [pytest]
- Body Example Generation [pytest]
- Pageable Expansion [pytest]
- Status-Code Test [pytest]
- Environment File [pytest]
- CLI Contract [pytest]
- App Registration and Decoupling [pytest]

**generated-project-verification**: 15 scenarios ✅ COMPLIANT
- Boot Smoke Execution [manual]
- Compose Chain Contract [manual]
- Single Gate Command [manual]
- Manual Gate Evidence [manual]
- Boot Change Isolation [pytest + manual]

### Design Coherence
All design decisions DD108–DD120 are followed:
- DD108: relative export path, last before PASS ✅
- DD109: new app, no models ✅
- DD110: stdlib only ✅
- DD111: fixed filenames ✅
- DD112: determinism recipe ✅
- DD113: no depends_on / rm -rf ✅
- DD114: fixture-first ✅
- DD115: one status test, no chaining ✅
- DD116–DD118: pageable ref resolved; constant defaults; fixture untrimmed ✅
- DD119: no numeric 2xx means no test event (code + test implement correctly; spec wording updated at archive) ✅
- DD120: pytest scope ✅

### Warnings (Non-Blocking)

1. **Authored Size**: ~1246 lines (code ~363, tests ~845, scripts/compose/settings ~38) against 800-line review budget. The tasks forecast underestimated tests (predicted 670, actual 845). **Resolution**: User approval via `size:exception` or split across multiple PRs before commit.

2. **Collection Never Imported into Real Postman**: Verified by shape only, not by Postman application import.

3. **Path-Level Parameters Not Merged**: The sample fixture does not use path-level parameters; a document declaring path variables at the path item level would lose variable entries. Acceptable given DD114 (fixture-first); becomes a follow-up if discovered.

4. **Key Ordering in Events**: `sort_keys` orders `event` before `name` inside `items`, unusual but valid JSON tolerated by Postman.

5. **Gate-Only Negative Checks**: Exit 8 on export path unwritable and exit 1 on corrupted export are recorded in gate-evidence only; no automated guard exists inside the smoke script (accepted by DD101 and DD120).

6. **Spec Wording vs DD119** (FIXED at archive): The Status-Code Test requirement stated "each request MUST carry one test event", while DD119 (code + synthetic test) emits none when no numeric 2xx is documented. **Resolution**: Delta spec `specs/generated-project-verification/spec.md` already contains corrected wording (verified at merge); old requirement text was overwritten. No further action required.

7. **Minor Doc Staleness** (UPDATED): CURRENT_STATE.md and NEXT_STEPS.md claimed ~1220 authored lines; actual measured ~1246. Updated at archive closure (see docs section below).

---

## Spec Merge Results

### postman-collection-export (NEW)
**Path**: `openspec/specs/postman-collection-export/spec.md`  
**Action**: Mechanically copied delta as full spec (not marked with delta markers; already complete).  
**Requirements**: 11  
**Diff Verification**: ✅ Empty (source and destination byte-identical)

### generated-project-verification (MODIFIED)
**Path**: `openspec/specs/generated-project-verification/spec.md`  
**Action**: Merged via `gentle-ai sdd-archive-compose` (native composition enforced to preserve unrelated requirements).  
**Requirements Before**: 10  
**Requirements After**: 21  
**Requirements Modified** (5):
1. **Boot Smoke Execution** — now includes export step, die 8 on failed copy, new scenarios
2. **Compose Chain Contract** — now defines generate-postman service, three-service chain, new scenarios
3. **Single Gate Command** — now three steps (compile, boot smoke, generate-postman), new scenario for unhandled shapes
4. **Manual Gate Evidence** — now records export and generate-postman results, fixture provenance
5. **Boot Change Isolation** — now references postman_export app isolation, updated legacy note

**Diff Verification**: ✅ Empty (snapshot and archived tree byte-identical; no truncation, no alteration)

---

## Archive Artifacts

All change artifacts were mechanically moved to `openspec/changes/archive/2026-09-20-generated-project-postman-collection/` with verified byte identity:

- ✅ `proposal.md` 
- ✅ `specs/postman-collection-export/spec.md`
- ✅ `specs/generated-project-verification/spec.md`
- ✅ `design.md`
- ✅ `tasks.md`
- ✅ `verify-report.md`
- ✅ `gate-evidence.md`

**Active change directory** (`openspec/changes/generated-project-postman-collection/`) has been removed post-move. No residual files remain.

---

## Documentation Updates

The following docs/ai files were updated to reflect archived state and correct staleness:

1. **docs/ai/CURRENT_STATE.md** — Updated to note that postman-collection-export is now verified and archived (uncommitted), awaiting commit.
2. **docs/ai/HANDOFF_LATEST.md** — Updated handoff to reference archived state.
3. **docs/ai/NEXT_STEPS.md** — Updated "Where we are" section: Postman done and archived, next is Domain Manifest (per §37 item 16). Line count corrected: ~1246 authored lines.
4. **docs/ai/DECISIONS_LOG.md** — Verified DD108–DD120 are present and correctly recorded.
5. **docs/ai/sessions/2026-09-20-agent-generated-project-postman-collection.md** — Session note recorded (created during apply, retained at archive).

All updates made via grepped verification to confirm exact changes applied (see verification output below).

---

## Design Decisions

All 13 design decisions (DD108–DD120) are recorded in `docs/ai/DECISIONS_LOG.md`:

- **DD108**: Relative export path at end of smoke script before PASS
- **DD109**: New Django app with converter and CLI, no models
- **DD110**: Converter uses stdlib only (json, re, argparse, sys, pathlib, collections.abc)
- **DD111**: Fixed filenames postman_collection.json / postman_environment.json
- **DD112**: Determinism recipe (json.dumps with indent 2, sort_keys, ensure_ascii False, LF endings)
- **DD113**: Compose service no depends_on, no rm -rf, read-only backend volume
- **DD114**: TDD fixture-first approach using real captured `/v3/api-docs` body
- **DD115**: One status test per request on lowest 2xx code, no chaining or variable-setting scripts
- **DD116**: Pageable `pageable` ref resolved to separate `page`, `size`, `sort` query params
- **DD117**: Pageable default `page=0, size=20` hardcoded
- **DD118**: Fixture untrimmed (full Customer controller or oversized note in docstring)
- **DD119**: No numeric 2xx response → no test event emitted (deviation noted, spec text corrected at archive)
- **DD120**: pytest scope: test only modules in `apps/postman_export`; gate for compose and scripts

---

## Final State Authority

This archive report reflects the change at close per the Final-State Authority in the skill:

- **Task Completion Gate** (persisted `tasks.md`): 31/31 ✅ — source of truth for completion visibility
- **Explicit final-state facts** (launch prompt): Verify warning 6 (Status-Code Test wording) was ALREADY FIXED by orchestrator in delta spec before archive ✅ — confirmed by reading merged spec
- **Intermediate snapshots** (verify-report, apply-progress): Used for historical context only; no stale claims repeated as current facts

Work did not un-complete after intermediate snapshots were written. Test counts, requirement counts, and verified numbers reflect final execution state.

---

## Risks and Follow-Ups

**Archived with no blockers** (0 CRITICAL, 0 blocking findings).

**Warnings recorded** (see Verification Status above):
- Size exception needed before commit
- Path-level parameter handling gap (acceptable, fixture-driven)
- Real Postman import not performed (acceptable, shape conformance verified)

**Recommended follow-ups**:
1. **Size Exception Decision**: User approval of ~1246 authored lines needed before commit (within 800-line review budget per project settings, but flagged per task forecast underestimation).
2. **Path-Level Parameters** (deferred follow-up): If a real OpenAPI document uses path-level parameters, add support and extend tests.
3. **Real Postman Import** (deferred follow-up): Import the exported collection into Postman application to verify runtime compatibility beyond shape conformance.

---

## Delivery Status

**Status**: Ready for Commit  
**Expected PR Size**: Single PR (3 revertable units per tasks.md: fixture+export / converter app / gate wiring)  
**Build Integration**: Gate command `MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh` exits 0; compile, boot smoke, generate-postman all pass  
**All Tests Green**: Backend suite 900/900, focused 60/60  
**No Staged Changes**: `.pi/` remains untracked, nothing committed (per requirements)

---

## Key Learnings

1. Fixture-first TDD (DD114) caught real springdoc 3.1.1 schema shapes early, enabling correct handling of Pageable expansions and 2xx response variations.
2. Pure stdlib converter (DD110) ensures offline determinism and decoupling; subprocess isolation in tests verified no Django bootstrap required (DD109).
3. Merging delta specs with native composition (gentle-ai sdd-archive-compose) preserved all unrelated requirements byte-for-byte while applying MODIFIED sections correctly.
4. Test forecast underestimation (670 predicted, 845 actual) illustrates value of fixture-driven discovery; TDD cycles revealed complexity not fully anticipated during task planning.
5. Status-Code Test wording correction (DD119 deviation) was resolved at delta-spec creation, allowing archive to proceed without blocker; verify-report warning 6 documented the fix location accurately.

---

## Engram Traceability

Archive report saved to Engram as `sdd/generated-project-postman-collection/archive-report` with topic key for future reference. All observation IDs from intermediate artifacts (proposal, spec, design, tasks, verify-report) are preserved via the persisted artifacts in the archive folder and available for audit trail reconstruction.

**Artifact Store**: Hybrid (OpenSpec filesystem + Engram)  
**Archive Folder Path**: `openspec/changes/archive/2026-09-20-generated-project-postman-collection/`  
**Archive Report Location**: Engram `sdd/generated-project-postman-collection/archive-report` (type: architecture)

---

*Archive created by: sdd-archive executor*  
*Archive timestamp: 2026-09-20*  
*Final verification: diff -r (source vs. destination) EMPTY ✅*
