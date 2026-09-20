# Design: Generated Spring API Filtering and Search

## Scope and Constraints

This design covers the Spring Boot source generator only, under `backend/apps/spring_generator/`.

The implementation must:

- preserve direct Spring `Pageable` binding;
- preserve byte-identical generated output for non-inheritance tables with no relevant searchable, sortable, or default-sort profile behavior;
- generate behavior only from `Table.profile` and `Column.profile` already present on the relational model;
- exclude inheritance API behavior, relationship filtering, enum filtering, UUID filtering, boolean filtering, date/timestamp filtering, primary-key filtering, frontend/mobile changes, Gradle changes, Docker changes, and generated-project infrastructure changes;
- keep generator behavior pure and atomic: invalid default-sort profile data must raise a typed generator error before returning `GeneratedSources`.

## Existing Generator Baseline

Current relevant files:

- `backend/apps/spring_generator/emit/context.py`
  - Builds immutable-ish template contexts for entity, repository, DTO, service, controller, and enum generation.
  - Does not currently inspect `Table.profile` or `Column.profile`.
- `backend/apps/spring_generator/emit/templates/Repository.java.j2`
  - Emits `interface <E>Repository extends JpaRepository<E, UUID>` only.
- `backend/apps/spring_generator/emit/templates/Controller.java.j2`
  - Emits `list(Pageable pageable)` and delegates to `service.list(pageable)`.
- `backend/apps/spring_generator/emit/templates/Service.java.j2`
  - Emits `list(Pageable pageable)` and delegates to `repository.findAll(pageable).map(this::toResponseDto)`.
- `backend/apps/spring_generator/emit/renderer.py`
  - Renders six files for each supported non-inheritance table in fixed order.

## Files to Modify or Add

### Modify: `backend/apps/spring_generator/emit/context.py`

Responsibilities:

1. Derive reusable search/sort generation metadata from `Table` and `Column`.
2. Add context fields consumed by repository, controller, service, and the new specification builder template.
3. Resolve `Table.profile.default_sort.attribute_id` against `Column.source_element_id`.
4. Raise a typed generator error for invalid default-sort declarations.

Recommended new context concepts:

- `SearchFilterContext`
  - `field_name`: generated Java field/query parameter name, e.g. `fullName`.
  - `pascal_name`: setter/getter suffix, e.g. `FullName`.
  - `java_type`: `String`, `Integer`, `Long`, or `BigDecimal`.
  - `column_type`: original `ColumnType` or a derived category.
  - `match_kind`: `string_contains_ignore_case` or `numeric_equals`.
- `SortableFieldContext`
  - `field_name`: generated Java sortable property name.
- `DefaultSortContext`
  - `field_name`: generated Java field name.
  - `direction`: uppercase Java enum token, `ASC` or `DESC`.
- `SpecificationContext`
  - `package`: `<base_package>.application`.
  - `class_name`: `<E>Specifications`.
  - `entity_class`: `<E>`.
  - `filters`: eligible searchable fields.
  - `import_groups`: includes `jakarta.persistence.criteria.Predicate`, `org.springframework.data.jpa.domain.Specification`, numeric imports when needed, and entity import.

Eligibility helpers should live in this module, not in Jinja templates:

- searchable column eligibility:
  - `column.profile is not None`;
  - `column.profile.searchable is True`;
  - column is not the primary key;
  - column is not a foreign-key column;
  - column is not discriminator/inheritance-only behavior;
  - `column.enum_type_name is None`;
  - type is one of `VARCHAR`, `TEXT`, `INTEGER`, `BIGINT`, `NUMERIC`.
- sortable column eligibility:
  - `column.profile is not None`;
  - `column.profile.sortable is True`;
  - column maps to a generated scalar Java field;
  - column is not a primary key, FK, enum, relationship, or discriminator column.

The context should expose booleans such as:

- `has_search_filters` for repository/specification generation.
- `has_sort_validation` for service/controller list behavior when at least one sortable field or default sort exists.
- `has_default_sort` when a valid default sort resolves.

### Modify: `backend/apps/spring_generator/emit/templates/Repository.java.j2`

Required generated behavior:

- For tables with at least one eligible searchable column, emit:
  - import `org.springframework.data.jpa.repository.JpaSpecificationExecutor`;
  - `public interface <E>Repository extends JpaRepository<<E>, UUID>, JpaSpecificationExecutor<<E>>`.
- For tables without eligible searchable columns, keep the current repository source byte-identical.

Template contract:

- Add a context variable such as `extends_clause` or `extends_interfaces` computed in `context.py`.
- Prefer precomputing the full `extends` suffix in context to avoid branching-heavy Jinja.

### Modify: `backend/apps/spring_generator/emit/templates/Controller.java.j2`

Required generated behavior:

- Keep `Pageable pageable` as a direct method parameter.
- For each eligible searchable column, add an optional `@RequestParam(required = false)` parameter whose name is the generated Java field name.
- Forward filter parameters to the service list method in the same deterministic order as columns appear in `table.columns`.
- For tables without eligible searchable columns, keep the current list endpoint signature and body byte-identical.

Generated signature examples:

- No filters:
  - `public Page<CustomerResponseDto> list(Pageable pageable)`.
- With filters:
  - `public Page<CustomerResponseDto> list(@RequestParam(required = false) String fullName, @RequestParam(required = false) Integer age, Pageable pageable)`.

Required imports:

- Add `org.springframework.web.bind.annotation.RequestParam` only when at least one filter parameter is generated.
- Add numeric Java imports only when required by generated parameter types, e.g. `java.math.BigDecimal` for `NUMERIC`.

HTTP 400 behavior:

- Invalid numeric parameter conversion relies on Spring MVC typed binding.
- Invalid sort requests should be rejected by service validation with an exception mapped to `400 Bad Request` by existing or bounded error handling. If no existing handler maps `IllegalArgumentException` to 400, add the smallest bounded generated-project error mapping in the shared error template only if implementation confirms it is necessary; otherwise keep the validation exception type aligned with current handler behavior.

### Modify: `backend/apps/spring_generator/emit/templates/Service.java.j2`

Required generated behavior:

- For tables without generated filtering/search/sort/default-sort behavior, preserve current `list(Pageable pageable)` source byte-for-byte.
- For tables with generated behavior, emit list flow that:
  1. validates requested sort properties against generated sortable allow-list;
  2. applies default sort only when the incoming `Pageable` is unsorted;
  3. builds the generated `Specification` from filter parameters when search filters exist;
  4. calls the correct repository overload.

Expected service variants:

1. No search filters and no sort/default-sort behavior:
   - `repository.findAll(pageable).map(this::toResponseDto)` unchanged.
2. Search filters present:
   - `Specification<E> specification = ESpecifications.byFilters(...);`
   - `Pageable effectivePageable = normalizePageable(pageable);`
   - `return repository.findAll(specification, effectivePageable).map(this::toResponseDto);`
3. Sort/default-sort behavior without search filters:
   - `Pageable effectivePageable = normalizePageable(pageable);`
   - `return repository.findAll(effectivePageable).map(this::toResponseDto);`

Sort validation logic:

- Generate a private static allow-list, e.g. `private static final Set<String> SORTABLE_FIELDS = Set.of("name", "email");`, only when sort validation is needed.
- Iterate through `pageable.getSort()`.
- If any `order.getProperty()` is absent from the allow-list, reject with a 400-compatible exception.
- Sort validation must run before repository execution.
- If no sortable columns exist and the client sends any sort, reject the request when validation behavior is generated for the table.

Default sort resolution:

- `context.py` resolves `Table.profile.default_sort.attribute_id` by matching `Column.source_element_id`.
- The matching column must also be an eligible sortable generated Java field.
- Direction maps from profile `asc`/`desc` to `Sort.Direction.ASC`/`Sort.Direction.DESC`.
- Generated service applies default sort only when `pageable.getSort().isUnsorted()`.
- Generated service must not override explicit client sort.
- Use `PageRequest.of(pageable.getPageNumber(), pageable.getPageSize(), Sort.by(Sort.Direction.<DIR>, "<field>"))`.

Required imports when behavior is generated:

- `org.springframework.data.domain.PageRequest` for default-sort normalization.
- `org.springframework.data.domain.Sort` for sort validation/default sort.
- `org.springframework.data.jpa.domain.Specification` when search filters exist.
- `java.util.Set` when sort validation is emitted.
- `<base_package>.application.<E>Specifications` is not imported when the service is in the same package; refer to the class directly.

### Add: `backend/apps/spring_generator/emit/templates/Specifications.java.j2`

Generated file path:

- `src/main/java/<package path>/application/<E>Specifications.java`.

Generate this file only when a non-inheritance table has at least one eligible searchable column.

Required generated behavior:

- Class name: `<E>Specifications`.
- Package: `<base_package>.application`.
- Public final class with private constructor.
- Public static method such as:
  - `public static Specification<E> byFilters(String fullName, Integer age, BigDecimal total)`.
- It must return a `Specification<E>` that:
  - creates a mutable predicate list;
  - appends one predicate per non-null filter parameter;
  - combines all predicates with `criteriaBuilder.and(...)`;
  - returns `criteriaBuilder.conjunction()` when no filter value is supplied.

String LIKE behavior:

- Applies to `VARCHAR` and `TEXT`.
- Skip the predicate when the parameter is `null`.
- Recommended blank-string behavior: skip the predicate when `value.isBlank()` to avoid `LIKE '%%'` matching everything while still treating the parameter as effectively absent.
- Matching expression:
  - `criteriaBuilder.like(criteriaBuilder.lower(root.get("fullName")), "%" + fullName.toLowerCase() + "%")`.
- Locale note: if implementation wants deterministic casing, it may use `toLowerCase(Locale.ROOT)` and import `java.util.Locale`; otherwise plain `toLowerCase()` is acceptable for this bounded slice if tests assert emitted shape rather than locale behavior.

Numeric equality behavior:

- Applies to `INTEGER`, `BIGINT`, and `NUMERIC`.
- Skip the predicate when the parameter is `null`.
- Matching expression:
  - `criteriaBuilder.equal(root.get("age"), age)`.

Generated imports:

- `java.util.ArrayList`.
- `java.util.List`.
- `jakarta.persistence.criteria.Predicate`.
- `org.springframework.data.jpa.domain.Specification`.
- entity import: `<base_package>.domain.<E>`.
- `java.math.BigDecimal` if any `NUMERIC` filter exists.

### Modify: `backend/apps/spring_generator/emit/renderer.py`

Required generated behavior:

- Build `SpecificationContext` after table validation and before rendering files.
- Render `Specifications.java.j2` only when `has_search_filters` is true.
- Add the specification file to `GeneratedSources.files` after service/controller or in the fixed layer order required by the spec.

Recommended file order for non-inheritance searchable tables:

1. `domain/<E>.java`
2. `persistence/<E>Repository.java`
3. `application/dto/<E>RequestDto.java`
4. `application/dto/<E>ResponseDto.java`
5. `application/<E>Service.java`
6. `api/<E>Controller.java`
7. `application/<E>Specifications.java`

If implementation chooses strict layer ordering with `application/<E>Specifications.java` before controller, tests must lock the chosen order. The spec requires exactly one additional file at the application path and unchanged six-file output for no-profile tables.

### Modify: `backend/apps/spring_generator/emit/errors.py`

Add a typed generator error for invalid default sort resolution.

Recommended class:

- `InvalidDefaultSortError(UngeneratableTableError)` with fields:
  - `table_name`
  - `attribute_id`
  - `reason`

Expected reasons:

- `attribute_not_found`
- `attribute_not_sortable`
- `attribute_not_scalar_sortable`
- `attribute_is_primary_key`
- `attribute_is_foreign_key`
- `attribute_is_enum`
- `attribute_type_unsupported`

This error should be raised during context construction before any `GeneratedSources` object is returned.

## Query Parameter to Java Field Mapping

The public query parameter name is the generated Java field name derived from the database column name with the existing `camel_case(column.name)` helper.

Examples:

| Database column | Generated Java field | Query parameter | Type |
|---|---:|---:|---|
| `full_name` | `fullName` | `fullName` | `String` |
| `name` | `name` | `name` | `String` |
| `age` | `age` | `age` | `Integer` |
| `total` | `total` | `total` | `BigDecimal` |
| `customer_id` FK | excluded | excluded | excluded |
| `id` primary key | excluded | excluded | excluded |

Type mapping:

| Column type | Request param Java type | Specification predicate |
|---|---|---|
| `VARCHAR` | `String` | case-insensitive `LIKE` contains |
| `TEXT` | `String` | case-insensitive `LIKE` contains |
| `INTEGER` | `Integer` | exact equality |
| `BIGINT` | `Long` | exact equality |
| `NUMERIC` | `BigDecimal` | exact equality |

## Runtime Flow

1. Client sends `GET /api/<resources>?fullName=ann&age=30&sort=name,asc`.
2. Spring MVC binds `fullName` as `String`, `age` as `Integer`, and `Pageable` directly.
3. Controller forwards generated filter parameters plus `Pageable` to service.
4. Service validates every requested sort property against generated sortable fields.
5. Service applies default sort only when pageable sort is unsorted.
6. Service builds `Specification` through `<E>Specifications.byFilters(...)` when search filters exist.
7. Repository executes either `findAll(specification, effectivePageable)` or `findAll(effectivePageable)` depending on generated behavior.
8. Service maps entities to response DTOs with existing `toResponseDto` logic.

## Backward Compatibility Rules

- If a table has no eligible searchable columns, no sortable columns, and no valid default sort behavior, the generated six files must be byte-identical to current output.
- `searchable=false`, `sortable=false`, and undeclared values must not generate behavior.
- Repository output changes only for tables with eligible searchable filters.
- Controller output changes only for tables with eligible searchable filters.
- Service output changes only for tables with eligible searchable filters, generated sort validation, or valid default sort behavior.
- Inheritance-table rendering remains under the existing inheritance path and must not emit DTO, controller, service, shared error, config, or specification files.

## Test Plan

All tests should be generator tests that verify emitted source text and paths. Do not require compiling or running generated Java.

Recommended focused tests:

1. Repository template output
   - A searchable table emits `JpaSpecificationExecutor` import and extends both `JpaRepository<E, UUID>` and `JpaSpecificationExecutor<E>`.
   - A no-profile table repository remains byte-identical to existing expected output.

2. Controller template output
   - A table with `full_name: VARCHAR searchable=true` emits `@RequestParam(required = false) String fullName`.
   - A table with `age: INTEGER searchable=true` emits `@RequestParam(required = false) Integer age`.
   - The list method still includes direct `Pageable pageable` binding.
   - Query parameter names use `fullName`, not `full_name`.
   - A no-profile table controller remains byte-identical.

3. Specification builder template output
   - Searchable `VARCHAR` or `TEXT` emits lower-case `LIKE` contains logic.
   - Searchable `INTEGER`, `BIGINT`, and `NUMERIC` emit `criteriaBuilder.equal(...)` logic with typed parameters.
   - Multiple filters are combined with `criteriaBuilder.and(...)`.
   - No unsupported operators such as `OR`, ranges, negation, or nested groups appear.

4. Service template output
   - Searchable table calls `repository.findAll(specification, effectivePageable).map(this::toResponseDto)`.
   - No-profile table keeps direct `repository.findAll(pageable).map(this::toResponseDto)`.
   - Sort validation checks every `pageable.getSort()` property against a generated allow-list.
   - Invalid sort path emits a 400-compatible rejection branch.
   - Unsorted pageable with valid default sort emits `PageRequest.of(..., Sort.by(Sort.Direction.<DIR>, "<field>"))`.
   - Explicit sorted pageable is not overwritten by default sort.

5. Renderer/file layout output
   - Searchable non-inheritance table emits exactly one additional `application/<E>Specifications.java` file.
   - Non-searchable no-profile table still emits exactly six files in the existing fixed order.
   - Inheritance table output remains domain/root repository only and emits no specification file.

6. Default-sort validation
   - Valid `default_sort.attribute_id` resolving to a sortable column succeeds.
   - Unknown default-sort attribute raises `InvalidDefaultSortError`.
   - Default sort pointing to an un-sortable, FK, enum, primary-key, or unsupported-type column raises `InvalidDefaultSortError`.
   - Aggregate generation returns no partial `GeneratedSources` when the error is raised.

## Rollout Notes

- No database migration is needed.
- No generated-project Gradle dependency change is expected because `JpaSpecificationExecutor` is part of Spring Data JPA.
- No frontend, mobile, OpenAPI, Postman, Docker, or infrastructure changes are included.
- Review size should be protected by keeping the first implementation tests focused on emitted source content rather than broad generated-project runtime coverage.
