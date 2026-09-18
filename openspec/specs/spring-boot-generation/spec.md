# Spring Boot Generation Specification

## Purpose

Defines the pure, deterministic `Table -> Java source` emission for one relational table's JPA entity (`domain/`) and Spring Data JPA repository (`persistence/`), per spec §22's mandatory generated-backend stack. No relationships, inheritance, enums, compilation, or layers beyond `domain/`+`persistence/` belong to this slice.

## Requirements

### Requirement: JPA Entity Generation from a Table

For a `Table` with only scalar columns (no FK, no `discriminator_column`, no `enum_type_name`), the system MUST produce Java source text for one `@Entity`-annotated class in the `domain/` layer, using Java 21, Jakarta Validation, and Jackson annotations as applicable, with one field per `Column` and the synthetic UUID `primary_key` mapped as the `@Id` field.

#### Scenario: Table with scalar columns yields an entity class
- GIVEN a `Table` named `Product` with a UUID `PrimaryKey` and scalar `Column`s `name: VARCHAR`, `price: NUMERIC`
- WHEN the generator emits the entity
- THEN the output is Java source text for a class `Product` annotated `@Entity`, with an `@Id` UUID field and one field per column, each correctly typed per the column-type mapping

### Requirement: Spring Data JPA Repository Generation from a Table

For the same `Table` input, the system MUST produce Java source text for one Spring Data JPA repository interface in the `persistence/` layer, extending a Spring Data repository parameterized by the entity type and its UUID id type.

#### Scenario: Table yields a matching repository interface
- GIVEN the `Product` table from above
- WHEN the generator emits the repository
- THEN the output is Java source text for `ProductRepository`, an interface extending a Spring Data JPA repository parameterized `<Product, UUID>`

### Requirement: Deterministic Column-Type-to-Java-Type Mapping

The system MUST map every non-enum `ColumnType` to exactly one Java type and JPA/Jakarta annotation set, applied consistently to every column of that type:

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

Every mapped field MUST carry `@Column(nullable = false)` (or the Jakarta `@NotNull` equivalent) unless `Column.nullable` is `True`, in which case the field MUST omit the not-null constraint.

#### Scenario: Nullable column omits the not-null constraint
- GIVEN a `Column` named `notes` of type `TEXT` with `nullable=True`
- WHEN the entity field for `notes` is emitted
- THEN the field carries no not-null constraint

#### Scenario: NUMERIC column carries precision and scale
- GIVEN a `Column` named `price` of type `NUMERIC` with `precision=10, scale=2`
- WHEN the entity field for `price` is emitted
- THEN the field is typed `BigDecimal` and its `@Column` annotation states `precision = 10, scale = 2`

### Requirement: Generator Purity

The generator MUST be a pure function of its `Table` input to Java source text. It MUST NOT call `relational_mapping`'s `validate()` or any validation routine, and MUST NOT open, query, or otherwise touch any database connection.

#### Scenario: Generation succeeds with no DB and no validation call
- GIVEN a valid in-memory `Table` and no database connection available in the test process
- WHEN the entity and repository are generated
- THEN generation completes and returns Java source text, with no validation function invoked and no DB access attempted

### Requirement: Rejection of Unsupported Table Shapes

The system MUST raise a typed error, and MUST NOT emit partial or malformed Java source, when the input `Table` contains any relationship, inheritance, or enum construct out of scope for this slice: a non-empty `foreign_keys`, a non-`None` `discriminator_column`, or any `Column` with a non-`None` `enum_type_name`.

#### Scenario: Table with a foreign key is rejected
- GIVEN a `Table` whose `foreign_keys` is non-empty
- WHEN the generator is invoked on it
- THEN it raises a typed error and produces no Java source

#### Scenario: Table with a discriminator column is rejected
- GIVEN a `Table` whose `discriminator_column` is set
- WHEN the generator is invoked on it
- THEN it raises a typed error and produces no Java source

#### Scenario: Table with an enum-typed column is rejected
- GIVEN a `Table` containing a `Column` with `enum_type_name` set
- WHEN the generator is invoked on it
- THEN it raises a typed error and produces no Java source

### Requirement: Deterministic, Repeatable Output

The system MUST produce byte-identical Java source text — same field order, same formatting, same annotations — for the same `Table` input on every invocation.

#### Scenario: Same table produces identical output on repeated calls
- GIVEN the same `Table` value generated twice, independently
- WHEN both entity outputs are compared
- THEN the two Java source texts are byte-identical, including column and field ordering

### Requirement: Package and File Path Layout

Generated files MUST be placed only under the `domain/` and `persistence/` subdirectories of the §22 layout (`domain/persistence/application/api/validation/errors/config`). The `application/`, `api/`, `validation/`, `errors/`, and `config/` subdirectories MUST NOT be produced by this slice.

#### Scenario: Only domain and persistence files are produced
- GIVEN the `Product` table generated end to end
- WHEN the set of emitted file paths is inspected
- THEN exactly one file exists under `domain/` and one under `persistence/`, and no files exist under `application/`, `api/`, `validation/`, `errors/`, or `config/`
