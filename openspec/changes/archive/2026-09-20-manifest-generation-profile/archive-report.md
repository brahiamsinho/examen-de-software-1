# Archive Report: manifest-generation-profile

**Archived**: 2026-09-20
**Archive path**: `openspec/changes/archive/2026-09-20-manifest-generation-profile/`
**Mode**: openspec (no Engram artifact observations existed for this change; the `sdd/manifest-generation-profile/*` search returned none, so there are no observation IDs to list)
**Outcome**: closed, verified PASS WITH WARNINGS, 0 critical. Work is uncommitted on `main`.

## Final state at close

- Tasks: 24/24 complete in `tasks.md` (task 11.4 ticked at archive, after the rename and Purpose fix were done on disk).
- Backend suite: 1107 passed (1070 before). `apps/domain_manifest`: 125 tests (88 before).
- ~419 authored lines; no `size:exception` needed.
- Sample-model `docs/domain-manifest.json` stays byte-identical; `schemaVersion` stays `1`.

## Specs synced

| Domain | Action | Details |
|--------|--------|---------|
| domain-manifest-export | Updated | 1 RENAMED (`Declared-Facts-Only Exclusion` -> `Declared-Facts-Only Emission`), 2 MODIFIED (`Entity Content`, `Declared-Facts-Only Emission`), 5 ADDED. Requirement count 10 -> 15 (re-counted on disk with `^### Requirement`). |

Composition command (exit 0, after the delta gained a RENAMED section; see Deviations):

```
gentle-ai sdd-archive-compose --canonical openspec/specs/domain-manifest-export/spec.md --delta openspec/changes/manifest-generation-profile/specs/domain-manifest-export/spec.md --output openspec/specs/domain-manifest-export/spec.md.compose-tmp && mv ...compose-tmp openspec/specs/domain-manifest-export/spec.md
```

ADDED requirements: Default Sort Attribute Resolution, ManifestError Location and Re-export, Profile Builder Decoupling, CRUD Declaration Does Not Filter Operations, Profile Emission Determinism and Sample Neutrality.

The main spec no longer contains `Declared-Facts-Only Exclusion`. Its Purpose paragraph now states the declared profile is emitted under `profile`, and that `aliases`, `entity` and the raw `generation_metadata` object are never emitted. No `*.compose-tmp` leftovers remain.

## Deviations from the plain flow

1. The original delta listed the new heading `Declared-Facts-Only Emission` only under MODIFIED, so the first compose run refused (`no canonical requirement named "Declared-Facts-Only Emission"`). Per the orchestrator's instruction, a `## RENAMED Requirements` section (`### Requirement: Old -> New` heading plus a `(Reason: ...)` note, the format the tool demands) was added to the change's delta spec BEFORE the archive snapshot; the compose then passed. The archived delta therefore composes on its own.
2. Before archive, `proposal.md` stale sentences were amended so `aliases`, `entity` and `generation_metadata` are all named as never emitted (Out of Scope list, Modified Capabilities, risk table row, success criterion). The design/spec text was the authority.
3. `git mv` refused (the change folder was untracked); the fallback plain `mv` ran after the snapshot, as the skill allows.

## Warnings accepted (recorded at close)

- M3 equivalent mutant: the `profile is None` guard is redundant, so the mutant is behaviourally equivalent.
- Task 11.4 was open at verification time (per `verify-report`, warning W1) and is closed at archive.
- `EXCLUDED_KEYS` equality is not asserted explicitly (the scenario is covered by the absence checks).
- The 'foreign id' `defaultSort` scenario is covered by an id that matches no column.
- Stale proposal text (per `verify-report`, second warning) was fixed at archive (Deviation 2).

## Readback evidence

Snapshot `cp -R` of the change folder, `mv`, then `diff -r <snapshot> <archive>` (archive-report excluded, additive-only). Verbatim output:

```
(empty)
```

exit status 0.

## Archive contents

proposal.md, specs/domain-manifest-export/spec.md, design.md, tasks.md (24/24), apply-progress.md, verify-report.md, archive-report.md.

## Follow-ups (not in this change)

1. Filtering/search in the generated Spring API using searchable/sortable/defaultSort.
2. Authoring path for the profile (commands/UI).
3. Make `crud` restrict `operations[]` in manifest and generator (DD147 tech debt).
4. Section 37 item 12 remainder.
5. Flutter frontend.
