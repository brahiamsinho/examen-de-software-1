# Spring Boot Generation Specification

## Purpose

Defines the pure, deterministic `Table -> Java source` emission for one relational table's JPA entity (`domain/`) and Spring Data JPA repository (`persistence/`), per spec §22's mandatory generated-backend stack. No relationships, inheritance, enums, compilation, or layers beyond `domain/`+`persistence/` belong to this slice.

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

The generator MUST be a pure function of its `Table` input to Java source text. It MUST NOT call `relational_mapping`'s `validate()` or any validation routine, and MUST NOT open, query, or otherwise touch any database connection.

#### Scenario: Generation succeeds with no DB and no validation call
- GIVEN a valid in-memory `Table` and no database connection available in the test process
- WHEN the entity and repository are generated
- THEN generation completes and returns Java source text, with no validation function invoked and no DB access attempted

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

Generated files MUST be placed only under the `domain/`, `persistence/`, `application/`, `application/dto/`, `api/`, and `errors/` subdirectories of the §22 layout (`domain/persistence/application/api/validation/errors/config`). The `validation/` and `config/` subdirectories MUST NOT be produced by this slice. For non-discriminator tables, `generate_table_sources(table, *, base_package)` MUST emit exactly six files per call, in fixed layer order: `domain/<E>.java`, `persistence/<E>Repository.java`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, `api/<E>Controller.java`. For supported discriminator-backed tables, `generate_table_sources(table, *, base_package)` MUST emit only `domain/` entity classes and the root `persistence/` repository according to the inheritance artifact boundary. A separate `generate_shared_error_sources(*, base_package)` entry point, taking no `Table`, MUST emit exactly two per-project files: `errors/ResourceNotFoundException.java` and `errors/GlobalExceptionHandler.java`. `generate_table_sources` MUST NOT emit any file under `errors/`.

(Previously: `generate_table_sources` emitted exactly six files for every accepted table and any table with a discriminator column was rejected.)

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

- GIVEN the `Product` table generated end to end and the shared error sources generated once
- WHEN the combined set of emitted file paths is inspected
- THEN no file exists under `validation/` or `config/`

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

For a supported discriminator-backed `Table`, `generate_table_sources(table, *, base_package)` MUST generate JPA Single Table inheritance domain source plus one root Spring Data repository. The supported shape MUST have a single UUID primary key, a non-empty `source_class_ids` sequence whose first entry is the root class id, a non-`None` `discriminator_column`, discriminator values for every generated hierarchy class id, and only columns that can be assigned to the root entity, a subclass entity, a supported single-column relationship field, an enum field, the synthetic id, or discriminator metadata. The generator MUST use the discriminator column as JPA inheritance metadata and MUST NOT emit it as a normal Java field on any generated class.

#### Scenario: Supported discriminator table yields root entity, subclass entities, and root repository

- GIVEN a `Table` named `Vehicle` with a UUID primary key, `source_class_ids=("vehicle", "car", "truck")`, `discriminator_column="class_type"`, discriminator values for `vehicle`, `car`, and `truck`, root-owned scalar columns, and subclass-owned scalar columns
- WHEN `generate_table_sources` is invoked for the table
- THEN generation succeeds
- AND the emitted files contain `domain/Vehicle.java`, `domain/Car.java`, `domain/Truck.java`, and `persistence/VehicleRepository.java`
- AND no emitted Java class declares a normal field for `class_type`

#### Scenario: Actual discriminator column name is used as metadata

- GIVEN a supported discriminator-backed `Table` whose discriminator column is named `kind`
- WHEN the root entity source is emitted
- THEN the root entity declares discriminator metadata using the name `kind`
- AND no generated entity declares `kind` as a normal Java field

### Requirement: Root and Subclass JPA Inheritance Annotations

For a supported discriminator-backed `Table`, the root entity MUST be annotated with `@Entity`, `@Table(name = "...")`, `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`, and `@DiscriminatorColumn(name = "...")`. The root entity MUST include `@DiscriminatorValue("...")` when `Table.discriminator_values` contains a value for the root class id. The root entity MUST be generated as non-abstract unless later UML metadata explicitly exposes abstract-class semantics. Each subclass entity MUST be annotated with `@Entity` and `@DiscriminatorValue("...")`, MUST extend the root entity Java class, and MUST NOT redeclare the inherited id or root-owned fields.

#### Scenario: Root entity contains Single Table metadata

- GIVEN a supported discriminator-backed `Vehicle` table with discriminator column `class_type` and root discriminator value `VEHICLE`
- WHEN the root entity source is emitted
- THEN `Vehicle.java` contains `@Entity`, `@Table(name = "Vehicle")`, `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`, `@DiscriminatorColumn(name = "class_type")`, and `@DiscriminatorValue("VEHICLE")`
- AND `Vehicle` is not declared `abstract`

#### Scenario: Subclass entity extends the root and declares its discriminator value

- GIVEN the same table has a subclass class id `car` with discriminator value `CAR`
- WHEN the subclass entity source is emitted
- THEN `Car.java` contains `@Entity` and `@DiscriminatorValue("CAR")`
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
