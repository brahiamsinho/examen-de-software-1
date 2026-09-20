```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:9c4949c6162b80e9426ede51eea772bbbe678e36dd9dba156f625a2dd6f1936a
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 11/11
scenarios: 15/15
test_command: docker compose exec -T backend pytest -q
test_exit_code: 0
test_output_hash: sha256:a86f154a0a6a39b25de3c8ba77c6054aecb4bc5f86b0239c970ab7f89e7f0076
build_command: bash scripts/verify-generated-project.sh
build_exit_code: 0
build_output_hash: sha256:baa204d949317ae6b489c838a8775e7d4ec9554bff170b4a6f1e1ead23da5c8c
```

## Verification Report

**Change**: generated-project-compile-check
**Version**: N/A (new capability `generated-project-verification`)
**Mode**: Strict TDD (Python half) + manual gate (DD85)
**Date**: 2026-09-19

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 42 |
| Tasks complete | 42 |
| Tasks incomplete | 0 |

`tasks.md` has 42 checked items and zero unchecked. Every file named by the tasks exists on disk (app shell, `domain/`, `writer/`, `samples/`, 6 test modules, `runner_image.py`, `cli.py`, compose services, `scripts/verify-generated-project.sh`, the `.gitignore` line, the `settings.py` line, DD75-DD86 in `DECISIONS_LOG.md`, the session note, `gate-evidence.md`).

### Build & Tests Execution
**Build (manual gate)**: PASSED on independent re-run. The first verify run FAILED (exit 1): Gradle could not download `postgresql-42.7.13.pom` (Remote host terminated the handshake, TLS). An immediate identical re-run gave `BUILD SUCCESSFUL in 46s`, exit 0, `5 actionable tasks: 5 executed`. Resolved `GRADLE_IMAGE=[gradle:9.7.1-jdk21]`. The failed run also showed that a failing Gradle run makes the script exit non-zero.

```text
bash scripts/verify-generated-project.sh   -> exit 0, BUILD SUCCESSFUL in 46s
```

**Tests**: 820 passed / 0 failed / 0 skipped (`docker compose exec -T backend pytest -q`, exit 0).
`apps/spring_generator`: 317 passed. `apps/generation_runner`: 56 passed (parametrized).

**Coverage**: Not available (no coverage tool configured); skipped, not a failure.

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD evidence reported | OK | apply-progress #681 has a per-task RED/GREEN table (condensed; no SAFETY NET/TRIANGULATE/REFACTOR columns) |
| All tasks have tests | OK | Python tasks 1.1-4.3 map to 6 test modules; phases 5-7 are manual by design (DD85) |
| RED confirmed (tests exist) | OK | 6/6 test files exist |
| GREEN confirmed (tests pass) | OK | 56/56 pass now, full suite 820 |
| Triangulation adequate | OK | 13 shape cases, case-dup vs exact-dup, escape helper accept and reject, CLI success/refusal/usage/bad-package, django trap plus control |
| Safety Net for modified files | OK | only 1-line edits to `settings.py` and `.gitignore`; 764 baseline preserved (820 = 764 + 56) |

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | writer, errors, image tag, sample model, apps | 4 | pytest |
| Integration (subprocess of `python -m`, no Docker) | CLI (8) + import check (1) | 2 | pytest + subprocess |
| E2E | manual compose gate | n/a | docker compose + gradle |

### Assertion Quality
No tautologies, no ghost loops, no smoke-only tests. `test_escape_helper_accepts_paths_that_stay_inside_the_target` asserts `is None` (paired with the reject test, acceptable). The guard test asserts at least 4 scanned files and the scanner has its own positive/negative triangulation test, so it is non-vacuous. **Assertion quality**: 0 CRITICAL, 0 WARNING.

### Spec Compliance Matrix
| Requirement | Scenario | Evidence | Result |
|-------------|----------|----------|--------|
| Writer Path Validation | Unsafe path is rejected | `test_write_sources.py::test_unsafe_path_shapes_are_rejected_and_nothing_is_written` (13 params), `test_escape_helper_rejects_a_path_through_a_symlinked_directory`, `test_write_sources_runs_the_escape_check_before_writing_anything` | COMPLIANT |
| Writer Path Validation | Case-insensitive duplicate | `test_case_only_duplicate_is_rejected_with_an_explanatory_message`, `test_exact_duplicate_path_is_rejected_and_nothing_is_written` | COMPLIANT |
| Validate-Before-Write Atomicity | Invalid last file writes nothing | `test_invalid_last_file_leaves_the_target_empty`, `test_missing_target_is_not_created_when_validation_fails` | COMPLIANT |
| Encoding and Output | Non-ASCII with LF | `test_contents_are_utf8_with_lf_only_and_paths_are_returned_in_input_order`, `test_a_bare_newline_in_contents_stays_a_single_lf_byte` | COMPLIANT |
| Non-Empty Target Refusal | Stale target refused | `test_non_empty_target_is_refused_and_stale_file_is_untouched`, `test_missing_target_is_created_on_success`, `test_empty_target_is_accepted` | COMPLIANT |
| Writer Decoupling | Import guard | `test_writer_decoupling.py::test_guarded_directories_never_import_the_generator`, `test_scanner_flags_a_generator_import`, `test_importing_the_writer_does_not_load_the_generator`; stub accepted via SimpleNamespace in write tests | COMPLIANT |
| Sample Model | Deterministic generation | `test_sample_model.py::test_generation_from_the_sample_model_is_deterministic`, `test_sample_model_generates_the_expected_project_files` (41 files, build.gradle) | COMPLIANT |
| CLI Behavior | Refused target non-zero | `test_cli.py::test_cli_refuses_a_non_empty_target_without_a_traceback`; manual 7.3 re-run: exit 1, stderr message, volume intact | COMPLIANT |
| CLI Behavior | No Django bootstrap | `test_cli_never_calls_django_setup` plus control `test_the_django_setup_trap_really_fires_when_setup_is_called` | COMPLIANT |
| Image Tag Derivation | Tag follows versions.py | `test_runner_image.py::test_gradle_runner_image_follows_the_pinned_versions` | COMPLIANT |
| Image Tag Derivation | Unset image fails loudly | gate-evidence 7.2: fails at image PULL naming `GRADLE_IMAGE`, after `generate-project` already ran; not before any container starts, and compose does not use the required-variable form | PARTIAL (accepted deviation, see W1) |
| Compose Chain Contract | Default up unaffected | Re-run: `docker compose config --services` without profile lists db redis backend frontend mailpit; with the profile it adds generate-project and jvm-verify | COMPLIANT |
| Compose Chain Contract | Failure propagates | Re-run: a failing Gradle build (network) gave script exit 1; `depends_on: service_completed_successfully` present. No recorded run of a failing `generate-project` (see W3) | COMPLIANT |
| Default Suite Isolation | Offline default suite | 820 pass; no docker or network call in tests; only subprocess use is `python -m ...` | COMPLIANT |
| Manual Gate Evidence | Evidence recorded | `gate-evidence.md` plus this report (command, exit 0, BUILD SUCCESSFUL) | COMPLIANT |

**Compliance summary**: 14/15 scenarios fully compliant, 1 compliant with an accepted, documented deviation (counted complete in the envelope because the orchestrator accepted it; see W1). Requirements: 11/11 counted complete; Image Tag Derivation carries the deviation (compose required-variable form replaced by a sentinel default). 11 requirements and 15 scenarios counted from the spec headings.

### Correctness (Static Evidence)
| Item | Status | Notes |
|------|--------|-------|
| write_sources order (target, shape, dups, escape, write) | Implemented | `writer/filesystem.py`; LF newline, utf-8 |
| Decoupling guard | Implemented, non-vacuous | scans writer and domain directories via AST; handles both import forms, including a from-apps-import-spring_generator form; asserts files exist |
| No version literal | Verified | grep for 9.7.1, jdk21, 21 in `apps/generation_runner`: no match; compose and script: no match (only the jvm-verify service/profile name) |
| No docker.sock, no jvm marker | Verified | no match in compose, script or `pyproject.toml` (pytest ini options define no markers) |
| Script safety | OK | set -euo pipefail, MSYS_NO_PATHCONV=1, empty-tag guard, quoted variable, cd relative to the script dir, no string-built commands, no eval, no rm in the script |
| rm -rf scope | OK | only in the compose command, literal `/generated/project` (a subdirectory); never `/generated`; no variable interpolation |
| Compose validity | OK | `docker compose config -q` rc 0 with GRADLE_IMAGE unset, with GRADLE_IMAGE=gradle:x, and with `--profile jvm-verify` |
| git status | OK | only intended files; `.pi/` untracked; no build/ or .gradle/ leaked (both ignored); nothing committed |
| Docs | Accurate | 820/317/56 present; DD75-DD86 in `DECISIONS_LOG.md`; docs say not yet verified, archived or committed |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| DD75/DD76 pure vs glue split, Protocol input | Yes | |
| DD77 typed errors | Yes | 4 subclasses plus base |
| DD78 validation order | Yes | step-1 vs symlink gap documented; resolve seam plus helper test |
| DD79 CLI no Django, exit 0/1/2 | Mostly | narrow gap, see W2 |
| DD80 tag from versions.py | Yes | |
| DD81 readable ids plus docstring | Yes | |
| DD82 script | Yes | kept --no-deps -T, CR stripping and tail -n 1 hardening (harmless) |
| DD83 two profile services, root, subdir-only rm | Yes | plus `./backend:/app:ro` mount (extra deviation, needed: dev image ships no source) |
| DD84 no container path in Python | Yes | asserted by `test_cli_source_has_no_django_import_and_no_container_path` |
| DD85 no jvm marker or socket | Yes | |
| DD86 .gitignore gradle entry | Yes | |

### Issues Found
**CRITICAL**: None.

**WARNING**:
- W1 (accepted deviation): spec Image Tag Derivation requires compose to consume the tag as a required variable and to fail before any container starts. The implementation uses a sentinel default image; with GRADLE_IMAGE unset the run fails at image pull naming GRADLE_IMAGE, after generate-project has already regenerated the volume. Justified by task 6.1 (the required form broke exec, ps and config). The spec text was not amended; update it at archive so it documents the sentinel behavior.
- W2: the CLI catches only (GeneratedSourceWriteError, ValueError). UngeneratableSourceError (extends Exception, not ValueError) and a plain OSError (observed: a read-only path gave a Traceback, exit 1) escape as tracebacks, contradicting DD79 (any generation error, no traceback). The exit code is still non-zero, so the gate is unaffected; unreachable with the fixed sample model.
- W3: no recorded run of a failing generate-project proving Gradle is skipped (relies on standard service_completed_successfully semantics; the gate log shows Exited before Gradle starts on success).
- W4: the gate depends on live network access to Maven Central (no Gradle cache volume, per spec). One transient TLS handshake failure was observed during this verify; the re-run passed. The script has no retry.
- W5: Default up unaffected is verified through config --services only, not an actual docker compose up.

**SUGGESTION**:
- S1: extend the CLI except clause to UngeneratableSourceError and OSError and add a test (fixes W2 in a later slice).
- S2: the apply-progress TDD table omits SAFETY NET, TRIANGULATE and REFACTOR columns; add them next time.
- S3: the symlink-escape check is only covered at helper level (DD78 step 1 makes the end-to-end case unreachable); it is documented as defense in depth.
- S4: `.pi/` remains untracked; do not commit it.

### Verdict
PASS WITH WARNINGS

All 42 tasks are complete, 820/820 tests pass, and the compile gate re-ran to BUILD SUCCESSFUL (exit 0) after one transient network failure. There are no CRITICAL issues; the warnings are the accepted GRADLE_IMAGE sentinel deviation and CLI error-handling gaps. Ready for sdd-archive (update the spec wording for W1 at archive).
