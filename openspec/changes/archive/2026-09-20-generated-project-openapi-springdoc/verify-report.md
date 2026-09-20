```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:bfa19bda58b548c3f0fc3a540e725daf91af793f4f911d341a30b2bc10984ebc
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 5/5
scenarios: 20/20
test_command: docker compose exec -T backend pytest -q
test_exit_code: 0
test_output_hash: sha256:eea8ecad343dd592ca81758afce5af99e19f1b0cb0a8171ffb084b08d00ed0a8
build_command: MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh
build_exit_code: 0
build_output_hash: sha256:2bf4780a38ac4e45d788660d40b666d8d804309b82f91b2cf926667f693e2b8e
```

## Verification Report

**Change**: generated-project-openapi-springdoc
**Version**: N/A (delta specs: spring-boot-generation, generated-project-verification)
**Mode**: Strict TDD
**Date**: 2026-09-20

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 22 |
| Tasks complete | 22 |
| Tasks incomplete | 0 |

Counted from tasks.md (1.1-1.6, 2.1-2.5, 3.1-3.2, 4.1-4.4, 5.1, 6.1, 7.1-7.3). apply-progress (Engram #704) also says 22/22. A "24" figure does not appear anywhere in the change or docs/ai.

### Build & Tests Execution
**Build (manual gate)**: PASSED, exit 0, BUILD SUCCESSFUL in 43s
```text
MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh
boot-smoke: ready after 6s | POST /api/customers -> 201 | GET -> 200 | DELETE -> 204 | GET -> 404
boot-smoke: GET /v3/api-docs -> 200
boot-smoke: PASS
gen-db containers after run: 0
```

**Tests**: 840 passed / 0 failed / 0 skipped (full backend, 68.8s). Focused: spring_generator + generation_runner 393 passed; the three changed test files 63 passed.

**Negative gate (run by verifier, temporary edit)**: the "/api/customers" needle in the /v3/api-docs assertion of scripts/boot-smoke.sh was temporarily replaced by "/api/bogus-verify". Gate exit 7, log: "GET /v3/api-docs -> 200" then "FAIL: /v3/api-docs does not document /api/customers". Reverted with sed; the sha256 of scripts/boot-smoke.sh and the output of git diff scripts/boot-smoke.sh are byte-identical to the pre-edit state, grep -c bogus = 0; a positive gate run afterwards was exit 0. This was the only temporary source edit.

**Coverage**: not available (no coverage tool configured); not a failure.

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | WARNING | apply-progress (#704) and the session note carry a narrative (baseline 389, RED = ImportError for SPRINGDOC_VERSION plus missing coordinate in generated build.gradle, GREEN 393) but no formal "TDD Cycle Evidence" table |
| All tasks have tests | OK | Docker-free half (tasks 1.1-1.6, 2.1-2.5) has tests in 3 files; script half (3.x, 4.x) is [manual] by design (DD101/DD106) |
| RED confirmed (tests exist) | OK | test_scaffold_context.py, test_project_scaffold_sources.py, test_boot_smoke_contract.py exist and contain the new tests |
| GREEN confirmed | OK | 63/63 in the three files, 393/393 focused, 840/840 full |
| Triangulation adequate | OK | oracle equality + positive starter/position/count test + excluded-param inversion (ui, actuator) + DD72 scan + contract coordinate pin + scaffold_context value/propagation for two base packages |
| Safety net for modified files | OK | baseline 389 recorded before edits; +4 tests reconciles (389 to 393; 836 to 840 full) |

Independent mutation checks (temporary copy of emit/ and tests/ under /tmp/mut inside the container, deleted afterwards, confirmed gone):
- Appending a comment containing 3.1.1 to a copy of emit/renderer.py: only test_no_pinned_version_literal_is_restated_outside_the_versions_module[springdoc-version] failed (offenders == renderer.py); the other three ids stayed green.
- Appending a Jinja comment containing 3.1.1 to a copy of build.gradle.j2: the same single id failed (offenders == build.gradle.j2).
- Control (unmutated copy): green. So the DD72 word-bounded 3.1.1 scan really fails when the literal is restated in emit python or templates.
- Renderer kwarg guard: rendering build.gradle.j2 without springdoc_version raises jinja2 UndefinedError (StrictUndefined), so an omitted kwarg is caught loudly; the docs say it "rendered empty", which is inaccurate.
- The springdoc excluded-parametrization inversion is confirmed in the diff: "springdoc" replaced by "springdoc-openapi-starter-webmvc-ui" and "spring-boot-starter-actuator"; a positive test asserts the coordinate at SPRINGDOC_VERSION, its order (after the validation starter, before postgres runtimeOnly) and count("springdoc-openapi") == 1.

**Assertion quality**: all assertions verify real behavior (no tautologies, no ghost loops, no smoke-only). Minor: the contract test hardcodes the version literal (allowed outside emit/, see SUGGESTION 3).

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit (Docker-free) | 4 net new tests plus extended assertions | 3 | pytest |
| Integration/E2E (manual gate) | 1 gate run (+1 negative) | scripts/ | docker compose + Gradle |

### Spec Compliance Matrix
Counts: 5 requirements, 20 scenarios (heading count matches native status: 1+4 requirements, 11+9 scenarios).

**spring-boot-generation / Project Scaffold Generation**
| Scenario | Evidence | Result |
|----------|----------|--------|
| Scaffold yields exactly three files in fixed order | test_project_scaffold_sources path/order tests pass | COMPLIANT |
| Single-segment base package | existing test, pass | COMPLIANT |
| Repeated generation byte-identical | test_repeated_scaffold_generation_is_byte_identical | COMPLIANT |
| build.gradle plugins, toolchain, repository | oracle equality test (_expected_build_gradle) | COMPLIANT |
| starters, springdoc and driver only | test_excluded_artifacts_are_absent_from_paths_and_contents[ui/actuator/dependency-management] + oracle | COMPLIANT |
| springdoc starter at single-sourced version | test_build_gradle_declares_the_springdoc_starter_at_the_pinned_version + DD72 param springdoc-version (mutation-proven) | COMPLIANT |
| group/version, settings.gradle | existing tests, pass | COMPLIANT |
| Application.java entry point | existing tests, pass | COMPLIANT |
| No scaffold file hardcodes deployable values | test_no_scaffold_file_hardcodes_a_deployable_value[*], absolute-path test | COMPLIANT |
| Pinned versions come from one module | test_pinned_versions_have_the_spike_verified_values, test_build_script_context_*, DD72 scan (4 ids) | COMPLIANT |
| Invalid base package rejected | test_invalid_base_package_is_rejected_without_output[*] | COMPLIANT |

**generated-project-verification**
| Requirement | Scenario | Evidence | Result |
|-------------|----------|----------|--------|
| OpenAPI Document Served [manual] | Document served | Verifier gate run: exit 0, "GET /v3/api-docs -> 200", PASS; gate-evidence.md runs 1 and 3 | COMPLIANT (manual) |
| OpenAPI Document Served | Negative check fails the gate | Verifier negative run: exit 7, reverted byte-identically; gate-evidence.md run 2 | COMPLIANT (manual) |
| OpenAPI Document Served | Document endpoint broken (non-200 -> exit 6) | assert_status reuses exit 6 (code inspection; existing mechanism); no fault-injection run of a non-200 /v3/api-docs | PARTIAL (see SUGGESTION 1) |
| Boot Change Isolation | Only the springdoc line is added to the sources | oracle equality on build.gradle + excluded tests; git diff shows no Java, application.yml or actuator changes | COMPLIANT |
| Boot Change Isolation | No version literal outside versions.py | DD72 scan (emit/) + verifier rg for 3.1.1 in generation_runner (non-test), docker-compose.yml, scripts, backend/config: no match | COMPLIANT (non-emit scan is manual) |
| Generated Contract Pin | Contract drift caught | existing test_boot_smoke_contract tests, pass | COMPLIANT |
| Generated Contract Pin | OpenAPI pin drift caught | test_build_gradle_declares_the_springdoc_starter_behind_v3_api_docs, pass; spec text no longer claims a pytest over scripts/ | COMPLIANT |
| Fix-Forward Findings | Defect found | none found; gate-evidence.md states no fix-forward | COMPLIANT (vacuous) |
| Fix-Forward Findings | springdoc incompatibility | Observed: springdoc 3.1.1 (Boot 4.1.0) boots and serves /v3/api-docs on Boot 4.1.1 with @RestControllerAdvice present; recorded | COMPLIANT (manual) |

**Compliance summary**: 19/20 scenarios compliant, 1 PARTIAL (non-200 path, non-critical: shared assert_status mechanism, no new code).

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Project Scaffold Generation (springdoc line, single-sourced) | Implemented | versions.py, scaffold_context.py (last field), renderer.py kwarg, template line |
| OpenAPI Document Served | Implemented | boot-smoke.sh block after CRUD, before PASS |
| Boot Change Isolation | Implemented | no application.yml, Java @Configuration, actuator or Swagger UI added; docker-compose.yml untouched; no new version constant elsewhere |
| Generated Contract Pin | Implemented | scripts/ literal not pinned from pytest; spec text aligned |
| Fix-Forward Findings | Implemented | recorded in gate-evidence.md |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| DD103 constant after SPRING_BOOT_VERSION, last dataclass field, set in builder, forwarded by renderer.py kwarg | Yes | renderer.py kwarg present; docstring names the Boot 4.1.0 gap |
| DD104 template line position and indent | Yes | 4-space indent, single quotes, after the three Boot starters, before runtimeOnly postgresql |
| DD105 assertion after CRUD, before PASS; non-200 exit 6, content exit 7; pure bash | Yes | assert_status 200 GET /v3/api-docs, whitespace-stripped case needles, die 7; header table lists 6 and 7 |
| DD106 pytest pins the generated side only | Yes | oracle, inverted param, DD72 id, contract coordinate pin; no test reads scripts/ |
| DD107 gate recorded, negative check, observed fact | Yes | gate-evidence.md complete; reproduced by verifier |
| Threat matrix | Yes | constant literal path; body matched only by bash case; no body dump on the exit-7 path; negative log has no password/secret strings |

### Hygiene checks
- CR count is 0 and there is no BOM in every changed/new file (scripts, emit, tests, openspec change files, docs/ai and the session note).
- gen-db container removed after every gate; db, redis, backend, frontend, mailpit still Up and healthy; no docker compose down used; docker compose config --services = backend db frontend mailpit redis (docker-compose.yml not in the diff).
- .pi/ untouched (no files newer than 2026-09-19; still untracked as before).
- The diff contains only expected files: 7 backend/scripts files, 4 docs/ai files, plus the untracked session note and the change folder.
- Observation: a stopped container examen-1-software-generate-project-1 (Exited 0) exists; it is a compose one-off/dependency container (not gen-db), harmless, not produced by this diff.

### Docs/ai staleness review
1. HANDOFF_LATEST, CURRENT_STATE, NEXT_STEPS, DECISIONS_LOG and the session note all say "applied, not yet verified" / "verify and archive pending": correct now, but must be flipped after this report and after archive. No document claims "archived" for this change prematurely.
2. HANDOFF_LATEST.md has two bullets starting "Newest work" (the new one and the older boot-smoke one); demote the older to "Previous work".
3. HANDOFF_LATEST.md header still says "Updated 2026-09-19" and "DD1-DD91" though DD103-DD107 exist (pre-existing drift, worsened by this change).
4. CURRENT_STATE.md "What does not exist" lists OpenAPI as missing; now the generated project serves /v3/api-docs (only static export/Postman/Manifest are missing). A later line "nothing compiles yet" is pre-existing stale.
5. DECISIONS_LOG DD103 (and design.md, tasks.md 2.3) say that without the renderer kwarg "the coordinate rendered empty"; the Jinja environment actually raises UndefinedError (StrictUndefined).
6. The session note filename is dated 2026-09-19 while its text says executed 2026-09-20 (explained in the note; matches the planned filename).
7. Task counts: 22 everywhere (tasks.md, apply-progress); no 24 claim found.

### Issues Found
**CRITICAL**: None.

**WARNING**:
1. apply-progress has no formal "TDD Cycle Evidence" table (narrative RED/GREEN only; independently reconciled by the verifier: 389 to 393, 836 to 840).
2. Docs staleness items 2-5 above (duplicate "Newest work", stale header/date, OpenAPI listed as nonexistent, "renders empty" inaccuracy).
3. Status wording in docs/ai and the session note must be updated from "not yet verified" after this verdict.

**SUGGESTION**:
1. The non-200 /v3/api-docs path (exit 6) has no dedicated fault-injection run; it relies on the shared assert_status.
2. The pytest DD72 scan covers emit/ only; the spec text "no 3.1.1 in generation_runner, compose, scripts" is verified manually (rg) and could get a Docker-free scan of generation_runner non-test sources.
3. test_boot_smoke_contract.py hardcodes the version literal (allowed), so a version bump touches 3 test files; consider importing SPRINGDOC_VERSION there.
4. Follow-ups out of scope: static openapi.json export, operationId/tag tuning, ProblemDetail documentation; re-observe the springdoc Boot 4.1.0 vs 4.1.1 gap on any Boot bump.

### Verdict
PASS WITH WARNINGS
0 CRITICAL, 3 WARNING, 4 SUGGESTION. Suite 840/840, gate exit 0 with GET /v3/api-docs -> 200, negative gate exit 7 reproduced and reverted byte-identically.
