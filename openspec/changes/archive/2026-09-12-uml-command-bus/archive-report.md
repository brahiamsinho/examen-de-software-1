# Archive Report: uml-command-bus

**Change**: uml-command-bus
**Archived**: 2026-09-12
**Status**: Complete — Ready for next SDD cycle

## Artifact Traceability

All artifacts successfully archived and merged into main specs:

| Artifact | Type | Engram ID | Status |
|----------|------|-----------|--------|
| Proposal | architecture | #507 | Retrieved, 2 open design questions flagged for spec/design |
| Specification | architecture | #508 | Retrieved, 1 new domain (uml-command-bus), 11 requirements / 13 scenarios merged |
| Design | architecture | #509 | Retrieved, 7 ADRs (DD1-DD7) verified in code |
| Tasks | architecture | #510 | Retrieved, 20/20 tasks completed and checked |
| Verify Report | filesystem-only (no matching Engram observation found; hybrid mode, this artifact lives at `openspec/changes/uml-command-bus/verify-report.md`) | n/a | Read directly from filesystem, PASS verdict with 0 CRITICAL, 0 open WARNING |
| Apply Progress (TDD evidence, referenced by verify-report) | architecture | #511 | Referenced by verify-report's post-verify amendment; not independently re-read for this archive |

## Verification Status (per verify-report.md, filesystem)

**Original verdict**: PASS WITH WARNINGS (1 WARNING: apply-progress artifact #511 missing a standalone "TDD Cycle Evidence" table).

**Post-verify amendment (same file, "Post-verify amendment" section)**: the WARNING was fixed by updating Engram observation #511 with the missing TDD Cycle Evidence table (RED/GREEN/TRIANGULATE/SAFETY NET columns, one row per task 1.1-10.2). No source or test file changed — a documentation-format fix only.

**Final Verdict**: PASS — 0 CRITICAL, 0 WARNING, 2 non-blocking SUGGESTION carried forward.

Per the Final-State Authority hierarchy, this archive report records the amended final state (PASS, 0 WARNING), not the original pre-amendment WARNING snapshot; the amendment is a fact recorded in the same verify-report.md, ranking above the original verdict text it supersedes within that same document.

### Completeness Confirmed
- **Tasks**: All 20/20 implementation tasks marked `[x]` in tasks.md (Phases 1-10); each corresponds to real, inspected code with passing tests, cross-checked against actual files in `backend/apps/uml_commands/` by direct source read (not checkbox-only).
- **Specs**: 1 new domain spec, 11 requirements, 13 scenarios; every scenario mapped to implementing code with a passing covering test.
- **Design**: 7 ADRs (DD1-DD7) documented in design.md; all followed in the actual code, including one documented self-package-import clarification in `test_import_boundary.py` (consistent with the spec's literal wording, not a violation).
- **Test Evidence** (independently re-run at verify time, not copied from apply-progress claims):
  - Scoped: 43/43 tests pass (`docker compose exec backend pytest apps/uml_commands -q`)
  - Full-suite regression: 276/276 tests pass, 0 regressions
  - Build: N/A (pure Python package, no build/compile step, no migrations)

### Spec Compliance by Domain

| Domain | Requirements | Scenarios | Status |
|--------|--------------|-----------|--------|
| uml-command-bus | 11 | 13 | PASS |

### Key Decisions Verified (DD1-DD7)

- **DD1**: `UmlCommand` is a closed `Union` type alias, one frozen dataclass per command — confirmed via `typing.get_args()` covering exactly 7 types in `test_commands.py`.
- **DD2**: Registry is a static `dict[type, Handler]` module constant (`dispatcher._HANDLERS`) — confirmed, exactly 7 entries.
- **DD3**: Commands carry already-constructed domain value objects (`AddAttribute.attribute`, `AddRelationship.relationship`); remove-only commands use flat id fields — confirmed in `commands.py`.
- **DD4**: `apply()` takes an explicit `now: datetime.datetime` keyword-only argument; no handler/dispatcher code calls `datetime.now()` — confirmed.
- **DD5**: Handlers organized one module per element kind (`classes.py`, `attributes.py`, `relationships.py`) — confirmed, exact layout.
- **DD6**: Missing-target no-op returns the same unchanged model object (identity, not equality) before any `replace()` — confirmed for all 4 spec-named commands plus the `rename_class` extrapolation.
- **DD7**: Import-boundary AST test scopes to `commands.py`/`dispatcher.py`/`handlers/*.py`, excludes `apps.py`/`__init__.py`/tests — confirmed; `apps.py` legitimately imports `django.apps.AppConfig` outside the scoped set.

### Issues Found and Resolution Status

**CRITICAL**: None

**WARNING** (1, resolved before archive):
- Original finding: apply-progress artifact (#511) lacked a standalone "TDD Cycle Evidence" table (RED/GREEN/TRIANGULATE/SAFETY NET columns per task), unlike the prior `canonical-uml-model` cycle's apply-progress.
- Resolution: Engram observation #511 was updated (topic_key upsert) with the missing table, one row per task 1.1-10.2, matching the prior cycle's format. No source or test file changed — documentation-format fix only.
- Status: RESOLVED — verify-report.md's own "Post-verify amendment" section confirms the "TDD Evidence reported" check now reads Yes, not Partial.

**SUGGESTIONS** (2, both non-blocking, carried forward, no action needed):
1. No coverage tool (pytest-cov) is configured for `backend/`; adding one in a future cycle would let subsequent verify passes report quantitative changed-file coverage instead of file-pairing inspection (same suggestion carried over from the prior `canonical-uml-model` cycle, still unaddressed).
2. `handlers/attributes.py::remove_attribute` and `handlers/relationships.py::remove_relationship` each perform two conceptually separate lookups (existence check, then filter); not a defect, both O(n) over small collections — a future cycle could fold them into one pass if collections grow large.

## Specs Synced to Main (openspec/specs/)

### New Capability Spec Created

1. **uml-command-bus** — `openspec/specs/uml-command-bus/spec.md` (new; no prior main spec existed for this domain, so the delta spec was copied mechanically in full)
   - Dispatcher Apply Contract (never mutates input, always runs validation)
   - AddClass, RemoveClass with Cascade, RenameClass
   - AddAttribute, RemoveAttribute
   - AddRelationship, RemoveRelationship
   - Always-Apply Diagnostics Policy (never raises, never refuses)
   - Missing-Target No-Op Policy
   - uml_commands Import Boundary
   - 11 requirements, 13 scenarios, all covered by passing tests

### Modified Main Specs

None. This cycle introduces one brand-new capability domain and touches no existing main spec.

## Archive Contents Verified

- [x] proposal.md — 2 open design questions recorded (cascade-remove vs. dangling; always-apply vs. reject-on-invalid), both resolved in design.md/spec.md
- [x] exploration.md — present (optional artifact from sdd-explore)
- [x] specs/ — 1 new domain spec, fully copied (no delta merge needed, no pre-existing main spec)
- [x] design.md — 7 ADRs documented and verified
- [x] tasks.md — 20/20 tasks complete and checked
- [x] verify-report.md — PASS verdict recorded (amended post-warning fix, final state 0 CRITICAL / 0 WARNING / 2 SUGGESTION)

## Native Review Receipt Gate

No `reviewGate` was present in structured status for this candidate — receipt-driven development was not engaged for this change (kill switch off / no review started). Archive proceeds under ordinary repository policy, consistent with the RDD contract's opt-in default.

## Mechanical Copy Evidence

**NEW Domain Spec Copied** (shell `cp` + `mv` via temp file, verified with `diff -r`):
```
uml-command-bus: PASS (empty diff)
  source: openspec/changes/uml-command-bus/specs/uml-command-bus/spec.md
  dest:   openspec/specs/uml-command-bus/spec.md
```

**Change Folder Moved to Archive** (shell `mv` — `git mv` reported "source directory is empty" because the change folder was untracked in git; fell back to plain `mv` per the skill's mechanical-move contract — verified with `diff -r` against a pre-move recursive snapshot):
```
Source snapshot → openspec/changes/archive/2026-09-12-uml-command-bus
Verification: PASS (empty diff, no bytes altered or truncated)
```

## SDD Cycle Complete

This change has been fully planned (proposal), specified (1 new domain spec, 13 scenarios), designed (7 ADRs), implemented (20 tasks, ~650-750 changed lines, single-PR budget), verified (PASS with 0 CRITICAL, 0 WARNING after post-verify amendment), and archived.

**Ready for next SDD cycle.**

---

**Archive Report Created**: 2026-09-12
**Orchestrator**: sdd-archive
**Artifact Store Mode**: hybrid (Engram + openspec)
**Observation IDs**: #507 (proposal), #508 (spec), #509 (design), #510 (tasks), #511 (apply-progress, referenced by verify-report's post-verify amendment) — no Engram observation found for verify-report; read directly from `openspec/changes/uml-command-bus/verify-report.md` (filesystem)
