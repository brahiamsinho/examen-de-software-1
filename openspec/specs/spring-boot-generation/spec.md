# Spring Boot Generation Specification

## Purpose

Defines the pure, deterministic Spring Boot source emission already implemented for the generated backend stack: one-table Java generation, enum generation, shared error Java generation, bounded Single Table inheritance Java generation, one project-singleton `application.yml` resource, and project scaffold generation (`build.gradle`, `settings.gradle`, root-package `Application.java`). The system provides a project aggregate via `generate_project_sources` that combines the model aggregate with the project scaffold. Java compilation, OpenAPI, Postman, Domain Manifest, generated frontend/mobile output, generated-project materialization, and Java `config/` classes remain out of scope. Whole-model and project orchestration are now supported as in-memory aggregate APIs.

## Requirements

### Requirement: JPA Entity Generation from a Table

For a `Table`, the system MUST produce Java source text for one `@Entity`-annotated class in the `domain/` layer, using Java 21, Jakarta Validation, and Jackson annotations as applicable, with one field per `Column` and the synthetic UUID `primary_key` mapped as the `@Id` field. A scalar `Column` (no FK, no `enum_type_name`) MUST be typed and annotated per the column-type mapping. A `Column` that is part of a FK on the table being rendered MUST instead be emitted as a relationship field: `@ManyToOne` + `@JoinColumn`, or `@OneToOne` + `@JoinColumn` when the owning `ForeignKey.column_names` exactly match one of the table's own `unique_constraints`, typed with the referenced entity's Java class name derived via `pascal_case(ForeignKey.referenced_table)`. A self-referencing FK (`ForeignKey.referenced_table == table.name`) MUST be accepted and MUST render as an ordinary self-referencing `@ManyToOne`/`@OneToOne` field, not rejected. A `Column` with a non-`None` `enum_type_name` MUST be emitted as a field typed `pascal_case(Column.enum_type_name)` annotated `@Enumerated(EnumType.STRING)`. The generated entity's no-arg constructor MUST be declared `public`, not `protected`, so a class in a different package (the `application` layer) can instantiate the entity directly.

(Previously: scoped to "only scalar columns (no FK, no `discriminator_column`, no `enum_type_name`)", with FK and enum columns out of scope; the no-arg constructor's visibility was `protected` and unspecified in this requirement's text.)

#### Scenario: Table with scalar columns yields an entity class

- GIVEN a `Table` named `Product` with a UUID `PrimaryKey` and scalar `Column`s `name: VARCHAR`, `price: NUMERIC`
- WHEN the generator emits the entity
- THEN the output is Java source text for a class `Product` annotated `@Entity`, with an `@Id` UUID field and one field per column, each correctly typed per the column-type mapping

#### Scenario: FK column yields a many-to-one relationship field

- GIVEN a `Table` named `Order` with a `Column`-backed `ForeignKey` whose `column_names` do not match any `unique_constraints` entry, referencing table `Customer`
- WHEN the generator emits the entity
- THEN the corresponding field is typed `Customer`, annotated `@ManyToOne` and `@JoinColumn`

#### Scenario: FK column matching a unique constraint yields a one-to-one relationship field

- GIVEN a `Table` whose `ForeignKey.column_names` exactly match one of its own `unique_constraints` entries, referencing table `Profile`
- WHEN the generator emits the entity
- THEN the corresponding field is typed `Profile`, annotated `@OneToOne` and `@JoinColumn`

#### Scenario: Self-referencing FK yields a self-referencing relationship field

- GIVEN a `Table` named `Category` with a `ForeignKey` whose `referenced_table` equals `Category`
- WHEN the generator emits the entity
- THEN generation succeeds and the corresponding field is typed `Category`, annotated `@ManyToOne` (or `@OneToOne` per the unique-constraint rule) and `@JoinColumn`

#### Scenario: Enum-typed column yields an enum field

- GIVEN a `Table` with a `Column` named `status` whose `enum_type_name` is `order_status`
- WHEN the generator emits the entity
- THEN the corresponding field is typed `OrderStatus`, annotated `@Enumerated(EnumType.STRING)`

#### Scenario: Entity no-arg constructor is public, not protected

- GIVEN any `Table` generated end to end
- WHEN the entity's no-arg constructor is inspected
- THEN the constructor is declared `public`, and no `protected` no-arg constructor is present

### Requirement: Spring Data JPA Repository Generation from a Table

For the same `Table` input, the system MUST produce Java source text for one Spring Data JPA repository interface in the `persistence/` layer, extending a Spring Data repository parameterized by the entity type and its UUID id type.

#### Scenario: Table yields a matching repository interface
- GIVEN the `Product` table from above
- WHEN the generator emits the repository
- THEN the output is Java source text for `ProductRepository`, an interface extending a Spring Data JPA repository parameterized `<Product, UUID>`

### Requirement: Deterministic Column-Type-to-Java-Type Mapping

The system MUST map every non-enum, non-FK `ColumnType` to exactly one Java type and JPA/Jakarta annotation set, applied consistently to every column of that type:

| `ColumnType` | Java type | Annotation notes |
|---|---|---|
| `UUID` | `java.util.UUID` | `@Id` + `@GeneratedValue` when it is the primary key column; plain `@Column` otherwise |
| `VARCHAR` | `String` | `@Column(length = <length>)`; `@Size(max = <length>)` when `length` is set |
| `TEXT` | `String` | `@Column(columnDefinition = "TEXT")` |
| `INTEGER` | `Integer` | `@Column` |
| `BIGINT` | `Long` | `@Column` |
| `NUMERIC` | `java.math.BigDecimal` | `@Column(precision = <precision>, scale = <scale>)` when set |
| `BOOLEAN` | `Boolean` | `@Column` |
| `DATE` | `java.time.LocalDate` | `@Column` |
| `TIMESTAMPTZ` | `java.time.OffsetDateTime` | `@Column` |

A `Column` with a non-`None` `enum_type_name` MUST NOT be resolved through this table. Its Java type MUST instead be `pascal_case(Column.enum_type_name)` — the enum's own generated Java type — annotated `@Enumerated(EnumType.STRING)`, deterministically, with no cross-table lookup required.

Every mapped field MUST carry `@Column(nullable = false)` (or the Jakarta `@NotNull` equivalent) unless `Column.nullable` is `True`, in which case the field MUST omit the not-null constraint.

(Previously: mapped "every non-enum `ColumnType`" only; enum-typed columns had no mapping rule because they were rejected before mapping.)

#### Scenario: Nullable column omits the not-null constraint

- GIVEN a `Column` named `notes` of type `TEXT` with `nullable=True`
- WHEN the entity field for `notes` is emitted
- THEN the field carries no not-null constraint

#### Scenario: NUMERIC column carries precision and scale

- GIVEN a `Column` named `price` of type `NUMERIC` with `precision=10, scale=2`
- WHEN the entity field for `price` is emitted
- THEN the field is typed `BigDecimal` and its `@Column` annotation states `precision = 10, scale = 2`

#### Scenario: Enum column resolves to the enum's own Java type, not a scalar ColumnType

- GIVEN a `Column` named `status` with `enum_type_name="order_status"`
- WHEN the Java type for `status` is resolved
- THEN the resolved type is `OrderStatus`, derived via `pascal_case(enum_type_name)`, with no entry looked up in the scalar `ColumnType` table

### Requirement: Generator Purity

The generator MUST be a pure function of its in-memory inputs to generated source text. It MUST NOT call `relational_mapping`'s `validate()` or any validation routine, and MUST NOT open, query, or otherwise touch any database connection. The project configuration generator MUST also avoid filesystem writes, environment-variable inspection, subprocess execution, Java compilation, Gradle execution, and network access. The project scaffold entry points (`generate_project_scaffold_sources` and `generate_project_sources`) MUST avoid the same: filesystem access, environment-variable inspection, subprocess execution, network access, Java compilation, and Gradle execution. Emitting `build.gradle` text is string rendering only; no Gradle process is started.

(Previously: the extra filesystem/environment/subprocess/compilation/Gradle/network restriction was stated only for the project configuration generator.)

#### Scenario: Generation succeeds with no DB and no validation call
- GIVEN a valid in-memory `Table` and no database connection available in the test process
- WHEN the entity and repository are generated
- THEN generation completes and returns Java source text, with no validation function invoked and no DB access attempted

#### Scenario: Scaffold and project generation are runtime-free

- GIVEN a valid `base_package`, a valid in-memory `RelationalModel`, and a test process with no project directory, database, JVM or Gradle available
- WHEN `generate_project_scaffold_sources` and `generate_project_sources` are invoked
- THEN both succeed using only in-memory inputs
- AND no filesystem access, environment read, subprocess, network access, Java compilation, Gradle execution, database access, or validation call occurs

### Requirement: Rejection of Unsupported Table Shapes

The system MUST raise a typed error, and MUST NOT emit partial or malformed Java source, when the input `Table` contains a construct out of scope for the applicable generation path: a primary key that is not a single UUID column, a `ForeignKey` whose `column_names` has more than one entry (composite FK), or malformed/unsupported discriminator-backed inheritance metadata. A non-empty `foreign_keys` with only single-column entries, and a `Column` with a non-`None` `enum_type_name`, MUST NOT be rejected solely for those reasons — both are supported and MUST be generated per the applicable entity-generation requirements. A discriminator-backed table MUST NOT be rejected merely because `discriminator_column` or `discriminator_values` is present when it satisfies the supported Single Table inheritance shape.

(Previously: any table with a non-`None` `discriminator_column` was rejected, even when the table carried ownership metadata and otherwise represented the mapper's Single Table inheritance shape.)

#### Scenario: Table with a foreign key is accepted

- GIVEN a `Table` whose `foreign_keys` is non-empty and every `ForeignKey.column_names` has exactly one entry
- WHEN the generator is invoked on it
- THEN it does not raise a rejection error and proceeds to emit the entity with the corresponding relationship field(s)

#### Scenario: Table with a composite foreign key is rejected

- GIVEN a `Table` containing a `ForeignKey` whose `column_names` has more than one entry
- WHEN the generator is invoked on it
- THEN it raises a typed error and produces no Java source

#### Scenario: Supported discriminator table is accepted

- GIVEN a discriminator-backed `Table` satisfying the supported Single Table inheritance shape
- WHEN the generator is invoked on it
- THEN it does not raise an inheritance-unsupported error
- AND it emits only inheritance domain classes plus the root repository

#### Scenario: Malformed discriminator table missing class ids is rejected

- GIVEN a `Table` with a discriminator column but an empty `source_class_ids` sequence
- WHEN the generator is invoked on it
- THEN it raises a typed malformed-inheritance error
- AND it produces no Java source

#### Scenario: Malformed discriminator table missing a discriminator value is rejected

- GIVEN a `Table` with `source_class_ids` containing `vehicle` and `car`
- AND `Table.discriminator_values` has no value for `car`
- WHEN the generator is invoked on it
- THEN it raises a typed malformed-inheritance error
- AND it produces no Java source

#### Scenario: Unsupported ownership shape is rejected before rendering

- GIVEN a discriminator-backed `Table` with an attribute-derived column whose `owning_class_id` is not present in `source_class_ids`
- WHEN the generator is invoked on it
- THEN it raises a typed malformed-inheritance error
- AND it produces no Java source

#### Scenario: Table with an enum-typed column is accepted

- GIVEN a `Table` containing a `Column` with `enum_type_name` set
- WHEN the generator is invoked on it
- THEN it does not raise a rejection error and proceeds to emit the entity with the corresponding enum field

### Requirement: Deterministic, Repeatable Output

The system MUST produce byte-identical Java source text — same field order, same formatting, same annotations — for the same `Table` input on every invocation.

#### Scenario: Same table produces identical output on repeated calls
- GIVEN the same `Table` value generated twice, independently
- WHEN both entity outputs are compared
- THEN the two Java source texts are byte-identical, including column and field ordering

### Requirement: Package and File Path Layout

Generated Java files MUST be placed only under the `domain/`, `persistence/`, `application/`, `application/dto/`, `api/`, and `errors/` subdirectories of the §22 layout (`domain/persistence/application/api/validation/errors/config`), with exactly one exception: the single project entry-point class `src/main/java/<pkg path>/Application.java`, which sits directly in the root base package and is emitted only by `generate_project_scaffold_sources` (and therefore by `generate_project_sources`). `Application` is NOT a `config/` class; it MUST live in the root base package because `@SpringBootApplication` scans its own package downward. Two non-Java root files, `build.gradle` and `settings.gradle`, are likewise emitted only by those scaffold entry points. The `validation/` and Java `config/` subdirectories MUST NOT be produced by this slice. For non-discriminator tables, `generate_table_sources(table, *, base_package)` MUST emit exactly six files per call, in fixed layer order: `domain/<E>.java`, `persistence/<E>Repository.java`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, `api/<E>Controller.java`. For supported discriminator-backed tables, `generate_table_sources(table, *, base_package)` MUST emit only `domain/` entity classes and the root `persistence/` repository according to the inheritance artifact boundary. A separate `generate_shared_error_sources(*, base_package)` entry point, taking no `Table`, MUST emit exactly two per-project Java files: `errors/ResourceNotFoundException.java` and `errors/GlobalExceptionHandler.java`. A separate `generate_project_config_sources()` entry point, taking no `Table`, `EnumType`, relational model, base package, or application name, MUST emit exactly one resource file at `src/main/resources/application.yml`. `generate_table_sources` MUST NOT emit any file under `errors/` or `src/main/resources/`. `generate_table_sources`, `generate_shared_error_sources` and `generate_project_config_sources` MUST NOT emit any scaffold path (`build.gradle`, `settings.gradle`, `src/main/java/<pkg path>/Application.java`).

(Previously: Java files were allowed only under the six layer directories with no exception, and no root-level build files were described. Now the root-package `Application.java` is the single Java file outside the layers, `build.gradle` and `settings.gradle` are the two allowed root files, and the three existing entry points are explicitly barred from emitting scaffold paths.)

#### Scenario: A non-discriminator table yields six layered files under domain, persistence, application, and api

- GIVEN the `Product` table generated end to end via `generate_table_sources`
- WHEN the set of emitted file paths is inspected
- THEN exactly six files exist, one each at `domain/`, `persistence/`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, and `api/<E>Controller.java`, in that fixed order

#### Scenario: A discriminator-backed table yields only domain and root persistence files

- GIVEN a supported discriminator-backed `Vehicle` table generated via `generate_table_sources`
- WHEN the set of emitted file paths is inspected
- THEN every emitted path is under `domain/` or is the root repository under `persistence/`
- AND no DTO, service, controller, shared error, validation, or config path is emitted

#### Scenario: Error sources are emitted only by the shared entry point

- GIVEN `generate_shared_error_sources(base_package=...)` is invoked
- WHEN the returned files are inspected
- THEN exactly two files exist under `errors/`, and no file under `errors/` is produced by any `generate_table_sources` call

#### Scenario: Validation and config directories remain forbidden

- GIVEN the `Product` table generated end to end, the shared error sources generated once, the project singleton configuration generated once, and the project scaffold generated once
- WHEN the combined set of emitted file paths is inspected
- THEN no file exists under `validation/` or `config/`
- AND `Application.java` is not under any `config/` directory

#### Scenario: Project application YAML is emitted only by the project singleton configuration generator

- GIVEN table generation, shared error generation, enum generation, and project singleton configuration generation are each invoked through their own entry point
- WHEN all returned file paths are inspected
- THEN only the project singleton configuration generator emits `src/main/resources/application.yml`
- AND no other generator emits a path under `src/main/resources/`

#### Scenario: Application.java is the single Java file outside the six layer directories

- GIVEN `generate_project_sources(model, base_package="com.example.generated")` for a model with tables, enums and shared errors
- WHEN every emitted `.java` path is classified
- THEN every path is under one of the six layer directories, except `src/main/java/com/example/generated/Application.java`, which is directly in the root base package
- AND the only non-Java, non-resource root files are `build.gradle` and `settings.gradle`

#### Scenario: Existing entry points never emit scaffold paths

- GIVEN `generate_table_sources` for a non-discriminator table and a discriminator-backed table, `generate_shared_error_sources`, and `generate_project_config_sources` are each invoked
- WHEN all returned file paths are inspected
- THEN none of them equals `build.gradle`, `settings.gradle`, or ends with `/Application.java` at the root base package

### Requirement: Project Singleton Application YAML Generation

The system MUST provide a pure project-singleton function `generate_project_config_sources() -> GeneratedSources` that is independent of `Table`, `EnumType`, relational model, orchestration, `base_package`, and application name inputs. It MUST return exactly one `GeneratedFile` at `src/main/resources/application.yml`. The content MUST be YAML resource text with no Java package declaration and MUST contain exactly these bounded runtime configuration placeholders with no defaults:

- `spring.application.name: ${SPRING_APPLICATION_NAME}`
- `spring.datasource.url: ${SPRING_DATASOURCE_URL}`
- `spring.datasource.username: ${SPRING_DATASOURCE_USERNAME}`
- `spring.datasource.password: ${SPRING_DATASOURCE_PASSWORD}`
- `spring.jpa.hibernate.ddl-auto: ${JPA_DDL_AUTO}`
- `server.port: ${SERVER_PORT}`

The generated YAML MUST NOT emit placeholder defaults such as `${SERVER_PORT:8080}`. It MUST NOT hardcode deployable values such as hosts, ports, URLs, JDBC connection strings, usernames, or passwords. It MUST NOT emit Hibernate dialect/platform settings, OpenAPI, Postman, Manifest, frontend, mobile, logging, Docker, Java `@Configuration`, validation, or Java `config/` scaffolding.

#### Scenario: Project config generator emits exactly one application YAML file

- GIVEN `generate_project_config_sources()` is invoked without table, enum, relational model, base-package, or application-name input
- WHEN the returned sources are inspected
- THEN exactly one file exists at `src/main/resources/application.yml`
- AND that file content contains no Java package declaration

#### Scenario: Application YAML contains only required no-default placeholders

- GIVEN `generate_project_config_sources()` is invoked
- WHEN the generated YAML content is inspected
- THEN it contains the six required no-default placeholders
- AND it contains no placeholder default value
- AND it contains no Hibernate dialect or database platform property

### Requirement: Enum Type Generation

The system MUST provide a pure function `generate_enum_source(enum_type: relational_mapping.domain.schema.EnumType, *, base_package) -> GeneratedFile` that produces Java source text for one standalone Java `enum` in the `domain/` layer, with one enum constant per entry in `EnumType.labels`, named after the `EnumType`'s `pascal_case(name)`. The function MUST be a pure function of its `EnumType` input, producing byte-identical output on every invocation for the same input, and MUST place the generated file under the `domain/` subdirectory of the §22 layout, following the same package/path convention already used for entity generation.

#### Scenario: EnumType with multiple labels yields Java enum constants

- GIVEN an `EnumType` named `order_status` with `labels=("PENDING", "PAID", "SHIPPED")`
- WHEN `generate_enum_source` is invoked on it
- THEN the output is Java source text for `enum OrderStatus` containing constants `PENDING`, `PAID`, `SHIPPED`, in that order

#### Scenario: Same EnumType produces identical output on repeated calls

- GIVEN the same `EnumType` value generated twice, independently, via `generate_enum_source`
- WHEN both outputs are compared
- THEN the two Java source texts are byte-identical, including constant ordering

#### Scenario: Generated enum file is placed under the domain layer

- GIVEN the `order_status` `EnumType` generated via `generate_enum_source`
- WHEN the returned `GeneratedFile`'s path is inspected
- THEN the file path is under the `domain/` subdirectory of the §22 layout, matching the package convention used by entity generation
### Requirement: Service Layer Generation from a Table

For a `Table`, the system MUST produce Java source text for one `@Service`-annotated class `<E>Service` in the `application/` layer, with constructor injection of the table's own repository and one repository per distinct `ForeignKey.referenced_table`, deduplicated (a self-reference deduplicates against the entity's own repository, adding no extra parameter). The class MUST be `@Transactional(readOnly = true)` at class level with `@Transactional` on `create`, `update`, and `delete`, and MUST expose exactly six public methods: `create`, `findById`, `update`, `delete`, `list(Pageable)`, `count()`. FK resolution MUST use `relatedRepository.findById(...).orElseThrow(...)`, never `EntityManager.getReference()` or `getReferenceById`; a nullable FK whose DTO value is `null` MUST skip the lookup.

#### Scenario: Table with no relationships yields a service with six methods

- GIVEN a `Table` named `Product` with only scalar columns
- WHEN the generator emits the service
- THEN the output is Java source for `@Service class ProductService` with a single constructor-injected `ProductRepository` and the six required public methods

#### Scenario: FK-bearing table injects the related repository and resolves via findById

- GIVEN a `Table` named `Order` with a non-nullable FK to `Customer`
- WHEN the generator emits the service
- THEN the constructor also injects `CustomerRepository`, and FK resolution calls `customerRepository.findById(...).orElseThrow(...)`, with no `getReference` call anywhere in the output

#### Scenario: Self-referencing FK does not duplicate the injected repository

- GIVEN a `Table` named `Category` with a self-referencing FK
- WHEN the generator emits the service
- THEN the constructor injects `CategoryRepository` exactly once, not twice

#### Scenario: Nullable FK skips lookup when the DTO value is null

- GIVEN a `Table` with a nullable FK column
- WHEN the generator emits the service's conversion logic
- THEN the emitted statement checks for `null` and skips the repository lookup instead of always resolving it

### Requirement: Flat-FK Request/Response DTO Generation from a Table

For a `Table`, the system MUST produce Java source text for two classes in `application/dto/`: `<E>RequestDto`, with one field per `Column` except the primary key, and `<E>ResponseDto`, with one field per `Column` including the primary key. A FK column MUST become a plain `UUID` field on both DTOs, never the related entity's Java type. Request fields MUST forward the entity's `@NotNull`/`@Size` Jakarta constraints; response fields MUST carry no validation annotation. Neither DTO MUST contain any JPA annotation (`@Entity`, `@Column`, `@JoinColumn`, `@Enumerated`).

#### Scenario: Scalar-only table yields matching request and response DTOs

- GIVEN a `Table` named `Product` with only scalar columns
- WHEN the generator emits both DTOs
- THEN `ProductRequestDto` omits the primary key field, `ProductResponseDto` includes it, and neither file contains a JPA annotation

#### Scenario: FK column becomes a flat UUID field, never the related entity type

- GIVEN a `Table` named `Order` with a FK column `customer_id` referencing `Customer`
- WHEN the generator emits both DTOs
- THEN each DTO declares `UUID customerId`, and the string `Customer` does not appear as a field type in either file

#### Scenario: Enum column keeps its enum type on both DTOs

- GIVEN a `Table` with a `Column` whose `enum_type_name` is `order_status`
- WHEN the generator emits both DTOs
- THEN both DTOs declare the field typed `OrderStatus`

### Requirement: REST Controller Generation from a Table

For a `Table`, the system MUST produce Java source text for one `@RestController` class `<E>Controller` in `api/`, annotated `@RequestMapping("/api/<segment>")` where `<segment>` is the table's pluralized, kebab-case resource path segment. The controller MUST expose exactly: `POST ""` returning 201, `GET "/{id}"` returning 200, `PUT "/{id}"` returning 200, `DELETE "/{id}"` returning 204, `GET ""` returning a paginated result, and `GET "/count"` returning a count. The request DTO MUST be annotated `@Valid` on `POST`/`PUT`. The list endpoint MUST bind Spring's `Pageable` directly as a method parameter with no custom `@RequestParam` parsing.

#### Scenario: Table yields a controller with all six required endpoints

- GIVEN a `Table` named `Product`
- WHEN the generator emits the controller
- THEN the output declares `@RequestMapping("/api/products")` and all six required endpoint methods with their documented HTTP methods and status codes

#### Scenario: Resource path segment is pluralized deterministically

- GIVEN a `Table` named `category` and a `Table` named `order_line`
- WHEN the generator emits each controller
- THEN the path segments are `/api/categories` and `/api/order-lines` respectively

#### Scenario: The count route coexists with the id route without ambiguity

- GIVEN a `Table` named `Product` generated end to end
- WHEN the controller's routes are inspected
- THEN both `GET "/count"` and `GET "/{id}"` are declared, as distinct, non-conflicting mappings

### Requirement: Shared Error Handling Generation

The system MUST provide a pure function `generate_shared_error_sources(*, base_package) -> GeneratedSources`, independent of any `Table`, that produces exactly two Java source files in `errors/`: `ResourceNotFoundException`, a `RuntimeException` subclass constructed from a resource name and a `UUID` id, and `GlobalExceptionHandler`, annotated `@RestControllerAdvice`, mapping `ResourceNotFoundException` to a 404 `ProblemDetail` and bean-validation failures to a 400 `ProblemDetail`. The function MUST be deterministic, producing byte-identical output on every invocation for the same `base_package`.

#### Scenario: Invocation yields exactly two error-handling files

- GIVEN `generate_shared_error_sources(base_package="com.modelia.generated")`
- WHEN the returned files are inspected
- THEN exactly two files are returned, `errors/ResourceNotFoundException.java` and `errors/GlobalExceptionHandler.java`, with the advice class annotated `@RestControllerAdvice`

#### Scenario: Repeated invocations produce byte-identical output

- GIVEN `generate_shared_error_sources` invoked twice with the same `base_package`
- WHEN both outputs are compared
- THEN the two sets of Java source text are byte-identical

### Requirement: Column Ownership Metadata Does Not Enable Inheritance Generation

The Spring Boot generator MUST use `Column.owning_class_id` to place attribute-derived columns on the correct entity class for supported discriminator-backed Single Table inheritance generation. This ownership metadata MUST NOT enable DTO, service, controller, subclass repository, relationship-ownership, or whole-model orchestration behavior for inheritance tables in this slice. Unsupported ownership shapes MUST still be rejected through typed unsupported-table-shape behavior before rendering.

(Previously: the generator did not treat `Column.owning_class_id` as support for Java inheritance generation and rejected any table with a discriminator column.)

#### Scenario: Discriminator table with ownership metadata generates bounded inheritance artifacts

- GIVEN a supported discriminator-backed `Table` with at least one root-owned attribute-derived `Column` and one subclass-owned attribute-derived `Column`
- WHEN the Spring Boot generator is invoked for that table
- THEN it emits Java inheritance domain classes with fields partitioned by `owning_class_id`
- AND it emits the root repository
- AND it produces no Java source for inheritance DTOs, services, controllers, or subclass repositories

#### Scenario: Ownership metadata outside the hierarchy is rejected

- GIVEN a discriminator-backed `Table` with an attribute-derived `Column.owning_class_id` that is not present in `Table.source_class_ids`
- WHEN the Spring Boot generator is invoked for that table
- THEN it raises a typed unsupported-table-shape error
- AND it produces no Java source for Java inheritance classes

### Requirement: Discriminator-Backed Single Table Domain Generation

For a supported discriminator-backed `Table`, `generate_table_sources(table, *, base_package)` MUST generate JPA Single Table inheritance domain source plus one root Spring Data repository. The supported shape MUST have a single UUID primary key, a non-empty `source_class_ids` sequence whose first entry is the root class id, a non-`None` `discriminator_column`, discriminator values for every generated hierarchy class id, and only columns that can be assigned to the root entity, a subclass entity, a supported single-column relationship field, an enum field, the synthetic id, or discriminator metadata. The generator MUST use the discriminator column as JPA inheritance metadata and MUST NOT emit it as a normal Java field on any generated class. The Java class name of each subclass entity MUST be `pascal_case` of `Table.discriminator_values[class_id]` (the UML class name) and MUST NOT be derived from the class id; the root entity name remains `pascal_case(Table.name)`. A subclass name that is not a valid Java identifier MUST keep raising the existing typed `InvalidJavaIdentifierError`.
(Previously: the requirement did not state how the subclass Java class name is derived, and the implementation derived it from the class id.)

#### Scenario: Supported discriminator table yields root entity, subclass entities, and root repository

- GIVEN a `Table` named `Vehicle` with a UUID primary key, `source_class_ids=("vehicle", "car", "truck")`, `discriminator_column="class_type"`, discriminator values `Vehicle`, `Car`, and `Truck` for those ids, root-owned scalar columns, and subclass-owned scalar columns
- WHEN `generate_table_sources` is invoked for the table
- THEN generation succeeds
- AND the emitted files contain `domain/Vehicle.java`, `domain/Car.java`, `domain/Truck.java`, and `persistence/VehicleRepository.java`
- AND no emitted Java class declares a normal field for `class_type`

#### Scenario: Actual discriminator column name is used as metadata

- GIVEN a supported discriminator-backed `Table` whose discriminator column is named `kind`
- WHEN the root entity source is emitted
- THEN the root entity declares discriminator metadata using the name `kind`
- AND no generated entity declares `kind` as a normal Java field

#### Scenario: Uuid-hex class ids generate subclasses named from the UML class name

- GIVEN a hierarchy whose class ids are `new_id()` uuid hex strings (some starting with a digit) and discriminator values `Vehicle`, `Car`, `Truck`
- WHEN `generate_project_sources` and `generate_model_sources` are invoked for the model
- THEN generation succeeds without `InvalidJavaIdentifierError`
- AND the emitted files include `domain/Car.java` and `domain/Truck.java`

#### Scenario: Subclass name does not depend on the class id

- GIVEN two otherwise identical tables whose class ids differ (readable ids versus uuid hex ids) with the same discriminator values
- WHEN `generate_table_sources` is invoked for each table
- THEN both return the same paths and byte-identical Java source text

#### Scenario: Class name that is not a valid Java identifier is rejected

- GIVEN a subclass whose discriminator value is `Electric Car`
- WHEN the Spring Boot generator is invoked for the table
- THEN it raises `InvalidJavaIdentifierError`
- AND this is a documented known limitation with no sanitizing behavior

### Requirement: Root and Subclass JPA Inheritance Annotations

For a supported discriminator-backed `Table`, the root entity MUST be annotated with `@Entity`, `@Table(name = "...")`, `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`, and `@DiscriminatorColumn(name = "...")`. The root entity MUST include `@DiscriminatorValue("...")` when `Table.discriminator_values` contains a value for the root class id. The root entity MUST be generated as non-abstract unless later UML metadata explicitly exposes abstract-class semantics. Each subclass entity MUST be annotated with `@Entity` and `@DiscriminatorValue("...")`, MUST extend the root entity Java class, and MUST NOT redeclare the inherited id or root-owned fields.
(Previously: unchanged text; scenarios used discriminator values `VEHICLE` and `CAR`, which coupled the file name to the value casing.)

#### Scenario: Root entity contains Single Table metadata

- GIVEN a supported discriminator-backed `Vehicle` table with discriminator column `class_type` and root discriminator value `Vehicle`
- WHEN the root entity source is emitted
- THEN `Vehicle.java` contains `@Entity`, `@Table(name = "Vehicle")`, `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`, `@DiscriminatorColumn(name = "class_type")`, and `@DiscriminatorValue("Vehicle")`
- AND `Vehicle` is not declared `abstract`

#### Scenario: Subclass entity extends the root and declares its discriminator value

- GIVEN the same table has a subclass class id `car` with discriminator value `Car`
- WHEN the subclass entity source is emitted
- THEN `Car.java` contains `@Entity` and `@DiscriminatorValue("Car")`
- AND the class declaration extends `Vehicle`
- AND `Car.java` does not redeclare the UUID id field
### Requirement: Field Ownership Partitioning for Inheritance Entities

For a supported discriminator-backed `Table`, the generator MUST partition entity fields by `Column.owning_class_id`. Attribute-derived columns whose `owning_class_id` is the root class id MUST be emitted only on the root entity. Attribute-derived columns whose `owning_class_id` is a subclass class id MUST be emitted only on that subclass entity. A subclass entity MUST NOT duplicate root-owned fields or fields owned by another subclass. Supported structural columns with no `owning_class_id`, such as the synthetic primary key, MUST be assigned according to their structural role. Unsupported non-discriminator, non-primary-key columns without an assignable ownership role MUST be rejected with a typed error before rendering.

#### Scenario: Root-owned attribute renders only on the root entity

- GIVEN a supported discriminator-backed `Vehicle` table with root-owned column `vin`
- WHEN inheritance domain sources are emitted
- THEN `Vehicle.java` declares field `vin`
- AND no subclass entity declares field `vin`

#### Scenario: Subclass-owned attribute renders only on the matching subclass entity

- GIVEN a supported discriminator-backed `Vehicle` table with `car`-owned column `door_count` and `truck`-owned column `payload_capacity`
- WHEN inheritance domain sources are emitted
- THEN `Car.java` declares `doorCount` and does not declare `payloadCapacity`
- AND `Truck.java` declares `payloadCapacity` and does not declare `doorCount`
- AND `Vehicle.java` declares neither subclass-owned field

### Requirement: Inheritance Artifact Boundary and Deterministic File Order

For a supported discriminator-backed `Table`, `generate_table_sources` MUST emit only the root entity, concrete subclass entities, and the root repository. It MUST emit files in deterministic order: root entity first, subclass entities in `Table.source_class_ids` order excluding the root class id, and root repository last. It MUST NOT emit request DTOs, response DTOs, services, controllers, subclass repositories, shared error sources, configuration, OpenAPI, Postman, Domain Manifest, or any non-Java infrastructure artifact for the discriminator-backed table.

#### Scenario: Inheritance files are emitted in deterministic hierarchy order

- GIVEN a supported discriminator-backed `Vehicle` table with `source_class_ids=("vehicle", "car", "truck")`
- WHEN `generate_table_sources` is invoked twice for the same table
- THEN both invocations return files in the exact order `domain/Vehicle.java`, `domain/Car.java`, `domain/Truck.java`, `persistence/VehicleRepository.java`
- AND each corresponding file's source text is byte-identical across invocations

#### Scenario: DTO service controller and subclass repositories are omitted

- GIVEN a supported discriminator-backed `Vehicle` table with subclasses `Car` and `Truck`
- WHEN `generate_table_sources` is invoked
- THEN no emitted path is under `application/`, `application/dto/`, `api/`, `errors/`, `validation/`, or `config/`
- AND no emitted path ends with `CarRepository.java` or `TruckRepository.java`

### Requirement: Root Repository for Inheritance Hierarchy

For a supported discriminator-backed `Table`, the generator MUST produce exactly one Spring Data JPA repository interface for the root entity type and UUID id type. The repository MUST be named from the root entity Java class name and MUST rely on JPA polymorphism rather than generated subclass repositories.

#### Scenario: Root repository is parameterized by the root entity

- GIVEN a supported discriminator-backed `Vehicle` table with subclasses `Car` and `Truck`
- WHEN repository source is emitted
- THEN `persistence/VehicleRepository.java` declares `VehicleRepository`
- AND the repository extends a Spring Data repository parameterized with `<Vehicle, UUID>`
- AND no repository source is emitted for `Car` or `Truck`

### Requirement: Exact Backward Compatibility for Non-Discriminator Table Generation

For any table with no discriminator inheritance metadata, `generate_table_sources(table, *, base_package)` MUST preserve the existing non-inheritance contract exactly. It MUST emit the same six files, in the same order, at the same paths, with byte-identical Java source text compared to the pre-inheritance implementation for the same supported non-discriminator input.

#### Scenario: Non-discriminator table output remains byte-identical

- GIVEN a supported non-discriminator `Product` table that generated six files before inheritance support
- WHEN `generate_table_sources` is invoked after inheritance support is added
- THEN exactly the same six paths are emitted in the same order
- AND every emitted file's Java source text is byte-identical to the pre-inheritance output

### Requirement: Whole-Model Source Aggregation

The system MUST provide a public pure function `generate_model_sources(model: RelationalModel, *, base_package: str = "com.modelia.generated") -> GeneratedSources` that accepts a complete `RelationalModel` and returns one in-memory `GeneratedSources` aggregate. The aggregate MUST contain generated files in this deterministic order: all table artifacts in `model.tables` order while preserving each table generator's internal file order; then all enum artifacts in `model.enum_types` order; then shared error artifacts; then the project singleton `src/main/resources/application.yml`. The aggregate MUST NOT sort artifacts alphabetically or reorder files beyond this contract.

#### Scenario: Normal model aggregates tables then enums then globals

- GIVEN a `RelationalModel` with tables `(Product, Order)` and enum types `(order_status,)`
- WHEN `generate_model_sources(model, base_package="com.example.generated")` is invoked
- THEN the returned `GeneratedSources.files` order starts with all `Product` table files in that table generator's order
- AND then contains all `Order` table files in that table generator's order
- AND then contains the `order_status` enum file
- AND then contains the shared error files
- AND ends with `src/main/resources/application.yml`

#### Scenario: Inheritance table keeps its table generator boundary inside the aggregate

- GIVEN a `RelationalModel` whose first table is a supported discriminator-backed `Vehicle` table and whose second table is a non-discriminator `Product` table
- WHEN `generate_model_sources(model)` is invoked
- THEN the aggregate begins with the `Vehicle` table artifacts exactly as `generate_table_sources(Vehicle)` defines them, including root entity, subclass entities, and root repository ordering
- AND the `Product` table artifacts appear only after all `Vehicle` table artifacts
- AND no inheritance DTO, service, controller, subclass repository, filtering API, or inheritance API expansion is added by whole-model aggregation

### Requirement: Whole-Model Singleton Artifacts

For every successful `generate_model_sources` invocation, the system MUST include the shared error source set exactly once and the project configuration source set exactly once. The shared error generation contract MUST receive the caller's `base_package`; the project configuration contract MUST remain package-independent. An empty `RelationalModel` MUST still return the project-level global artifacts only.

#### Scenario: Shared errors and application YAML are included exactly once

- GIVEN a `RelationalModel` with multiple tables and multiple enum types
- WHEN `generate_model_sources(model, base_package="com.example.generated")` is invoked
- THEN exactly one `ResourceNotFoundException.java` path is present
- AND exactly one `GlobalExceptionHandler.java` path is present
- AND exactly one `src/main/resources/application.yml` path is present
- AND shared error package paths and content use `com.example.generated`
- AND `application.yml` contains no Java package dependency

#### Scenario: Empty model yields globals

- GIVEN an empty `RelationalModel` with no tables and no enum types
- WHEN `generate_model_sources(model)` is invoked
- THEN the returned `GeneratedSources` contains only the shared error files and `src/main/resources/application.yml`
- AND the shared error files appear before `src/main/resources/application.yml`

### Requirement: Whole-Model Duplicate Path Rejection

Before returning a whole-model aggregate, the system MUST reject any exact duplicate `GeneratedFile.path` across all generated table, enum, shared error, and project configuration artifacts. The same atomic, typed rejection MUST apply to `generate_project_sources`, across the `generate_model_sources` artifacts and the three scaffold artifacts combined. Duplicate path rejection MUST raise a typed generator error under the existing `UngeneratableSourceError` family (`GeneratedSourcePathCollisionError`). On duplicate path failure, the system MUST NOT return a partial `GeneratedSources`, MUST NOT overwrite any file, MUST NOT deduplicate files, and MUST NOT silently keep the first or last occurrence.

(Previously: the rejection was specified for the whole-model aggregate only; `generate_project_sources` did not exist. Note: with the current renderers a model class cannot produce a scaffold path, since even a UML class named `Application` renders to `domain/Application.java`, so the project-level check is a structural invariant and is specified through injected duplicates.)

#### Scenario: Duplicate exact output path fails atomically

- GIVEN a `RelationalModel` containing two source artifacts that would produce the same exact generated output path
- WHEN `generate_model_sources(model)` is invoked
- THEN a typed duplicate-path generator error is raised
- AND no `GeneratedSources` aggregate is returned
- AND no partial result is exposed to the caller

#### Scenario: Project aggregate rejects two generated files sharing an exact path

- GIVEN two generated files that share an exact path, presented to the project aggregate's combination step
- WHEN they are combined by the project aggregate
- THEN `GeneratedSourcePathCollisionError` is raised
- AND no `GeneratedSources` is returned and no partial result is exposed

#### Scenario: Model-level duplicate propagates through the project aggregate

- GIVEN a `RelationalModel` whose model artifacts already contain a duplicate exact path
- WHEN `generate_project_sources(model)` is invoked
- THEN the same typed `GeneratedSourcePathCollisionError` is raised
- AND no scaffold file or partial aggregate is returned

### Requirement: Whole-Model Determinism and Purity

`generate_model_sources` MUST be a pure function of the provided `RelationalModel` and `base_package`. For the same inputs, it MUST return equal `GeneratedSources` values with identical file paths, identical file ordering, and byte-identical content. It MUST NOT write or materialize files, inspect environment variables, open database connections, access the network, run subprocesses, compile Java, execute Gradle, use Docker, or invoke validation routines.

#### Scenario: Repeated whole-model generation is deterministic

- GIVEN the same `RelationalModel` value and the same `base_package`
- WHEN `generate_model_sources` is invoked twice
- THEN both returned `GeneratedSources` values are equal
- AND every corresponding file has the same path and byte-identical content

#### Scenario: Whole-model generation remains filesystem-free and runtime-free

- GIVEN a valid in-memory `RelationalModel` and no database or project directory available to the test process
- WHEN `generate_model_sources(model)` is invoked
- THEN generation succeeds using only in-memory inputs
- AND no filesystem write, generated-project materialization, environment read, database access, network access, subprocess, Java compilation, Gradle execution, Docker interaction, or validation call occurs

### Requirement: Existing Generator Contracts Are Preserved

Whole-model generation MUST preserve all existing table, enum, shared-error, and project-configuration generator contracts. It MUST NOT change lower-level generated paths, generated content, file ordering inside each lower-level generator result, supported inheritance table behavior, unsupported-shape typed errors, package propagation rules, or project configuration placeholders. `generate_model_sources` MUST NOT add OpenAPI, Postman, Domain Manifest, filtering/search metadata, generated filtering APIs, inheritance API expansion, frontend output, mobile output, Java `config/` classes, filesystem writing, project materialization, compilation, Docker behavior, or any Gradle artifact (`build.gradle`, `settings.gradle`, wrapper), and its output MUST remain byte-identical to its output before the project scaffold change. This prohibition is scoped to `generate_model_sources`. Emitting Gradle build text from a different entry point (`generate_project_scaffold_sources`, `generate_project_sources`) is not "Gradle behavior" in the sense of this requirement, because no Gradle is executed, and it does not alter any lower-level generator contract.

(Previously: the ban on Docker and Gradle artifacts was stated for whole-model generation in general, with no distinction between `generate_model_sources` and later project-level entry points.)

#### Scenario: Lower-level generator outputs are unchanged inside the aggregate

- GIVEN a supported `Table`, a supported `EnumType`, the shared error source set, and the project configuration source set
- WHEN each lower-level generator is invoked directly and the same inputs are also generated through `generate_model_sources`
- THEN the corresponding files inside the whole-model aggregate have the same paths, ordering within their own generator boundary, and byte-identical content as the direct lower-level generator outputs
- AND the whole-model aggregate contains no out-of-scope OpenAPI, Postman, Manifest, filtering, frontend, mobile, Java `config/`, materialization, compilation, Docker, or Gradle artifact

#### Scenario: generate_model_sources output contains no scaffold path

- GIVEN any valid `RelationalModel` and `base_package`
- WHEN `generate_model_sources` is invoked
- THEN no returned path equals `build.gradle` or `settings.gradle`, and no returned path is the root-package `Application.java`
- AND the returned files and their order are identical to the pre-change output for the same input

#### Scenario: Project-level Gradle text does not change the model aggregate

- GIVEN `generate_project_sources(model, base_package=...)` and `generate_model_sources(model, base_package=...)` for the same inputs
- WHEN both are invoked
- THEN the leading files of the project aggregate equal the model aggregate exactly
- AND only the trailing three scaffold files are added by the project entry point
### Requirement: Project Scaffold Generation

The system MUST provide a pure function `generate_project_scaffold_sources(*, base_package) -> GeneratedSources`, independent of any `Table`, `EnumType` or relational model, that returns exactly three `GeneratedFile`s in this fixed order: `build.gradle`, `settings.gradle`, `src/main/java/<pkg path>/Application.java`, where `<pkg path>` is the validated `base_package` with dots replaced by directory separators. It MUST NOT emit a `.gitignore`, a Gradle wrapper, a Dockerfile, or any other file.

`build.gradle` MUST: apply the `java` plugin and the `org.springframework.boot` plugin at the pinned Spring Boot version; configure a Java toolchain at the pinned Java version (21); declare `mavenCentral()` as the only repository; import the Boot BOM with `implementation platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)`; declare the starters `spring-boot-starter-webmvc`, `spring-boot-starter-data-jpa` and `spring-boot-starter-validation`; declare `runtimeOnly 'org.postgresql:postgresql'`; set `group` equal to `base_package`; and set `version = '0.0.1-SNAPSHOT'`. It MUST NOT declare springdoc/OpenAPI or the `io.spring.dependency-management` plugin. `settings.gradle` MUST set `rootProject.name = 'generated-backend'`. `Application.java` MUST declare `package <base_package>;`, annotate the class `Application` with `@SpringBootApplication`, and declare a `main` method that calls `SpringApplication.run`.

`Application` is NOT a `config/` class. It MUST live in the root base package because `@SpringBootApplication` scans its own package and its sub-packages, so `domain`, `persistence`, `application`, `api` and `errors` are only discovered from the root.

The scaffold MUST NOT contain a hardcoded host, port, URL, credential or absolute path. The pinned Spring Boot and Java versions (and any pinned Gradle runner version) MUST be sourced from one module, so that a version bump changes exactly one place. An invalid `base_package` MUST be rejected by the existing base-package validation, with the same error the other entry points raise, and no file MUST be returned.

#### Scenario: Scaffold yields exactly three files in fixed order

- GIVEN `generate_project_scaffold_sources(base_package="com.example.generated")`
- WHEN the returned file paths are inspected
- THEN the paths are exactly `build.gradle`, `settings.gradle`, `src/main/java/com/example/generated/Application.java`, in that order
- AND no `.gitignore`, Gradle wrapper file or Dockerfile path is present

#### Scenario: Single-segment base package places Application at the shortest path

- GIVEN `generate_project_scaffold_sources(base_package="app")`
- WHEN the returned file paths are inspected
- THEN the third path is `src/main/java/app/Application.java`

#### Scenario: Repeated scaffold generation is byte-identical

- GIVEN the same `base_package`
- WHEN `generate_project_scaffold_sources` is invoked twice
- THEN both returned `GeneratedSources` values are equal
- AND every corresponding file has the same path and byte-identical content

#### Scenario: build.gradle declares the verified plugins, toolchain and repository

- GIVEN `generate_project_scaffold_sources(base_package="com.example.generated")`
- WHEN the content of `build.gradle` is inspected
- THEN it applies the `java` and `org.springframework.boot` plugins with the pinned Boot version
- AND it sets the Java toolchain to 21 and declares only `mavenCentral()` as a repository
- AND it contains `implementation platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)`

#### Scenario: build.gradle declares the verified starters and driver only

- GIVEN the same scaffold
- WHEN the dependency declarations in `build.gradle` are inspected
- THEN `spring-boot-starter-webmvc`, `spring-boot-starter-data-jpa` and `spring-boot-starter-validation` are declared
- AND `runtimeOnly 'org.postgresql:postgresql'` is declared
- AND the content contains no `springdoc` and no `io.spring.dependency-management`

#### Scenario: build.gradle carries group and version, settings.gradle carries the project name

- GIVEN `generate_project_scaffold_sources(base_package="com.example.generated")`
- WHEN `build.gradle` and `settings.gradle` are inspected
- THEN `build.gradle` sets `group` to `com.example.generated` and `version = '0.0.1-SNAPSHOT'`
- AND `settings.gradle` sets `rootProject.name = 'generated-backend'`

#### Scenario: Application.java is a Spring Boot entry point in the root package

- GIVEN `generate_project_scaffold_sources(base_package="com.example.generated")`
- WHEN the content of `Application.java` is inspected
- THEN it declares `package com.example.generated;`, a class `Application` annotated `@SpringBootApplication`, and a `main` method calling `SpringApplication.run`
- AND its package equals the `group` in `build.gradle`, so component scanning covers every generated layer package

#### Scenario: No scaffold file hardcodes deployable values

- GIVEN the three scaffold files
- WHEN their content is scanned
- THEN no file contains a URL scheme (`http://`, `https://`), `localhost`, an IP address, a port number, a username or password value, or an absolute filesystem path
- AND `build.gradle` names no repository other than `mavenCentral()`

#### Scenario: Pinned versions come from one module

- GIVEN the pinned Spring Boot and Java versions declared in the single versions module
- WHEN the scaffold is generated and the emit package sources are inspected
- THEN the Boot version in `build.gradle` equals the module's Boot value and the toolchain version equals its Java value
- AND each pinned version literal is defined in that module only, not in the renderer, templates or other emit modules

#### Scenario: Invalid base package is rejected without output

- GIVEN a `base_package` that fails the existing validation (for example `Com.Example`, `com-example`, `com..example`, an empty string, or a Java-invalid leading digit segment)
- WHEN `generate_project_scaffold_sources` is invoked
- THEN it raises the same error the existing base-package validation raises for the other entry points
- AND no `GeneratedSources` is returned

#### Scenario: Project aggregate is the model aggregate followed by the scaffold

- GIVEN a valid `RelationalModel` and `base_package="com.example.generated"`
- WHEN `generate_project_sources(model, base_package="com.example.generated")` is invoked
- THEN the returned files are exactly the files of `generate_model_sources(model, base_package="com.example.generated")` in their own order, followed by the three scaffold files in scaffold order
- AND the three trailing files are identical to the output of `generate_project_scaffold_sources` for the same `base_package`
- AND `generate_model_sources` returns the same output as before this change

#### Scenario: Empty model still yields the full project

- GIVEN an empty `RelationalModel`
- WHEN `generate_project_sources(model, base_package="com.example.generated")` is invoked
- THEN the returned files are the shared error files, `src/main/resources/application.yml`, then the three scaffold files

#### Scenario: Project aggregate rejects an invalid base package

- GIVEN a valid `RelationalModel` and an invalid `base_package`
- WHEN `generate_project_sources` is invoked
- THEN the same base-package validation error is raised
- AND no `GeneratedSources` is returned

