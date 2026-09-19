# Delta for Relational Mapping

## ADDED Requirements

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
