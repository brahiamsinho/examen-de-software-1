# Delta for spring-boot-generation

## MODIFIED Requirements

### Requirement: JPA Entity Generation from a Table

For a `Table`, the system MUST produce Java source text for one `@Entity`-annotated class in the `domain/` layer, using Java 21, Jakarta Validation, and Jackson annotations as applicable, with one field per `Column` and the synthetic UUID `primary_key` mapped as the `@Id` field. A scalar `Column` (no FK, no `enum_type_name`) MUST be typed and annotated per the column-type mapping. A `Column` that is part of a FK on the table being rendered MUST instead be emitted as a relationship field: `@ManyToOne` + `@JoinColumn`, or `@OneToOne` + `@JoinColumn` when the owning `ForeignKey.column_names` exactly match one of the table's own `unique_constraints`, typed with the referenced entity's Java class name derived via `pascal_case(ForeignKey.referenced_table)`. A self-referencing FK (`ForeignKey.referenced_table == table.name`) MUST be accepted and MUST render as an ordinary self-referencing `@ManyToOne`/`@OneToOne` field, not rejected. A `Column` with a non-`None` `enum_type_name` MUST be emitted as a field typed `pascal_case(Column.enum_type_name)` annotated `@Enumerated(EnumType.STRING)`.

(Previously: scoped to "only scalar columns (no FK, no `discriminator_column`, no `enum_type_name`)"; FK and enum columns were out of scope and handled by rejection instead of generation.)

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

### Requirement: Rejection of Unsupported Table Shapes

The system MUST raise a typed error, and MUST NOT emit partial or malformed Java source, when the input `Table` contains a construct out of scope for this slice: a primary key that is not a single UUID column, a non-`None` `discriminator_column`, or a `ForeignKey` whose `column_names` has more than one entry (composite FK). A non-empty `foreign_keys` with only single-column entries, and a `Column` with a non-`None` `enum_type_name`, MUST NOT be rejected — both are supported and MUST be generated per the "JPA Entity Generation from a Table" requirement.

(Previously: rejected any `Table` with a non-empty `foreign_keys` or any `Column` with a non-`None` `enum_type_name`, in addition to non-UUID/composite PK and discriminator; composite FK had no explicit scenario and was covered only implicitly under "any FK rejected".)

#### Scenario: Table with a foreign key is accepted

- GIVEN a `Table` whose `foreign_keys` is non-empty and every `ForeignKey.column_names` has exactly one entry
- WHEN the generator is invoked on it
- THEN it does not raise a rejection error and proceeds to emit the entity with the corresponding relationship field(s)

#### Scenario: Table with a composite foreign key is rejected

- GIVEN a `Table` containing a `ForeignKey` whose `column_names` has more than one entry
- WHEN the generator is invoked on it
- THEN it raises a typed error and produces no Java source

#### Scenario: Table with a discriminator column is rejected

- GIVEN a `Table` whose `discriminator_column` is set
- WHEN the generator is invoked on it
- THEN it raises a typed error and produces no Java source

#### Scenario: Table with an enum-typed column is accepted

- GIVEN a `Table` containing a `Column` with `enum_type_name` set
- WHEN the generator is invoked on it
- THEN it does not raise a rejection error and proceeds to emit the entity with the corresponding enum field

## ADDED Requirements

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
