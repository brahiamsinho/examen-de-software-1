# Proposal: Spring Boot Generator — `application/` + `api/` Layers for CRUD Capabilities

## Intent

`backend/apps/spring_generator/` emits only `domain/` (JPA `@Entity`) and `persistence/` (Spring Data repository). A generated backend therefore has no callable REST surface, leaving spec §22/§23 unmet. Exploration also confirmed a real defect, not a hypothetical: FK fields are typed as the related entity, JPA's default fetch for `@ManyToOne`/`@OneToOne` is EAGER, and no `@JsonIgnore` exists — serializing an entity directly would nest full related entities, contradicting §27's flat FK-id UI contract. This change adds the service and REST layers and fixes that defect in the same slice.

## Scope

### In Scope

- `application/`: one Spring `@Service` per `Table`, wrapping repository create/read/update/delete/list/count and mapping entity ↔ DTO.
- `api/`: one `@RestController` per `Table` exposing create, read, update, delete, list (pagination + sorting), and count; `@Valid` on the request DTO.
- A new request/response DTO per `Table` whose relationship fields are flattened to raw FK `UUID` scalars (e.g. `customerId`), never nested objects. The `@Entity` keeps its typed `@ManyToOne`/`@OneToOne` field for JPA/Hibernate; the DTO is what crosses the wire.
- DTO carries forward the entity's existing `@NotNull`/`@Size` Jakarta constraints.
- `errors/`: a minimal `@ControllerAdvice` mapping a typed not-found exception → 404 and validation failure → 400. The service MUST check `Optional.isPresent()` and throw the typed exception rather than assume Spring Data raises a catchable one.
- Pure, one-`Table`-at-a-time functions plus Jinja templates, same signature shape as both archived cycles.

### Out of Scope

- **Filtering and search** — deferred to a later change, pending a §33 generation-metadata extension to `relational_mapping.domain.schema` that does not yet exist.
- **Relation-navigation sub-resource endpoints** (`GET /parent/{id}/children`) — deferred; satisfied for now by the flat FK id in the response, and would require whole-`RelationalModel` awareness.
- **§33 metadata consumption** of any kind (`searchable`, `sortable`, `crud`, `auditable`, …).
- **`Repository.java.j2` changes** — `JpaRepository<T, UUID>` already provides `findAll(Pageable)`, `findAll(Sort)`, `count()`, `save`, `findById`, `deleteById`. No `PagingAndSortingRepository`/`JpaSpecificationExecutor` declaration.
- `config/` and `validation/` layer generation.
- Compilation/Gradle verification of generated Java (roadmap item 13), OpenAPI/Postman, Domain Manifest.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `spring-boot-generation`: adds service, controller, DTO, and error-handler generation requirements. The existing **Package and File Path Layout** requirement MUST change — it currently forbids any output under `application/`, `api/`, and `errors/`.

## Approach

Exploration's Approach 3. Extend the existing `spring_generator` app (no new Django app) with context builders and templates sibling to `generate_table_sources`. Every capability included is deterministically derivable from a single `Table` plus `JpaRepository`'s inherited contract — no cross-table awareness, no `validate()` call, no DB access, so Generator Purity and determinism hold unchanged.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/spring_generator/emit/context.py` | Modified | Service/controller/DTO context builders |
| `backend/apps/spring_generator/emit/renderer.py` | Modified | New render entry point(s) beside `generate_table_sources` |
| `backend/apps/spring_generator/emit/templates/` | New | `Service`, `Controller`, DTO, not-found exception, `@ControllerAdvice` templates |
| `backend/apps/spring_generator/emit/templates/Repository.java.j2` | Unchanged | Explicitly not modified |
| `backend/apps/spring_generator/emit/errors.py` | Modified | Only if a new typed generator-side rejection is needed |
| `backend/apps/spring_generator/tests/` | New | Text-assertion tests mirroring `test_entity_structure.py` |
| `docs/ai/CURRENT_STATE.md`, `NEXT_STEPS.md`, `DECISIONS_LOG.md` | Modified | `AGENTS.md` memory convention |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| EAGER-fetch nested-entity serialization (confirmed defect) | — | Fixed here: flat-FK DTO; the entity is never serialized directly |
| Generated Java is never compiled or run | High | Accepted; text assertions only, compilation is roadmap item 13 |
| DTO and entity constraints drift apart | Medium | Both derived from the same `Table` context in one pass |
| §33 metadata absence blocks metadata-gated filtering/search | High | Explicitly out of scope; revisit after the schema extension |
| Scope creep toward whole-`RelationalModel` input | Low | One-`Table`-at-a-time signature preserved |

## Rollback Plan

Purely additive. Revert the new templates, context builders, renderer entry points, and tests, and restore the original **Package and File Path Layout** requirement. `domain/` and `persistence/` output stays byte-identical, so both archived cycles' tests remain green with no data or migration impact.

## Dependencies

- None new. No new Python or Java runtime dependency; generated code targets the Spring Boot stack already named by §22.

## Success Criteria

- [ ] A single `Table` yields a `@Service`, a `@RestController`, a DTO, and error-handling sources in addition to the existing entity and repository.
- [ ] Every relationship field appears in request/response DTOs as a flat FK `UUID` scalar; no generated DTO references another entity type.
- [ ] List endpoints expose pagination and sorting, and a count endpoint exists, with `Repository.java.j2` unmodified.
- [ ] Not-found maps to 404 and validation failure to 400 via the generated `@ControllerAdvice`.
- [ ] Output remains byte-identical across repeated invocations, with no `validate()` call and no DB access.
- [ ] No generated source under `validation/` or `config/`, and no filtering, search, or sub-resource endpoint is emitted.
