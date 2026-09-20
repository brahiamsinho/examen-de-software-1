# Archive Report: UML Generation Profile Authoring

**Status**: Complete and archived
**Change**: `uml-generation-profile-authoring`
**Archive date**: 2026-09-20
**Archived to**: `openspec/changes/archive/2026-09-20-uml-generation-profile-authoring/`
**Artifact store**: OpenSpec

## Final State

- Native SDD status was refreshed before archival: `archive: ready`, `nextRecommended: archive`, and no blocked reasons.
- All 31/31 persisted implementation tasks are checked in `tasks.md`.
- The accepted verification report is authoritative at close: 7/7 requirements, 54/54 current scenarios, 1184 full backend tests passed, focused suites passed with 86 + 134 + 588 tests, Docker build passed, and native attempt settlement passed.
- Evidence revision: `sha256:dbfacc556f3de0c66119568318264e383866f32317452cb54fe926fde2c8b860`.
- Verification result: `PASS WITH WARNINGS`; no critical findings or blockers remain.
- Warnings retained as final-state context: coverage is unavailable by project configuration, no backend linter/type checker is configured, browser E2E is not configured, and apply-progress safety-net evidence uses narrative markers.

## Artifacts Read

The following authoritative native artifacts were read directly before archival:

- `openspec/changes/uml-generation-profile-authoring/proposal.md`
- `openspec/changes/uml-generation-profile-authoring/specs/uml-command-bus/spec.md`
- `openspec/changes/uml-generation-profile-authoring/specs/uml-document-persistence/spec.md`
- `openspec/changes/uml-generation-profile-authoring/design.md`
- `openspec/changes/uml-generation-profile-authoring/tasks.md`
- `openspec/changes/uml-generation-profile-authoring/apply-progress.md`
- `openspec/changes/uml-generation-profile-authoring/verify-report.md`
- `openspec/config.yaml`

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| `uml-command-bus` | Updated | Native `sdd-archive-compose` applied the delta requirements and preserved unrelated requirements. |
| `uml-document-persistence` | Updated | Native `sdd-archive-compose` applied the delta requirements, including the import-boundary amendment and layout requirement rescoping. |

Composition commands executed:

```text
gentle-ai sdd-archive-compose --canonical openspec/specs/uml-command-bus/spec.md --delta openspec/changes/uml-generation-profile-authoring/specs/uml-command-bus/spec.md --output openspec/specs/uml-command-bus/spec.md.compose-tmp
gentle-ai sdd-archive-compose --canonical openspec/specs/uml-document-persistence/spec.md --delta openspec/changes/uml-generation-profile-authoring/specs/uml-document-persistence/spec.md --output openspec/specs/uml-document-persistence/spec.md.compose-tmp
```

Both compositions completed successfully and atomically replaced their canonical specs.

## Mechanical Archive Evidence

The active change directory was moved mechanically to the dated archive destination. The mandatory recursive readback was executed against a pre-move snapshot.

Verbatim command output:

```text
diff -r snapshot/source openspec/changes/archive/2026-09-20-uml-generation-profile-authoring
```

The `diff -r` output was empty, confirming byte-identical archived contents. The active source directory is absent. `archive-report.md` was added afterward and is therefore intentionally excluded from the pre-move comparison.

## Archive Contents

- `proposal.md` ✅
- `specs/` ✅
- `design.md` ✅
- `tasks.md` ✅ (31/31 tasks complete)
- `apply-progress.md` ✅
- `verify-report.md` ✅
- `archive-report.md` ✅

## SDD Cycle Complete

The change was planned, implemented, independently verified, delta-synced into the canonical specifications, and archived. The frontend follow-up remains outside this change's scope.
