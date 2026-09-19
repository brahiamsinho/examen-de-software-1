# Delta for Spring Boot Generation

## MODIFIED Requirements

### Requirement: Package and File Path Layout

Generated files MUST be placed only under the `domain/`, `persistence/`, `application/`, `application/dto/`, `api/`, and `errors/` subdirectories of the §22 layout (`domain/persistence/application/api/validation/errors/config`). The `validation/` and `config/` subdirectories MUST NOT be produced by this slice. `generate_table_sources(table, *, base_package)` MUST emit exactly six files per call, in fixed layer order: `domain/<E>.java`, `persistence/<E>Repository.java`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, `api/<E>Controller.java`. A separate `generate_shared_error_sources(*, base_package)` entry point, taking no `Table`, MUST emit exactly two per-project files: `errors/ResourceNotFoundException.java` and `errors/GlobalExceptionHandler.java`. `generate_table_sources` MUST NOT emit any file under `errors/`.

(Previously: only `domain/` and `persistence/` were permitted, `generate_table_sources` emitted exactly two files, and `application/`, `api/`, `errors/` were forbidden outright.)

#### Scenario: A table yields six layered files under domain, persistence, application, and api

- GIVEN the `Product` table generated end to end via `generate_table_sources`
- WHEN the set of emitted file paths is inspected
- THEN exactly six files exist, one each at `domain/`, `persistence/`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, and `api/<E>Controller.java`, in that fixed order

#### Scenario: Error sources are emitted only by the shared entry point

- GIVEN `generate_shared_error_sources(base_package=...)` is invoked
- WHEN the returned files are inspected
- THEN exactly two files exist under `errors/`, and no file under `errors/` is produced by any `generate_table_sources` call

#### Scenario: Validation and config directories remain forbidden

- GIVEN the `Product` table generated end to end and the shared error sources generated once
- WHEN the combined set of emitted file paths is inspected
- THEN no file exists under `validation/` or `config/`

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

## ADDED Requirements

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
