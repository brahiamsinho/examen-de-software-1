# Tasks: Spring Boot Project Scaffold Generation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~700-850 (source+templates ~150, tests ~400, docs ~180) |
| 400-line budget risk | High (also at/over the 800-line project budget) |
| Chained PRs recommended | Yes (by the 400 guard); a single PR is the user's standing size:exception choice |
| Suggested split | Unit 1 PR 1 (units 1-4, code+tests) -> Unit 2 PR 2 (docs); or one size:exception PR |
| Delivery strategy | single-pr (standing user choice) |
| Chain strategy | size:exception, single PR (user's standing choice in 7 prior cycles; applied by the orchestrator, to be confirmed by the user) |

Decision needed before apply: No, resolved by the standing choice
Chained PRs recommended: Yes (not taken; size:exception applied instead)
Chain strategy: size:exception, single PR
400-line budget risk: High (accepted via size:exception)

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | versions + contexts + templates | PR 1 | `pytest backend/apps/spring_generator/tests/test_scaffold_context.py` | N/A: pure text, no runtime (slice 2 compiles) | new files only |
| 2 | scaffold + project entry points | PR 1 | `pytest backend/apps/spring_generator/tests/test_project_scaffold_sources.py backend/apps/spring_generator/tests/test_project_sources.py` | N/A: same | `renderer.py` additions |
| 3 | guards: purity, determinism, no-concat, regression | PR 1 | `pytest backend/apps/spring_generator` | full suite (685 before) | test files only |
| 4 | docs | PR 2 | N/A (markdown) | N/A | `docs/ai/*` |

Settled decisions: (a) both entry points default `base_package="com.modelia.generated"` (same constant as `generate_table_sources`, `generate_model_sources`, `generate_shared_error_sources`, `generate_enum_source`), keyword-only. (b) `GRADLE_VERSION` is pinned but rendered by no template (proposal decision; slice 2 reads it). (c) collision seam = DD71 (monkeypatch module-global collaborator). (d) Purity technique: `patch` guards as in existing `test_purity.py` (`os.getenv`, `os.environ.get`, `subprocess.run/Popen/check_call/check_output`) plus `socket.socket`/`socket.create_connection`, and a write-only filesystem guard (`builtins.open` wrapper rejecting modes `w/a/x/+`, `Path.write_text/write_bytes/mkdir`, `os.makedirs/mkdir`). Read guard is impossible: Jinja lazily reads `.j2` on first render.

## Phase 1: Versions and contexts

- [x] 1.1 RED: create `backend/apps/spring_generator/tests/test_scaffold_context.py`: constants equal `4.1.1`, `21` (int), `0.0.1-SNAPSHOT`, `9.7.1`; builders return frozen dataclasses (mutation raises `FrozenInstanceError`) with `group == package == base_package`, `class_name == "Application"`.
- [x] 1.2 GREEN: create `backend/apps/spring_generator/emit/versions.py` (exact DD62 shape).
- [x] 1.3 GREEN: create `backend/apps/spring_generator/emit/scaffold_context.py` (DD63; no `+`, `.join`, `%`, f-string).

## Phase 2: Templates and scaffold entry point

- [x] 2.1 RED: create `backend/apps/spring_generator/tests/test_project_scaffold_sources.py`: exact 3 paths in DD68 order (`com.example.generated`; `app` gives `src/main/java/app/Application.java`); full-string equality for all three files vs oracle constants (oracle build.gradle/settings.gradle/Application.java in `exploration.md`, read-only); `.format()` from imported constants; group/package propagation (`org.example.app`); excluded artifacts absent; LF, one trailing `\n`, no `\r`; no `{{`/`{%`/`{#` rendered.
- [x] 2.2 GREEN: create `emit/templates/build.gradle.j2`, `emit/templates/settings.gradle.j2`, `emit/templates/Application.java.j2` under `backend/apps/spring_generator/` (DD64-DD67 verbatim, zero block tags).
- [x] 2.3 RED: add to 2.1 file: `.j2` scaffold sources contain no `{%`; invalid `base_package` (`Com.Bad`, `com-example`, `com..example`, `""`, `1bad`) raises `ValueError`, no return; two calls equal.
- [x] 2.4 GREEN: in `backend/apps/spring_generator/emit/renderer.py` add `generate_project_scaffold_sources(*, base_package=...)`: `_validate_base_package`, both builders, path via `"src/main/java/{}/{}.java".format(...)`, `settings.gradle.j2` rendered with no context.
- [x] 2.5 RED: DD72 negative scan in 2.1 file: no `\b4\.1\.1\b`, `\b9\.7\.1\b`, bare toolchain `21` in `emit/**/*.py` (except `versions.py`) or `emit/templates/*.j2`.
- [x] 2.6 GREEN: fix any leaked literal found by 2.5 (expected none).
- [x] 2.7 RED: DD73 forbidden-literal test in 2.1 file (`localhost`, `http://`, `https://`, `jdbc:`, `5432`, `8080`, `0.0.0.0`, `password`, `secret`, drive/absolute paths); deliberately omit `postgres` and `port` (GAV `org.postgresql:postgresql`); only `mavenCentral()` repository. GREEN needs no code if 2.2 is right.

## Phase 3: Project aggregate

- [x] 3.1 RED: create `backend/apps/spring_generator/tests/test_project_sources.py`: files == `generate_model_sources` files then scaffold files (slice asserts); empty `RelationalModel()` -> 2 errors, `application.yml`, 3 scaffold; invalid base_package `ValueError`; only `Application.java` is a Java file outside the six layers; no `validation/`/`config/` path; existing entry points (`generate_table_sources` plain+discriminator, shared errors, config) emit no scaffold path; model aggregate has none; determinism.
- [x] 3.2 RED: same file, DD71 injection: `monkeypatch.setattr(renderer, "generate_project_scaffold_sources", ...)` returns a model path -> `GeneratedSourcePathCollisionError`, `.path`, `.occurrences == 2`, no aggregate; monkeypatched/duplicate-model `generate_model_sources` error propagates, scaffold not called; `_reject_duplicate_generated_paths` on hand-built tuple with `build.gradle` twice.
- [x] 3.3 GREEN: in `renderer.py` add `generate_project_sources(model, *, base_package=...)`: call `generate_model_sources` then `generate_project_scaffold_sources` by module-global name, one `_reject_duplicate_generated_paths` over the combined tuple, then build `GeneratedSources` (DD69-DD71).

## Phase 4: Guards and regression

- [x] 4.1 RED then GREEN: extend `backend/apps/spring_generator/tests/test_purity.py` for both entry points (technique (d) above, plus `validate()` never called, no DB).
- [x] 4.2 Extend `backend/apps/spring_generator/tests/test_determinism.py` with both entry points.
- [x] 4.3 Run `backend/apps/spring_generator/tests/test_no_concat_guard.py` unmodified; must stay green over `versions.py`, `scaffold_context.py`.
- [x] 4.4 Run the full backend suite: 685 pre-existing tests unmodified and green, incl. inheritance SHA-256 snapshot (`generate_model_sources` byte-identical).

## Phase 5: Docs

- [x] 5.1 Update `docs/ai/DECISIONS_LOG.md` (DD61-DD74), `docs/ai/CURRENT_STATE.md` (six entry points; §37 item 13 slice 1 of 3), `docs/ai/NEXT_STEPS.md` (slice 2 compile-check, slice 3 boot-smoke, `inheritance_context.py:169` defect).
- [x] 5.2 Update `docs/ai/HANDOFF_LATEST.md` and fix stale lines: `743a572`->`c876f79` (no uncommitted work); "about 670" -> 685 before this change; add `2026-09-19-spring-boot-whole-model-orchestrator` to the archived list; `DD1-DD50` -> `DD1-DD60`, then extend to DD74.
- [x] 5.3 Create `docs/ai/sessions/2026-09-19-agent-spring-boot-project-scaffold.md`.

## Spec coverage

Project Scaffold Generation (13 scenarios): 2.1, 2.3, 2.5, 2.7, 3.1. Package and File Path Layout (8): 2.1, 3.1. Generator Purity (2): 4.1. Duplicate Path Rejection (3): 3.2. Existing Contracts Preserved (3): 3.1, 4.4.
