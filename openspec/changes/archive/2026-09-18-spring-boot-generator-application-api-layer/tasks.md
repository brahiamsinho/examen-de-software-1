# Tasks: Spring Boot Generator — `application/` + `api/` Layers for CRUD Capabilities

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1400-1900 (6 templates, 5 dataclasses+4 builders, 5 new + 4 modified test modules, renderer/naming/errors deltas, docs) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy | ask-on-risk (not overridden by orchestrator) |
| Chain strategy | size:exception — single PR, confirmed by user |

Decision needed before apply: No — resolved
Chained PRs recommended: Yes (declined; size:exception accepted instead)
Chain strategy: size:exception, single PR
400-line budget risk: High (accepted via size:exception)

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | DD48 entity ctor fix + DD45 naming/path validation | PR 1 | `pytest backend/apps/spring_generator/tests/test_entity_structure.py backend/apps/spring_generator/tests/test_resource_path.py -q` | N/A — pure text-assertion unit tests, no server/DB | Revert `Entity.java.j2`, `naming.py`, `errors.py` additions; no other layer depends on them yet |
| 2 | DTO generation (DD37, DD38) | PR 2 | `pytest backend/apps/spring_generator/tests/test_dto_generation.py -q` | N/A — pure generator, no server/DB | Revert 2 templates + DTO context/builders; entity/repository output unaffected |
| 3 | Service + shared error handling (DD39-DD44) | PR 3 | `pytest backend/apps/spring_generator/tests/test_service_generation.py backend/apps/spring_generator/tests/test_error_sources.py -q` | N/A — pure generator, no server/DB | Revert Service/error templates, `generate_shared_error_sources`; DTO/entity output unaffected |
| 4 | Controller + renderer wiring + determinism/purity + docs | PR 4 | `pytest backend/apps/spring_generator/tests -q` | N/A — pure generator, no server/DB | Revert Controller template/context, renderer 6-file wiring, doc updates |

## Phase 1: DD48 Entity Constructor Fix (prerequisite, isolated)

- [x] 1.1 RED: in `backend/apps/spring_generator/tests/test_entity_structure.py`, flip the constructor assertion to require `public <E>() {` and assert `protected <E>() {` is absent
- [x] 1.2 GREEN: in `backend/apps/spring_generator/emit/templates/Entity.java.j2`, change the no-arg constructor visibility `protected` → `public` (DD48)

## Phase 2: Resource Path Naming (DD45)

- [x] 2.1 RED: create `backend/apps/spring_generator/tests/test_resource_path.py` — parametrized pluralization (`product→products`, `category→categories`, `status→statuses`, `box→boxes`, `order_line→order-lines`, `day→days`), no `_`/uppercase in output, illegal segment raises `InvalidResourcePathError`, and an order test proving the check runs after DD35's four
- [x] 2.2 GREEN: in `backend/apps/spring_generator/emit/naming.py`, add `resource_path_segment(table_name)` with the 3-rule `re.sub` pluralizer + kebab-case + `^[a-z0-9]+(-[a-z0-9]+)*$` validation
- [x] 2.3 GREEN: in `backend/apps/spring_generator/emit/errors.py`, add `InvalidResourcePathError(UngeneratableTableError)` and `reject_invalid_resource_path(table)`, wired as DD35's step 5

## Phase 3: Flat-FK Request/Response DTOs (DD37, DD38)

- [x] 3.1 RED: create `backend/apps/spring_generator/tests/test_dto_generation.py` — paths/package under `application/dto/`; request omits PK, response includes it; FK column → `UUID <camelCase>Id`, related entity name never appears; two FKs to one table stay distinct; enum column keeps enum type; `@NotNull`/`@Size` on request only; no `jakarta.persistence`/`@Column`/`@JoinColumn`/`@Enumerated` substring; field order == `table.columns`
- [x] 3.2 GREEN: in `backend/apps/spring_generator/emit/context.py`, add `DtoFieldContext`, `DtoContext`, `build_request_dto_context`, `build_response_dto_context` (DD38 field rules)
- [x] 3.3 GREEN: create `backend/apps/spring_generator/emit/templates/RequestDto.java.j2` and `ResponseDto.java.j2` (DD49 whitespace rule: no trailing `{% %}` on content lines)

## Phase 4: Service Layer (DD39, DD40, DD44)

- [x] 4.1 RED: create `backend/apps/spring_generator/tests/test_service_generation.py` — `@Service`/no `@Component`; constructor injection, no `@Autowired`; six DD39 signatures; class `@Transactional(readOnly=true)` + method-level on mutators; `orElseThrow`+`ResourceNotFoundException` on `findById`/`update`; `existsById` guard before `deleteById`; no `getReference` substring; FK repo dedup (two FKs to same table → one repo; self-reference → no extra repo); nullable-FK null guard; `toResponseDto`/`applyRequestDto` are `private`; no `MapStruct`/`Mapper`/`BeanUtils`; DTO imports present (DD50e)
- [x] 4.2 GREEN: in `backend/apps/spring_generator/emit/context.py`, add `RepositoryDependencyContext`, `ServiceContext`, `build_service_context` — dedup ordering (DD40, DD50c), precomputed conversion-statement tuples (DD44)
- [x] 4.3 GREEN: create `backend/apps/spring_generator/emit/templates/Service.java.j2` (DD49)

## Phase 5: Shared Error Handling (DD41, DD42, DD43)

- [x] 5.1 RED: create `backend/apps/spring_generator/tests/test_error_sources.py` — `generate_shared_error_sources()` returns exactly 2 files at DD37 paths; `generate_table_sources` emits nothing under `errors/`; `ResourceNotFoundException extends RuntimeException` with `(String, UUID)`; `@RestControllerAdvice` present, bare `@ControllerAdvice` absent; both `@ExceptionHandler`s mapped to `NOT_FOUND`/`BAD_REQUEST` via `ProblemDetail`; repeated invocation byte-identical; custom `base_package` honored
- [x] 5.2 GREEN: create `backend/apps/spring_generator/emit/templates/ResourceNotFoundException.java.j2` and `GlobalExceptionHandler.java.j2` (DD41, DD43)
- [x] 5.3 GREEN: in `backend/apps/spring_generator/emit/renderer.py`, add `generate_shared_error_sources(*, base_package)` reusing `_ENVIRONMENT`/`_validate_base_package`/`package_path` (DD42)

## Phase 6: REST Controller (DD45 routes, DD46, DD47)

- [x] 6.1 RED: create `backend/apps/spring_generator/tests/test_controller_generation.py` — `@RestController`+`@RequestMapping("/api/products")`; all six DD46 mappings/statuses; `@Valid @RequestBody` on POST/PUT only; `@PathVariable UUID id`; `Pageable pageable` bound directly, no `@RequestParam` for page/size/sort; controller references only DTOs, never the entity type; `order_line`→`/api/order-lines`
- [x] 6.2 GREEN: in `backend/apps/spring_generator/emit/context.py`, add `ControllerContext`, `build_controller_context` (uses `resource_path_segment`)
- [x] 6.3 GREEN: create `backend/apps/spring_generator/emit/templates/Controller.java.j2` (DD49)

## Phase 7: Renderer Wiring & Determinism (DD50)

- [x] 7.1 RED: modify `backend/apps/spring_generator/tests/test_paths_and_package.py` — `generate_table_sources` now yields exactly 6 files in DD50a layer order; no file under `validation/`/`config/`; custom `base_package` honored across all six
- [x] 7.2 GREEN: in `backend/apps/spring_generator/emit/renderer.py`, extend `generate_table_sources` to call all 4 new builders + render RequestDto/ResponseDto/Service/Controller in fixed layer order, after `reject_invalid_resource_path` (Phase 2)
- [x] 7.3 RED→GREEN: extend `backend/apps/spring_generator/tests/test_determinism.py` to cover all six files (byte-identical output, fixed file order, DTO field order, brace/paren balance, grouped/sorted imports incl. `org.springframework.*`)
- [x] 7.4 RED→GREEN: extend `backend/apps/spring_generator/tests/test_purity.py` to cover `generate_shared_error_sources` (no DB fixture, no `validate()` call)
- [x] 7.5 Verify `backend/apps/spring_generator/tests/test_no_concat_guard.py` stays green over all modified `emit/` modules

## Phase 8: Documentation

- [x] 8.1 Update `docs/ai/CURRENT_STATE.md`, `docs/ai/NEXT_STEPS.md`, `docs/ai/DECISIONS_LOG.md` with DD37-DD50 per `rules.design` dual-documentation convention
