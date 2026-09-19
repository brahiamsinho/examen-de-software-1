# Relational Mapping Specification

## Purpose

Defines the pure, deterministic `CanonicalUmlModel → RelationalModel` pipeline (spec §21): the `RelationalModel` domain structure and the `RelationalMapper` that produces it. No persistence, DB, Django, or Java/Spring Boot concerns belong here.

## Requirements

### Requirement: RelationalModel Domain Structure

The system MUST provide frozen, DB-free, framework-agnostic dataclasses: `Table`, `Column`, `PrimaryKey`, `ForeignKey`, `UniqueConstraint`, `Index`, `EnumType`, and `RelationalModel` (aggregating `tables` and `enum_types`). These MUST NOT import Django, any DB driver, or Java/Spring Boot code.

#### Scenario: Domain module has zero framework imports
- GIVEN the `relational_mapping` domain module source
- WHEN its imports are inspected
- THEN no `django`, DB driver, or Java/Spring code is imported

### Requirement: Class-to-Table Mapping

Each `UmlClass` MUST map to exactly one `Table` named after the class, except a subclass in a Single Table hierarchy (see below), which contributes columns to its root ancestor's table instead of a new table.

#### Scenario: Simple class becomes a table
- GIVEN a `CanonicalUmlModel` with one class `Order` and no generalization
- WHEN `map_to_relational(model)` is called
- THEN the result contains exactly one `Table` named `Order`

### Requirement: Attribute-to-Column Mapping

Each `UmlAttribute` MUST map to one `Column` on its owning table, preserving name and a relational type derived from its `AttributeType` (primitive or `EnumerationRef`).

#### Scenario: Primitive attribute becomes a typed column
- GIVEN a class with attribute `total: DECIMAL`
- WHEN mapped
- THEN the table has a `Column` named `total` with a decimal relational type

### Requirement: Unconditional Synthetic UUID Primary Key

Every `Table` MUST have exactly one synthetic UUID `PrimaryKey` column, generated unconditionally regardless of any `UmlAttribute`. No `UmlAttribute` or `UmlClass` metadata drives PK selection.

#### Scenario: Every table has a UUID PK
- GIVEN any `CanonicalUmlModel` with at least one class
- WHEN mapped
- THEN every resulting `Table` has exactly one `PrimaryKey` column of UUID type, independent of the class's attributes

### Requirement: Enumeration-to-ENUM Type Mapping

Each `Enumeration` MUST map to one `EnumType` using native PostgreSQL `ENUM` semantics, with values equal to the ordered literal names. Any attribute typed `EnumerationRef` MUST map to a `Column` referencing that `EnumType`, never a lookup table or `VARCHAR` + `CHECK`.

#### Scenario: Enumeration produces a native ENUM type
- GIVEN an `Enumeration` with literals `ACTIVE`, `INACTIVE`
- WHEN mapped
- THEN the result contains one `EnumType` with values `["ACTIVE", "INACTIVE"]`, and any attribute of that type maps to a `Column` referencing it

### Requirement: Single Table Inheritance for Generalization

A `GENERALIZATION` chain (child = source, parent = target) MUST map using Single Table strategy: all classes in the chain share the root ancestor's `Table`, subclass-only attributes become nullable columns on that table, and the table gains a discriminator `Column` identifying the concrete class per row.

#### Scenario: Subclass columns merge into the root table
- GIVEN class `Vehicle` and subclass `Car` (source=Car, target=Vehicle)
- WHEN mapped
- THEN one `Table` named `Vehicle` exists containing `Vehicle`'s columns, `Car`'s columns (nullable), and a discriminator column; no separate `Car` table exists

### Requirement: Mapper Rejects Multi-Parent Generalization

`map_to_relational` MUST raise an error, and MUST NOT silently select one parent, when a class has more than one `GENERALIZATION` relationship as source. This is the mapper's second line of defense; the `MULTI_PARENT_GENERALIZATION` validation rule is the first.

#### Scenario: Multi-parent model raises instead of mapping
- GIVEN a class `C` with two `GENERALIZATION` relationships as source, targeting `A` and `B`
- WHEN `map_to_relational(model)` is called
- THEN it raises an error and produces no `RelationalModel`

### Requirement: Composition Maps to Mandatory Owning FK

A `COMPOSITION` relationship MUST map to a `ForeignKey` column on the part's table, referencing the whole's table, with `NOT NULL` and `ON DELETE CASCADE`, regardless of the relationship's declared multiplicity.

#### Scenario: Composition FK is always NOT NULL CASCADE
- GIVEN a `COMPOSITION` from `Order` (whole) to `OrderLine` (part) with `lower=0` on the whole-side endpoint
- WHEN mapped
- THEN `OrderLine`'s table has a `NOT NULL`, `ON DELETE CASCADE` `ForeignKey` to `Order`

### Requirement: Association/Aggregation Map to Plain FK or Join Table

An `ASSOCIATION` or `AGGREGATION` relationship MUST map to a nullable `ForeignKey` on the many-multiplicity side's table when exactly one end is many; when both ends are many, it MUST map to a join table with two `ForeignKey` columns, one per end.

#### Scenario: One-to-many association produces a single FK
- GIVEN an `ASSOCIATION` where `Customer` is 1 and `Order` is many
- WHEN mapped
- THEN `Order`'s table has a nullable `ForeignKey` to `Customer`; no join table is created

#### Scenario: Many-to-many association produces a join table
- GIVEN an `ASSOCIATION` where both `Student` and `Course` ends are many
- WHEN mapped
- THEN a join table exists with a `ForeignKey` to `Student` and a `ForeignKey` to `Course`

### Requirement: FK Nullability Derived from Multiplicity Lower Bound

For any FK produced by an association or aggregation, nullability MUST be derived from the `lower` bound of the multiplicity on the endpoint attached to the referenced (non-FK-holding) class: `lower == 0` MUST produce a nullable FK column; `lower >= 1` MUST produce a `NOT NULL` FK column. This rule does not apply to composition FKs, which are always `NOT NULL` per the requirement above.

#### Scenario: Optional referenced end produces nullable FK
- GIVEN an `ASSOCIATION` where `Order` (many side) references `Customer` (one side, `lower=0`)
- WHEN mapped
- THEN `Order`'s FK column to `Customer` is nullable

#### Scenario: Mandatory referenced end produces NOT NULL FK
- GIVEN an `ASSOCIATION` where `Order` (many side) references `Customer` (one side, `lower=1`)
- WHEN mapped
- THEN `Order`'s FK column to `Customer` is `NOT NULL`

### Requirement: Self-Referencing Relationships Use Generic Rules

A relationship where `source.class_id == target.class_id` MUST map using the same kind-specific rule (composition, association/aggregation, generalization) as a non-self relationship, placing the FK column on the same table it references, with no additional table introduced solely due to self-reference.

#### Scenario: Self-referencing association produces a self-FK
- GIVEN a self-referencing `ASSOCIATION` on class `Employee` (manager relationship), one-to-many
- WHEN mapped
- THEN `Employee`'s table gains one nullable `ForeignKey` column referencing `Employee` itself; no second table is created

### Requirement: Deterministic Mapping

`map_to_relational` MUST be a pure function: given the same `CanonicalUmlModel`, it MUST always produce a structurally identical `RelationalModel`, with tables, columns, and constraints in a stable, deterministic order.

#### Scenario: Repeated mapping is identical
- GIVEN a fixed `CanonicalUmlModel`
- WHEN `map_to_relational(model)` is called twice
- THEN both `RelationalModel` results are structurally equal

### Requirement: Attribute Column Ownership Metadata

The system MUST expose `owning_class_id` on every `Column` value, and it MUST set `owning_class_id` to the UML class id that owns the source UML attribute only when the column is derived from a `UmlAttribute`. The system MUST keep `source_element_id` as the source UML attribute id and MUST NOT use `source_element_id` as a substitute for class ownership.

#### Scenario: Root attribute column carries root class ownership

- GIVEN a `CanonicalUmlModel` with a root class `Vehicle` containing attribute `vin`
- WHEN the model is mapped to a `RelationalModel`
- THEN the `vin` column has `source_element_id` equal to the `vin` attribute id
- AND the `vin` column has `owning_class_id` equal to the `Vehicle` class id

#### Scenario: Subclass attribute column carries subclass ownership after Single Table flattening

- GIVEN a `CanonicalUmlModel` with class `Vehicle`, subclass `Car`, and subclass attribute `horsepower`
- WHEN the model is mapped to a `RelationalModel`
- THEN one root table named `Vehicle` contains the `horsepower` column
- AND the `horsepower` column has `source_element_id` equal to the `horsepower` attribute id
- AND the `horsepower` column has `owning_class_id` equal to the `Car` class id

### Requirement: Non-Attribute Columns Have No Class Ownership Metadata

The system MUST leave `owning_class_id` as `None` for columns that are not derived from UML attributes, including synthetic primary key columns, Single Table discriminator columns, relationship foreign-key columns, and many-to-many join-table columns.

#### Scenario: Synthetic id and discriminator columns have no owning class

- GIVEN a `CanonicalUmlModel` with a Single Table hierarchy from `Vehicle` to `Car`
- WHEN the model is mapped to a `RelationalModel`
- THEN the root table's synthetic `id` column has `owning_class_id` equal to `None`
- AND the root table's discriminator `class_type` column has `owning_class_id` equal to `None`

#### Scenario: Relationship foreign key column has no owning class

- GIVEN a `CanonicalUmlModel` with a one-to-many association from `Customer` to `Order`
- WHEN the model is mapped to a `RelationalModel`
- THEN the generated relationship foreign-key column on the `Order` table has `owning_class_id` equal to `None`

#### Scenario: Many-to-many join-table columns have no owning class

- GIVEN a `CanonicalUmlModel` with a many-to-many association between `Student` and `Course`
- WHEN the model is mapped to a `RelationalModel`
- THEN the generated join table's foreign-key columns have `owning_class_id` equal to `None`
