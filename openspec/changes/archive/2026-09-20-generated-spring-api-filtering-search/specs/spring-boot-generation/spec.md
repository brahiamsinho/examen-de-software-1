# Delta for Spring Boot Generation

## ADDED Requirements

### Requirement: Searchable Column Specification Builder Generation

For each supported non-discriminator `Table` with at least one eligible searchable column, the system MUST generate one table-specific JPA `Specification` builder class in the `application/` layer. Eligible searchable columns MUST be columns whose `Column.profile.searchable` is exactly `true` and whose type is one of `VARCHAR`, `TEXT`, `INTEGER`, `BIGINT`, or `NUMERIC`. Columns with `searchable` unset or `false` MUST NOT generate filter inputs or specification clauses. String columns (`VARCHAR`, `TEXT`) MUST use case-insensitive contains semantics equivalent to `lower(field) LIKE %lower(value)%`. Numeric columns (`INTEGER`, `BIGINT`, `NUMERIC`) MUST use exact equality semantics equivalent to `field = value`. Multiple provided filters MUST be combined conjunctively with `AND`. The builder MUST NOT generate full-text search, complex operators, relationship/FK filtering, enum filtering, UUID filtering, boolean filtering, date filtering, timestamp filtering, primary-key filtering, inheritance API behavior, frontend behavior, or pagination contract changes.

#### Scenario: Searchable string field uses case-insensitive contains

- GIVEN a non-discriminator table `Customer` with a `VARCHAR` column `full_name` whose profile has `searchable=true`
- WHEN the Spring Boot generator emits table sources
- THEN it emits a `CustomerSpecifications` builder under the `application/` layer
- AND the specification for Java field `fullName` applies case-insensitive contains matching with `LIKE`.

#### Scenario: Searchable numeric field uses exact equality

- GIVEN a non-discriminator table `Order` with a `NUMERIC` column `total` whose profile has `searchable=true`
- WHEN the Spring Boot generator emits table sources
- THEN it emits an `OrderSpecifications` builder under the `application/` layer
- AND the specification for Java field `total` applies exact equality with `=`.

#### Scenario: Multiple filters are conjunctive

- GIVEN a non-discriminator table `Customer` with searchable fields `name` and `age`
- WHEN the generated list behavior receives both filter values
- THEN the generated specification combines both predicates with `AND`
- AND it MUST NOT generate `OR`, range, negation, nested-group, or custom-operator behavior.

#### Scenario: Non-opted-in columns are ignored

- GIVEN a non-discriminator table with columns whose `searchable` profile value is unset or `false`
- WHEN the Spring Boot generator emits table sources
- THEN those columns do not appear as generated list query parameters
- AND they do not appear in the generated specification builder.

### Requirement: Sort Allow-List and Default Sort Behavior

For supported non-discriminator tables, generated list behavior MUST validate every client-provided sort property against the allow-list of generated Java field names whose `Column.profile.sortable` is exactly `true`. If any requested sort property is not in that allow-list, the generated API MUST reject the request with `400 Bad Request`. When the client `Pageable` contains no sort and `Table.profile.default_sort` resolves to a generated Java field whose column is sortable, the generated list behavior MUST apply that default sort. Explicit client sort MUST NOT be overridden by default sort. If a declared default sort cannot be resolved to a sortable generated Java field, generation MUST fail with a typed generator error before returning partial aggregate output.

#### Scenario: Invalid sort is rejected

- GIVEN a generated API for table `Customer` where only Java field `name` is sortable
- WHEN a client requests the list endpoint with sort property `createdAt`
- THEN the generated API rejects the request with `400 Bad Request`.

#### Scenario: Valid sort is accepted

- GIVEN a generated API for table `Customer` where Java field `name` has `sortable=true`
- WHEN a client requests the list endpoint with sort property `name`
- THEN the generated list behavior accepts the sort property
- AND it does not reject the request as an unsupported sort.

#### Scenario: Default sort applies only when pageable is unsorted

- GIVEN a table profile whose `default_sort` resolves to sortable Java field `name`
- WHEN the generated list endpoint receives a `Pageable` with no client sort
- THEN the generated list behavior applies the default sort on `name`.

#### Scenario: Explicit client sort overrides default sort

- GIVEN a table profile whose `default_sort` resolves to sortable Java field `name`
- WHEN the generated list endpoint receives a `Pageable` explicitly sorted by sortable Java field `email`
- THEN the generated list behavior uses the client sort
- AND it MUST NOT replace it with the default sort.

#### Scenario: Invalid default sort fails generation atomically

- GIVEN a table profile whose `default_sort.attribute_id` does not resolve to a sortable generated Java field
- WHEN the Spring Boot generator emits sources for that table or aggregate
- THEN it raises a typed generator error
- AND no partial `GeneratedSources` result is returned.

## MODIFIED Requirements

### Requirement: Spring Data JPA Repository Generation from a Table

For the same `Table` input, the system MUST produce Java source text for one Spring Data JPA repository interface in the `persistence/` layer, extending a Spring Data repository parameterized by the entity type and its UUID id type. For a supported non-discriminator table with at least one eligible searchable column, the repository MUST also extend `JpaSpecificationExecutor<Entity>` and MUST import `org.springframework.data.jpa.repository.JpaSpecificationExecutor`. For tables with no eligible searchable columns, the repository output MUST remain byte-identical to the previous repository contract.

(Previously: repositories extended only the Spring Data repository parameterized by entity type and UUID id type.)

#### Scenario: Table yields a matching repository interface

- GIVEN a `Product` table with no eligible searchable columns
- WHEN the generator emits the repository
- THEN the output is Java source text for `ProductRepository`, an interface extending a Spring Data JPA repository parameterized `<Product, UUID>`
- AND the output does not include `JpaSpecificationExecutor`.

#### Scenario: Searchable table repository extends JpaSpecificationExecutor

- GIVEN a supported non-discriminator `Customer` table with at least one eligible searchable column
- WHEN the generator emits the repository
- THEN `CustomerRepository` extends both `JpaRepository<Customer, UUID>` and `JpaSpecificationExecutor<Customer>`
- AND it imports `JpaSpecificationExecutor`.

### Requirement: Package and File Path Layout

Generated Java files MUST be placed only under the `domain/`, `persistence/`, `application/`, `application/dto/`, `api/`, and `errors/` subdirectories of the §22 layout (`domain/persistence/application/api/validation/errors/config`), with exactly one exception: the single project entry-point class `src/main/java/<pkg path>/Application.java`, which sits directly in the root base package and is emitted only by `generate_project_scaffold_sources` (and therefore by `generate_project_sources`). `Application` is NOT a `config/` class; it MUST live in the root base package because `@SpringBootApplication` scans its own package downward. Two non-Java root files, `build.gradle` and `settings.gradle`, are likewise emitted only by those scaffold entry points. The `validation/` and Java `config/` subdirectories MUST NOT be produced by this slice. For non-discriminator tables, `generate_table_sources(table, *, base_package)` MUST emit the existing six files per call, in fixed layer order, and MUST additionally emit exactly one `application/<E>Specifications.java` file when the table has at least one eligible searchable column. For non-discriminator tables with no eligible searchable columns, the emitted file paths, file count, ordering, and Java source text MUST remain byte-identical to the previous six-file output. For supported discriminator-backed tables, `generate_table_sources(table, *, base_package)` MUST emit only `domain/` entity classes and the root `persistence/` repository according to the inheritance artifact boundary. A separate `generate_shared_error_sources(*, base_package)` entry point, taking no `Table`, MUST emit exactly two per-project Java files: `errors/ResourceNotFoundException.java` and `errors/GlobalExceptionHandler.java`. A separate `generate_project_config_sources()` entry point, taking no `Table`, `EnumType`, relational model, base package, or application name, MUST emit exactly one resource file at `src/main/resources/application.yml`. `generate_table_sources` MUST NOT emit any file under `errors/` or `src/main/resources/`. `generate_table_sources`, `generate_shared_error_sources` and `generate_project_config_sources` MUST NOT emit any scaffold path (`build.gradle`, `settings.gradle`, `src/main/java/<pkg path>/Application.java`).

(Previously: every non-discriminator table always emitted exactly six files and no table-specific Specification builder.)

#### Scenario: A non-discriminator table without searchable columns yields six layered files

- GIVEN a `Product` table with no eligible searchable columns generated end to end via `generate_table_sources`
- WHEN the set of emitted file paths is inspected
- THEN exactly six files exist, one each at `domain/`, `persistence/`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, and `api/<E>Controller.java`, in that fixed order.

#### Scenario: A searchable non-discriminator table yields a specification builder file

- GIVEN a supported non-discriminator `Customer` table with at least one eligible searchable column
- WHEN the set of emitted file paths is inspected
- THEN the existing table artifacts are emitted
- AND exactly one additional file exists at `application/CustomerSpecifications.java`.

#### Scenario: A discriminator-backed table yields only domain and root persistence files

- GIVEN a supported discriminator-backed `Vehicle` table generated via `generate_table_sources`
- WHEN the set of emitted file paths is inspected
- THEN every emitted path is under `domain/` or is the root repository under `persistence/`
- AND no DTO, service, controller, shared error, validation, specification builder, or config path is emitted.

### Requirement: Service Layer Generation from a Table

For a `Table`, the system MUST produce Java source text for one `@Service`-annotated class `<E>Service` in the `application/` layer, with constructor injection of the table's own repository and one repository per distinct `ForeignKey.referenced_table`, deduplicated (a self-reference deduplicates against the entity's own repository, adding no extra parameter). The class MUST be `@Transactional(readOnly = true)` at class level with `@Transactional` on `create`, `update`, and `delete`. For tables without generated filtering/search behavior, the service MUST preserve the existing public list method behavior equivalent to `list(Pageable)` and direct `repository.findAll(pageable)` usage. For tables with generated filtering/search behavior, the service list behavior MUST accept the generated filter inputs, build a table-specific `Specification`, and call `repository.findAll(specification, pageable).map(this::toResponseDto)`. Sort allow-list validation and default-sort fallback MUST be applied to list behavior before repository execution. FK resolution MUST use `relatedRepository.findById(...).orElseThrow(...)`, never `EntityManager.getReference()` or `getReferenceById`; a nullable FK whose DTO value is `null` MUST skip the lookup.

(Previously: the service exposed exactly six public methods including `list(Pageable)` and did not accept filter inputs, build specifications, validate sort properties, or apply default sort.)

#### Scenario: Table with no relationships and no profiles yields unchanged service list behavior

- GIVEN a `Product` table with only scalar columns and no eligible search/sort/default-sort profile behavior
- WHEN the generator emits the service
- THEN the output is Java source for `@Service class ProductService` with a single constructor-injected `ProductRepository`
- AND the list behavior remains direct `repository.findAll(pageable)` behavior.

#### Scenario: Searchable table service uses specification-based findAll

- GIVEN a `Customer` table with at least one eligible searchable column
- WHEN the generator emits the service
- THEN the list behavior accepts the generated filter inputs
- AND it calls `repository.findAll(specification, pageable).map(this::toResponseDto)`.

#### Scenario: FK-bearing table injects the related repository and resolves via findById

- GIVEN a `Table` named `Order` with a non-nullable FK to `Customer`
- WHEN the generator emits the service
- THEN the constructor also injects `CustomerRepository`, and FK resolution calls `customerRepository.findById(...).orElseThrow(...)`, with no `getReference` call anywhere in the output.

#### Scenario: Nullable FK skips lookup when the DTO value is null

- GIVEN a `Table` with a nullable FK column
- WHEN the generator emits the service's conversion logic
- THEN the emitted statement checks for `null` and skips the repository lookup instead of always resolving it.

### Requirement: REST Controller Generation from a Table

For a `Table`, the system MUST produce Java source text for one `@RestController` class `<E>Controller` in `api/`, annotated `@RequestMapping("/api/<segment>")` where `<segment>` is the table's pluralized, kebab-case resource path segment. The controller MUST expose exactly: `POST ""` returning 201, `GET "/{id}"` returning 200, `PUT "/{id}"` returning 200, `DELETE "/{id}"` returning 204, `GET ""` returning a paginated result, and `GET "/count"` returning a count. The request DTO MUST be annotated `@Valid` on `POST`/`PUT`. The list endpoint MUST bind Spring's `Pageable` directly as a method parameter. For supported non-discriminator tables with eligible searchable columns, the list endpoint MUST also accept optional query parameters whose names match the generated Java field names for those searchable columns. String searchable parameters MUST be typed as `String`; numeric searchable parameters MUST use the corresponding generated Java numeric type. Invalid numeric query parameter conversion MAY rely on Spring MVC standard binding failure behavior and MUST produce a client error rather than silent filtering. Tables without eligible searchable columns MUST preserve the existing list endpoint signature and output byte-for-byte.

(Previously: the list endpoint bound only Spring's `Pageable` directly with no custom `@RequestParam` parsing or additional searchable query parameters.)

#### Scenario: Table yields a controller with all six required endpoints

- GIVEN a `Table` named `Product`
- WHEN the generator emits the controller
- THEN the output declares `@RequestMapping("/api/products")` and all six required endpoint methods with their documented HTTP methods and status codes.

#### Scenario: Searchable fields become optional query parameters

- GIVEN a `Customer` table with searchable columns `full_name: VARCHAR` and `age: INTEGER`
- WHEN the generator emits the controller
- THEN the list endpoint accepts optional query parameters named `fullName` and `age`
- AND it still binds Spring's `Pageable` directly.

#### Scenario: Query parameter names use generated Java field names

- GIVEN a searchable database column named `full_name` that generates Java field `fullName`
- WHEN the generator emits the list endpoint
- THEN the query parameter is named `fullName`
- AND it is not named `full_name`.

#### Scenario: Resource path segment is pluralized deterministically

- GIVEN a `Table` named `category` and a `Table` named `order_line`
- WHEN the generator emits each controller
- THEN the path segments are `/api/categories` and `/api/order-lines` respectively.

### Requirement: Exact Backward Compatibility for Tables Without Profiles

For any table with no discriminator inheritance metadata and no generation profile behavior relevant to searchable filters, sortable columns, or default sort, `generate_table_sources(table, *, base_package)` MUST preserve the existing non-inheritance contract exactly. It MUST emit the same six files, in the same order, at the same paths, with byte-identical Java source text compared to the pre-filtering/search implementation for the same supported non-discriminator input.

(Previously: backward compatibility was scoped to preserving non-discriminator output after inheritance support.)

#### Scenario: No-profile table output remains byte-identical

- GIVEN a supported non-discriminator `Product` table with no searchable, sortable, or default-sort profile behavior
- WHEN `generate_table_sources` is invoked after filtering/search support is added
- THEN exactly the same six paths are emitted in the same order
- AND every emitted file's Java source text is byte-identical to the pre-filtering/search output.

#### Scenario: Ineligible profile values do not change output

- GIVEN a supported non-discriminator table whose profile values are unset or explicitly `false` for searchable and sortable behavior and whose table has no valid default sort
- WHEN `generate_table_sources` is invoked
- THEN no repository specification executor, specification builder, filter query parameter, sort validation behavior, or default sort behavior is generated
- AND the output remains byte-identical to the previous no-profile output.

### Requirement: Existing Generator Contracts Are Preserved

Whole-model generation MUST preserve all existing table, enum, shared-error, and project-configuration generator contracts except for the explicitly specified generated filtering/search, sort validation, and default-sort behavior for supported non-discriminator tables that opt in through profiles. It MUST NOT change unsupported-shape typed errors, package propagation rules, project configuration placeholders, pagination contracts, full-text search behavior, complex operator behavior, frontend output, mobile output, Java `config/` classes, filesystem writing, project materialization, compilation, Docker behavior, or any Gradle artifact (`build.gradle`, `settings.gradle`, wrapper), and output for tables without relevant profiles MUST remain byte-identical to its output before this change. This prohibition is scoped to `generate_model_sources`. Emitting Gradle build text from a different entry point (`generate_project_scaffold_sources`, `generate_project_sources`) is not "Gradle behavior" in the sense of this requirement, because no Gradle is executed, and it does not alter any lower-level generator contract.

(Previously: `generate_model_sources` was prohibited from adding filtering/search metadata or generated filtering APIs at all.)

#### Scenario: Lower-level generator outputs are unchanged for unaffected tables inside the aggregate

- GIVEN a supported table with no relevant profiles, a supported `EnumType`, the shared error source set, and the project configuration source set
- WHEN each lower-level generator is invoked directly and the same inputs are also generated through `generate_model_sources`
- THEN the corresponding files inside the whole-model aggregate have the same paths, ordering within their own generator boundary, and byte-identical content as the direct lower-level generator outputs
- AND the whole-model aggregate contains no out-of-scope OpenAPI expansion, Postman, Manifest, frontend, mobile, Java `config/`, materialization, compilation, Docker, or Gradle artifact.

#### Scenario: Filtering support does not change pagination or frontend scope

- GIVEN a model containing a table with eligible searchable and sortable profile behavior
- WHEN `generate_model_sources` emits generated filtering/search support
- THEN the list endpoint remains paginated through Spring `Pageable`
- AND no frontend, mobile, full-text search, complex operator, inheritance API expansion, or generated-project infrastructure artifact is emitted.
