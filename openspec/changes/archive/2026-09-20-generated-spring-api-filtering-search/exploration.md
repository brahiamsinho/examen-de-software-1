# Exploration: generated-spring-api-filtering-search

Read-only exploration. Goal: define a bounded first slice for generated Spring Boot API filtering/search using generation profiles already carried by the relational schema and emitted in the Domain Manifest.

## 1. Existing generated Spring API

Evidence:

- `backend/apps/spring_generator/emit/templates/Controller.java.j2` currently emits six flat CRUD endpoints: `POST ""`, `GET "/{id}"`, `PUT "/{id}"`, `DELETE "/{id}"`, `GET ""`, and `GET "/count"`.
- The list endpoint signature is `public Page<ResponseDto> list(Pageable pageable)` and forwards only `pageable` to the service.
- `backend/apps/spring_generator/emit/templates/Service.java.j2` implements `list(Pageable pageable)` as `repository.findAll(pageable).map(this::toResponseDto)`.
- `backend/apps/spring_generator/emit/templates/Repository.java.j2` extends `JpaRepository<Entity, UUID>` only.
- `backend/apps/spring_generator/emit/context.py` builds controller/service/repository imports and contexts but does not read `Table.profile` or `Column.profile`.

Implication: filtering must add generated repository capability and modify list plumbing, while preserving the existing six endpoint shapes and avoiding project-level changes.

## 2. Profile schema shape

Evidence:

- `backend/apps/relational_mapping/domain/profile.py` defines:
  - `ColumnProfile(searchable: bool | None, sortable: bool | None, read_only: bool | None)`.
  - `TableProfile(entity: bool | None, auditable: bool | None, read_only: bool | None, crud: tuple[CrudOperation, ...] | None, default_sort: DefaultSort | None)`.
  - `DefaultSort(attribute_id: ElementId, direction: SortDirection)` where direction is `"asc"` or `"desc"`.
- `backend/apps/relational_mapping/mapping/profile_parser.py` accepts only table keys `entity`, `auditable`, `readOnly`, `crud`, `defaultSort` and column keys `searchable`, `sortable`, `readOnly` under the reserved `profile` object.
- The parser stores `defaultSort.attribute` unresolved as a source UML attribute id; resolution is deliberately left to consumers.
- `None` means undeclared; declared `false` must remain meaningful and must not be treated as truthy omission.

Implication: generated filtering should opt in only when `column.profile.searchable is True`; generated sorting should allow only when `column.profile.sortable is True`; `False` and `None` are both non-enabled for generation behavior, but `False` remains a declared fact for manifest purposes.

## 3. Domain Manifest profile emission

Evidence:

- `backend/apps/domain_manifest/builder/profile.py` emits declared profile keys only and duck-types profile objects with `getattr`.
- `defaultSort` is emitted as `{ "attribute": <manifest attribute name>, "direction": "asc" | "desc" }` after resolution through the manifest builder.
- `backend/apps/domain_manifest/builder/entities.py` resolves `defaultSort.attribute_id` by scanning `table.columns` for matching `source_element_id`, excluding the discriminator column.

Implication: Spring generation must perform its own default-sort attribute resolution, because the Spring generator consumes `RelationalModel` directly, not Domain Manifest JSON. Reuse the same conceptual rule: resolve `Table.profile.default_sort.attribute_id` to a generated Java field / DTO query parameter based on the column with matching `source_element_id`.

## 4. Generation metadata carry-through

Evidence:

- `backend/apps/relational_mapping/domain/schema.py` appends `profile` to `Column` and `Table` with defaults of `None`.
- `backend/apps/relational_mapping/mapping/mapper.py` parses `generation_metadata` once up front, attaches class profile to `Table.profile`, and attaches attribute profile to `Column.profile`.
- Synthetic columns, discriminator columns, FK columns, join-table columns, and join-table tables carry no profile unless they come from a UML attribute.
- `openspec/specs/relational-mapping/spec.md` explicitly states no consumer read `profile` in that prior change, and Spring output stayed neutral.

Implication: the first Spring filtering slice can inspect only `Table.profile` and `Column.profile`; it should not revisit UML metadata or change mapper behavior.

## 5. Bounded first slice

Recommended change name: `2026-09-20-generated-spring-api-filtering-search`.

Generate a simple JPA Specification-style filter path for non-inheritance tables only:

1. Repository generation
   - Change generated repositories for eligible non-inheritance entities from `JpaRepository<Entity, UUID>` to `JpaRepository<Entity, UUID>, JpaSpecificationExecutor<Entity>`.
   - Add `org.springframework.data.jpa.repository.JpaSpecificationExecutor` import only when the table has at least one generated searchable filter.

2. Specification generation
   - Add one generated application-layer helper per eligible entity, e.g. `application/<Entity>Specifications.java`, or embed private static builders in the service.
   - Prefer a separate helper only if review size permits; service-private methods minimize file count but can make the service template harder to read.
   - Supported searchable scalar types in this first slice:
     - `VARCHAR` and `TEXT`: case-insensitive contains match using `lower(field) like %lower(value)%`.
     - `INTEGER`, `BIGINT`, `NUMERIC`: exact match by typed request parameter.
   - Exclude `UUID`, `BOOLEAN`, `DATE`, `TIMESTAMPTZ`, enum columns, FK relationship columns, discriminator/inheritance tables, and primary key from filtering in the first slice.

3. Controller/list parameters
   - Keep `Pageable pageable` direct binding.
   - Add optional `@RequestParam(required = false)` parameters for each supported searchable field, using Java field/query names derived from existing `camel_case(column.name)`.
   - Do not introduce a generic `Map<String, String>` filter bag, because it weakens generated API clarity and OpenAPI discoverability.

4. Service/list behavior
   - Change list service signature to include a generated filter request/value object or explicit parameters.
   - Build a basic `Specification<Entity>` with only conjunctive `AND` composition across provided parameters.
   - Call `repository.findAll(specification, pageable).map(this::toResponseDto)` when at least one filter is generated; keep `findAll(pageable)` when no filter is generated.

5. Sorting and defaultSort
   - Do not parse custom sort query parameters manually.
   - Allow Spring `Pageable` sort to continue carrying requested sort information, but generate a guard or normalization layer only if this slice explicitly commits to enforcing sortable allow-lists.
   - First slice should at least apply `Table.profile.default_sort` when the incoming `Pageable` is unsorted.
   - Resolve `default_sort.attribute_id` to a sortable column by `Column.source_element_id`; reject generation with a typed Spring generator error if it points to an unknown, unsupported, non-sortable, FK, primary-key, or excluded column.
   - Use `PageRequest.of(pageable.getPageNumber(), pageable.getPageSize(), Sort.by(direction, "fieldName"))` only when `pageable.getSort().isUnsorted()`.

6. Sortable allow-list
   - A safe first-slice interpretation: generated default sort may use only `sortable: true` columns, and documentation/spec scenarios should define this.
   - Runtime enforcement of arbitrary client sort allow-list is riskier because Spring binds `Pageable` directly before controller code. If enforcing requested sort is required, add a small generated validator in service/controller and reject unsortable properties with `IllegalArgumentException`/400 via existing error handling or a new bounded error mapping. Otherwise, record requested-sort enforcement as a follow-up.

## 6. Exclusions confirmed

Explicitly exclude from this change:

- Full-text search.
- Pagination contract changes or custom pagination parameters.
- Complex operators and nested `AND`/`OR`; only implicit `AND` over present filters.
- Frontend/mobile changes.
- Generated-project-level infrastructure changes, Gradle dependency changes, Docker changes, OpenAPI/Postman/Manifest changes.
- Inheritance table API expansion.
- Filtering over relationships/FKs, enums, UUIDs, booleans, dates/timestamps, and primary keys.

## 7. Risks and questions for proposal/design

- **Dependency risk:** `JpaSpecificationExecutor` is already part of Spring Data JPA, so no Gradle dependency change should be needed.
- **Template-size risk:** adding explicit params, spec builders, and default-sort logic may exceed 400 changed lines if tests are broad. Keep one entity-focused test path first.
- **Default sort resolution:** Spring cannot reuse manifest-resolved names, so generator needs a shared internal resolver.
- **Client sort enforcement:** direct `Pageable` binding accepts arbitrary sort properties unless validated after binding. Decide whether first slice enforces it or only uses `sortable` for generated defaults/documented capability.
- **Type conversion:** Spring can bind `Integer`, `Long`, `BigDecimal`, and `String` request params directly; invalid numeric input should produce a standard 400 without custom code.

## 8. Suggested acceptance scenarios

- Given a table with `name` marked `searchable: true`, the generated controller list endpoint accepts optional `name` and the service applies a case-insensitive contains specification.
- Given a table with `total` marked `searchable: true`, the generated controller list endpoint accepts optional `total` as `BigDecimal` and the service applies an exact equality specification.
- Given two searchable supported columns, both present filters are combined with basic `AND`.
- Given a column with `searchable: false` or undeclared `searchable`, no request parameter or specification clause is generated for it.
- Given a table with `defaultSort` pointing at a `sortable: true` column, unsorted list requests are passed to the repository with that default sort.
- Given a sorted pageable request, generated `defaultSort` does not override the explicit sort.
- Given `defaultSort` points at an unknown or unsupported column, generation raises a typed error and emits no partial aggregate.
- Given a table with no eligible search/default-sort profile, generated output remains byte-identical to the current flat CRUD output.

## 9. Recommended design direction

Start with explicit generated parameters and a generated `Specification` builder because it gives the clearest API and keeps type conversion in Spring MVC. Keep direct `Pageable` binding to preserve the existing contract. Treat profile facts as opt-in generation controls: only `True` enables search/sort behavior, and undeclared/false means no generated behavior. Keep the change table-local and pure, with all decisions derived from `Table` and `Column` objects already present in the relational model.
