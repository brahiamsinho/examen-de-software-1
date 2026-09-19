# Tasks: Spring Boot Generator Config Layer

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 220–320 changed lines |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Scope Guardrails

- Touch only `backend/apps/spring_generator/emit/renderer.py`, `backend/apps/spring_generator/emit/templates/application.yml.j2`, focused files under `backend/apps/spring_generator/tests/`, `openspec/changes/2026-09-19-spring-boot-generator-config-layer/`, `openspec/specs/spring-boot-generation/spec.md`, and living project docs under `docs/ai/` if the implementation lands.
- Do not change table generator behavior except to add boundary tests proving `generate_table_sources(...)` still emits no `src/main/resources/` paths.
- Do not add a whole-model orchestrator, Java compilation, Gradle/Docker runtime smoke tests, OpenAPI, Postman, Domain Manifest, frontend/mobile output, `config/` Java classes, inheritance API behavior, or table/enum/shared-error behavior changes.
- Use strict TDD with focused backend checks from `backend/`: `pytest apps/spring_generator/tests` for the RED/GREEN loop, then broader `pytest` when the slice is stable.

## Tasks

- [x] 1. RED — add focused project config contract tests in `backend/apps/spring_generator/tests/test_project_config_sources.py`.
  - Assert importing/calling `generate_project_config_sources()` currently fails or is missing.
  - Cover exactly one `GeneratedSources` result, exactly one path `src/main/resources/application.yml`, no Java `package ` declaration, the six required placeholder-backed YAML settings, no placeholder defaults, no hardcoded deployable literals, no dialect/platform keys, and no excluded scopes.
  - Run `cd backend && pytest apps/spring_generator/tests/test_project_config_sources.py` and keep the failure as the expected RED evidence.

- [x] 2. RED — add generator-boundary tests in `backend/apps/spring_generator/tests/test_project_config_sources.py`.
  - Use existing factory helpers from `backend/apps/spring_generator/tests/factories.py` for a supported non-discriminator table.
  - Assert `generate_table_sources(...)` emits no `src/main/resources/application.yml` and no `src/main/resources/` paths.
  - Assert `generate_shared_error_sources(...)` still emits exactly two `errors/` Java files and no resource paths.
  - Assert `generate_project_config_sources()` emits no `domain/`, `persistence/`, `application/`, `application/dto/`, `api/`, `errors/`, `validation/`, or `config/` paths.
  - Re-run `cd backend && pytest apps/spring_generator/tests/test_project_config_sources.py` and preserve the RED failure caused only by the missing new entry point/template.

- [x] 3. RED — extend determinism coverage in `backend/apps/spring_generator/tests/test_determinism.py`.
  - Add `test_project_config_generation_is_byte_identical` with two calls to `generate_project_config_sources()`.
  - Assert returned objects compare equal, path order is the one-item sequence `src/main/resources/application.yml`, and contents are byte-identical.
  - Run `cd backend && pytest apps/spring_generator/tests/test_determinism.py -k project_config` and keep the missing-symbol/template failure as RED evidence.

- [x] 4. RED — extend purity coverage in `backend/apps/spring_generator/tests/test_purity.py`.
  - Add a no-DB-access test for `generate_project_config_sources()` without requesting `db` or `django_db`.
  - Add a validation-engine spy asserting `apps.uml_modeling.validation.engine.validate` is not called.
  - If compatible with the existing test style, add spies/patches proving `os.getenv`, `os.environ.get`, and subprocess entry points are not called.
  - Run `cd backend && pytest apps/spring_generator/tests/test_purity.py -k project_config` and preserve the expected RED failure from the missing entry point.

- [x] 5. GREEN — create the static YAML template at `backend/apps/spring_generator/emit/templates/application.yml.j2`.
  - Emit only the bounded YAML keys from the approved design:
    `SPRING_APPLICATION_NAME`, `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`, `JPA_DDL_AUTO`, and `SERVER_PORT`.
  - Use bare placeholders only, for example `${SERVER_PORT}`, never `${SERVER_PORT:8080}`.
  - Do not emit Hibernate dialect/platform, logging, Docker, OpenAPI/springdoc, Postman, Manifest, frontend, mobile, Java `@Configuration`, `validation/`, or `config/` settings.

- [x] 6. GREEN — add `generate_project_config_sources()` in `backend/apps/spring_generator/emit/renderer.py`.
  - Implement `def generate_project_config_sources() -> GeneratedSources` with no parameters.
  - Reuse `_ENVIRONMENT.get_template("application.yml.j2")` and render with no dynamic context.
  - Return `GeneratedSources(files=(GeneratedFile(path="src/main/resources/application.yml", contents=rendered_yaml),))`.
  - Do not call `_validate_base_package`, table context builders, enum context builders, validation routines, environment-variable readers, filesystem writers, subprocesses, or orchestration code.

- [x] 7. GREEN — run the focused Spring generator test loop.
  - Run `cd backend && pytest apps/spring_generator/tests/test_project_config_sources.py apps/spring_generator/tests/test_determinism.py -k "project_config or table_generation_does_not_emit_resources or shared_error_generation_does_not_emit_resources"`.
  - Run `cd backend && pytest apps/spring_generator/tests/test_purity.py -k "generation_succeeds_with_no_db_access or validation_engine or environment or subprocess"`.
  - Fix only defects in `renderer.py`, `application.yml.j2`, or the focused tests; do not broaden generator behavior.

- [x] 8. TRIANGULATE — verify the existing generator boundaries did not regress.
  - Run `cd backend && pytest apps/spring_generator/tests/test_paths_and_package.py apps/spring_generator/tests/test_resource_path.py apps/spring_generator/tests/test_error_sources.py apps/spring_generator/tests/test_inheritance_rendering.py apps/spring_generator/tests/test_inheritance_backward_compatibility.py`.
  - Confirm table, enum, inheritance, and shared-error outputs remain unchanged except for the new independent config entry point.
  - If a regression appears, rollback the offending code path rather than adapting existing behavior to the new config generator.

- [x] 9. TRIANGULATE — update OpenSpec/docs boundaries after implementation lands.
  - Confirm `openspec/changes/2026-09-19-spring-boot-generator-config-layer/specs/spring-boot-generation/spec.md` still matches the actual `JPA_DDL_AUTO` placeholder and dialect/platform omission.
  - If needed, update `openspec/specs/spring-boot-generation/spec.md` to allow the single project-level `src/main/resources/application.yml` while preserving the rule that `generate_table_sources(...)` emits no resources and no `validation/` or `config/` files.
  - Update `docs/ai/CURRENT_STATE.md`, `docs/ai/HANDOFF_LATEST.md`, and `docs/ai/NEXT_STEPS.md` to state that the config layer is a pure singleton YAML resource generator only, with no whole-model orchestration and no generated Java `config/` layer.
  - Add a concise session note under `docs/ai/sessions/` for the implementation/verification handoff.

- [x] 10. REFACTOR — keep the slice minimal and reviewable.
  - Remove any duplicated literal lists in tests only if doing so clarifies the assertions without hiding exact required placeholders.
  - Keep production code to the new public entry point plus the template; do not introduce helper modules, settings objects, new dependencies, or generated-project materializers.
  - Check the no-concatenation guard remains green with `cd backend && pytest apps/spring_generator/tests/test_no_concat_guard.py`.

- [x] 11. REFACTOR — run final backend verification and document evidence.
  - Run `cd backend && pytest apps/spring_generator/tests`.
  - Run `cd backend && pytest` if Docker/Postgres test prerequisites are available; otherwise document the exact environment blocker and the focused test evidence.
  - Record the final commands and results in this `tasks.md` under a short implementation note or in the verify report, without adding delivery-gate or ownership metadata.

## Implementation note

Strict TDD evidence was recorded in `apply-progress.md`. Host `cd backend && pytest ...` was attempted first and failed because `pytest` is not installed on the host shell (`/usr/bin/bash: line 1: pytest: command not found`), so Docker backend equivalents were used for backend checks. Final evidence: `docker compose exec -T backend pytest apps/spring_generator/tests` reported 223 passed; `docker compose exec -T backend pytest` reported 670 passed; `cd frontend && npm test` reported 54 files and 335 tests passed. The frontend command only verified the session runner because this slice changed no frontend code.
