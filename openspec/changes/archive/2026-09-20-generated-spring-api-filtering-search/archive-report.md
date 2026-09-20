# Archive Report: Generated Spring API Filtering/Search

**Change**: 2026-09-20-generated-spring-api-filtering-search
**Archived**: 2026-09-20
**Tasks**: 20/20 complete
**Status**: PASS

## Summary

Added filtering/search capabilities to the generated Spring Boot API, driven by generation profile metadata on columns (`searchable`, `sortable`) and entities (`defaultSort`). Tables with searchable columns now generate `JpaSpecificationExecutor` extension, `Specifications` builder classes, controller filter query params, sort validation with HTTP 400, and default sort fallback. Tables without profiles produce byte-identical output.

## Artifacts Composed into Canonical Spec

- `Searchable Column Specification Builder Generation` (4 scenarios) — ADDED
- `Sort Allow-List and Default Sort Behavior` (3 scenarios) — ADDED
- `Spring Data JPA Repository Generation from a Table` — MODIFIED (conditional JpaSpecificationExecutor)
- `REST Controller Generation from a Table` — MODIFIED (filter query params)
- `Exact Backward Compatibility for Non-Discriminator Table Generation` — MODIFIED (profile-aware)
- `Existing Generator Contracts Are Preserved` — MODIFIED (filtering allowed with profile opt-in)

## Verification Evidence

| Check | Result |
|---|---|
| Spring generator tests | 354 passed |
| Full backend tests | 1214 passed |
| Frontend tests | 351 passed (55 files) |
| `git diff --check` | PASS |
| Strict TDD | PASS (RED evidence, GREEN confirmed, triangulation adequate) |

## Changed Files

- `backend/apps/spring_generator/emit/context.py` — filtering context extraction
- `backend/apps/spring_generator/emit/errors.py` — sort validation error
- `backend/apps/spring_generator/emit/renderer.py` — filtering wire-up
- `backend/apps/spring_generator/emit/templates/Specifications.java.j2` — new template
- `backend/apps/spring_generator/emit/templates/Repository.java.j2` — conditional JpaSpecificationExecutor
- `backend/apps/spring_generator/emit/templates/Controller.java.j2` — filter query params
- `backend/apps/spring_generator/emit/templates/Service.java.j2` — specification composition
- `backend/apps/spring_generator/emit/templates/GlobalExceptionHandler.java.j2` — IllegalArgumentException → 400
- Generator tests (focused and regression)
- `backend/apps/generation_runner/tests/test_profile_output_neutral.py` — neutrality test
- OpenSpec specs, tasks, design, proposal, verify-report
- docs/ai updates
