# Session — Generated Spring API filtering/search

Date: 2026-09-20
Change: `2026-09-20-generated-spring-api-filtering-search`
Status: applied, verify pending, uncommitted

## What changed

- Spring generator now consumes `Table.profile` and `Column.profile` for searchable filters, sortable fields, and `defaultSort`.
- Searchable non-inheritance tables generate `application/<Entity>Specifications.java` with case-insensitive string contains and exact numeric equality predicates.
- Repositories conditionally extend `JpaSpecificationExecutor` only when searchable filters exist.
- Controllers conditionally bind optional Java-field-name query parameters while preserving direct `Pageable` binding.
- Services compose specifications, validate sort allow-lists, apply valid default sort only for unsorted pageables, and keep no-profile output byte-identical.
- Invalid default sort declarations raise typed `InvalidDefaultSortError` before generated sources are returned.
- Generated `GlobalExceptionHandler` now maps `IllegalArgumentException` to HTTP 400 for invalid sort requests.

## Evidence

- RED focused generator tests failed before implementation because `build_specification_context` did not exist.
- Focused generator tests passed: `68 passed in 3.10s`.
- Full Spring generator suite passed: `354 passed in 25.24s`.
- Docker backend regression passed: `1214 passed in 93.70s`.
- Frontend configured strict command passed: `55 files / 351 tests`.

## Notes for next agent

- The previous generation-runner test claiming true profile metadata was Spring-output neutral was intentionally updated; true searchable/sortable profiles now change Spring output, while false/unset values remain neutral.
- The slice used the accepted `size:exception` path; no commit or push was performed.
- Continue with verify/archive for this OpenSpec change before starting DD147 (`crud` restricting operations) or inheritance API behavior.

## Archive Complete

- 20/20 tasks complete
- 354 Spring generator tests, 1214 backend tests, 351 frontend tests
- Canonical spec updated with 2 ADDED + 4 MODIFIED requirements
- Archive report written
- Change folder moved to archive/2026-09-20-generated-spring-api-filtering-search/
- docs/ai updated: CURRENT_STATE.md, HANDOFF_LATEST.md, NEXT_STEPS.md
