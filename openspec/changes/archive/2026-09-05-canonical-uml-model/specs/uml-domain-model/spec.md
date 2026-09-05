# UML Domain Model Specification

## Purpose

Defines `CanonicalUmlModel` (alias `UmlModel`) as the single convergence point every UML input channel (manual, voice, image, XMI) normalizes to. It is a DB-free, framework-agnostic structure of classes, enumerations, relationships, and generation metadata.

## Requirements

### Requirement: Canonical Model Structure

The system MUST expose one `CanonicalUmlModel` dataclass, exported also as `UmlModel`, aggregating `classes`, `enumerations`, `relationships`, and `generation_metadata` as the sole structure every manual, voice, image, and XMI input path normalizes to.

#### Scenario: Alias resolves to the same type
- GIVEN a `CanonicalUmlModel` instance built by any input channel
- WHEN it is referenced through the `UmlModel` alias
- THEN both names resolve to the identical object and type

### Requirement: Class Element Composition

A `Class` element MUST have an `id`, a `name`, an ordered `attributes` list, an ordered `operations` list, and MAY declare per-member `visibility` (public/private/protected/package).

#### Scenario: Class with attributes and operations
- GIVEN a `CanonicalUmlModel` with one class `Order`
- WHEN the class declares two attributes and one operation
- THEN the model exposes `Order` with both attributes and the operation in declaration order

### Requirement: Closed Attribute Type Union

An attribute's type MUST be exactly one of eight primitives (`String`, `Text`, `Integer`, `Long`, `Decimal`, `Boolean`, `Date`, `DateTime`) or an `EnumerationRef(enumeration_id)`. The system MUST NOT accept a class reference as an attribute type.

#### Scenario: Primitive type accepted
- GIVEN an attribute typed as `Integer`
- WHEN the `CanonicalUmlModel` is constructed
- THEN the attribute type is accepted as a valid primitive

#### Scenario: Class-typed attribute rejected
- GIVEN an attempt to type an attribute as another `Class`
- WHEN the `CanonicalUmlModel` attribute type is set
- THEN the system MUST reject the class type, since class-to-class links MUST be expressed only as a `Relationship`

### Requirement: Enumeration as Top-Level Element

An `Enumeration` MUST be a top-level sibling of `Class` in `CanonicalUmlModel.enumerations`, with an `id`, a `name`, and an ordered list of `EnumerationLiteral` (`id`, `name`, optional `value`). Attribute references to an enumeration MUST use `EnumerationRef(enumeration_id)`, never the enumeration's name.

#### Scenario: Attribute references enumeration by id
- GIVEN an enumeration `OrderStatus` with id `enum-1` and an attribute typed `EnumerationRef("enum-1")`
- WHEN the enumeration is renamed to `Status`
- THEN the attribute's reference remains valid because it resolves by id, not by name

#### Scenario: Literal order preserved
- GIVEN an enumeration with literals declared in order `DRAFT, SENT, PAID`
- WHEN the enumeration is read back from the model
- THEN the literals are returned in the same declared order

### Requirement: Relationship and Structured Multiplicity

A `Relationship` MUST declare a `kind` (association, aggregation, composition, or generalization), source and target endpoint ids, and a `Multiplicity(lower: int, upper: int | None)` per endpoint, where `upper=None` means unbounded. The system MUST provide pure `parse`/`format` helpers converting between `Multiplicity` and UML string notation (`"1"`, `"0..1"`, `"0..*"`, `"1..*"`).

#### Scenario: Multiplicity parse/format round-trip
- GIVEN the UML string `"0..*"`
- WHEN it is parsed into a `Multiplicity` and then formatted back to a string
- THEN the result equals `"0..*"` and the parsed value is `Multiplicity(lower=0, upper=None)`

#### Scenario: Bounded multiplicity round-trip
- GIVEN the UML string `"1..*"` parsed to `Multiplicity`
- WHEN formatted back
- THEN the output string is `"1..*"`

### Requirement: Generation Metadata Separation

`CanonicalUmlModel` MUST expose a `generation_metadata` container keyed by element id, structurally separate from every UML element dataclass; pure UML elements MUST NOT embed generation-specific fields.

#### Scenario: Metadata does not alter element shape
- GIVEN a class with an entry in `generation_metadata` keyed by its id
- WHEN the class's attributes are inspected
- THEN no generation-specific field is present on the class or its attributes

### Requirement: Flat Namespace (No Package)

This cycle's `CanonicalUmlModel` MUST NOT include a `Package` element; all classes and enumerations MUST resolve within a single flat namespace at the model root.

#### Scenario: No package nesting
- GIVEN a `CanonicalUmlModel` with two classes
- WHEN their names are compared for uniqueness
- THEN uniqueness is evaluated against the model root, with no package-qualified name
