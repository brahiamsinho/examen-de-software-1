# Proposal: Generated Spring API Filtering and Search

## Intent

Generate a bounded first slice of filtering, search, sort validation, and default-sort behavior for generated Spring Boot REST APIs.

The generated API should use generation profile metadata already carried on `Table.profile` and `Column.profile` so generated list endpoints become more useful without changing pagination, frontend behavior, inheritance APIs, or project-level infrastructure.

## Problem

Generated Spring controllers currently expose a flat list endpoint that accepts only `Pageable` and delegates directly to `repository.findAll(pageable)`. Even when the UML/profile layer marks columns as searchable, sortable, or declares a table `defaultSort`, the Spring generator does not consume those facts.

This leaves generated APIs unable to express common list workflows such as:

- filtering customers by a searchable name field;
- filtering orders by an exact numeric total;
- rejecting unsupported sort keys instead of passing arbitrary sort properties to Spring Data;
- applying the modeled default sort when the client sends no explicit sort.

## Scope

This change modifies the Spring generator only.

In scope:

1. **Repository generation**
   - For non-inheritance tables with at least one eligible searchable column, generated repositories extend both `JpaRepository<Entity, UUID>` and `JpaSpecificationExecutor<Entity>`.
   - Add the `JpaSpecificationExecutor` import only when needed.

2. **Generated filtering/search**
   - Generate JPA `Specification` builders for eligible searchable columns.
   - Supported searchable column behavior:
     - `VARCHAR` / `TEXT`: case-insensitive contains using `lower(field) like %lower(value)%`.
     - `INTEGER` / `BIGINT` / `NUMERIC`: exact equality using typed request parameters.
   - Combine provided filters with implicit `AND`.
   - Treat only `column.profile.searchable is True` as opt-in.

3. **Controller list query parameters**
   - The generated list endpoint accepts optional query parameters matching eligible searchable column Java field names.
   - Query parameter names are derived from the generated Java field name, not raw database column names.
   - Keep direct Spring `Pageable` binding.

4. **Service list behavior**
   - Generated service list methods accept the generated filter inputs.
   - When filters exist, call `repository.findAll(specification, pageable).map(this::toResponseDto)`.
   - When no table-level filtering/search behavior is generated, preserve the existing direct `repository.findAll(pageable)` behavior.

5. **Sort allow-list validation**
   - Reject client sort requests containing properties not generated as sortable columns.
   - Return HTTP 400 for invalid sort properties.
   - Treat only `column.profile.sortable is True` as sortable.

6. **Default sort**
   - When the client sends no sort, apply `Table.profile.default_sort` if it resolves to an eligible sortable generated Java field.
   - Do not override explicit client sort.
   - Resolve `defaultSort.attribute_id` from `Table.profile.default_sort` against `Column.source_element_id`, using the generated Java field name.

## Out of Scope

The change explicitly excludes:

- pagination contract changes;
- full-text search;
- complex operators such as ranges, `OR`, nested groups, negation, or custom operator syntax;
- frontend, mobile, Postman, Domain Manifest, or OpenAPI customization work;
- inheritance API behavior;
- generated-project-level Gradle, Docker, runtime, or infrastructure changes;
- relationship/FK filtering;
- enum, UUID, boolean, date, timestamp, discriminator, and primary-key filtering;
- project-level architectural changes outside `backend/apps/spring_generator/`.

## Affected Areas

Expected affected generator areas:

- `backend/apps/spring_generator/emit/context.py` for deriving searchable/sortable/default-sort generation context.
- `backend/apps/spring_generator/emit/templates/Repository.java.j2` for conditional `JpaSpecificationExecutor` support.
- `backend/apps/spring_generator/emit/templates/Controller.java.j2` for generated list query parameters and 400 behavior wiring.
- `backend/apps/spring_generator/emit/templates/Service.java.j2` for filter composition, sort validation, default-sort normalization, and `findAll(specification, pageable)`.
- Potential new generated helper template under `application/` if a separate specification builder keeps the service template readable within review budget.
- Focused Spring generator tests proving emitted Java source shape and unchanged output for unaffected tables.

## Product Rules

- Profile flags are opt-in: only declared `true` enables behavior.
- `false` and undeclared profile values do not generate search/sort behavior.
- Query parameters use generated Java field names so the public generated API matches DTO/entity naming rather than raw database names.
- String search is intentionally fuzzy but simple: case-insensitive contains.
- Numeric search is intentionally exact.
- Multiple supplied filters are conjunctive only.
- Sort validation protects the generated API from accidental or unsupported property sorting.
- Default sort is only a fallback and must never override explicit client sort.

## Risks

| Risk | Mitigation |
|---|---|
| Template size and readability may degrade if all logic is embedded in the service template. | Prefer small generated helpers when they reduce template complexity without expanding scope too much. |
| Direct `Pageable` binding accepts arbitrary sort properties before application code sees them. | Validate `pageable.getSort()` after binding and reject unsupported properties with 400. |
| Default-sort resolution duplicates Domain Manifest resolution concepts. | Keep the resolver local to Spring generator context and derive only from `Table` / `Column` data already present. |
| Invalid numeric query parameters rely on Spring MVC conversion behavior. | Let Spring's typed request parameter binding return standard 400 instead of adding custom parsing. |
| Existing generated output could change for tables with no eligible profile metadata. | Add unchanged-output tests for no-profile / non-eligible tables. |
| Review budget may be exceeded if tests cover too many combinations at once. | Keep the first implementation slice focused on one representative string field, one numeric field, default sort, and invalid sort validation. |

## Rollback

Rollback is straightforward because this is generator-only text emission:

1. Revert the Spring generator context/template/test changes.
2. Regenerate the sample generated project if any generated artifacts were refreshed during verification.
3. Tables without eligible profiles should already remain byte-identical; rollback should not require data migration or runtime configuration changes.

No database migration, infrastructure change, or generated-project dependency change is expected.

## Success Criteria

The change is successful when:

- A table with a searchable string column generates a list query parameter and a case-insensitive contains specification clause.
- A table with a searchable numeric column generates a typed list query parameter and an equality specification clause.
- Multiple supported filters are combined with `AND`.
- Searchable `false` and undeclared searchable columns do not generate query parameters or specification clauses.
- Generated repositories extend `JpaSpecificationExecutor` only when needed.
- Client sort requests using non-sortable properties are rejected with HTTP 400.
- An unsorted request applies the table `defaultSort` when it resolves to a sortable generated Java field.
- An explicitly sorted request is not overridden by default sort.
- Invalid `defaultSort` references produce a typed generator error before partial aggregate output.
- Existing generated output remains unchanged for tables with no eligible search/sort/default-sort profile.

## Delivery Notes

- Artifact store: OpenSpec.
- Execution mode: auto.
- Delivery strategy: ask-on-risk.
- Review budget: 400 changed lines.
- This proposal does not authorize scope expansion into pagination, full-text search, complex operators, frontend work, inheritance APIs, or project-level generated runtime changes.
