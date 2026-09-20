# Archive Report: relational-generation-metadata

Archived 2026-09-20 (hybrid mode). Status at close: verified PASS WITH WARNINGS (0 critical), 34/34 tasks complete, uncommitted.

## Artifacts read (filesystem, openspec/hybrid)
exploration.md, proposal.md, specs/generation-profile/spec.md, specs/relational-mapping/spec.md, design.md, tasks.md, apply-progress.md, verify-report.md. No Engram observation IDs were read by the archive phase (artifacts came from the change folder).

## Specs synced
| Domain | Action | Requirements on disk after merge |
|---|---|---|
| generation-profile | Created (mechanical `cp`, empty `diff`) | 9 |
| relational-mapping | Updated via `gentle-ai sdd-archive-compose` (exit 0): 4 MODIFIED, 3 ADDED, 0 REMOVED | 17 (was 14) |

## Final state (Final-State Authority)
- Backend suite 1070 passed (987 before); `apps/relational_mapping` 138 passed; `apps/domain_manifest` 88 passed; 34/34 tasks (persisted tasks.md, no unchecked items).
- Source: orchestrator launch prompt (final numbers). The verify-report snapshot recorded 1069 tests at verification time (per verify-report); the higher final count comes from later work and outranks that snapshot.
- Authored size ~960 lines accepted as `size:exception`.

## Accepted warnings
1. `Table` / `RelationalModel` are already unhashable (pre-existing); spec wording amended.
2. The manifest half of the output-neutrality test lives in `apps/domain_manifest/tests` (import guard forbids other apps importing it).
3. `InvalidGenerationProfileError` is not imported in `mapper.py` (design wiring table lists it; not needed).
4. Three tests pass by construction (characterization/neutrality); protected by mutation checks.

## Readback
- generation-profile: `diff` of change spec vs main spec printed nothing.
- Folder move: `diff -r` of the pre-move snapshot vs the archived folder printed nothing (archive-report.md excluded, additive). The change was untracked, so `git mv` refused and plain `mv` was used after the snapshot diff.
