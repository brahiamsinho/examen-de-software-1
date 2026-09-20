# Apply Progress: Generated Spring API Filtering and Search

## Status consumed

- Native status schema: `gentle-ai.sdd-status` v2.
- Change: `2026-09-20-generated-spring-api-filtering-search`.
- Artifact store: `openspec`.
- Native `nextRecommended`: `apply`.
- `actionContext.mode`: `repo-local`.
- `workspaceRoot`: `C:\Users\brahi\OneDrive\Escritorio\Examen-1-Software`.
- `allowedEditRoots`: `C:\Users\brahi\OneDrive\Escritorio\Examen-1-Software`.
- Strict TDD: active from `openspec/config.yaml` and user prompt.
- Workload gate: tasks forecast had `Decision needed before apply: Yes`, `Chained PRs recommended: Yes`, and `400-line budget risk: High`; parent prompt explicitly accepted the 450-650 line size exception, so implementation proceeded as one work unit.

## Completed tasks and checkbox updates

All implementation tasks 1-20 are complete and are marked `- [x]` in `openspec/changes/2026-09-20-generated-spring-api-filtering-search/tasks.md`.

## TDD Cycle Evidence

| Cycle | RED evidence | GREEN / refactor evidence |
|---|---|---|
| Profile context, repository, specification, controller, service, renderer, compatibility tests | `docker compose exec -T backend pytest apps/spring_generator/tests/test_filtering_profile_context.py apps/spring_generator/tests/test_repository.py apps/spring_generator/tests/test_specification_generation.py apps/spring_generator/tests/test_controller_generation.py apps/spring_generator/tests/test_service_generation.py apps/spring_generator/tests/test_paths_and_package.py apps/spring_generator/tests/test_filtering_backward_compatibility.py -q` failed with collection errors for missing `build_specification_context` before production code existed. | Same focused command passed: `68 passed in 3.10s` after implementing context, templates, renderer, and compatibility behavior. |
| Full Spring generator regression | Initial full focused generator run after GREEN found one backward-compatibility SHA failure in the no-profile service output. | `docker compose exec -T backend pytest apps/spring_generator/tests -q` passed: `354 passed in 25.24s` after restoring the byte-identical blank line. |
| Full backend regression | `docker compose exec -T backend pytest -q` initially failed `apps/generation_runner/tests/test_profile_output_neutral.py::test_declared_profile_does_not_change_spring_sources`, because true profile metadata is no longer Spring-output neutral. | Updated the regression to preserve false/unset neutrality and assert true searchable/sortable profiles do change Spring output; rerun passed: `1214 passed in 93.70s`. |
| Frontend configured strict-TDD command | Not applicable as a RED cycle because this change has no frontend production scope. | `cd frontend && npm test` passed: `55 passed (55 files), 351 passed (351 tests)` with existing Vite warnings. |

## Files changed

- `backend/apps/generation_runner/tests/test_profile_output_neutral.py`
- `backend/apps/spring_generator/emit/context.py`
- `backend/apps/spring_generator/emit/errors.py`
- `backend/apps/spring_generator/emit/renderer.py`
- `backend/apps/spring_generator/emit/templates/Controller.java.j2`
- `backend/apps/spring_generator/emit/templates/GlobalExceptionHandler.java.j2`
- `backend/apps/spring_generator/emit/templates/Repository.java.j2`
- `backend/apps/spring_generator/emit/templates/Service.java.j2`
- `backend/apps/spring_generator/emit/templates/Specifications.java.j2`
- `backend/apps/spring_generator/tests/factories.py`
- `backend/apps/spring_generator/tests/test_controller_generation.py`
- `backend/apps/spring_generator/tests/test_filtering_backward_compatibility.py`
- `backend/apps/spring_generator/tests/test_filtering_profile_context.py`
- `backend/apps/spring_generator/tests/test_paths_and_package.py`
- `backend/apps/spring_generator/tests/test_repository.py`
- `backend/apps/spring_generator/tests/test_service_generation.py`
- `backend/apps/spring_generator/tests/test_specification_generation.py`
- `docs/ai/CURRENT_STATE.md`
- `docs/ai/DECISIONS_LOG.md`
- `docs/ai/HANDOFF_LATEST.md`
- `docs/ai/NEXT_STEPS.md`
- `docs/ai/sessions/2026-09-20-agent-generated-spring-api-filtering-search.md`
- `openspec/changes/2026-09-20-generated-spring-api-filtering-search/apply-progress.md`
- `openspec/changes/2026-09-20-generated-spring-api-filtering-search/tasks.md`

## Implementation summary

- Added profile-derived context extraction for eligible searchable fields, sortable fields, default sort resolution, and specification-builder rendering.
- Added typed `InvalidDefaultSortError` with deterministic reasons for unresolved or structurally invalid default sort declarations.
- Repository generation conditionally imports and extends `JpaSpecificationExecutor` only for tables with eligible searchable columns.
- Added `Specifications.java.j2` and renderer wiring for one table-specific `application/<Entity>Specifications.java` file when searchable filters exist.
- Controller list endpoints conditionally accept optional `@RequestParam(required = false)` filter parameters using generated Java field names and typed numeric values while preserving direct `Pageable` binding.
- Service list behavior now composes generated `Specification` objects, validates client sort properties, rejects unsupported sort with `IllegalArgumentException`, applies valid default sort only for unsorted pageables, and preserves direct `findAll(pageable)` for unaffected tables.
- Shared generated error handling now maps `IllegalArgumentException` to `400 Bad Request`, providing the smallest generated-project handler change needed for invalid sort rejection.
- Backward compatibility is pinned for no-profile and false/unset profile tables, including the pre-existing no-profile SHA snapshot.

## Verification commands run

1. RED focused command: `docker compose exec -T backend pytest apps/spring_generator/tests/test_filtering_profile_context.py apps/spring_generator/tests/test_repository.py apps/spring_generator/tests/test_specification_generation.py apps/spring_generator/tests/test_controller_generation.py apps/spring_generator/tests/test_service_generation.py apps/spring_generator/tests/test_paths_and_package.py apps/spring_generator/tests/test_filtering_backward_compatibility.py -q` → failed with missing `build_specification_context` import.
2. GREEN focused command: same command → `68 passed in 3.10s`.
3. Spring generator regression: `docker compose exec -T backend pytest apps/spring_generator/tests -q` → first failed one SHA compatibility test, then passed `354 passed in 25.24s`.
4. Docker backend regression: `docker compose exec -T backend pytest -q` → first failed one stale profile-neutrality regression, then passed `1214 passed in 93.70s`.
5. Frontend configured strict command: `cd frontend && npm test` → `55 passed (55 files), 351 passed (351 tests)`; Vite config warnings were informational and pre-existing.

## Deviations from design

- The generated shared error handler was extended with `@ExceptionHandler(IllegalArgumentException.class)` to map sort validation failures to HTTP 400. This follows the design's bounded fallback when no existing handler maps the chosen validation exception to 400.
- The earlier generation-runner output-neutrality test for declared true profiles was updated because this change intentionally makes true searchable/sortable profiles affect Spring output; false/unset profile neutrality remains pinned.

## Remaining tasks

No unchecked implementation tasks remain.

## Workload / PR boundary

- Delivery path: single work unit under accepted `size:exception` for the forecast 450-650 line change.
- Actual `git diff --stat` before docs/OpenSpec updates showed approximately `583 insertions(+), 31 deletions(-)` across production and tests, plus this progress/docs update. The slice exceeded the 400-line review budget as expected; it stayed cohesive because tests and generator behavior are tightly coupled.

## ActionContext warnings

- No source edit occurred outside the authoritative workspace or allowed edit root.
- `.pi/` remains untracked and was not committed or pushed.
