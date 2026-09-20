# Tasks: Generated Spring API Filtering and Search

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 450-650 additions/deletions |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 context + repository + specification builder → PR 2 controller + service filtering/sort/defaultSort → PR 3 backward-compatibility and aggregate regression hardening |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

## Implementation Tasks

- [x] 1. RED: Add focused failing profile-context tests in `backend/apps/spring_generator/tests/test_filtering_profile_context.py` for eligible searchable fields, eligible sortable fields, generated Java query names, unsupported searchable types, FK/PK/enum exclusions, and valid/invalid `Table.profile.default_sort` resolution.

- [x] 2. GREEN: Implement profile-derived context in `backend/apps/spring_generator/emit/context.py`, including `SearchFilterContext`, `SortableFieldContext`, `DefaultSortContext`, `SpecificationContext`, deterministic ordering, and helper booleans consumed by repository, service, controller, and renderer templates.

- [x] 3. RED: Add failing repository tests in `backend/apps/spring_generator/tests/test_repository.py` proving searchable tables import and extend `JpaSpecificationExecutor`, while no-profile or ineligible-profile repositories remain byte-identical and omit the import.

- [x] 4. GREEN: Update `backend/apps/spring_generator/emit/templates/Repository.java.j2` and `build_repository_context()` so `JpaSpecificationExecutor` is added conditionally through precomputed context rather than template-heavy branching.

- [x] 5. RED: Add failing specification-builder tests in `backend/apps/spring_generator/tests/test_specification_generation.py` for `VARCHAR`/`TEXT` case-insensitive contains, `INTEGER`/`BIGINT`/`NUMERIC` exact equality, `AND` composition, blank string skip behavior, and absence of unsupported `OR`/range/nested operators.

- [x] 6. GREEN: Add `backend/apps/spring_generator/emit/templates/Specifications.java.j2` and render it from `backend/apps/spring_generator/emit/renderer.py` only for non-inheritance tables with eligible searchable columns at `src/main/java/<pkg>/application/<Entity>Specifications.java`.

- [x] 7. RED: Add failing controller tests in `backend/apps/spring_generator/tests/test_controller_generation.py` for optional `@RequestParam(required = false)` filter parameters, Java field-name query params such as `fullName`, typed numeric params, preserved direct `Pageable pageable` binding, and no-profile byte-identical controller output.

- [x] 8. GREEN: Update `build_controller_context()` and `backend/apps/spring_generator/emit/templates/Controller.java.j2` to include conditional filter params, `RequestParam` import, needed numeric imports, and service call forwarding in column order.

- [x] 9. RED: Add failing service filtering tests in `backend/apps/spring_generator/tests/test_service_generation.py` proving filter-aware list signatures, `Specification<Entity> specification = <Entity>Specifications.byFilters(...)`, and `repository.findAll(specification, effectivePageable).map(this::toResponseDto)` for searchable tables.

- [x] 10. GREEN: Update `build_service_context()` and `backend/apps/spring_generator/emit/templates/Service.java.j2` to compose the generated specification and keep the existing direct `repository.findAll(pageable)` path byte-identical when no search/sort/default-sort behavior exists.

- [x] 11. RED: Add failing service sort-validation tests in `backend/apps/spring_generator/tests/test_service_generation.py` for generated `SORTABLE_FIELDS`, validation of every `pageable.getSort()` order, invalid-sort rejection, valid-sort acceptance, and rejecting any sort when validation exists but the allow-list is empty.

- [x] 12. GREEN: Implement service sort allow-list generation and 400-compatible invalid-sort rejection in `Service.java.j2`, reusing existing generated error handling if available and adding only the smallest bounded handler change if tests prove `IllegalArgumentException` is not mapped to HTTP 400.

- [x] 13. RED: Add failing default-sort tests in `backend/apps/spring_generator/tests/test_service_generation.py` and `backend/apps/spring_generator/tests/test_filtering_profile_context.py` proving unsorted `Pageable` uses `PageRequest.of(..., Sort.by(Sort.Direction.<DIR>, "<field>"))`, explicit client sort is not overridden, and invalid default-sort references fail before generated output is returned.

- [x] 14. GREEN: Add typed `InvalidDefaultSortError` in `backend/apps/spring_generator/emit/errors.py`, raise it during context construction, and implement default-sort normalization in `Service.java.j2` with conditional `PageRequest` and `Sort` imports.

- [x] 15. TRIANGULATE: Add renderer and aggregate tests in `backend/apps/spring_generator/tests/test_paths_and_package.py`, `backend/apps/spring_generator/tests/test_model_sources.py`, and/or a focused new test file proving searchable tables emit exactly one extra specification file, no-profile tables still emit exactly six files in the existing order, and inheritance tables emit no specification/controller/service/DTO expansion.

- [x] 16. TRIANGULATE: Add backward-compatibility tests for searchable/sortable unset or `false` profiles in `backend/apps/spring_generator/tests/test_filtering_backward_compatibility.py`, comparing generated paths and contents against existing no-profile fixture output.

- [x] 17. TRIANGULATE: Add focused unit tests for factory/profile construction in `backend/apps/spring_generator/tests/factories.py` if needed, using `ColumnProfile`, `TableProfile`, `DefaultSort`, and `SortDirection` from `backend/apps/relational_mapping/domain/profile.py` without cross-importing relational-mapping test packages.

- [x] 18. REFACTOR: Simplify context/template boundaries so eligibility logic remains in `context.py`, Jinja files stay data-driven, imports remain grouped through `_group_imports()`, and `backend/apps/spring_generator/tests/test_no_concat_guard.py` still passes.

- [x] 19. REFACTOR: Run the focused verification command `cd backend && pytest apps/spring_generator/tests` and then the configured strict-TDD command `cd backend && pytest ; cd frontend && npm test`, fixing only regressions within `backend/apps/spring_generator/` unless the bounded 400 handler change is required.

- [x] 20. REFACTOR: Update implementation notes only if code changes create a durable project-state change, especially `docs/ai/CURRENT_STATE.md`, `docs/ai/HANDOFF_LATEST.md`, and `docs/ai/NEXT_STEPS.md`, keeping OpenSpec artifacts as the authoritative SDD plan for this change.
