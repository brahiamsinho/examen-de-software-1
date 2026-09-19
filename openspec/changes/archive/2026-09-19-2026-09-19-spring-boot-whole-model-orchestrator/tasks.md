# Tasks: Spring Boot whole-model source orchestrator

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | Source: ~35-55; tests: ~180-240; docs: ~0-20; total: ~215-315 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Scope Guard

- Scope is only pure `generate_model_sources` orchestration and typed duplicate path collision handling.
- No implementation in this task artifact.
- No Java templates, materialization, compilation, Gradle, Docker, OpenAPI, Postman, frontend, mobile, mapper, validation, or relational schema changes.
- Strict TDD is active; apply must proceed RED → GREEN → TRIANGULATE → REFACTOR.
- Primary focused check: `cd backend && pytest apps/spring_generator/tests`.

## Tasks

### RED

- [x] 1. Add failing public API and aggregate-order tests in `backend/apps/spring_generator/tests/test_model_sources.py`.
  - Cover import of `apps.spring_generator.emit.renderer.generate_model_sources`.
  - Build a mixed `RelationalModel(tables=(product, order), enum_types=(order_status,))` using `backend/apps/spring_generator/tests/factories.py` or local helpers.
  - Assert paths equal direct lower-level outputs concatenated as table block(s), enum file(s), `generate_shared_error_sources(...).files`, then `generate_project_config_sources().files`.
  - Run `cd backend && pytest apps/spring_generator/tests/test_model_sources.py` and confirm RED for missing API.

- [x] 2. Add failing globals, empty-model, package-propagation, and lower-level identity tests in `backend/apps/spring_generator/tests/test_model_sources.py`.
  - Assert `RelationalModel()` returns only shared errors followed by `src/main/resources/application.yml`.
  - Assert multiple tables/enums include exactly one `ResourceNotFoundException.java`, one `GlobalExceptionHandler.java`, and one `application.yml`.
  - Assert custom `base_package` affects table, enum, and shared-error Java paths/content, while `application.yml` remains package-independent.
  - Assert corresponding aggregate files equal direct outputs from `generate_table_sources`, `generate_enum_source`, `generate_shared_error_sources`, and `generate_project_config_sources`.

- [x] 3. Add failing inheritance-boundary and mixed aggregate-order regression coverage in `backend/apps/spring_generator/tests/test_model_sources.py`.
  - Create or reuse the existing supported discriminator-backed `Vehicle` fixture pattern from `backend/apps/spring_generator/tests/test_inheritance_rendering.py` or nearby inheritance tests.
  - Assert the aggregate starts with exactly `generate_table_sources(vehicle).files`, followed by the next table block.
  - Assert no new inheritance API expansion paths are introduced by the whole-model orchestrator.

- [x] 4. Add failing typed duplicate-path collision tests in `backend/apps/spring_generator/tests/test_model_source_collisions.py`.
  - Cover table/enum collision such as table `status` and enum type `status` targeting the same `src/main/java/<pkg>/domain/Status.java`.
  - Cover duplicate enum normalized-name collision.
  - Assert `GeneratedSourcePathCollisionError` is raised, is an `UngeneratableSourceError`, and exposes deterministic `path` and `occurrences` payloads.
  - Assert first-collision determinism when two collision pairs are present.
  - Express atomic no-partial behavior with `pytest.raises(...)` and no returned aggregate variable.

- [x] 5. Extend determinism and purity failing tests in existing files.
  - In `backend/apps/spring_generator/tests/test_determinism.py`, add repeated-call coverage for `generate_model_sources` with at least two tables and one enum; assert equal `GeneratedSources` and identical path/content pairs.
  - In `backend/apps/spring_generator/tests/test_purity.py`, add no-DB fixture coverage for `generate_model_sources`.
  - In `test_purity.py`, patch `apps.uml_modeling.validation.engine.validate` and assert whole-model generation does not call it.
  - If existing guards are straightforward to reuse, include `generate_model_sources` in filesystem/environment/subprocess purity checks without broadening scope.

### GREEN

- [x] 6. Add the typed collision error in `backend/apps/spring_generator/emit/errors.py`.
  - Define `GeneratedSourcePathCollisionError(UngeneratableSourceError)`.
  - Store `path: str` and `occurrences: int` attributes.
  - Format the message as `Generated source path {!r} appears {} times`.
  - Do not change existing lower-level error classes or rejection order.

- [x] 7. Add `generate_model_sources` in `backend/apps/spring_generator/emit/renderer.py` with minimal pure orchestration.
  - Import `RelationalModel` from `apps.relational_mapping.domain.schema`.
  - Aggregate table sources in `model.tables` order using `generate_table_sources(table, base_package=base_package).files`.
  - Aggregate enum files in `model.enum_types` order using `generate_enum_source(enum_type, base_package=base_package)`.
  - Append `generate_shared_error_sources(base_package=base_package).files` exactly once.
  - Append `generate_project_config_sources().files` exactly once.
  - Preserve each delegated generator's path, content, and internal order.

- [x] 8. Implement atomic exact-path duplicate rejection in `backend/apps/spring_generator/emit/renderer.py`.
  - Add private helper(s), for example `_extend_generated_files(...)` and `_reject_duplicate_generated_paths(...)`.
  - Build a local candidate tuple before constructing the returned `GeneratedSources`.
  - Scan candidate files left to right, count exact `GeneratedFile.path` strings, and raise the first colliding path discovered.
  - Do not call `GeneratedSources.as_mapping()` for collision detection.
  - Do not sort, deduplicate, overwrite, mutate the model, mutate generated files, or expose a partial aggregate.

- [x] 9. Run the focused GREEN checks and fix only in-scope failures.
  - Run `cd backend && pytest apps/spring_generator/tests/test_model_sources.py apps/spring_generator/tests/test_model_source_collisions.py apps/spring_generator/tests/test_determinism.py apps/spring_generator/tests/test_purity.py`.
  - Then run `cd backend && pytest apps/spring_generator/tests`.
  - Keep fixes limited to `backend/apps/spring_generator/emit/errors.py`, `backend/apps/spring_generator/emit/renderer.py`, and `backend/apps/spring_generator/tests/` unless a test factory-only adjustment is necessary.

### TRIANGULATE

- [x] 10. Strengthen coverage against false positives without changing product scope.
  - Verify mixed aggregate order with at least two table blocks and at least one enum block.
  - Verify globals exactly once with multiple tables and multiple enums.
  - Verify empty model output has no table/enum files and still includes singleton globals.
  - Verify duplicate collisions include table/enum, enum/enum, and first-collision determinism.
  - Verify preexisting APIs still pass their existing tests unchanged.

- [x] 11. Run preexisting API regression checks.
  - Run `cd backend && pytest apps/spring_generator/tests/test_enum_source.py apps/spring_generator/tests/test_error_sources.py apps/spring_generator/tests/test_project_config_sources.py apps/spring_generator/tests/test_sources.py`.
  - Confirm `generate_table_sources`, `generate_enum_source`, `generate_shared_error_sources`, `generate_project_config_sources`, and `GeneratedSources.as_mapping()` behavior remains unchanged.

### REFACTOR

- [x] 12. Refactor only for clarity after all tests are green.
  - Keep private helpers small and local to `backend/apps/spring_generator/emit/renderer.py`.
  - Remove duplication in tests only when it improves readability and does not hide explicit order expectations.
  - Preserve public API name, aggregate ordering, collision payloads, and pure in-memory behavior.

- [x] 13. Run final focused verification.
  - Run `cd backend && pytest apps/spring_generator/tests`.
  - Optionally run the broader backend check `cd backend && pytest` if time allows.
  - Record test commands and results in the apply/verify report; do not add runtime/materialization checks for this slice.
