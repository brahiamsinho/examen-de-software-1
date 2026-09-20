# Archive Report: Generated Project Domain Manifest

**Date**: 2026-09-20  
**Change**: generated-project-domain-manifest  
**Status**: ARCHIVED — verified PASS WITH WARNINGS, 0 CRITICAL  
**Task Completion**: 31/31 ✓

## Final State Authority

This report records the state of the change AT CLOSE per the Final-State Authority hierarchy in sdd-archive/SKILL.md.

- **Explicit final-state facts from orchestrator**: verify warnings 1, 3, 4 were already fixed by the orchestrator in the delta specs before this archive. Warning 2 (no formal TDD cycle table in apply-progress; tasks.md records RED/GREEN pairs) is accepted. Warnings 5-8 accepted per verify-report context. All 31/31 tasks confirmed done. Gate `MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh` exit 0 re-run independently by the orchestrator: BUILD SUCCESSFUL 45s, /v3/api-docs 200, Postman files and domain-manifest.json written.

- **Task Completion Gate** (source of truth): All 31 implementation tasks in `tasks.md` are marked complete (checked: [x]). No stale unchecked tasks remain.

- **Verification Report** (per verify-report.md): PASS WITH WARNINGS, 0 CRITICAL, 14 requirements, 36 scenarios, 87 domain_manifest tests passing, 987 total backend tests passing.

## Specs Synced

Two delta specs merged into main openspec/specs:

| Domain | Action | Spec File | Requirements | Scenarios |
|--------|--------|-----------|--------------|-----------|
| domain-manifest-export | Created | openspec/specs/domain-manifest-export/spec.md | 9 | 21 |
| generated-project-verification | Modified | openspec/specs/generated-project-verification/spec.md | 10 | 15 |

**Total in archive**: 14 requirements, 36 scenarios  
**Total main specs after archive**: 24 (added domain-manifest-export)

### Spec Amendments at Archive

Per verify-report WARNING 1 and 4, the following delta-spec amendments were applied by the orchestrator before archive and are reflected in the merged main specs:

- **WARNING 1**: Spec Deterministic Ordering language changed from "ordered by TABLE name" to "ordered by entity name" (matches design DD125 and implementation).
- **WARNING 4**: Spec wording clarified: inheritance scenarios mention the single root entity (not separate subclasses per DD125/DD126); enum `values` items are `{value, label}` objects (not just `{name, values}`).

These amendments were confirmed present in the delta specs at merge time.

## Artifacts in Archive

```
openspec/changes/archive/2026-09-20-generated-project-domain-manifest/
├── proposal.md
├── specs/
│   ├── domain-manifest-export/
│   │   └── spec.md
│   └── generated-project-verification/
│       └── spec.md
├── design.md
├── tasks.md
├── gate-evidence.md
└── archive-report.md (this file)
```

## Verification Summary

**Verdict**: PASS WITH WARNINGS (0 CRITICAL)

- Tasks: 31/31 complete
- Build: passed (compileall-q apps/domain_manifest exit 0)
- Tests: 87 passed in apps/domain_manifest, 987 total backend suite
- Gate: exit 0, BUILD SUCCESSFUL 45s, /v3/api-docs 200, Postman and manifest outputs verified
- TDD: RED/GREEN pairs recorded in tasks.md (2.1/2.2 through 8.1/8.2); tests meaningful and mutation-sensitive

### Accepted Warnings

1. **Spec vs design mismatch (WARNING 1 — FIXED)**: Spec now correctly states "ordered by entity name" (matches DD125).
2. **Strict TDD evidence (WARNING 2 — ACCEPTED)**: apply-progress has no "TDD Cycle Evidence" table, but tests are on disk and meaningful; tasks.md records RED/GREEN pairs.
3. **Version literal scan (WARNING 3 — FIXED)**: Scenario retagged [manual]; verified by hand (no 3.1.1 in domain_manifest, compose, scripts).
4. **Spec wording drift (WARNING 4 — FIXED)**: Spec now correctly describes single root entity with subtypes and `{value, label}` enum structure.
5. **Write-failure scenario (WARNING 5 — ACCEPTED)**: Spec uses existing regular file; test uses child of file. Both behave correctly (exit 1, error:). No automated test for literal case; verified by hand.
6. **Manual-only proof (WARNING 6 — ACCEPTED)**: Compose stanza, script step 4, default-services are manual-only. One negative check recorded in gate-evidence.md; green gate after revert rests on orchestrator re-run.
7. **Authored size (WARNING 7 — ACCEPTED)**: ~1000 lines total vs 800 budget (tests table-driven). Orchestrator decision: `size:exception`.
8. **Minor assertion issues (WARNING 8 — ACCEPTED)**: `issubclass(ManifestError, ValueError)` class-level only; determinism lambdas report ids on failure.

## Coherence Check

All 11 design decisions (DD121–DD131) confirmed implemented and coherent per design.md:

- DD121: new app after postman_export ✓
- DD122: RelationalModel as source ✓
- DD123: naming import only, local oneToOne ✓
- DD124: serialize duplicated, cli glue ✓
- DD125: ordering, neutral types, subtypes (spec amended) ✓
- DD126: resourcePath null iff no operations ✓
- DD127: determinism ✓
- DD128: compose stanza and step 4 ✓
- DD129: drift guard ✓
- DD130: manual proof for compose/script ✓
- DD131: declared facts only ✓

## Isolation Check

**Boot Change Isolation** confirmed per verify-report:

- Generated sources unchanged (41-file sample oracle passes)
- Domain Manifest not in generated sources
- No actuator, Flyway, Swagger UI, or application.yml keys added
- `SPRINGDOC_VERSION` remains only in `emit/versions.py`
- No new apps import domain_manifest; domain_manifest imports only `spring_generator.emit.naming` (plus sample_model in CLI glue)
- Default services and behavior unchanged

## Next Steps

After commit, the next recommended SDD work is:

1. **Mapper with generation_metadata** (enabling item 12 of previous roadmap): mapper must carry section 33 metadata (generation_metadata) to support searchable, sortable, defaultSort, auditable, readOnly, aliases.
2. **Flutter frontend driven by manifest**: client-side generation using the domain manifest.
3. **Optional Postman import**: import Postman collection into the API.
4. Filter/search API enhancements (depends on generation_metadata).
5. Assistant/AssistantCommand integration (out of scope for this cycle).

## Engram Observation IDs

Archive report persisted to Engram (`sdd/generated-project-domain-manifest/archive-report`) via mem_save.

## Date and Authority

**Archived by**: sdd-archive phase executor  
**Archive date**: 2026-09-20  
**Verification date**: 2026-09-20 (per verify-report)  
**Final-state decision**: All work complete, no blockers, archive can close the SDD cycle.

---

**SDD Cycle Status**: ✓ COMPLETE — Change fully planned, implemented, verified and archived.
