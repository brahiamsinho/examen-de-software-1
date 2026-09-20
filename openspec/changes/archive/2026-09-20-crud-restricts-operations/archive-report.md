# Archive Report: crud-restricts-operations

**Archived**: 2026-09-20
**Archive path**: `openspec/changes/archive/2026-09-20-crud-restricts-operations/`
**Mode**: hybrid (no Engram artifact observations existed for this change; the `sdd/crud-restricts-operations` search returned none, so the only observation is this report)
**Outcome**: closed, verified PASS WITH WARNINGS, 0 critical. Work is uncommitted on `main` (slice 1 of 2: manifest side only).

## Final state at close

- Tasks: 24/24 complete in `tasks.md` (task 9.1 ticked at archive, after the spec wording fix and the merge were done on disk).
- Backend suite: 1267 passed (1214 before the change). `apps/relational_mapping`: 170 tests. `apps/domain_manifest`: 146 tests.
- ~570 authored lines; no `size:exception` needed.
- Per `verify-report` (at verification time) the verdict was FAIL with one CRITICAL (C1: scenario "Declared crud and readOnly are still emitted verbatim" had no covering test). The orchestrator added the test and re-ran; the `verify-report` Addendum records PASS WITH WARNINGS, 0 CRITICAL (`apps/domain_manifest` 146 passed, backend 1267 passed). The Addendum is the final state; the initial FAIL is history only.

## Specs synced

| Domain | Action | Details |
|--------|--------|---------|
| generation-profile | Updated | 1 ADDED (`Effective Operations Derivation`). Requirement count 9 -> 10 (re-counted on disk with `^### Requirement`). |
| domain-manifest-export | Updated | 1 RENAMED (`CRUD Declaration Does Not Filter Operations` -> `CRUD Declaration Restricts Operations`), 3 MODIFIED (`CRUD Operations`, `CRUD Declaration Restricts Operations`, `Declared-Facts-Only Emission`). Requirement count 15 -> 15. |

Composition commands (both exit 0), each followed by `mv <main>.compose-tmp <main>`:

```
gentle-ai sdd-archive-compose --canonical openspec/specs/generation-profile/spec.md --delta openspec/changes/crud-restricts-operations/specs/generation-profile/spec.md --output openspec/specs/generation-profile/spec.md.compose-tmp
gentle-ai sdd-archive-compose --canonical openspec/specs/domain-manifest-export/spec.md --delta openspec/changes/crud-restricts-operations/specs/domain-manifest-export/spec.md --output openspec/specs/domain-manifest-export/spec.md.compose-tmp
```

The old heading `CRUD Declaration Does Not Filter Operations` no longer exists in `openspec/specs/`. No `*.compose-tmp` leftovers remain.

## Deviations from the plain flow

1. Spec wording amended BEFORE the merge and the archive snapshot (per `verify-report` W2): the Table property requirement and the scenario "The Table property is not a field" no longer claim equal `Table`s "hash equal". They now state `Table` is unhashable (dict-typed field) and equal tables compare `==` with equal fields and `repr`. `design.md` and the `tasks.md` task 2.1 text were aligned. `Column`/`TableProfile` hashability claims were kept untouched.
2. `tasks.md` Review Workload Forecast corrected (spec deltas ~286 lines, not ~118; estimated total ~473, from ~305).
3. `git mv` refused (the change folder was untracked); the fallback plain `mv` ran after the snapshot, as the skill allows.

## Warnings accepted (recorded at close)

- M3 equivalent mutant: covered by a direct test.
- Task 9.1 was open at verification time (per `verify-report` W1, open by design) and is closed at archive.
- W4: no safety-net column in `apply-progress` (baseline counts recorded instead).
- The private `_OPERATIONS` / `_operations` from `builder.entities` are imported by tests (per `verify-report` S2); revisit if the builder is refactored.
- Transient manifest/generator divergence: the manifest `operations[]` is filtered by `crud`/`readOnly`, but the Spring generator still emits all six controller operations until slice 2 (`spring-generator-crud-restriction`).

## Readback evidence

Snapshot `cp -R` of the change folder, `mv`, then `diff -r <snapshot> <archive>` (archive-report excluded, additive-only; it was written after the readback). Verbatim output:

```
(empty)
```

exit status 0.

## Archive contents

proposal.md, exploration.md, specs/generation-profile/spec.md, specs/domain-manifest-export/spec.md, design.md, tasks.md (24/24), apply-progress.md, verify-report.md, archive-report.md.

## Follow-ups (not in this change)

1. Slice 2 `spring-generator-crud-restriction`: gate the Spring controller/service/imports with the same `effective_operations`; no controller/service when the set is empty; undeclared output byte-identical.
2. Inheritance API.
3. Relation navigation endpoints.
4. Undo/Redo + Presence verification.
5. Flutter frontend.
