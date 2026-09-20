# Archive Report: Generated Project Compile Check

**Change**: generated-project-compile-check
**Archive Date**: 2026-09-19
**Archive Location**: `openspec/changes/archive/2026-09-19-generated-project-compile-check/`
**Spec Merged To**: `openspec/specs/generated-project-verification/spec.md` (new full capability)
**SDD Phase**: archive
**Status**: COMPLETE

## Cycle Summary

Slice 2 of 3 (§37 item 13, "generated backend compilable"). For the first time, the in-memory Gradle project returned by `generate_project_sources` is materialized to disk and proven to compile with `gradle build --no-daemon`. Scope: new `apps/generation_runner` app (pure `write_sources` writer, CLI, sample builder, image-tag function), manual compose-based gate, spec.

**Final Verdict**: VERIFIED (PASS WITH WARNINGS, 0 CRITICAL) and ARCHIVED
- Tasks complete: 42/42 ✅
- Requirements compliant: 11/11 ✅
- Scenarios compliant: 15/15 (1 with accepted deviation) ✅
- Tests passing: 822 backend (58 new in generation_runner), 317 spring_generator ✅
- Manual gate: BUILD SUCCESSFUL, exit 0 ✅

## Final-State Facts (Post-Verify Amendments)

### W2 Resolved (Fixed by Orchestrator)
The CLI exception handling was **widened in a follow-on commit** after verify:
```python
# OLD (as verified):
except (GeneratedSourceWriteError, ValueError) as e:
    
# NEW (fixed):
except (GeneratedSourceWriteError, UngeneratableSourceError, ValueError, OSError) as e:
```

Two new test cases added to `tests/test_cli.py`:
- Test for `UngeneratableSourceError` surface as non-zero exit (1) with stderr message, no traceback
- Test for `OSError` (e.g., read-only path) surface as non-zero exit (1) with stderr message, no traceback

**Final test count after W2 fix**: 822 backend tests (764 pre-change + 58 new), 317 spring_generator unchanged.

### W1 Accepted Deviation (Documented)
The verify-report spec text claimed the required-variable form `${GRADLE_IMAGE:?}`, but during apply (task 6.1), this broke ordinary compose commands (`config`, `exec`, `ps`, `--profile` without a run). Fallback applied and accepted: sentinel default image value:

```yaml
image: ${GRADLE_IMAGE:-gradle.invalid/unset:GRADLE_IMAGE-not-set-run-scripts-verify-generated-project.sh}
```

With GRADLE_IMAGE unset, compose pulls the image and fails at pull time naming `GRADLE_IMAGE`. This is the actual behavior; the spec text should document it. **Amendment applied to merged spec**: the "Unset image fails loudly" scenario now correctly states that the failure occurs at image pull (after `generate-project` starts), not at interpolation time.

### W3, W4, W5 Remain Accepted Warnings
- **W3**: No recorded run of a failing `generate-project` proving `service_completed_successfully` skips Gradle. Relies on Docker standard semantics, confirmed by gate-evidence log.
- **W4**: Gate depends on live network access to Maven Central. One transient TLS failure during verify was observed; immediate re-run succeeded. No retry mechanism in the script (by design).
- **W5**: "Default up unaffected" verified by `docker compose config --services` (no live `docker compose up`).

All three remain accepted per the initial risk analysis; they do not block archive.

### Manual Gate Re-Run
The orchestrator independently re-ran the compile gate after verify:
```
bash scripts/verify-generated-project.sh
→ BUILD SUCCESSFUL in 50s
→ exit code 0
→ resolved GRADLE_IMAGE: gradle:9.7.1-jdk21
→ 41 files generated and compiled
```

Evidence: `openspec/changes/archive/2026-09-19-generated-project-compile-check/gate-evidence.md` (original verify run); orchestrator re-run confirmed independently.

### Commit Status
**NOT YET COMMITTED**. All work (apply + fixes after verify) remains staged/uncommitted. Repository state:
- Untracked: `.pi/` (explicitly never committed per project convention)
- Modified: `.gitignore`, `backend/config/settings.py`, `docker-compose.yml`, `docs/ai/*`
- New (untracked): `backend/apps/generation_runner/`, `scripts/verify-generated-project.sh`, `docs/ai/sessions/2026-09-19-agent-generated-project-compile-check.md`

## Artifacts Archived

All change artifacts moved to `openspec/changes/archive/2026-09-19-generated-project-compile-check/`:

- `proposal.md` ✅
- `specs/generated-project-verification/spec.md` ✅
- `design.md` ✅
- `tasks.md` (42/42 complete) ✅
- `verify-report.md` (PASS WITH WARNINGS) ✅
- `gate-evidence.md` ✅
- `exploration.md` ✅
- `archive-report.md` (this file) ✅

## Spec Merged

New capability spec created in main specs tree:
- **Destination**: `openspec/specs/generated-project-verification/spec.md`
- **Status**: Full capability spec (not a delta; the delta specs in `openspec/changes/generated-project-compile-check/specs/` represent a NEW capability, not a modification to an existing one)
- **Coverage**: 11 requirements, 15 scenarios, all addressed by implementation
- **Amendment**: Scenario "Unset image fails loudly" now documents the sentinel-default behavior (pull-time failure naming GRADLE_IMAGE, not interpolation-time abort)

## Traceability

This archive closes the SDD cycle:

| Artifact | Where |
|----------|-------|
| Proposal | `openspec/changes/archive/2026-09-19-generated-project-compile-check/proposal.md` |
| Spec | `openspec/specs/generated-project-verification/spec.md` (merged) |
| Design | `openspec/changes/archive/2026-09-19-generated-project-compile-check/design.md` (DD75–DD86) |
| Tasks | `openspec/changes/archive/2026-09-19-generated-project-compile-check/tasks.md` (42/42) |
| Apply | Not persisted; work reflected in repo tree (not yet committed) |
| Verify | `openspec/changes/archive/2026-09-19-generated-project-compile-check/verify-report.md` (PASS WITH WARNINGS) |
| Archive | This report + Engram entry `sdd/generated-project-compile-check/archive-report` |

## Learned

1. Compose interpolation happens on the whole file before any service runs, so a required-variable form that names an unset variable breaks all commands. Sentinel defaults that fail at pull time are safer for optional runtime setup.
2. A manual gate outside the pytest suite (DD85) requires explicit re-run evidence, not a proxy test. The orchestrator's independent gate re-run confirmed repeatability after archive.
3. Post-verify fixes (W2 widened exception handling) are appropriate when the verify report explicitly names the gap and recommends it. Apply-time findings should be recorded, fixed quickly, and reflected in the final archive record.
